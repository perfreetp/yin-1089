from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid

from app.models import FollowUpQueue, ContactRecord, AssessmentTask, FollowUpStaff, Patient
from app.models.enums import QueueStatus, ContactChannel, ContactResult, TaskStatus, AlertType, AlertLevel
from app.schemas import FollowUpQueueCreate, FollowUpQueueUpdate, ContactRecordCreate
from app.services.base_service import BaseService
from app.services.assignment_service import AssignmentService
from app.services.rule_engine_service import RuleEngineService


class QueueService(BaseService[FollowUpQueue, FollowUpQueueCreate, FollowUpQueueUpdate]):
    def __init__(self):
        super().__init__(FollowUpQueue)
        self.assignment_service = AssignmentService()
        self.rule_engine = RuleEngineService()

    def _generate_queue_no(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_str = uuid.uuid4().hex[:6].upper()
        return f"QUEUE{timestamp}{random_str}"

    async def get_by_queue_no(self, db: AsyncSession, queue_no: str) -> Optional[FollowUpQueue]:
        result = await db.execute(select(FollowUpQueue).filter(FollowUpQueue.queue_no == queue_no))
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: FollowUpQueueCreate) -> FollowUpQueue:
        queue_data = obj_in.model_dump()
        queue_data["queue_no"] = self._generate_queue_no()
        queue_data["status"] = QueueStatus.PENDING

        if not queue_data.get("assigned_staff_id"):
            staff_id = await self.assignment_service.assign_to_staff(
                db,
                hospital_id=obj_in.hospital_id,
                priority=obj_in.priority
            )
            if staff_id:
                queue_data["assigned_staff_id"] = staff_id
                queue_data["assigned_time"] = datetime.now()

        db_queue = FollowUpQueue(**queue_data)
        db.add(db_queue)
        await db.flush()
        await db.refresh(db_queue)
        return db_queue

    async def get_pending_queues(
        self,
        db: AsyncSession,
        *,
        hospital_id: Optional[int] = None,
        staff_id: Optional[int] = None,
        priority: Optional[int] = None,
        skip: int = 0,
        limit: int = 50
    ) -> tuple[List[FollowUpQueue], int]:
        query = select(FollowUpQueue).filter(
            FollowUpQueue.is_active == True,
            FollowUpQueue.status.notin_([QueueStatus.COMPLETED, QueueStatus.CANCELLED])
        )

        if hospital_id:
            query = query.filter(FollowUpQueue.hospital_id == hospital_id)
        if staff_id:
            query = query.filter(FollowUpQueue.assigned_staff_id == staff_id)
        if priority is not None:
            query = query.filter(FollowUpQueue.priority >= priority)

        now = datetime.now()
        query = query.filter(
            or_(
                FollowUpQueue.next_attempt_time == None,
                FollowUpQueue.next_attempt_time <= now
            )
        )

        count_query = select(func.count()).select_from(query.subquery())
        total = await db.execute(count_query)
        total_count = total.scalar_one()

        query = query.order_by(
            FollowUpQueue.priority.desc(),
            FollowUpQueue.deadline.asc(),
            FollowUpQueue.scheduled_time.asc()
        )
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        items = result.scalars().all()

        return list(items), total_count

    async def get_overdue_queues(
        self,
        db: AsyncSession,
        *,
        hospital_id: Optional[int] = None
    ) -> List[FollowUpQueue]:
        now = datetime.now()
        query = select(FollowUpQueue).filter(
            FollowUpQueue.is_active == True,
            FollowUpQueue.status.notin_([QueueStatus.COMPLETED, QueueStatus.CANCELLED]),
            FollowUpQueue.deadline < now
        )

        if hospital_id:
            query = query.filter(FollowUpQueue.hospital_id == hospital_id)

        query = query.order_by(FollowUpQueue.deadline.asc())
        result = await db.execute(query)
        return list(result.scalars().all())

    async def start_follow_up(
        self,
        db: AsyncSession,
        *,
        queue_id: int,
        staff_id: int
    ) -> Optional[FollowUpQueue]:
        queue = await self.get(db, queue_id)
        if not queue:
            return None

        can_contact, reason, next_time = await self.rule_engine.can_contact_now(
            db,
            queue_id=queue_id,
            hospital_id=queue.hospital_id
        )

        if not can_contact:
            queue.next_attempt_time = next_time
            await db.flush()
            await db.refresh(queue)
            return queue

        queue.status = QueueStatus.IN_PROGRESS
        queue.assigned_staff_id = staff_id
        queue.assigned_time = datetime.now()
        queue.attempt_count = queue.attempt_count + 1
        queue.last_attempt_time = datetime.now()

        await db.flush()
        await db.refresh(queue)
        return queue

    async def record_contact(
        self,
        db: AsyncSession,
        *,
        contact_data: ContactRecordCreate
    ) -> ContactRecord:
        db_contact = ContactRecord(**contact_data.model_dump())
        db.add(db_contact)
        await db.flush()
        await db.refresh(db_contact)

        queue = await self.get(db, contact_data.queue_id)
        if queue:
            queue.last_attempt_time = contact_data.contact_time

            if contact_data.contact_result == ContactResult.SUCCESS or contact_data.contact_result == ContactResult.APPOINTMENT_SCHEDULED:
                pass
            else:
                interval_rule = await self.rule_engine.interval_rule_service.get_applicable_rule(
                    db,
                    contact_result=contact_data.contact_result,
                    hospital_id=queue.hospital_id
                )
                if interval_rule:
                    queue.next_attempt_time = datetime.now() + timedelta(hours=interval_rule.min_interval_hours)

            await db.flush()

        return db_contact

    async def complete_queue(
        self,
        db: AsyncSession,
        *,
        queue_id: int,
        staff_id: int,
        completion_note: Optional[str] = None
    ) -> Optional[FollowUpQueue]:
        queue = await self.get(db, queue_id)
        if not queue:
            return None

        queue.status = QueueStatus.COMPLETED
        queue.completed_time = datetime.now()
        queue.completion_note = completion_note

        task = await db.get(AssessmentTask, queue.task_id)
        if task:
            task.follow_up_count = task.follow_up_count + 1

            if task.follow_up_count >= task.max_follow_up_count:
                task.status = TaskStatus.COMPLETED
            else:
                task.status = TaskStatus.IN_PROGRESS
                task.current_follow_up_round = queue.follow_up_round + 1

        await db.flush()
        await db.refresh(queue)
        return queue

    async def escalate_queue(
        self,
        db: AsyncSession,
        *,
        queue_id: int,
        reason: str
    ) -> Optional[FollowUpQueue]:
        queue = await self.get(db, queue_id)
        if not queue:
            return None

        queue.is_escalated = True
        queue.escalation_time = datetime.now()
        queue.escalation_reason = reason
        queue.status = QueueStatus.ESCALATED

        from app.services.alert_service import AlertService
        alert_service = AlertService()

        await alert_service.create_alert(
            db,
            queue_id=queue_id,
            hospital_id=queue.hospital_id,
            alert_type=AlertType.ESCALATION,
            alert_level=AlertLevel.URGENT,
            title=f"随访任务升级 - {queue.queue_no}",
            message=f"随访任务已升级，原因：{reason}",
            triggered_time=datetime.now()
        )

        await db.flush()
        await db.refresh(queue)
        return queue

    async def reassign_queue(
        self,
        db: AsyncSession,
        *,
        queue_id: int,
        new_staff_id: int,
        reason: str
    ) -> Optional[FollowUpQueue]:
        queue = await self.get(db, queue_id)
        if not queue:
            return None

        old_staff_id = queue.assigned_staff_id
        queue.assigned_staff_id = new_staff_id
        queue.assigned_time = datetime.now()
        queue.status = QueueStatus.PENDING

        if queue.extra_data:
            queue.extra_data["reassign_history"] = queue.extra_data.get("reassign_history", [])
            queue.extra_data["reassign_history"].append({
                "from_staff": old_staff_id,
                "to_staff": new_staff_id,
                "reason": reason,
                "time": datetime.now().isoformat()
            })

        from app.services.alert_service import AlertService
        alert_service = AlertService()

        await alert_service.create_alert(
            db,
            queue_id=queue_id,
            hospital_id=queue.hospital_id,
            alert_type=AlertType.REASSIGN,
            alert_level=AlertLevel.NORMAL,
            title=f"随访任务重新分配 - {queue.queue_no}",
            message=f"随访任务已重新分配，原因：{reason}",
            triggered_time=datetime.now()
        )

        await db.flush()
        await db.refresh(queue)
        return queue

    async def generate_daily_queues(self, db: AsyncSession) -> int:
        tasks = await db.execute(
            select(AssessmentTask).filter(
                AssessmentTask.is_active == True,
                AssessmentTask.status.notin_([TaskStatus.COMPLETED, TaskStatus.CANCELLED]),
                AssessmentTask.current_follow_up_round <= AssessmentTask.max_follow_up_count
            )
        )
        tasks_list = list(tasks.scalars().all())

        generated_count = 0
        for task in tasks_list:
            existing_queue = await db.execute(
                select(FollowUpQueue).filter(
                    FollowUpQueue.task_id == task.id,
                    FollowUpQueue.follow_up_round == task.current_follow_up_round,
                    FollowUpQueue.is_active == True
                )
            )
            if existing_queue.scalar_one_or_none():
                continue

            rule = await self.rule_engine.get_applicable_rule(
                db,
                patient_type=task.patient_type,
                is_retest=task.is_retest
            )

            scheduled_time, deadline = await self.rule_engine.calculate_next_follow_up_time(
                db,
                task_id=task.id,
                patient_type=task.patient_type,
                is_retest=task.is_retest,
                current_round=task.current_follow_up_round
            )

            queue_data = FollowUpQueueCreate(
                task_id=task.id,
                patient_id=task.patient_id,
                hospital_id=task.hospital_id,
                follow_up_round=task.current_follow_up_round,
                scheduled_time=scheduled_time,
                deadline=deadline,
                priority=task.priority
            )

            await self.create(db, obj_in=queue_data)
            generated_count += 1

        return generated_count

    async def get_contact_history(
        self,
        db: AsyncSession,
        *,
        queue_id: int
    ) -> List[ContactRecord]:
        result = await db.execute(
            select(ContactRecord)
            .filter(ContactRecord.queue_id == queue_id)
            .order_by(ContactRecord.contact_time.desc())
        )
        return list(result.scalars().all())

    async def get_patient_contact_history(
        self,
        db: AsyncSession,
        *,
        patient_id: int
    ) -> List[ContactRecord]:
        result = await db.execute(
            select(ContactRecord)
            .join(FollowUpQueue)
            .filter(FollowUpQueue.patient_id == patient_id)
            .order_by(ContactRecord.contact_time.desc())
        )
        return list(result.scalars().all())
