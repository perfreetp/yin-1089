from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.models.enums import AlertLevel, AlertType


class AlertBase(BaseModel):
    queue_id: int = Field(..., description="队列ID")
    hospital_id: Optional[int] = Field(None, description="院区ID")
    alert_type: AlertType = Field(..., description="告警类型")
    alert_level: AlertLevel = Field(..., description="告警级别")
    title: str = Field(..., max_length=200, description="告警标题")
    message: str = Field(..., description="告警内容")
    triggered_time: datetime = Field(..., description="触发时间")
    extra_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="额外数据")


class AlertCreate(AlertBase):
    pass


class AlertUpdate(BaseModel):
    alert_level: Optional[AlertLevel] = None
    is_read: Optional[bool] = None
    read_by: Optional[str] = None
    is_handled: Optional[bool] = None
    handled_by: Optional[str] = None
    handle_note: Optional[str] = None
    escalation_count: Optional[int] = None


class AlertResponse(AlertBase):
    id: int
    alert_no: str
    is_read: bool
    read_time: Optional[datetime] = None
    read_by: Optional[str] = None
    is_handled: bool
    handled_time: Optional[datetime] = None
    handled_by: Optional[str] = None
    handle_note: Optional[str] = None
    escalation_count: int
    last_escalation_time: Optional[datetime] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AlertEscalationLogResponse(BaseModel):
    id: int
    alert_id: int
    from_level: AlertLevel
    to_level: AlertLevel
    escalation_reason: Optional[str] = None
    escalation_time: datetime
    escalated_by: Optional[str] = None
    notified_staff: Optional[List[Any]] = None
    notification_channels: Optional[List[Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True
