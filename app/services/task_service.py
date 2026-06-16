from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid

from app.models import AssessmentTask, Patient, Hospital, FollowUpQueue
from app.models.enums import TaskStatus, PatientType, QueueStatus
from app.schemas import AssessmentTaskCreate, AssessmentTaskUpdate
from app.services.base_service import BaseService
from app.services.rule_engine_service import RuleEngineService
from app.services.queue_service import QueueService


class TaskService(BaseService[AssessmentTask, AssessmentTaskCreate, AssessmentTaskUpdate]):
    def __init__(self):
        super().__init__(AssessmentTask)
        self.rule_engine = RuleEngineService()
        self.queue_service = QueueService()

    def _generate_task_no(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_str = uuid.uuid4().hex[:6].upper()
        return f"TASK{timestamp}{random_str}"

    async def get_by_task_no(self, db: AsyncSession, task_no: str) -> Optional[AssessmentTask]:
        result = await db.execute(select(AssessmentTask).filter(AssessmentTask.task_no == task_no))
        return result.scalar_one_or_none()

    async def get_by_patient(self, db: AsyncSession, patient_id: int) -> List[AssessmentTask]:
        result = await db.execute(
            select(AssessmentTask)
            .filter(
                AssessmentTask.patient_id == patient_id,
                AssessmentTask.is_active == True
            )
            .order_by(AssessmentTask.created_at.desc())
        )
        return list(result.scalars().all())

    async def determine_if_retest(
        self,
        db: AsyncSession,
        patient_id: int,
        hospital_id: int
    ) -> bool:
        result = await db.execute(
            select(func.count(AssessmentTask.id))
            .filter(
                AssessmentTask.patient_id == patient_id,
                AssessmentTask.hospital_id == hospital_id,
                AssessmentTask.is_active == True
            )
        )
        count = result.scalar_one()
        return count > 0

    async def create_task(
        self,
        db: AsyncSession,
        *,
        obj_in: AssessmentTaskCreate
    ) -> AssessmentTask:
        is_retest = await self.determine_if_retest(
            db,
            patient_id=obj_in.patient_id,
            hospital_id=obj_in.hospital_id
        )

        rule = await self.rule_engine.get_applicable_rule(
            db,
            patient_type=obj_in.patient_type,
            is_retest=is_retest
        )

        task_data = obj_in.model_dump()
        task_data["task_no"] = self._generate_task_no()
        task_data["is_retest"] = is_retest
        task_data["status"] = TaskStatus.PENDING

        if rule and not obj_in.deadline:
            deadline_hours = rule.overdue_hours if rule else 72
            task_data["deadline"] = datetime.now() + timedelta(hours=deadline_hours)

        if rule:
            task_data["max_follow_up_count"] = rule.total_follow_up_count
            task_data["priority"] = rule.priority

        db_task = AssessmentTask(**task_data)
        db.add(db_task)
        await db.flush()
        await db.refresh(db_task)

        await self._generate_initial_queue(db, task=db_task, rule=rule)

        return db_task

    async def _generate_initial_queue(
        self,
        db: AsyncSession,
        *,
        task: AssessmentTask,
        rule: Optional[Any] = None
    ):
        from app.schemas import FollowUpQueueCreate

        if not rule:
            rule = await self.rule_engine.get_applicable_rule(
                db,
                patient_type=task.patient_type,
                is_retest=task.is_retest
            )

        first_follow_up_hours = rule.first_follow_up_hours if rule else 24
        overdue_hours = rule.overdue_hours if rule else 72

        scheduled_time = datetime.now() + timedelta(hours=first_follow_up_hours)
        deadline = datetime.now() + timedelta(hours=overdue_hours)

        queue_data = FollowUpQueueCreate(
            task_id=task.id,
            patient_id=task.patient_id,
            hospital_id=task.hospital_id,
            follow_up_round=1,
            scheduled_time=scheduled_time,
            deadline=deadline,
            priority=task.priority,
            assigned_staff_id=None
        )

        await self.queue_service.create(db, obj_in=queue_data)

    async def update_task_status(
        self,
        db: AsyncSession,
        *,
        task_id: int,
        status: TaskStatus,
        notes: Optional[str] = None
    ) -> Optional[AssessmentTask]:
        task = await self.get(db, task_id)
        if not task:
            return None

        update_data = {"status": status}
        if notes:
            update_data["clinical_notes"] = notes

        return await self.update(db, db_obj=task, obj_in=update_data)

    async def cancel_task(
        self,
        db: AsyncSession,
        *,
        task_id: int,
        reason: str
    ) -> Optional[AssessmentTask]:
        task = await self.get(db, task_id)
        if not task:
            return None

        task.status = TaskStatus.CANCELLED
        task.is_active = False
        task.clinical_notes = f"{task.clinical_notes or ''}\n取消原因: {reason}"

        await db.execute(
            update(FollowUpQueue)
            .where(FollowUpQueue.task_id == task_id)
            .values(status=QueueStatus.CANCELLED, is_active=False)
        )

        await db.flush()
        await db.refresh(task)
        return task

    async def get_task_list(
        self,
        db: AsyncSession,
        *,
        hospital_id: Optional[int] = None,
        status: Optional[TaskStatus] = None,
        patient_type: Optional[PatientType] = None,
        is_retest: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 20
    ) -> tuple[List[AssessmentTask], int]:
        query = select(AssessmentTask).filter(AssessmentTask.is_active == True)

        if hospital_id:
            query = query.filter(AssessmentTask.hospital_id == hospital_id)
        if status:
            query = query.filter(AssessmentTask.status == status)
        if patient_type:
            query = query.filter(AssessmentTask.patient_type == patient_type)
        if is_retest is not None:
            query = query.filter(AssessmentTask.is_retest == is_retest)
        if start_date:
            query = query.filter(AssessmentTask.created_at >= start_date)
        if end_date:
            query = query.filter(AssessmentTask.created_at <= end_date)

        count_query = select(func.count()).select_from(query.subquery())
        total = await db.execute(count_query)
        total_count = total.scalar_one()

        query = query.order_by(AssessmentTask.priority.desc(), AssessmentTask.created_at.desc())
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        items = result.scalars().all()

        return list(items), total_count

    async def get_overdue_tasks(self, db: AsyncSession) -> List[AssessmentTask]:
        from app.models import FollowUpQueue
        from app.models.enums import QueueStatus

        now = datetime.now()
        overdue_task_ids_query = select(FollowUpQueue.task_id).filter(
            FollowUpQueue.is_active == True,
            FollowUpQueue.status.notin_([QueueStatus.COMPLETED, QueueStatus.CANCELLED]),
            FollowUpQueue.deadline < now
        ).distinct()

        result = await db.execute(
            select(AssessmentTask)
            .filter(
                AssessmentTask.is_active == True,
                AssessmentTask.id.in_(overdue_task_ids_query)
            )
            .order_by(AssessmentTask.deadline.asc())
        )
        return list(result.scalars().all())

    async def mark_task_completed(
        self,
        db: AsyncSession,
        *,
        task_id: int
    ) -> Optional[AssessmentTask]:
        task = await self.get(db, task_id)
        if not task:
            return None

        task.status = TaskStatus.COMPLETED
        task.follow_up_count = task.follow_up_count + 1

        await db.flush()
        await db.refresh(task)
        return task

    async def reassign_failed_task(
        self,
        db: AsyncSession,
        *,
        task_id: int,
        reason: str
    ) -> Optional[AssessmentTask]:
        task = await self.get(db, task_id)
        if not task:
            return None

        task.status = TaskStatus.REASSIGNED
        task.follow_up_count = task.follow_up_count + 1

        from app.schemas import FollowUpQueueCreate

        rule = await self.rule_engine.get_applicable_rule(
            db,
            patient_type=task.patient_type,
            is_retest=task.is_retest
        )

        next_round = task.current_follow_up_round + 1
        if next_round <= task.max_follow_up_count:
            task.current_follow_up_round = next_round

            frequency_days = rule.follow_up_frequency_days if rule else 7
            overdue_hours = rule.overdue_hours if rule else 72

            scheduled_time = datetime.now() + timedelta(days=frequency_days)
            deadline = datetime.now() + timedelta(hours=overdue_hours)

            queue_data = FollowUpQueueCreate(
                task_id=task.id,
                patient_id=task.patient_id,
                hospital_id=task.hospital_id,
                follow_up_round=next_round,
                scheduled_time=scheduled_time,
                deadline=deadline,
                priority=task.priority,
                extra_data={"reassign_reason": reason}
            )

            await self.queue_service.create(db, obj_in=queue_data)
            task.status = TaskStatus.IN_PROGRESS

        await db.flush()
        await db.refresh(task)
        return task
