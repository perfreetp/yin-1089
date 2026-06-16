from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, case
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta

from app.models import (
    Hospital, FollowUpStaff, AssessmentTask, FollowUpQueue,
    ContactRecord, PSQIResult, ScoreHistory, Alert, Patient
)
from app.models.enums import TaskStatus, QueueStatus, ScoreChangeType, AlertLevel, ContactResult
from app.schemas.stats import (
    HospitalStatsResponse, StaffPerformanceResponse,
    ScoreTrendResponse, ScoreTrendItem,
    ExecutiveDashboardResponse, TaskStatusSummary, PatientTypeDistribution
)


class StatsService:
    async def get_hospital_stats(
        self,
        db: AsyncSession,
        *,
        hospital_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> HospitalStatsResponse:
        hospital = await db.get(Hospital, hospital_id)
        if not hospital:
            raise ValueError(f"Hospital {hospital_id} not found")

        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()

        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())

        tasks_result = await db.execute(
            select(
                func.count(AssessmentTask.id).label("total"),
                func.sum(case((AssessmentTask.status == TaskStatus.PENDING, 1), else_=0)).label("pending"),
                func.sum(case((AssessmentTask.status == TaskStatus.IN_PROGRESS, 1), else_=0)).label("in_progress"),
                func.sum(case((AssessmentTask.status == TaskStatus.COMPLETED, 1), else_=0)).label("completed"),
                func.sum(case((AssessmentTask.status == TaskStatus.OVERDUE, 1), else_=0)).label("overdue"),
                func.sum(case((AssessmentTask.status == TaskStatus.CANCELLED, 1), else_=0)).label("cancelled")
            ).filter(
                AssessmentTask.hospital_id == hospital_id,
                AssessmentTask.created_at >= start_datetime,
                AssessmentTask.created_at <= end_datetime,
                AssessmentTask.is_active == True
            )
        )
        tasks_stats = tasks_result.first()

        queues_result = await db.execute(
            select(
                func.count(FollowUpQueue.id).label("total"),
                func.sum(case((FollowUpQueue.status == QueueStatus.COMPLETED, 1), else_=0)).label("completed"),
                func.avg(FollowUpQueue.attempt_count).label("avg_attempts")
            ).filter(
                FollowUpQueue.hospital_id == hospital_id,
                FollowUpQueue.created_at >= start_datetime,
                FollowUpQueue.created_at <= end_datetime,
                FollowUpQueue.is_active == True
            )
        )
        queues_stats = queues_result.first()

        calls_result = await db.execute(
            select(
                func.avg(ContactRecord.call_duration_seconds).label("avg_duration")
            ).select_from(ContactRecord)
            .join(FollowUpQueue)
            .filter(
                FollowUpQueue.hospital_id == hospital_id,
                ContactRecord.contact_time >= start_datetime,
                ContactRecord.contact_time <= end_datetime
            )
        )
        calls_stats = calls_result.first()

        psqi_result = await db.execute(
            select(
                func.count(PSQIResult.id).label("total"),
                func.avg(PSQIResult.total_score).label("avg_score"),
                func.sum(case((PSQIResult.score_change_type == ScoreChangeType.IMPROVED, 1), else_=0)).label("improved"),
                func.sum(case((PSQIResult.score_change_type == ScoreChangeType.WORSENED, 1), else_=0)).label("worsened"),
                func.sum(case((PSQIResult.score_change_type == ScoreChangeType.STABLE, 1), else_=0)).label("stable"),
                func.sum(case((PSQIResult.score_change_type == ScoreChangeType.SIGNIFICANT_IMPROVEMENT, 1), else_=0)).label("sig_improved"),
                func.sum(case((PSQIResult.score_change_type == ScoreChangeType.SIGNIFICANT_WORSENING, 1), else_=0)).label("sig_worsened")
            ).filter(
                PSQIResult.hospital_id == hospital_id,
                PSQIResult.assessment_date >= start_datetime,
                PSQIResult.assessment_date <= end_datetime
            )
        )
        psqi_stats = psqi_result.first()

        alerts_result = await db.execute(
            select(
                func.count(Alert.id).label("total"),
                func.sum(case((Alert.is_handled == False, 1), else_=0)).label("unhandled"),
                func.sum(case((Alert.alert_level == AlertLevel.CRITICAL, 1), else_=0)).label("critical")
            ).filter(
                Alert.hospital_id == hospital_id,
                Alert.triggered_time >= start_datetime,
                Alert.triggered_time <= end_datetime,
                Alert.is_active == True
            )
        )
        alerts_stats = alerts_result.first()

        total_tasks = tasks_stats.total or 0
        completed_tasks = tasks_stats.completed or 0
        overdue_tasks = tasks_stats.overdue or 0

        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0.0
        execution_rate = ((completed_tasks) / max(total_tasks - (tasks_stats.cancelled or 0), 1) * 100) if total_tasks > 0 else 0.0
        overdue_rate = (overdue_tasks / total_tasks * 100) if total_tasks > 0 else 0.0

        improved_total = (psqi_stats.improved or 0) + (psqi_stats.sig_improved or 0)
        worsened_total = (psqi_stats.worsened or 0) + (psqi_stats.sig_worsened or 0)

        return HospitalStatsResponse(
            hospital_id=hospital.id,
            hospital_name=hospital.name,
            hospital_code=hospital.code,
            zone=hospital.zone.value,
            total_tasks=total_tasks,
            pending_tasks=tasks_stats.pending or 0,
            in_progress_tasks=tasks_stats.in_progress or 0,
            completed_tasks=completed_tasks,
            overdue_tasks=overdue_tasks,
            cancelled_tasks=tasks_stats.cancelled or 0,
            completion_rate=round(completion_rate, 2),
            execution_rate=round(execution_rate, 2),
            overdue_rate=round(overdue_rate, 2),
            total_queues=queues_stats.total or 0,
            completed_queues=queues_stats.completed or 0,
            average_contact_attempts=round(queues_stats.avg_attempts or 0, 2),
            average_call_duration=round(calls_stats.avg_duration or 0, 2),
            total_psqi_results=psqi_stats.total or 0,
            average_psqi_score=round(psqi_stats.avg_score or 0, 2),
            improved_patients=improved_total,
            worsened_patients=worsened_total,
            stable_patients=psqi_stats.stable or 0,
            total_alerts=alerts_stats.total or 0,
            unhandled_alerts=alerts_stats.unhandled or 0,
            critical_alerts=alerts_stats.critical or 0,
            period_start=start_date,
            period_end=end_date
        )

    async def get_staff_performance(
        self,
        db: AsyncSession,
        *,
        staff_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> StaffPerformanceResponse:
        staff = await db.get(FollowUpStaff, staff_id)
        if not staff:
            raise ValueError(f"Staff {staff_id} not found")

        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()

        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())

        queues_result = await db.execute(
            select(
                func.count(FollowUpQueue.id).label("total"),
                func.sum(case((FollowUpQueue.status == QueueStatus.COMPLETED, 1), else_=0)).label("completed"),
                func.sum(case((FollowUpQueue.status == QueueStatus.IN_PROGRESS, 1), else_=0)).label("in_progress"),
                func.sum(case((FollowUpQueue.status == QueueStatus.OVERDUE, 1), else_=0)).label("overdue")
            ).filter(
                FollowUpQueue.assigned_staff_id == staff_id,
                FollowUpQueue.created_at >= start_datetime,
                FollowUpQueue.created_at <= end_datetime,
                FollowUpQueue.is_active == True
            )
        )
        queues_stats = queues_result.first()

        avg_time_result = await db.execute(
            select(
                func.avg(
                    func.julianday(FollowUpQueue.completed_time) - func.julianday(FollowUpQueue.assigned_time)
                ) * 24
            ).filter(
                FollowUpQueue.assigned_staff_id == staff_id,
                FollowUpQueue.status == QueueStatus.COMPLETED,
                FollowUpQueue.completed_time >= start_datetime,
                FollowUpQueue.completed_time <= end_datetime,
                FollowUpQueue.assigned_time.isnot(None)
            )
        )
        avg_handling_time = avg_time_result.scalar_one() or 0

        contacts_result = await db.execute(
            select(
                func.count(ContactRecord.id).label("total"),
                func.sum(case((ContactRecord.contact_result.in_([ContactResult.SUCCESS, ContactResult.APPOINTMENT_SCHEDULED]), 1), else_=0)).label("successful"),
                func.avg(ContactRecord.call_duration_seconds).label("avg_duration")
            ).filter(
                ContactRecord.staff_id == staff_id,
                ContactRecord.contact_time >= start_datetime,
                ContactRecord.contact_time <= end_datetime
            )
        )
        contacts_stats = contacts_result.first()

        psqi_result = await db.execute(
            select(
                func.count(PSQIResult.id).label("total"),
                func.avg(PSQIResult.total_score).label("avg_score")
            ).select_from(PSQIResult)
            .join(FollowUpQueue)
            .filter(
                FollowUpQueue.assigned_staff_id == staff_id,
                PSQIResult.assessment_date >= start_datetime,
                PSQIResult.assessment_date <= end_datetime
            )
        )
        psqi_stats = psqi_result.first()

        total_queues = queues_stats.total or 0
        completed = queues_stats.completed or 0
        total_contacts = contacts_stats.total or 0
        successful = contacts_stats.successful or 0

        completion_rate = (completed / total_queues * 100) if total_queues > 0 else 0.0
        contact_success_rate = (successful / total_contacts * 100) if total_contacts > 0 else 0.0

        hospital = await db.get(Hospital, staff.hospital_id)

        return StaffPerformanceResponse(
            staff_id=staff.id,
            staff_name=staff.name,
            staff_no=staff.staff_no,
            hospital_id=staff.hospital_id,
            hospital_name=hospital.name if hospital else "",
            total_assigned_queues=total_queues,
            completed_queues=completed,
            in_progress_queues=queues_stats.in_progress or 0,
            overdue_queues=queues_stats.overdue or 0,
            completion_rate=round(completion_rate, 2),
            average_handling_time_hours=round(avg_handling_time, 2),
            total_contacts=total_contacts,
            successful_contacts=successful,
            contact_success_rate=round(contact_success_rate, 2),
            average_call_duration=round(contacts_stats.avg_duration or 0, 2),
            total_psqi_results=psqi_stats.total or 0,
            average_psqi_score=round(psqi_stats.avg_score or 0, 2),
            period_start=start_date,
            period_end=end_date
        )

    async def get_score_trend(
        self,
        db: AsyncSession,
        *,
        hospital_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> ScoreTrendResponse:
        if not start_date:
            start_date = date.today() - timedelta(days=90)
        if not end_date:
            end_date = date.today()

        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())

        query = select(
            func.date(ScoreHistory.assessment_date).label("assessment_date"),
            func.avg(ScoreHistory.total_score).label("avg_score"),
            func.count(ScoreHistory.id).label("patient_count"),
            func.sum(case(
                (PSQIResult.score_change_type.in_([ScoreChangeType.IMPROVED, ScoreChangeType.SIGNIFICANT_IMPROVEMENT]), 1),
                else_=0
            )).label("improved_count"),
            func.sum(case(
                (PSQIResult.score_change_type.in_([ScoreChangeType.WORSENED, ScoreChangeType.SIGNIFICANT_WORSENING]), 1),
                else_=0
            )).label("worsened_count"),
            func.sum(case((PSQIResult.score_change_type == ScoreChangeType.STABLE, 1), else_=0)).label("stable_count")
        ).select_from(ScoreHistory)
        query = query.join(PSQIResult, ScoreHistory.result_id == PSQIResult.id, isouter=True)

        if hospital_id:
            query = query.filter(ScoreHistory.patient_id.in_(
                select(Patient.id).filter(Patient.id == ScoreHistory.patient_id).join(
                    AssessmentTask, AssessmentTask.patient_id == Patient.id
                ).filter(AssessmentTask.hospital_id == hospital_id)
            ))

        query = query.filter(
            ScoreHistory.assessment_date >= start_datetime,
            ScoreHistory.assessment_date <= end_datetime
        )
        query = query.group_by(func.date(ScoreHistory.assessment_date))
        query = query.order_by(func.date(ScoreHistory.assessment_date))

        result = await db.execute(query)
        rows = result.all()

        trend_data = []
        total_score_sum = 0.0
        total_patients = 0

        for row in rows:
            assessment_date = row.assessment_date
            if isinstance(assessment_date, str):
                assessment_date = datetime.strptime(assessment_date, "%Y-%m-%d").date()

            avg_score = row.avg_score or 0
            patient_count = row.patient_count or 0

            trend_data.append(ScoreTrendItem(
                date=assessment_date,
                average_score=round(avg_score, 2),
                patient_count=patient_count,
                improved_count=row.improved_count or 0,
                worsened_count=row.worsened_count or 0,
                stable_count=row.stable_count or 0
            ))

            total_score_sum += avg_score * patient_count
            total_patients += patient_count

        overall_avg = (total_score_sum / total_patients) if total_patients > 0 else 0.0

        hospital_name = None
        if hospital_id:
            hospital = await db.get(Hospital, hospital_id)
            hospital_name = hospital.name if hospital else None

        return ScoreTrendResponse(
            hospital_id=hospital_id,
            hospital_name=hospital_name,
            trend_data=trend_data,
            period_start=start_date,
            period_end=end_date,
            overall_average_score=round(overall_avg, 2),
            total_patients=total_patients
        )

    async def get_executive_dashboard(
        self,
        db: AsyncSession
    ) -> ExecutiveDashboardResponse:
        hospitals_result = await db.execute(
            select(
                func.count(Hospital.id).label("total"),
                func.sum(case((Hospital.is_active == True, 1), else_=0)).label("active")
            )
        )
        hospitals = hospitals_result.first()

        staff_result = await db.execute(
            select(
                func.count(FollowUpStaff.id).label("total"),
                func.sum(case((FollowUpStaff.is_active == True, 1), else_=0)).label("active")
            )
        )
        staff = staff_result.first()

        patients_result = await db.execute(
            select(
                func.count(Patient.id).label("total"),
                func.sum(case((Patient.is_key_patient == True, 1), else_=0)).label("key")
            )
        )
        patients = patients_result.first()

        today_start = datetime.combine(date.today(), datetime.min.time())
        today_end = datetime.combine(date.today(), datetime.max.time())

        tasks_today_result = await db.execute(
            select(
                func.count(AssessmentTask.id).label("total"),
                func.sum(case((AssessmentTask.status == TaskStatus.COMPLETED, 1), else_=0)).label("completed")
            ).filter(
                AssessmentTask.created_at >= today_start,
                AssessmentTask.created_at <= today_end,
                AssessmentTask.is_active == True
            )
        )
        tasks_today = tasks_today_result.first()

        pending_result = await db.execute(
            select(func.count(AssessmentTask.id)).filter(
                AssessmentTask.status == TaskStatus.PENDING,
                AssessmentTask.is_active == True
            )
        )
        pending_total = pending_result.scalar_one()

        overdue_result = await db.execute(
            select(func.count(AssessmentTask.id)).filter(
                AssessmentTask.status == TaskStatus.OVERDUE,
                AssessmentTask.is_active == True
            )
        )
        overdue_total = overdue_result.scalar_one()

        all_tasks_result = await db.execute(
            select(
                func.count(AssessmentTask.id).label("total"),
                func.sum(case((AssessmentTask.status == TaskStatus.COMPLETED, 1), else_=0)).label("completed"),
                func.sum(case((AssessmentTask.status == TaskStatus.OVERDUE, 1), else_=0)).label("overdue")
            ).filter(AssessmentTask.is_active == True)
        )
        all_tasks = all_tasks_result.first()

        psqi_result = await db.execute(
            select(
                func.count(PSQIResult.id).label("total"),
                func.avg(PSQIResult.total_score).label("avg_score")
            )
        )
        psqi = psqi_result.first()

        status_summary_result = await db.execute(
            select(
                AssessmentTask.status,
                func.count(AssessmentTask.id).label("count")
            ).filter(AssessmentTask.is_active == True)
            .group_by(AssessmentTask.status)
        )
        status_rows = status_summary_result.all()

        total_tasks_all = all_tasks.total or 0
        task_status_summary = []
        for row in status_rows:
            count = row.count or 0
            percentage = (count / total_tasks_all * 100) if total_tasks_all > 0 else 0
            task_status_summary.append(TaskStatusSummary(
                status=row.status.value,
                count=count,
                percentage=round(percentage, 2)
            ))

        type_distribution_result = await db.execute(
            select(
                Patient.patient_type,
                func.count(Patient.id).label("count")
            ).group_by(Patient.patient_type)
        )
        type_rows = type_distribution_result.all()

        total_patients_all = patients.total or 0
        patient_type_distribution = []
        for row in type_rows:
            count = row.count or 0
            percentage = (count / total_patients_all * 100) if total_patients_all > 0 else 0
            patient_type_distribution.append(PatientTypeDistribution(
                patient_type=row.patient_type.value,
                count=count,
                percentage=round(percentage, 2)
            ))

        hospital_ids_result = await db.execute(select(Hospital.id).filter(Hospital.is_active == True))
        hospital_ids = [row[0] for row in hospital_ids_result.all()]

        hospital_ranking = []
        for hid in hospital_ids:
            try:
                stats = await self.get_hospital_stats(db, hospital_id=hid)
                hospital_ranking.append({
                    "hospital_id": hid,
                    "hospital_name": stats.hospital_name,
                    "execution_rate": stats.execution_rate,
                    "completion_rate": stats.completion_rate,
                    "overdue_rate": stats.overdue_rate,
                    "total_tasks": stats.total_tasks,
                    "completed_tasks": stats.completed_tasks
                })
            except:
                continue

        hospital_ranking.sort(key=lambda x: x["execution_rate"], reverse=True)

        avg_completion = (all_tasks.completed / all_tasks.total * 100) if all_tasks.total else 0
        avg_execution = avg_completion
        avg_overdue = (all_tasks.overdue / all_tasks.total * 100) if all_tasks.total else 0

        return ExecutiveDashboardResponse(
            total_hospitals=hospitals.total or 0,
            active_hospitals=hospitals.active or 0,
            total_staff=staff.total or 0,
            active_staff=staff.active or 0,
            total_patients=patients.total or 0,
            key_patients=patients.key or 0,
            total_tasks_today=tasks_today.total or 0,
            completed_tasks_today=tasks_today.completed or 0,
            pending_tasks_total=pending_total,
            overdue_tasks_total=overdue_total,
            average_completion_rate=round(avg_completion, 2),
            average_execution_rate=round(avg_execution, 2),
            average_overdue_rate=round(avg_overdue, 2),
            overall_average_psqi_score=round(psqi.avg_score or 0, 2),
            total_psqi_assessments=psqi.total or 0,
            task_status_summary=task_status_summary,
            patient_type_distribution=patient_type_distribution,
            hospital_ranking_by_execution=hospital_ranking,
            last_updated=datetime.now()
        )

    async def mark_key_patient(
        self,
        db: AsyncSession,
        *,
        patient_id: int,
        is_key: bool,
        reason: Optional[str] = None
    ) -> Optional[Patient]:
        patient = await db.get(Patient, patient_id)
        if not patient:
            return None

        patient.is_key_patient = is_key
        if is_key and reason:
            patient.key_patient_reason = reason

        await db.flush()
        await db.refresh(patient)
        return patient

    async def get_key_patients(
        self,
        db: AsyncSession,
        *,
        hospital_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50
    ) -> tuple[List[Patient], int]:
        query = select(Patient).filter(Patient.is_key_patient == True)

        if hospital_id:
            query = query.filter(Patient.id.in_(
                select(AssessmentTask.patient_id)
                .filter(AssessmentTask.hospital_id == hospital_id)
                .distinct()
            ))

        count_query = select(func.count()).select_from(query.subquery())
        total = await db.execute(count_query)
        total_count = total.scalar_one()

        query = query.order_by(Patient.updated_at.desc())
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        items = result.scalars().all()

        return list(items), total_count

    async def retry_failed_tasks(
        self,
        db: AsyncSession,
        *,
        hospital_id: Optional[int] = None
    ) -> int:
        from app.services.task_service import TaskService

        query = select(AssessmentTask).filter(
            AssessmentTask.status == TaskStatus.FAILED,
            AssessmentTask.is_active == True
        )

        if hospital_id:
            query = query.filter(AssessmentTask.hospital_id == hospital_id)

        result = await db.execute(query)
        failed_tasks = list(result.scalars().all())

        task_service = TaskService()
        retried_count = 0

        for task in failed_tasks:
            await task_service.reassign_failed_task(
                db,
                task_id=task.id,
                reason="系统自动重派失败任务"
            )
            retried_count += 1

        return retried_count
