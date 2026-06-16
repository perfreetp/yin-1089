from sqlalchemy import Column, Integer, String, Boolean, Text, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.sqlite import JSON

from app.database import Base
from app.models.enums import QueueStatus, ContactChannel, ContactResult


class FollowUpQueue(Base):
    __tablename__ = "follow_up_queues"

    id = Column(Integer, primary_key=True, index=True)

    queue_no = Column(String(50), unique=True, index=True, nullable=False)
    task_id = Column(Integer, ForeignKey("assessment_tasks.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=False)

    follow_up_round = Column(Integer, default=1)
    scheduled_time = Column(DateTime(timezone=True), nullable=False)
    deadline = Column(DateTime(timezone=True), nullable=False)

    status = Column(Enum(QueueStatus), default=QueueStatus.PENDING)
    priority = Column(Integer, default=0)

    assigned_staff_id = Column(Integer, ForeignKey("follow_up_staff.id"), nullable=True)
    assigned_time = Column(DateTime(timezone=True))

    attempt_count = Column(Integer, default=0)
    last_attempt_time = Column(DateTime(timezone=True))
    next_attempt_time = Column(DateTime(timezone=True))

    completed_time = Column(DateTime(timezone=True))
    completion_note = Column(Text)

    is_escalated = Column(Boolean, default=False)
    escalation_time = Column(DateTime(timezone=True))
    escalation_reason = Column(Text)

    is_active = Column(Boolean, default=True)
    extra_data = Column(JSON, default={})

    task = relationship("AssessmentTask", back_populates="queues")
    patient = relationship("Patient", back_populates="queues")
    hospital = relationship("Hospital", back_populates="queues")
    assigned_staff = relationship("FollowUpStaff", foreign_keys=[assigned_staff_id], back_populates="assigned_queues")
    contact_records = relationship("ContactRecord", back_populates="queue")
    alerts = relationship("Alert", back_populates="queue")


class ContactRecord(Base):
    __tablename__ = "contact_records"

    id = Column(Integer, primary_key=True, index=True)

    queue_id = Column(Integer, ForeignKey("follow_up_queues.id"), nullable=False)
    staff_id = Column(Integer, ForeignKey("follow_up_staff.id"), nullable=False)

    contact_channel = Column(Enum(ContactChannel), nullable=False)
    contact_time = Column(DateTime(timezone=True), nullable=False)
    contact_result = Column(Enum(ContactResult), nullable=False)

    call_duration_seconds = Column(Integer, default=0)
    contact_notes = Column(Text)

    patient_response = Column(JSON, default={})
    next_suggested_action = Column(Text)

    queue = relationship("FollowUpQueue", back_populates="contact_records")
    staff = relationship("FollowUpStaff", back_populates="contact_records")
