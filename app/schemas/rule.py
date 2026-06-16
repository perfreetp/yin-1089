from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

from app.models.enums import PatientType, AssignmentStrategy


class FollowUpRuleBase(BaseModel):
    name: str = Field(..., max_length=200, description="规则名称")
    description: Optional[str] = Field(None, description="规则描述")
    patient_type: PatientType = Field(..., description="患者类型")
    is_retest: bool = Field(False, description="是否复测规则")
    follow_up_frequency_days: int = Field(..., ge=1, description="随访频率(天)")
    total_follow_up_count: int = Field(..., ge=1, description="总随访次数")
    first_follow_up_hours: int = Field(24, ge=1, description="首次随访时间(小时)")
    overdue_hours: int = Field(72, ge=1, description="超期时间(小时)")
    escalation_hours: int = Field(120, ge=1, description="升级时间(小时)")
    max_attempts: int = Field(3, ge=1, description="最大尝试次数")
    assignment_strategy: AssignmentStrategy = Field(AssignmentStrategy.ROUND_ROBIN, description="分配策略")
    priority: int = Field(0, description="优先级")
    is_active: bool = Field(True, description="是否启用")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="配置")


class FollowUpRuleCreate(FollowUpRuleBase):
    pass


class FollowUpRuleUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    follow_up_frequency_days: Optional[int] = None
    total_follow_up_count: Optional[int] = None
    first_follow_up_hours: Optional[int] = None
    overdue_hours: Optional[int] = None
    escalation_hours: Optional[int] = None
    max_attempts: Optional[int] = None
    assignment_strategy: Optional[AssignmentStrategy] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


class FollowUpRuleResponse(FollowUpRuleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ContactIntervalRuleBase(BaseModel):
    name: str = Field(..., max_length=200, description="规则名称")
    description: Optional[str] = Field(None, description="规则描述")
    contact_result: Optional[str] = Field(None, max_length=50, description="适用于的联系结果")
    min_interval_hours: int = Field(..., ge=1, description="最小间隔时间(小时)")
    max_daily_attempts: int = Field(3, ge=1, description="每日最大尝试次数")
    max_total_attempts: int = Field(10, ge=1, description="总最大尝试次数")
    time_window_start: str = Field("08:00", max_length=10, description="联系时段开始")
    time_window_end: str = Field("20:00", max_length=10, description="联系时段结束")
    apply_to_all: bool = Field(False, description="是否应用于所有院区")
    hospital_id: Optional[int] = Field(None, description="院区ID")
    is_active: bool = Field(True, description="是否启用")


class ContactIntervalRuleCreate(ContactIntervalRuleBase):
    pass


class ContactIntervalRuleUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    min_interval_hours: Optional[int] = None
    max_daily_attempts: Optional[int] = None
    max_total_attempts: Optional[int] = None
    time_window_start: Optional[str] = None
    time_window_end: Optional[str] = None
    apply_to_all: Optional[bool] = None
    hospital_id: Optional[int] = None
    is_active: Optional[bool] = None


class ContactIntervalRuleResponse(ContactIntervalRuleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
