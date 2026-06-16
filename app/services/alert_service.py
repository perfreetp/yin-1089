from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid

from app.models import Alert, AlertEscalationLog, FollowUpQueue, Patient
from app.models.enums import AlertLevel, AlertType, QueueStatus
from app.schemas import AlertCreate, AlertUpdate
from app.services.base_service import BaseService
from app.services.rule_engine_service import RuleEngineService
from app.config import settings


class AlertService(BaseService[Alert, AlertCreate, AlertUpdate]):
    def __init__(self):
        super().__init__(Alert)
        self.rule_engine = RuleEngineService()

    def _generate_alert_no(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_str = uuid.uuid4().hex[:6].upper()
        return f"ALERT{timestamp}{random_str}"

    async def create_alert(
        self,
        db: AsyncSession,
        *,
        queue_id: int,
        hospital_id: Optional[int] = None,
        alert_type: AlertType,
        alert_level: AlertLevel,
        title: str,
        message: str,
        triggered_time: datetime,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Alert:
        alert_data = {
            "alert_no": self._generate_alert_no(),
            "queue_id": queue_id,
            "hospital_id": hospital_id,
            "alert_type": alert_type,
            "alert_level": alert_level,
            "title": title,
            "message": message,
            "triggered_time": triggered_time,
            "extra_data": extra_data or {}
        }

        db_alert = Alert(**alert_data)
        db.add(db_alert)
        await db.flush()
        await db.refresh(db_alert)
        return db_alert

    async def get_unhandled_alerts(
        self,
        db: AsyncSession,
        *,
        hospital_id: Optional[int] = None,
        min_level: Optional[AlertLevel] = None,
        skip: int = 0,
        limit: int = 50
    ) -> tuple[List[Alert], int]:
        query = select(Alert).filter(
            Alert.is_active == True,
            Alert.is_handled == False
        )

        if hospital_id:
            query = query.filter(Alert.hospital_id == hospital_id)

        if min_level:
            level_order = {
                AlertLevel.NORMAL: 0,
                AlertLevel.WARNING: 1,
                AlertLevel.URGENT: 2,
                AlertLevel.CRITICAL: 3
            }
            min_order = level_order.get(min_level, 0)
            query = query.filter(
                Alert.alert_level.in_([
                    level for level, order in level_order.items()
                    if order >= min_order
                ])
            )

        count_query = select(func.count()).select_from(query.subquery())
        total = await db.execute(count_query)
        total_count = total.scalar_one()

        query = query.order_by(
            Alert.alert_level.desc(),
            Alert.triggered_time.asc()
        )
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        items = result.scalars().all()

        return list(items), total_count

    async def mark_as_read(
        self,
        db: AsyncSession,
        *,
        alert_id: int,
        read_by: str
    ) -> Optional[Alert]:
        alert = await self.get(db, alert_id)
        if not alert:
            return None

        alert.is_read = True
        alert.read_time = datetime.now()
        alert.read_by = read_by

        await db.flush()
        await db.refresh(alert)
        return alert

    async def mark_as_handled(
        self,
        db: AsyncSession,
        *,
        alert_id: int,
        handled_by: str,
        handle_note: Optional[str] = None
    ) -> Optional[Alert]:
        alert = await self.get(db, alert_id)
        if not alert:
            return None

        alert.is_handled = True
        alert.handled_time = datetime.now()
        alert.handled_by = handled_by
        alert.handle_note = handle_note

        await db.flush()
        await db.refresh(alert)
        return alert

    async def escalate_alert(
        self,
        db: AsyncSession,
        *,
        alert_id: int,
        escalation_reason: str,
        escalated_by: str,
        new_level: Optional[AlertLevel] = None
    ) -> Optional[Alert]:
        alert = await self.get(db, alert_id)
        if not alert:
            return None

        level_order = [AlertLevel.NORMAL, AlertLevel.WARNING, AlertLevel.URGENT, AlertLevel.CRITICAL]
        current_index = level_order.index(alert.alert_level)

        if new_level:
            target_level = new_level
        else:
            target_level = level_order[min(current_index + 1, len(level_order) - 1)]

        from_level = alert.alert_level
        to_level = target_level

        alert.alert_level = target_level
        alert.escalation_count = alert.escalation_count + 1
        alert.last_escalation_time = datetime.now()

        escalation_log = AlertEscalationLog(
            alert_id=alert_id,
            from_level=from_level,
            to_level=to_level,
            escalation_reason=escalation_reason,
            escalation_time=datetime.now(),
            escalated_by=escalated_by
        )
        db.add(escalation_log)

        await db.flush()
        await db.refresh(alert)
        return alert

    async def check_and_create_overdue_alerts(self, db: AsyncSession) -> int:
        now = datetime.now()
        queues_result = await db.execute(
            select(FollowUpQueue).filter(
                FollowUpQueue.is_active == True,
                FollowUpQueue.status.notin_([QueueStatus.COMPLETED, QueueStatus.CANCELLED]),
                FollowUpQueue.deadline < now
            )
        )
        overdue_queues = list(queues_result.scalars().all())

        created_count = 0
        for queue in overdue_queues:
            existing_alert = await db.execute(
                select(Alert).filter(
                    Alert.queue_id == queue.id,
                    Alert.alert_type == AlertType.OVERDUE,
                    Alert.is_handled == False,
                    Alert.is_active == True
                )
            )
            if existing_alert.scalar_one_or_none():
                continue

            time_overdue = now - queue.deadline
            hours_overdue = time_overdue.total_seconds() / 3600

            if hours_overdue >= 120:
                level = AlertLevel.CRITICAL
            elif hours_overdue >= 72:
                level = AlertLevel.URGENT
            elif hours_overdue >= 24:
                level = AlertLevel.WARNING
            else:
                level = AlertLevel.NORMAL

            await self.create_alert(
                db,
                queue_id=queue.id,
                hospital_id=queue.hospital_id,
                alert_type=AlertType.OVERDUE,
                alert_level=level,
                title=f"随访任务超期 - {queue.queue_no}",
                message=f"随访任务已超期 {int(hours_overdue)} 小时，随访轮次：{queue.follow_up_round}",
                triggered_time=now,
                extra_data={
                    "hours_overdue": hours_overdue,
                    "follow_up_round": queue.follow_up_round,
                    "patient_id": queue.patient_id
                }
            )
            created_count += 1

        return created_count

    async def check_and_create_escalation_alerts(self, db: AsyncSession) -> int:
        queues_result = await db.execute(
            select(FollowUpQueue).filter(
                FollowUpQueue.is_active == True,
                FollowUpQueue.status.notin_([QueueStatus.COMPLETED, QueueStatus.CANCELLED]),
                FollowUpQueue.is_escalated == False
            )
        )
        queues = list(queues_result.scalars().all())

        created_count = 0
        for queue in queues:
            should_escalate, reason = await self.rule_engine.check_escalation(db, queue=queue)
            if should_escalate:
                existing_alert = await db.execute(
                    select(Alert).filter(
                        Alert.queue_id == queue.id,
                        Alert.alert_type == AlertType.ESCALATION,
                        Alert.is_handled == False,
                        Alert.is_active == True
                    )
                )
                if existing_alert.scalar_one_or_none():
                    continue

                await self.create_alert(
                    db,
                    queue_id=queue.id,
                    hospital_id=queue.hospital_id,
                    alert_type=AlertType.ESCALATION,
                    alert_level=AlertLevel.URGENT,
                    title=f"随访任务需升级处理 - {queue.queue_no}",
                    message=reason or "随访任务长时间未完成，需升级处理",
                    triggered_time=datetime.now(),
                    extra_data={
                        "follow_up_round": queue.follow_up_round,
                        "attempt_count": queue.attempt_count,
                        "patient_id": queue.patient_id
                    }
                )
                created_count += 1

        return created_count

    async def check_high_priority_patients(self, db: AsyncSession) -> int:
        result = await db.execute(
            select(Patient).filter(
                Patient.is_key_patient == True
            )
        )
        key_patients = list(result.scalars().all())

        created_count = 0
        for patient in key_patients:
            queue_result = await db.execute(
                select(FollowUpQueue).filter(
                    FollowUpQueue.patient_id == patient.id,
                    FollowUpQueue.is_active == True,
                    FollowUpQueue.status.notin_([QueueStatus.COMPLETED, QueueStatus.CANCELLED])
                ).order_by(FollowUpQueue.created_at.desc()).limit(1)
            )
            queue = queue_result.scalar_one_or_none()
            if not queue:
                continue

            existing_alert = await db.execute(
                select(Alert).filter(
                    Alert.queue_id == queue.id,
                    Alert.alert_type == AlertType.HIGH_PRIORITY,
                    Alert.is_handled == False,
                    Alert.is_active == True
                )
            )
            if existing_alert.scalar_one_or_none():
                continue

            await self.create_alert(
                db,
                queue_id=queue.id,
                hospital_id=queue.hospital_id,
                alert_type=AlertType.HIGH_PRIORITY,
                alert_level=AlertLevel.URGENT,
                title=f"重点患者随访提醒 - {patient.name}",
                message=f"重点患者 {patient.name}（{patient.patient_no}）的随访任务待处理，原因：{patient.key_patient_reason}",
                triggered_time=datetime.now(),
                extra_data={
                    "patient_id": patient.id,
                    "patient_name": patient.name,
                    "key_patient_reason": patient.key_patient_reason
                }
            )
            created_count += 1

        return created_count

    async def run_alert_checks(self, db: AsyncSession) -> Dict[str, int]:
        overdue_count = await self.check_and_create_overdue_alerts(db)
        escalation_count = await self.check_and_create_escalation_alerts(db)
        high_priority_count = await self.check_high_priority_patients(db)

        return {
            "overdue_alerts": overdue_count,
            "escalation_alerts": escalation_count,
            "high_priority_alerts": high_priority_count,
            "total": overdue_count + escalation_count + high_priority_count
        }

    async def get_alert_escalation_history(
        self,
        db: AsyncSession,
        *,
        alert_id: int
    ) -> List[AlertEscalationLog]:
        result = await db.execute(
            select(AlertEscalationLog)
            .filter(AlertEscalationLog.alert_id == alert_id)
            .order_by(AlertEscalationLog.escalation_time.desc())
        )
        return list(result.scalars().all())
