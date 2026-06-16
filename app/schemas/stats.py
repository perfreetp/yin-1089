from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, date
from decimal import Decimal

from app.models.enums import PatientType


class HospitalStatsResponse(BaseModel):
    hospital_id: int
    hospital_name: str
    hospital_code: str
    zone: str

    total_tasks: int = Field(0, description="总任务数")
    pending_tasks: int = Field(0, description="待处理任务数")
    in_progress_tasks: int = Field(0, description="进行中任务数")
    completed_tasks: int = Field(0, description="已完成任务数")
    overdue_tasks: int = Field(0, description="超期任务数")
    cancelled_tasks: int = Field(0, description="已取消任务数")

    completion_rate: float = Field(0.0, description="完成率")
    execution_rate: float = Field(0.0, description="执行率")
    overdue_rate: float = Field(0.0, description="超期率")

    total_queues: int = Field(0, description="总随访队列数")
    completed_queues: int = Field(0, description="已完成队列数")
    average_contact_attempts: float = Field(0.0, description="平均联系次数")
    average_call_duration: float = Field(0.0, description="平均通话时长(秒)")

    total_psqi_results: int = Field(0, description="PSQI评估结果数")
    average_psqi_score: float = Field(0.0, description="平均PSQI分数")
    improved_patients: int = Field(0, description="改善患者数")
    worsened_patients: int = Field(0, description="恶化患者数")
    stable_patients: int = Field(0, description="稳定患者数")

    total_alerts: int = Field(0, description="总告警数")
    unhandled_alerts: int = Field(0, description="未处理告警数")
    critical_alerts: int = Field(0, description="严重告警数")

    period_start: Optional[date] = None
    period_end: Optional[date] = None

    class Config:
        from_attributes = True


class StaffPerformanceResponse(BaseModel):
    staff_id: int
    staff_name: str
    staff_no: str
    hospital_id: int
    hospital_name: str

    total_assigned_queues: int = Field(0, description="分配的总队列数")
    completed_queues: int = Field(0, description="已完成队列数")
    in_progress_queues: int = Field(0, description="进行中队列数")
    overdue_queues: int = Field(0, description="超期队列数")

    completion_rate: float = Field(0.0, description="完成率")
    average_handling_time_hours: float = Field(0.0, description="平均处理时长(小时)")

    total_contacts: int = Field(0, description="总联系次数")
    successful_contacts: int = Field(0, description="成功联系次数")
    contact_success_rate: float = Field(0.0, description="联系成功率")
    average_call_duration: float = Field(0.0, description="平均通话时长(秒)")

    total_psqi_results: int = Field(0, description="登记的PSQI结果数")
    average_psqi_score: float = Field(0.0, description="平均PSQI分数")

    period_start: Optional[date] = None
    period_end: Optional[date] = None

    class Config:
        from_attributes = True


class ScoreTrendItem(BaseModel):
    date: date
    average_score: float
    patient_count: int
    improved_count: int
    worsened_count: int
    stable_count: int


class ScoreTrendResponse(BaseModel):
    hospital_id: Optional[int] = None
    hospital_name: Optional[str] = None
    trend_data: List[ScoreTrendItem]
    period_start: date
    period_end: date
    overall_average_score: float = 0.0
    total_patients: int = 0


class TaskStatusSummary(BaseModel):
    status: str
    count: int
    percentage: float


class PatientTypeDistribution(BaseModel):
    patient_type: str
    count: int
    percentage: float


class ExecutiveDashboardResponse(BaseModel):
    total_hospitals: int = 0
    active_hospitals: int = 0
    total_staff: int = 0
    active_staff: int = 0
    total_patients: int = 0
    key_patients: int = 0

    total_tasks_today: int = 0
    completed_tasks_today: int = 0
    pending_tasks_total: int = 0
    overdue_tasks_total: int = 0

    average_completion_rate: float = 0.0
    average_execution_rate: float = 0.0
    average_overdue_rate: float = 0.0

    overall_average_psqi_score: float = 0.0
    total_psqi_assessments: int = 0

    task_status_summary: List[TaskStatusSummary] = []
    patient_type_distribution: List[PatientTypeDistribution] = []
    hospital_ranking_by_execution: List[Dict[str, Any]] = []

    last_updated: datetime


class OverdueQueueDetail(BaseModel):
    queue_id: int
    queue_no: str
    task_id: int
    task_no: str
    patient_id: int
    patient_name: str
    patient_type: str
    hospital_id: int
    hospital_name: str
    assigned_staff_id: Optional[int] = None
    assigned_staff_name: Optional[str] = None
    follow_up_round: int
    scheduled_time: Optional[datetime] = None
    deadline: Optional[datetime] = None
    status: str
    attempt_count: int
    overdue_hours: float = 0.0

    class Config:
        from_attributes = True


class OverdueTaskDetail(BaseModel):
    task_id: int
    task_no: str
    patient_id: int
    patient_name: str
    patient_type: str
    hospital_id: int
    hospital_name: str
    is_retest: bool
    deadline: Optional[datetime] = None
    status: str
    overdue_queues: int = 0
    total_queues: int = 0

    class Config:
        from_attributes = True


class OverdueBreakdownResponse(BaseModel):
    dimension: str
    dimension_value: str
    overdue_count: int
    total_count: int
    overdue_rate: float = 0.0


class OverdueTrendItem(BaseModel):
    date: str
    overdue_count: int = 0
    overdue_queue_count: int = 0
    new_overdue_count: int = 0


class OverdueTrendResponse(BaseModel):
    dimension: str = "date"
    granularity: str = "day"
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    items: List[OverdueTrendItem] = []


class OverdueDetailsResponse(BaseModel):
    total: int = 0
    items: List[OverdueQueueDetail] = []


class BatchTransmitResponse(BaseModel):
    total: int = 0
    success_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    success_ids: List[int] = []
    failed_ids: List[int] = []
    skipped_ids: List[int] = []
    failed_details: List[Dict[str, Any]] = []
    skipped_details: List[Dict[str, Any]] = []


class RuleTrialRequest(BaseModel):
    patient_type: PatientType
    is_retest: bool = False
    hospital_id: Optional[int] = None
    last_contact_result: Optional[Any] = None
    last_contact_time: Optional[datetime] = None


class RuleTrialResponse(BaseModel):
    matched_rule: Optional[str] = None
    rule_id: Optional[int] = None
    follow_up_frequency_days: int = 7
    total_follow_up_count: int = 3
    max_attempts: int = 3
    first_follow_up_hours: int = 24
    overdue_hours: int = 72
    escalation_hours: int = 120

    matched_interval_rule: Optional[str] = None
    interval_rule_id: Optional[int] = None
    min_interval_hours: int = 0
    max_daily_attempts: int = 0
    max_total_attempts: int = 0
    time_window_start: Optional[str] = None
    time_window_end: Optional[str] = None

    can_contact_now: bool = True
    next_allowed_time: Optional[datetime] = None
    contact_restriction_reason: Optional[str] = None

    trial_reason: str = ""
