from sqlalchemy import Column, Integer, String, Boolean, Text, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.sqlite import JSON

from app.database import Base
from app.models.enums import AlertLevel, AlertType


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)

    alert_no = Column(String(50), unique=True, index=True, nullable=False)
    queue_id = Column(Integer, ForeignKey("follow_up_queues.id"), nullable=False)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=True)

    alert_type = Column(Enum(AlertType), nullable=False)
    alert_level = Column(Enum(AlertLevel), nullable=False)

    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)

    triggered_time = Column(DateTime(timezone=True), nullable=False)
    is_read = Column(Boolean, default=False)
    read_time = Column(DateTime(timezone=True))
    read_by = Column(String(100))

    is_handled = Column(Boolean, default=False)
    handled_time = Column(DateTime(timezone=True))
    handled_by = Column(String(100))
    handle_note = Column(Text)

    escalation_count = Column(Integer, default=0)
    last_escalation_time = Column(DateTime(timezone=True))

    is_active = Column(Boolean, default=True)
    extra_data = Column(JSON, default={})

    queue = relationship("FollowUpQueue", back_populates="alerts")
    escalation_logs = relationship("AlertEscalationLog", back_populates="alert")


class AlertEscalationLog(Base):
    __tablename__ = "alert_escalation_logs"

    id = Column(Integer, primary_key=True, index=True)

    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=False)
    from_level = Column(Enum(AlertLevel), nullable=False)
    to_level = Column(Enum(AlertLevel), nullable=False)

    escalation_reason = Column(Text)
    escalation_time = Column(DateTime(timezone=True), nullable=False)
    escalated_by = Column(String(100))

    notified_staff = Column(JSON, default=[])
    notification_channels = Column(JSON, default=[])

    alert = relationship("Alert", back_populates="escalation_logs")
