from sqlalchemy import Column, Integer, String, Boolean, Text, Enum, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.sqlite import JSON

from app.database import Base
from app.models.enums import ScoreChangeType, PSQIComponent


class PSQIResult(Base):
    __tablename__ = "psqi_results"

    id = Column(Integer, primary_key=True, index=True)

    result_no = Column(String(50), unique=True, index=True, nullable=False)
    task_id = Column(Integer, ForeignKey("assessment_tasks.id"), nullable=False)
    queue_id = Column(Integer, ForeignKey("follow_up_queues.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=False)

    assessment_date = Column(DateTime(timezone=True), nullable=False)
    assessor = Column(String(100))

    sleep_quality = Column(Integer, nullable=False)
    sleep_latency = Column(Integer, nullable=False)
    sleep_duration = Column(Integer, nullable=False)
    sleep_efficiency = Column(Integer, nullable=False)
    sleep_disturbances = Column(Integer, nullable=False)
    use_of_medication = Column(Integer, nullable=False)
    daytime_dysfunction = Column(Integer, nullable=False)

    total_score = Column(Float, nullable=False)
    score_interpretation = Column(String(500))

    previous_score = Column(Float)
    score_change = Column(Float)
    score_change_type = Column(Enum(ScoreChangeType))
    clinically_significant = Column(Boolean, default=False)

    is_transmitted = Column(Boolean, default=False)
    transmitted_time = Column(DateTime(timezone=True))
    transmission_status = Column(String(50))
    transmission_error = Column(Text)

    notes = Column(Text)
    extra_data = Column(JSON, default={})

    patient = relationship("Patient", back_populates="psqi_results")


class ScoreHistory(Base):
    __tablename__ = "score_histories"

    id = Column(Integer, primary_key=True, index=True)

    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    result_id = Column(Integer, ForeignKey("psqi_results.id"), nullable=False)
    assessment_task_id = Column(Integer, ForeignKey("assessment_tasks.id"), nullable=False)

    assessment_date = Column(DateTime(timezone=True), nullable=False)
    total_score = Column(Float, nullable=False)
    component_scores = Column(JSON, default={})

    is_baseline = Column(Boolean, default=False)
    is_latest = Column(Boolean, default=False)

    notes = Column(Text)

    patient = relationship("Patient", back_populates="score_histories")


class ResultFeedback(Base):
    __tablename__ = "result_feedbacks"

    id = Column(Integer, primary_key=True, index=True)

    feedback_no = Column(String(50), unique=True, index=True, nullable=False)
    result_id = Column(Integer, ForeignKey("psqi_results.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("assessment_tasks.id"), nullable=False)

    feedback_to_department = Column(String(200))
    feedback_to_doctor = Column(String(100))
    feedback_content = Column(Text, nullable=False)

    feedback_time = Column(DateTime(timezone=True), nullable=False)
    feedback_by = Column(String(100))

    is_read = Column(Boolean, default=False)
    read_time = Column(DateTime(timezone=True))
    doctor_response = Column(Text)
    response_time = Column(DateTime(timezone=True))

    priority = Column(Integer, default=0)
    requires_follow_up = Column(Boolean, default=False)
    follow_up_suggestion = Column(Text)

    extra_data = Column(JSON, default={})
