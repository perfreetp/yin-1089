from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

from app.models.enums import QueueStatus, ContactChannel, ContactResult
from app.schemas.base import HospitalResponse, PatientResponse, FollowUpStaffResponse
from app.schemas.task import AssessmentTaskResponse


class FollowUpQueueBase(BaseModel):
    task_id: int = Field(..., description="任务ID")
    patient_id: int = Field(..., description="患者ID")
    hospital_id: int = Field(..., description="院区ID")
    follow_up_round: int = Field(1, ge=1, description="随访轮次")
    scheduled_time: datetime = Field(..., description="计划随访时间")
    deadline: datetime = Field(..., description="截止时间")
    priority: int = Field(0, description="优先级")
    assigned_staff_id: Optional[int] = Field(None, description="分配的随访员ID")
    extra_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="额外数据")


class FollowUpQueueCreate(FollowUpQueueBase):
    pass


class FollowUpQueueUpdate(BaseModel):
    status: Optional[QueueStatus] = None
    priority: Optional[int] = None
    assigned_staff_id: Optional[int] = None
    next_attempt_time: Optional[datetime] = None
    completion_note: Optional[str] = None
    is_escalated: Optional[bool] = None
    escalation_reason: Optional[str] = None
    is_active: Optional[bool] = None
    extra_data: Optional[Dict[str, Any]] = None


class FollowUpQueueResponse(FollowUpQueueBase):
    id: int
    queue_no: str
    status: QueueStatus
    assigned_time: Optional[datetime] = None
    attempt_count: int
    last_attempt_time: Optional[datetime] = None
    completed_time: Optional[datetime] = None
    is_escalated: bool
    escalation_time: Optional[datetime] = None
    escalation_reason: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    task: Optional[AssessmentTaskResponse] = None
    patient: Optional[PatientResponse] = None
    hospital: Optional[HospitalResponse] = None
    assigned_staff: Optional[FollowUpStaffResponse] = None

    class Config:
        from_attributes = True


class ContactRecordBase(BaseModel):
    queue_id: int = Field(..., description="队列ID")
    staff_id: int = Field(..., description="随访员ID")
    contact_channel: ContactChannel = Field(..., description="联系渠道")
    contact_time: datetime = Field(..., description="联系时间")
    contact_result: ContactResult = Field(..., description="联系结果")
    call_duration_seconds: int = Field(0, description="通话时长(秒)")
    contact_notes: Optional[str] = Field(None, description="联系备注")
    patient_response: Optional[Dict[str, Any]] = Field(default_factory=dict, description="患者反馈")
    next_suggested_action: Optional[str] = Field(None, description="下一步建议")


class ContactRecordCreate(ContactRecordBase):
    pass


class ContactRecordResponse(ContactRecordBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class QueueListResponse(BaseModel):
    queues: list[FollowUpQueueResponse]
    total: int
    page: int
    page_size: int
