from sqlalchemy import Column, Integer, String, Boolean, Text, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.sqlite import JSON

from app.database import Base
from app.models.enums import TaskStatus, PatientType


class AssessmentTask(Base):
    __tablename__ = "assessment_tasks"

    id = Column(Integer, primary_key=True, index=True)

    task_no = Column(String(50), unique=True, index=True, nullable=False)
    source_task_no = Column(String(100))
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)

    patient_type = Column(Enum(PatientType), nullable=False)
    is_retest = Column(Boolean, default=False)
    assessment_type = Column(String(100), default="PSQI")

    order_department = Column(String(200))
    order_doctor = Column(String(100))
    order_time = Column(DateTime(timezone=True))
    clinical_diagnosis = Column(Text)
    clinical_notes = Column(Text)

    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)
    priority = Column(Integer, default=0)
    deadline = Column(DateTime(timezone=True))

    follow_up_count = Column(Integer, default=0)
    current_follow_up_round = Column(Integer, default=1)
    max_follow_up_count = Column(Integer, default=3)

    is_active = Column(Boolean, default=True)
    extra_data = Column(JSON, default={})

    hospital = relationship("Hospital", back_populates="tasks")
    patient = relationship("Patient", back_populates="tasks")
    queues = relationship("FollowUpQueue", back_populates="task")
