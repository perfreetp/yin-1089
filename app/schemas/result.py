from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

from app.models.enums import ScoreChangeType


class PSQIResultBase(BaseModel):
    task_id: int = Field(..., description="任务ID")
    queue_id: int = Field(..., description="队列ID")
    patient_id: int = Field(..., description="患者ID")
    hospital_id: int = Field(..., description="院区ID")
    assessment_date: datetime = Field(..., description="评估日期")
    assessor: Optional[str] = Field(None, max_length=100, description="评估人员")
    sleep_quality: int = Field(..., ge=0, le=3, description="睡眠质量")
    sleep_latency: int = Field(..., ge=0, le=3, description="入睡时间")
    sleep_duration: int = Field(..., ge=0, le=3, description="睡眠时间")
    sleep_efficiency: int = Field(..., ge=0, le=3, description="睡眠效率")
    sleep_disturbances: int = Field(..., ge=0, le=3, description="睡眠障碍")
    use_of_medication: int = Field(..., ge=0, le=3, description="使用睡眠药物")
    daytime_dysfunction: int = Field(..., ge=0, le=3, description="日间功能障碍")
    score_interpretation: Optional[str] = Field(None, max_length=500, description="评分解读")
    notes: Optional[str] = Field(None, description="备注")
    extra_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="额外数据")


class PSQIResultCreate(PSQIResultBase):
    pass


class PSQIResultUpdate(BaseModel):
    sleep_quality: Optional[int] = Field(None, ge=0, le=3)
    sleep_latency: Optional[int] = Field(None, ge=0, le=3)
    sleep_duration: Optional[int] = Field(None, ge=0, le=3)
    sleep_efficiency: Optional[int] = Field(None, ge=0, le=3)
    sleep_disturbances: Optional[int] = Field(None, ge=0, le=3)
    use_of_medication: Optional[int] = Field(None, ge=0, le=3)
    daytime_dysfunction: Optional[int] = Field(None, ge=0, le=3)
    score_interpretation: Optional[str] = None
    is_transmitted: Optional[bool] = None
    transmission_status: Optional[str] = None
    transmission_error: Optional[str] = None
    notes: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None


class PSQIResultResponse(PSQIResultBase):
    id: int
    result_no: str
    total_score: float
    previous_score: Optional[float] = None
    score_change: Optional[float] = None
    score_change_type: Optional[ScoreChangeType] = None
    clinically_significant: bool
    is_transmitted: bool
    transmitted_time: Optional[datetime] = None
    transmission_status: Optional[str] = None
    transmission_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScoreHistoryResponse(BaseModel):
    id: int
    patient_id: int
    result_id: int
    assessment_task_id: int
    assessment_date: datetime
    total_score: float
    component_scores: Optional[Dict[str, Any]] = None
    is_baseline: bool
    is_latest: bool
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ResultFeedbackBase(BaseModel):
    result_id: int = Field(..., description="结果ID")
    task_id: int = Field(..., description="任务ID")
    feedback_to_department: Optional[str] = Field(None, max_length=200, description="反馈科室")
    feedback_to_doctor: Optional[str] = Field(None, max_length=100, description="反馈医生")
    feedback_content: str = Field(..., description="反馈内容")
    feedback_time: datetime = Field(..., description="反馈时间")
    feedback_by: Optional[str] = Field(None, max_length=100, description="反馈人")
    priority: int = Field(0, description="优先级")
    requires_follow_up: bool = Field(False, description="是否需要后续随访")
    follow_up_suggestion: Optional[str] = Field(None, description="随访建议")
    extra_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="额外数据")


class ResultFeedbackCreate(ResultFeedbackBase):
    pass


class ResultFeedbackResponse(ResultFeedbackBase):
    id: int
    feedback_no: str
    is_read: bool
    read_time: Optional[datetime] = None
    doctor_response: Optional[str] = None
    response_time: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
