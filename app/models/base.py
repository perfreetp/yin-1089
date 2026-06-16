from sqlalchemy import Column, Integer, String, Boolean, Text, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.sqlite import JSON

from app.database import Base
from app.models.enums import HospitalZone, PatientType


class Hospital(Base):
    __tablename__ = "hospitals"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    zone = Column(Enum(HospitalZone), nullable=False)
    address = Column(String(500))
    contact_phone = Column(String(50))
    department = Column(String(200))
    is_active = Column(Boolean, default=True)
    config = Column(JSON, default={})

    tasks = relationship("AssessmentTask", back_populates="hospital")
    staff = relationship("FollowUpStaff", back_populates="hospital")
    queues = relationship("FollowUpQueue", back_populates="hospital")


class FollowUpStaff(Base):
    __tablename__ = "follow_up_staff"

    id = Column(Integer, primary_key=True, index=True)
    staff_no = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    phone = Column(String(50))
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=False)
    department = Column(String(200))
    title = Column(String(100))
    skills = Column(JSON, default=[])
    max_tasks_per_day = Column(Integer, default=20)
    is_active = Column(Boolean, default=True)

    hospital = relationship("Hospital", back_populates="staff")
    assigned_queues = relationship("FollowUpQueue", foreign_keys="FollowUpQueue.assigned_staff_id", back_populates="assigned_staff")
    contact_records = relationship("ContactRecord", back_populates="staff")


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    patient_no = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    gender = Column(String(10))
    age = Column(Integer)
    phone = Column(String(50), nullable=False)
    id_card = Column(String(50))
    address = Column(String(500))
    patient_type = Column(Enum(PatientType), nullable=False)
    is_key_patient = Column(Boolean, default=False)
    key_patient_reason = Column(Text)
    notes = Column(Text)
    medical_history = Column(JSON, default={})

    tasks = relationship("AssessmentTask", back_populates="patient")
    queues = relationship("FollowUpQueue", back_populates="patient")
    psqi_results = relationship("PSQIResult", back_populates="patient")
    score_histories = relationship("ScoreHistory", back_populates="patient")
