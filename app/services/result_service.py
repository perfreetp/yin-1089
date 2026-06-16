from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, date
import uuid

from app.models import PSQIResult, ScoreHistory, ResultFeedback, Patient, AssessmentTask, FollowUpQueue, Alert
from app.models.enums import ScoreChangeType, PSQIComponent, AlertType, AlertLevel
from app.schemas import PSQIResultCreate, PSQIResultUpdate, ResultFeedbackCreate
from app.services.base_service import BaseService


class ResultService(BaseService[PSQIResult, PSQIResultCreate, PSQIResultUpdate]):
    def __init__(self):
        super().__init__(PSQIResult)

    def _generate_result_no(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_str = uuid.uuid4().hex[:6].upper()
        return f"RESULT{timestamp}{random_str}"

    def _generate_feedback_no(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_str = uuid.uuid4().hex[:6].upper()
        return f"FEEDBACK{timestamp}{random_str}"

    def calculate_total_score(
        self,
        *,
        sleep_quality: int,
        sleep_latency: int,
        sleep_duration: int,
        sleep_efficiency: int,
        sleep_disturbances: int,
        use_of_medication: int,
        daytime_dysfunction: int
    ) -> float:
        return float(
            sleep_quality + sleep_latency + sleep_duration +
            sleep_efficiency + sleep_disturbances +
            use_of_medication + daytime_dysfunction
        )

    def interpret_score(self, total_score: float) -> str:
        if total_score <= 5:
            return f"PSQI总分 {total_score}，睡眠质量良好"
        elif total_score <= 10:
            return f"PSQI总分 {total_score}，睡眠质量一般"
        elif total_score <= 15:
            return f"PSQI总分 {total_score}，睡眠质量较差"
        else:
            return f"PSQI总分 {total_score}，睡眠质量严重障碍"

    def determine_score_change(
        self,
        *,
        current_score: float,
        previous_score: Optional[float]
    ) -> tuple[Optional[float], Optional[ScoreChangeType], bool]:
        if previous_score is None:
            return None, None, False

        score_change = current_score - previous_score
        abs_change = abs(score_change)

        if abs_change >= 3:
            if score_change < 0:
                change_type = ScoreChangeType.SIGNIFICANT_IMPROVEMENT
            else:
                change_type = ScoreChangeType.SIGNIFICANT_WORSENING
            clinically_significant = True
        elif abs_change >= 1:
            if score_change < 0:
                change_type = ScoreChangeType.IMPROVED
            else:
                change_type = ScoreChangeType.WORSENED
            clinically_significant = False
        else:
            change_type = ScoreChangeType.STABLE
            clinically_significant = False

        return score_change, change_type, clinically_significant

    async def get_previous_score(
        self,
        db: AsyncSession,
        *,
        patient_id: int,
        current_result_id: Optional[int] = None
    ) -> Optional[float]:
        query = select(PSQIResult).filter(
            PSQIResult.patient_id == patient_id,
            PSQIResult.is_transmitted == True
        )

        if current_result_id:
            query = query.filter(PSQIResult.id != current_result_id)

        query = query.order_by(PSQIResult.assessment_date.desc()).limit(1)
        result = await db.execute(query)
        previous = result.scalar_one_or_none()

        return previous.total_score if previous else None

    async def create_result(
        self,
        db: AsyncSession,
        *,
        obj_in: PSQIResultCreate
    ) -> PSQIResult:
        total_score = self.calculate_total_score(
            sleep_quality=obj_in.sleep_quality,
            sleep_latency=obj_in.sleep_latency,
            sleep_duration=obj_in.sleep_duration,
            sleep_efficiency=obj_in.sleep_efficiency,
            sleep_disturbances=obj_in.sleep_disturbances,
            use_of_medication=obj_in.use_of_medication,
            daytime_dysfunction=obj_in.daytime_dysfunction
        )

        score_interpretation = obj_in.score_interpretation or self.interpret_score(total_score)

        previous_score = await self.get_previous_score(
            db,
            patient_id=obj_in.patient_id
        )

        score_change, change_type, clinically_significant = self.determine_score_change(
            current_score=total_score,
            previous_score=previous_score
        )

        result_data = obj_in.model_dump()
        result_data.update({
            "result_no": self._generate_result_no(),
            "total_score": total_score,
            "score_interpretation": score_interpretation,
            "previous_score": previous_score,
            "score_change": score_change,
            "score_change_type": change_type,
            "clinically_significant": clinically_significant
        })

        db_result = PSQIResult(**result_data)
        db.add(db_result)
        await db.flush()
        await db.refresh(db_result)

        await self._update_score_history(db, result=db_result)

        await self._complete_queue(db, queue_id=obj_in.queue_id)

        if clinically_significant:
            await self._handle_clinically_significant(db, result=db_result)

        return db_result

    async def _update_score_history(
        self,
        db: AsyncSession,
        *,
        result: PSQIResult
    ) -> ScoreHistory:
        await db.execute(
            update(ScoreHistory)
            .where(
                ScoreHistory.patient_id == result.patient_id,
                ScoreHistory.is_latest == True
            )
            .values(is_latest=False)
        )

        is_baseline_result = await db.execute(
            select(func.count(ScoreHistory.id))
            .filter(ScoreHistory.patient_id == result.patient_id)
        )
        is_baseline = is_baseline_result.scalar_one() == 0

        component_scores = {
            PSQIComponent.SLEEP_QUALITY.value: result.sleep_quality,
            PSQIComponent.SLEEP_LATENCY.value: result.sleep_latency,
            PSQIComponent.SLEEP_DURATION.value: result.sleep_duration,
            PSQIComponent.SLEEP_EFFICIENCY.value: result.sleep_efficiency,
            PSQIComponent.SLEEP_DISTURBANCES.value: result.sleep_disturbances,
            PSQIComponent.USE_OF_MEDICATION.value: result.use_of_medication,
            PSQIComponent.DAYTIME_DYSFUNCTION.value: result.daytime_dysfunction
        }

        score_history = ScoreHistory(
            patient_id=result.patient_id,
            result_id=result.id,
            assessment_task_id=result.task_id,
            assessment_date=result.assessment_date,
            total_score=result.total_score,
            component_scores=component_scores,
            is_baseline=is_baseline,
            is_latest=True,
            notes=f"PSQI评估结果，总分: {result.total_score}"
        )

        db.add(score_history)
        await db.flush()
        return score_history

    async def _complete_queue(
        self,
        db: AsyncSession,
        *,
        queue_id: int
    ):
        queue = await db.get(FollowUpQueue, queue_id)
        if queue:
            from app.models.enums import QueueStatus
            queue.status = QueueStatus.COMPLETED
            queue.completed_time = datetime.now()
            await db.flush()

    async def _handle_clinically_significant(
        self,
        db: AsyncSession,
        *,
        result: PSQIResult
    ):
        queue = await db.get(FollowUpQueue, result.queue_id)
        if not queue:
            return

        from app.services.alert_service import AlertService
        alert_service = AlertService()

        if result.score_change_type in [ScoreChangeType.SIGNIFICANT_WORSENING, ScoreChangeType.WORSENED]:
            await alert_service.create_alert(
                db,
                queue_id=result.queue_id,
                hospital_id=result.hospital_id,
                alert_type=AlertType.SCORE_ABNORMAL,
                alert_level=AlertLevel.URGENT,
                title=f"PSQI评分显著变化 - {result.result_no}",
                message=f"患者PSQI评分{result.score_change_type.value}，变化值：{result.score_change:+.1f}分，当前总分：{result.total_score}",
                triggered_time=datetime.now(),
                extra_data={
                    "patient_id": result.patient_id,
                    "total_score": result.total_score,
                    "score_change": result.score_change,
                    "change_type": result.score_change_type.value if result.score_change_type else None
                }
            )

        if result.score_change_type == ScoreChangeType.SIGNIFICANT_WORSENING:
            patient = await db.get(Patient, result.patient_id)
            if patient:
                patient.is_key_patient = True
                patient.key_patient_reason = f"PSQI评分显著恶化，变化值：{result.score_change:+.1f}分"
                await db.flush()

    async def transmit_to_clinic(
        self,
        db: AsyncSession,
        *,
        result_id: int
    ) -> Optional[PSQIResult]:
        result = await self.get(db, result_id)
        if not result:
            return None

        result.is_transmitted = True
        result.transmitted_time = datetime.now()
        result.transmission_status = "success"

        await db.flush()
        await db.refresh(result)
        return result

    async def create_feedback(
        self,
        db: AsyncSession,
        *,
        obj_in: ResultFeedbackCreate
    ) -> ResultFeedback:
        feedback_data = obj_in.model_dump()
        feedback_data["feedback_no"] = self._generate_feedback_no()

        db_feedback = ResultFeedback(**feedback_data)
        db.add(db_feedback)
        await db.flush()
        await db.refresh(db_feedback)
        return db_feedback

    async def mark_feedback_read(
        self,
        db: AsyncSession,
        *,
        feedback_id: int,
        doctor_response: Optional[str] = None
    ) -> Optional[ResultFeedback]:
        feedback = await db.get(ResultFeedback, feedback_id)
        if not feedback:
            return None

        feedback.is_read = True
        feedback.read_time = datetime.now()
        if doctor_response:
            feedback.doctor_response = doctor_response
            feedback.response_time = datetime.now()

        await db.flush()
        await db.refresh(feedback)
        return feedback

    async def get_patient_score_history(
        self,
        db: AsyncSession,
        *,
        patient_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 50
    ) -> List[ScoreHistory]:
        query = select(ScoreHistory).filter(ScoreHistory.patient_id == patient_id)

        if start_date:
            query = query.filter(ScoreHistory.assessment_date >= start_date)
        if end_date:
            query = query.filter(ScoreHistory.assessment_date <= end_date)

        query = query.order_by(ScoreHistory.assessment_date.desc()).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_result_feedbacks(
        self,
        db: AsyncSession,
        *,
        result_id: int
    ) -> List[ResultFeedback]:
        result = await db.execute(
            select(ResultFeedback)
            .filter(ResultFeedback.result_id == result_id)
            .order_by(ResultFeedback.feedback_time.desc())
        )
        return list(result.scalars().all())

    async def get_untransmitted_results(
        self,
        db: AsyncSession,
        *,
        hospital_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50
    ) -> tuple[List[PSQIResult], int]:
        query = select(PSQIResult).filter(PSQIResult.is_transmitted == False)

        if hospital_id:
            query = query.filter(PSQIResult.hospital_id == hospital_id)

        count_query = select(func.count()).select_from(query.subquery())
        total = await db.execute(count_query)
        total_count = total.scalar_one()

        query = query.order_by(PSQIResult.assessment_date.asc())
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        items = result.scalars().all()

        return list(items), total_count

    async def batch_transmit(
        self,
        db: AsyncSession,
        *,
        result_ids: List[int]
    ) -> int:
        now = datetime.now()
        await db.execute(
            update(PSQIResult)
            .where(PSQIResult.id.in_(result_ids))
            .values(
                is_transmitted=True,
                transmitted_time=now,
                transmission_status="success"
            )
        )
        await db.flush()
        return len(result_ids)

    async def retry_failed_transmissions(
        self,
        db: AsyncSession,
        *,
        hospital_id: Optional[int] = None
    ) -> int:
        query = select(PSQIResult).filter(
            PSQIResult.is_transmitted == False,
            PSQIResult.transmission_status == "failed"
        )

        if hospital_id:
            query = query.filter(PSQIResult.hospital_id == hospital_id)

        result = await db.execute(query)
        failed_results = list(result.scalars().all())

        if not failed_results:
            return 0

        result_ids = [r.id for r in failed_results]
        return await self.batch_transmit(db, result_ids=result_ids)

    async def get_patient_latest_result(
        self,
        db: AsyncSession,
        *,
        patient_id: int
    ) -> Optional[PSQIResult]:
        result = await db.execute(
            select(PSQIResult)
            .filter(
                PSQIResult.patient_id == patient_id,
                PSQIResult.is_transmitted == True
            )
            .order_by(PSQIResult.assessment_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
