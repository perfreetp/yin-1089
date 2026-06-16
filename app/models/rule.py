from sqlalchemy import Column, Integer, String, Boolean, Text, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.sqlite import JSON

from app.database import Base
from app.models.enums import PatientType, AssignmentStrategy


class FollowUpRule(Base):
    __tablename__ = "follow_up_rules"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(200), nullable=False)
    description = Column(Text)
    patient_type = Column(Enum(PatientType), nullable=False)
    is_retest = Column(Boolean, default=False)

    follow_up_frequency_days = Column(Integer, nullable=False)
    total_follow_up_count = Column(Integer, nullable=False)
    first_follow_up_hours = Column(Integer, default=24)

    overdue_hours = Column(Integer, default=72)
    escalation_hours = Column(Integer, default=120)
    max_attempts = Column(Integer, default=3)

    assignment_strategy = Column(Enum(AssignmentStrategy), default=AssignmentStrategy.ROUND_ROBIN)
    priority = Column(Integer, default=0)

    is_active = Column(Boolean, default=True)
    config = Column(JSON, default={})


class ContactIntervalRule(Base):
    __tablename__ = "contact_interval_rules"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(200), nullable=False)
    description = Column(Text)

    contact_result = Column(String(50))
    min_interval_hours = Column(Integer, nullable=False)
    max_daily_attempts = Column(Integer, default=3)
    max_total_attempts = Column(Integer, default=10)

    time_window_start = Column(String(10), default="08:00")
    time_window_end = Column(String(10), default="20:00")

    apply_to_all = Column(Boolean, default=False)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=True)

    is_active = Column(Boolean, default=True)
