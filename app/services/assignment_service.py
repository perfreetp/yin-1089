from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update
from typing import Optional, List, Dict, Any
from datetime import datetime, date

from app.models import FollowUpStaff, FollowUpQueue, Hospital
from app.models.enums import AssignmentStrategy, QueueStatus
from app.services.base_service import BaseService


class AssignmentService:
    def __init__(self, strategy: AssignmentStrategy = AssignmentStrategy.LOAD_BALANCE):
        self.default_strategy = strategy

    async def assign_to_staff(
        self,
        db: AsyncSession,
        *,
        hospital_id: int,
        priority: int = 0,
        strategy: Optional[AssignmentStrategy] = None,
        required_skills: Optional[List[str]] = None
    ) -> Optional[int]:
        use_strategy = strategy or self.default_strategy

        if use_strategy == AssignmentStrategy.ROUND_ROBIN:
            return await self._assign_round_robin(db, hospital_id=hospital_id)
        elif use_strategy == AssignmentStrategy.LOAD_BALANCE:
            return await self._assign_load_balance(db, hospital_id=hospital_id)
        elif use_strategy == AssignmentStrategy.SKILL_BASED:
            return await self._assign_skill_based(
                db,
                hospital_id=hospital_id,
                required_skills=required_skills
            )
        elif use_strategy == AssignmentStrategy.PRIORITY:
            return await self._assign_by_priority(
                db,
                hospital_id=hospital_id,
                priority=priority
            )
        else:
            return await self._assign_load_balance(db, hospital_id=hospital_id)

    async def _get_available_staff(
        self,
        db: AsyncSession,
        *,
        hospital_id: int,
        required_skills: Optional[List[str]] = None
    ) -> List[FollowUpStaff]:
        query = select(FollowUpStaff).filter(
            FollowUpStaff.hospital_id == hospital_id,
            FollowUpStaff.is_active == True
        )

        if required_skills:
            for skill in required_skills:
                query = query.filter(FollowUpStaff.skills.op('->')(func.json_each(FollowUpStaff.skills)).like(f"%{skill}%"))

        query = query.order_by(FollowUpStaff.id.asc())
        result = await db.execute(query)
        return list(result.scalars().all())

    async def _get_staff_today_load(
        self,
        db: AsyncSession,
        *,
        staff_id: int
    ) -> int:
        today_start = datetime.combine(date.today(), datetime.min.time())
        today_end = datetime.combine(date.today(), datetime.max.time())

        result = await db.execute(
            select(func.count(FollowUpQueue.id))
            .filter(
                FollowUpQueue.assigned_staff_id == staff_id,
                FollowUpQueue.created_at >= today_start,
                FollowUpQueue.created_at <= today_end,
                FollowUpQueue.is_active == True
            )
        )
        return result.scalar_one()

    async def _get_staff_pending_count(
        self,
        db: AsyncSession,
        *,
        staff_id: int
    ) -> int:
        result = await db.execute(
            select(func.count(FollowUpQueue.id))
            .filter(
                FollowUpQueue.assigned_staff_id == staff_id,
                FollowUpQueue.status.notin_([QueueStatus.COMPLETED, QueueStatus.CANCELLED]),
                FollowUpQueue.is_active == True
            )
        )
        return result.scalar_one()

    async def _assign_round_robin(
        self,
        db: AsyncSession,
        *,
        hospital_id: int
    ) -> Optional[int]:
        staff_list = await self._get_available_staff(db, hospital_id=hospital_id)
        if not staff_list:
            return None

        hospital = await db.get(Hospital, hospital_id)
        if not hospital:
            return staff_list[0].id

        config = hospital.config or {}
        last_assigned_index = config.get("last_round_robin_index", -1)
        next_index = (last_assigned_index + 1) % len(staff_list)

        config["last_round_robin_index"] = next_index
        hospital.config = config
        await db.flush()

        return staff_list[next_index].id

    async def _assign_load_balance(
        self,
        db: AsyncSession,
        *,
        hospital_id: int
    ) -> Optional[int]:
        staff_list = await self._get_available_staff(db, hospital_id=hospital_id)
        if not staff_list:
            return None

        best_staff = None
        min_load = float('inf')

        for staff in staff_list:
            today_load = await self._get_staff_today_load(db, staff_id=staff.id)
            pending_count = await self._get_staff_pending_count(db, staff_id=staff.id)

            effective_load = (today_load / max(staff.max_tasks_per_day, 1)) + (pending_count * 0.5)

            if effective_load < min_load and today_load < staff.max_tasks_per_day:
                min_load = effective_load
                best_staff = staff

        if best_staff:
            return best_staff.id

        return staff_list[0].id if staff_list else None

    async def _assign_skill_based(
        self,
        db: AsyncSession,
        *,
        hospital_id: int,
        required_skills: Optional[List[str]] = None
    ) -> Optional[int]:
        staff_list = await self._get_available_staff(
            db,
            hospital_id=hospital_id,
            required_skills=required_skills
        )

        if not staff_list:
            return await self._assign_load_balance(db, hospital_id=hospital_id)

        if required_skills:
            best_staff = None
            max_match_count = 0

            for staff in staff_list:
                skills = staff.skills or []
                match_count = sum(1 for skill in required_skills if skill in skills)

                if match_count > max_match_count:
                    max_match_count = match_count
                    best_staff = staff

            if best_staff:
                return best_staff.id

        return await self._assign_load_balance(db, hospital_id=hospital_id)

    async def _assign_by_priority(
        self,
        db: AsyncSession,
        *,
        hospital_id: int,
        priority: int
    ) -> Optional[int]:
        staff_list = await self._get_available_staff(db, hospital_id=hospital_id)
        if not staff_list:
            return None

        if priority >= 5:
            best_staff = None
            min_pending = float('inf')

            for staff in staff_list:
                pending_count = await self._get_staff_pending_count(db, staff_id=staff.id)
                if pending_count < min_pending:
                    min_pending = pending_count
                    best_staff = staff

            return best_staff.id if best_staff else staff_list[0].id

        return await self._assign_load_balance(db, hospital_id=hospital_id)

    async def batch_assign(
        self,
        db: AsyncSession,
        *,
        queue_ids: List[int],
        hospital_id: int,
        strategy: Optional[AssignmentStrategy] = None
    ) -> Dict[int, Optional[int]]:
        results = {}
        for queue_id in queue_ids:
            staff_id = await self.assign_to_staff(
                db,
                hospital_id=hospital_id,
                strategy=strategy
            )
            results[queue_id] = staff_id

            if staff_id:
                await db.execute(
                    update(FollowUpQueue)
                    .where(FollowUpQueue.id == queue_id)
                    .values(
                        assigned_staff_id=staff_id,
                        assigned_time=datetime.now(),
                        status=QueueStatus.ASSIGNED
                    )
                )

        await db.flush()
        return results

    async def auto_reassign_overdue(
        self,
        db: AsyncSession,
        *,
        hospital_id: Optional[int] = None
    ) -> int:
        from app.models import FollowUpQueue
        from app.models.enums import QueueStatus

        now = datetime.now()
        query = select(FollowUpQueue).filter(
            FollowUpQueue.is_active == True,
            FollowUpQueue.status.notin_([QueueStatus.COMPLETED, QueueStatus.CANCELLED, QueueStatus.ESCALATED]),
            FollowUpQueue.deadline < now
        )

        if hospital_id:
            query = query.filter(FollowUpQueue.hospital_id == hospital_id)

        result = await db.execute(query)
        overdue_queues = list(result.scalars().all())

        reassigned_count = 0
        for queue in overdue_queues:
            new_staff_id = await self.assign_to_staff(
                db,
                hospital_id=queue.hospital_id,
                priority=queue.priority + 2,
                strategy=AssignmentStrategy.PRIORITY
            )

            if new_staff_id and new_staff_id != queue.assigned_staff_id:
                queue.assigned_staff_id = new_staff_id
                queue.assigned_time = datetime.now()
                queue.status = QueueStatus.REASSIGNED if hasattr(QueueStatus, 'REASSIGNED') else QueueStatus.IN_PROGRESS
                reassigned_count += 1

        await db.flush()
        return reassigned_count
