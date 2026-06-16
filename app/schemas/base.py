from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

from app.models.enums import HospitalZone, PatientType


class HospitalBase(BaseModel):
    code: str = Field(..., max_length=50, description="院区编码")
    name: str = Field(..., max_length=200, description="院区名称")
    zone: HospitalZone = Field(..., description="院区区域")
    address: Optional[str] = Field(None, max_length=500, description="地址")
    contact_phone: Optional[str] = Field(None, max_length=50, description="联系电话")
    department: Optional[str] = Field(None, max_length=200, description="科室")
    is_active: bool = Field(True, description="是否启用")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="配置")


class HospitalCreate(HospitalBase):
    pass


class HospitalUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    zone: Optional[HospitalZone] = None
    address: Optional[str] = Field(None, max_length=500)
    contact_phone: Optional[str] = Field(None, max_length=50)
    department: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


class HospitalResponse(HospitalBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FollowUpStaffBase(BaseModel):
    staff_no: str = Field(..., max_length=50, description="员工编号")
    name: str = Field(..., max_length=100, description="姓名")
    phone: Optional[str] = Field(None, max_length=50, description="电话")
    hospital_id: int = Field(..., description="院区ID")
    department: Optional[str] = Field(None, max_length=200, description="部门")
    title: Optional[str] = Field(None, max_length=100, description="职称")
    skills: Optional[list] = Field(default_factory=list, description="技能标签")
    max_tasks_per_day: int = Field(20, ge=1, description="每日最大任务数")
    is_active: bool = Field(True, description="是否启用")


class FollowUpStaffCreate(FollowUpStaffBase):
    pass


class FollowUpStaffUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=50)
    hospital_id: Optional[int] = None
    department: Optional[str] = Field(None, max_length=200)
    title: Optional[str] = Field(None, max_length=100)
    skills: Optional[list] = None
    max_tasks_per_day: Optional[int] = None
    is_active: Optional[bool] = None


class FollowUpStaffResponse(FollowUpStaffBase):
    id: int
    created_at: datetime
    updated_at: datetime
    hospital: Optional[HospitalResponse] = None

    class Config:
        from_attributes = True


class PatientBase(BaseModel):
    patient_no: str = Field(..., max_length=50, description="患者编号")
    name: str = Field(..., max_length=100, description="姓名")
    gender: Optional[str] = Field(None, max_length=10, description="性别")
    age: Optional[int] = Field(None, ge=0, description="年龄")
    phone: str = Field(..., max_length=50, description="联系电话")
    id_card: Optional[str] = Field(None, max_length=50, description="身份证号")
    address: Optional[str] = Field(None, max_length=500, description="地址")
    patient_type: PatientType = Field(..., description="患者类型")
    is_key_patient: bool = Field(False, description="是否重点患者")
    key_patient_reason: Optional[str] = Field(None, description="重点患者原因")
    notes: Optional[str] = Field(None, description="备注")
    medical_history: Optional[Dict[str, Any]] = Field(default_factory=dict, description="病史")


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    gender: Optional[str] = Field(None, max_length=10)
    age: Optional[int] = None
    phone: Optional[str] = Field(None, max_length=50)
    id_card: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=500)
    patient_type: Optional[PatientType] = None
    is_key_patient: Optional[bool] = None
    key_patient_reason: Optional[str] = None
    notes: Optional[str] = None
    medical_history: Optional[Dict[str, Any]] = None


class PatientResponse(PatientBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
