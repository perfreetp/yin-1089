from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

from app.models.enums import TaskStatus, PatientType
from app.schemas.base import HospitalResponse, PatientResponse


class AssessmentTaskBase(BaseModel):
    source_task_no: Optional[str] = Field(None, max_length=100, description="来源任务编号")
    hospital_id: int = Field(..., description="院区ID")
    patient_id: int = Field(..., description="患者ID")
    patient_type: PatientType = Field(..., description="患者类型")
    is_retest: bool = Field(False, description="是否复测")
    assessment_type: str = Field("PSQI", max_length=100, description="评估类型")
    order_department: Optional[str] = Field(None, max_length=200, description="开单科室")
    order_doctor: Optional[str] = Field(None, max_length=100, description="开单医生")
    order_time: Optional[datetime] = Field(None, description="开单时间")
    clinical_diagnosis: Optional[str] = Field(None, description="临床诊断")
    clinical_notes: Optional[str] = Field(None, description="临床备注")
    priority: int = Field(0, description="优先级")
    deadline: Optional[datetime] = Field(None, description="截止时间")
    max_follow_up_count: int = Field(3, ge=1, description="最大随访次数")
    extra_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="额外数据")


class AssessmentTaskCreate(AssessmentTaskBase):
    pass


class AssessmentTaskUpdate(BaseModel):
    patient_type: Optional[PatientType] = None
    is_retest: Optional[bool] = None
    status: Optional[TaskStatus] = None
    priority: Optional[int] = None
    deadline: Optional[datetime] = None
    clinical_notes: Optional[str] = None
    max_follow_up_count: Optional[int] = None
    is_active: Optional[bool] = None
    extra_data: Optional[Dict[str, Any]] = None


class AssessmentTaskResponse(AssessmentTaskBase):
    id: int
    task_no: str
    status: TaskStatus
    follow_up_count: int
    current_follow_up_round: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    hospital: Optional[HospitalResponse] = None
    patient: Optional[PatientResponse] = None

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    tasks: list[AssessmentTaskResponse]
    total: int
    page: int
    page_size: int
