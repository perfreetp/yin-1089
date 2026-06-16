from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from app.models import FollowUpRule, ContactIntervalRule, FollowUpQueue, ContactRecord
from app.models.enums import PatientType, ContactResult, QueueStatus
from app.schemas import FollowUpRuleCreate, FollowUpRuleUpdate
from app.schemas import ContactIntervalRuleCreate, ContactIntervalRuleUpdate
from app.services.base_service import BaseService
from app.config import settings


class RuleEngineService(BaseService[FollowUpRule, FollowUpRuleCreate, FollowUpRuleUpdate]):
    def __init__(self):
        super().__init__(FollowUpRule)
        self.interval_rule_service = ContactIntervalRuleService()

    async def get_applicable_rule(
        self,
        db: AsyncSession,
        *,
        patient_type: PatientType,
        is_retest: bool = False
    ) -> Optional[FollowUpRule]:
        result = await db.execute(
            select(FollowUpRule)
            .filter(
                FollowUpRule.patient_type == patient_type,
                FollowUpRule.is_retest == is_retest,
                FollowUpRule.is_active == True
            )
            .order_by(FollowUpRule.priority.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_all_active_rules(self, db: AsyncSession) -> List[FollowUpRule]:
        result = await db.execute(
            select(FollowUpRule)
            .filter(FollowUpRule.is_active == True)
            .order_by(FollowUpRule.priority.desc())
        )
        return list(result.scalars().all())

    async def calculate_next_follow_up_time(
        self,
        db: AsyncSession,
        *,
        task_id: int,
        patient_type: PatientType,
        is_retest: bool,
        current_round: int
    ) -> tuple[datetime, datetime]:
        rule = await self.get_applicable_rule(
            db,
            patient_type=patient_type,
            is_retest=is_retest
        )

        if rule:
            frequency_days = rule.follow_up_frequency_days
            overdue_hours = rule.overdue_hours
        else:
            frequency_days = 7
            overdue_hours = settings.DEFAULT_OVERDUE_HOURS

        scheduled_time = datetime.now() + timedelta(days=frequency_days * current_round)
        deadline = scheduled_time + timedelta(hours=overdue_hours)

        return scheduled_time, deadline

    async def can_contact_now(
        self,
        db: AsyncSession,
        *,
        queue_id: int,
        contact_result: Optional[ContactResult] = None,
        hospital_id: Optional[int] = None
    ) -> tuple[bool, Optional[str], Optional[datetime]]:
        interval_rule = await self.interval_rule_service.get_applicable_rule(
            db,
            contact_result=contact_result,
            hospital_id=hospital_id
        )

        if not interval_rule:
            return True, None, None

        now = datetime.now()

        current_time_str = now.strftime("%H:%M")
        if current_time_str < interval_rule.time_window_start or current_time_str > interval_rule.time_window_end:
            next_allowed_time = datetime.combine(
                now.date(),
                datetime.strptime(interval_rule.time_window_start, "%H:%M").time()
            )
            if now.time() > datetime.strptime(interval_rule.time_window_start, "%H:%M").time():
                next_allowed_time = next_allowed_time + timedelta(days=1)
            return False, f"不在允许的联系时段内 ({interval_rule.time_window_start}-{interval_rule.time_window_end})", next_allowed_time

        contact_records = await db.execute(
            select(ContactRecord)
            .filter(
                ContactRecord.queue_id == queue_id,
                ContactRecord.contact_time >= now - timedelta(hours=interval_rule.min_interval_hours)
            )
            .order_by(ContactRecord.contact_time.desc())
        )
        recent_contacts = list(contact_records.scalars().all())

        if recent_contacts:
            last_contact = recent_contacts[0]
            next_allowed_time = last_contact.contact_time + timedelta(hours=interval_rule.min_interval_hours)
            return False, f"距离上次联系不足{interval_rule.min_interval_hours}小时", next_allowed_time

        today_start = datetime.combine(now.date(), datetime.min.time())
        today_end = datetime.combine(now.date(), datetime.max.time())

        today_count_result = await db.execute(
            select(func.count(ContactRecord.id))
            .filter(
                ContactRecord.queue_id == queue_id,
                ContactRecord.contact_time >= today_start,
                ContactRecord.contact_time <= today_end
            )
        )
        today_count = today_count_result.scalar_one()

        if today_count >= interval_rule.max_daily_attempts:
            next_allowed_time = datetime.combine(now.date() + timedelta(days=1), datetime.min.time())
            return False, f"今日联系次数已达上限 ({interval_rule.max_daily_attempts}次)", next_allowed_time

        total_count_result = await db.execute(
            select(func.count(ContactRecord.id))
            .filter(ContactRecord.queue_id == queue_id)
        )
        total_count = total_count_result.scalar_one()

        if total_count >= interval_rule.max_total_attempts:
            return False, f"总联系次数已达上限 ({interval_rule.max_total_attempts}次)", None

        return True, None, None

    async def check_overdue(
        self,
        db: AsyncSession,
        *,
        queue: FollowUpQueue
    ) -> bool:
        now = datetime.now()
        if queue.deadline and queue.deadline < now and queue.status not in [QueueStatus.COMPLETED, QueueStatus.CANCELLED]:
            return True
        return False

    async def check_escalation(
        self,
        db: AsyncSession,
        *,
        queue: FollowUpQueue
    ) -> tuple[bool, Optional[str]]:
        if queue.is_escalated:
            return False, None

        rule = await self.get_applicable_rule(
            db,
            patient_type=queue.task.patient_type if queue.task else PatientType.FOLLOW_UP,
            is_retest=queue.task.is_retest if queue.task else False
        )

        escalation_hours = rule.escalation_hours if rule else settings.DEFAULT_UPGRADE_HOURS
        now = datetime.now()

        time_scheduled = queue.scheduled_time
        if time_scheduled and (now - time_scheduled) > timedelta(hours=escalation_hours):
            if queue.status not in [QueueStatus.COMPLETED, QueueStatus.CANCELLED]:
                return True, f"随访任务已超过{escalation_hours}小时未完成"

        return False, None

    async def determine_follow_up_frequency(
        self,
        db: AsyncSession,
        *,
        patient_type: PatientType,
        is_retest: bool,
        clinical_priority: Optional[int] = 0
    ) -> Dict[str, Any]:
        rule = await self.get_applicable_rule(
            db,
            patient_type=patient_type,
            is_retest=is_retest
        )

        if not rule:
            return {
                "frequency_days": 7,
                "total_count": 3,
                "first_follow_up_hours": 24,
                "overdue_hours": 72,
                "escalation_hours": 120,
                "max_attempts": 3,
                "priority": clinical_priority or 0
            }

        return {
            "frequency_days": rule.follow_up_frequency_days,
            "total_count": rule.total_follow_up_count,
            "first_follow_up_hours": rule.first_follow_up_hours,
            "overdue_hours": rule.overdue_hours,
            "escalation_hours": rule.escalation_hours,
            "max_attempts": rule.max_attempts,
            "priority": max(rule.priority, clinical_priority or 0)
        }


class ContactIntervalRuleService(BaseService[ContactIntervalRule, ContactIntervalRuleCreate, ContactIntervalRuleUpdate]):
    def __init__(self):
        super().__init__(ContactIntervalRule)

    async def get_applicable_rule(
        self,
        db: AsyncSession,
        *,
        contact_result: Optional[ContactResult] = None,
        hospital_id: Optional[int] = None
    ) -> Optional[ContactIntervalRule]:
        query = select(ContactIntervalRule).filter(ContactIntervalRule.is_active == True)

        conditions = []

        if contact_result:
            conditions.append(
                or_(
                    ContactIntervalRule.contact_result == contact_result.value,
                    ContactIntervalRule.contact_result == None,
                    ContactIntervalRule.contact_result == ""
                )
            )

        if hospital_id:
            conditions.append(
                or_(
                    ContactIntervalRule.hospital_id == hospital_id,
                    ContactIntervalRule.apply_to_all == True
                )
            )
        else:
            conditions.append(ContactIntervalRule.apply_to_all == True)

        if conditions:
            query = query.filter(and_(*conditions))

        query = query.order_by(
            ContactIntervalRule.apply_to_all.asc(),
            ContactIntervalRule.contact_result.is_(None).asc(),
            ContactIntervalRule.min_interval_hours.desc()
        ).limit(1)

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_all_active_rules(self, db: AsyncSession, hospital_id: Optional[int] = None) -> List[ContactIntervalRule]:
        query = select(ContactIntervalRule).filter(ContactIntervalRule.is_active == True)

        if hospital_id:
            query = query.filter(
                or_(
                    ContactIntervalRule.hospital_id == hospital_id,
                    ContactIntervalRule.apply_to_all == True
                )
            )

        query = query.order_by(ContactIntervalRule.apply_to_all.asc(), ContactIntervalRule.id.asc())
        result = await db.execute(query)
        return list(result.scalars().all())
