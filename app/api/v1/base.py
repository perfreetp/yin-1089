from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import date

from app.database import get_db
from app.models import Hospital, FollowUpStaff, Patient
from app.schemas import (
    HospitalCreate, HospitalUpdate, HospitalResponse,
    FollowUpStaffCreate, FollowUpStaffUpdate, FollowUpStaffResponse,
    PatientCreate, PatientUpdate, PatientResponse,
    SuccessResponse, PaginationResponse
)
from app.services.base_service import BaseService

router = APIRouter()

hospital_service = BaseService[Hospital, HospitalCreate, HospitalUpdate](Hospital)
staff_service = BaseService[FollowUpStaff, FollowUpStaffCreate, FollowUpStaffUpdate](FollowUpStaff)
patient_service = BaseService[Patient, PatientCreate, PatientUpdate](Patient)


@router.get("/hospitals", response_model=SuccessResponse[PaginationResponse[HospitalResponse]])
async def get_hospitals(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: Optional[bool] = None,
    zone: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    filters = {}
    if is_active is not None:
        filters["is_active"] = is_active
    if zone:
        filters["zone"] = zone

    skip = (page - 1) * page_size
    items, total = await hospital_service.get_multi(
        db, skip=skip, limit=page_size, filters=filters
    )

    total_pages = (total + page_size - 1) // page_size
    return SuccessResponse(
        data=PaginationResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    )


@router.get("/hospitals/{hospital_id}", response_model=SuccessResponse[HospitalResponse])
async def get_hospital(hospital_id: int, db: AsyncSession = Depends(get_db)):
    hospital = await hospital_service.get(db, hospital_id)
    if not hospital:
        raise HTTPException(status_code=404, detail="院区不存在")
    return SuccessResponse(data=hospital)


@router.post("/hospitals", response_model=SuccessResponse[HospitalResponse])
async def create_hospital(hospital_in: HospitalCreate, db: AsyncSession = Depends(get_db)):
    hospital = await hospital_service.create(db, obj_in=hospital_in)
    return SuccessResponse(data=hospital, message="院区创建成功")


@router.put("/hospitals/{hospital_id}", response_model=SuccessResponse[HospitalResponse])
async def update_hospital(
    hospital_id: int,
    hospital_in: HospitalUpdate,
    db: AsyncSession = Depends(get_db)
):
    hospital = await hospital_service.get(db, hospital_id)
    if not hospital:
        raise HTTPException(status_code=404, detail="院区不存在")

    updated = await hospital_service.update(db, db_obj=hospital, obj_in=hospital_in)
    return SuccessResponse(data=updated, message="院区更新成功")


@router.delete("/hospitals/{hospital_id}", response_model=SuccessResponse)
async def delete_hospital(hospital_id: int, db: AsyncSession = Depends(get_db)):
    hospital = await hospital_service.get(db, hospital_id)
    if not hospital:
        raise HTTPException(status_code=404, detail="院区不存在")

    await hospital_service.delete(db, id=hospital_id)
    return SuccessResponse(message="院区删除成功")


@router.get("/staff", response_model=SuccessResponse[PaginationResponse[FollowUpStaffResponse]])
async def get_staff_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    hospital_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    filters = {}
    if hospital_id:
        filters["hospital_id"] = hospital_id
    if is_active is not None:
        filters["is_active"] = is_active

    skip = (page - 1) * page_size
    items, total = await staff_service.get_multi(
        db, skip=skip, limit=page_size, filters=filters
    )

    total_pages = (total + page_size - 1) // page_size
    return SuccessResponse(
        data=PaginationResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    )


@router.get("/staff/{staff_id}", response_model=SuccessResponse[FollowUpStaffResponse])
async def get_staff(staff_id: int, db: AsyncSession = Depends(get_db)):
    staff = await staff_service.get(db, staff_id)
    if not staff:
        raise HTTPException(status_code=404, detail="随访员不存在")
    return SuccessResponse(data=staff)


@router.post("/staff", response_model=SuccessResponse[FollowUpStaffResponse])
async def create_staff(staff_in: FollowUpStaffCreate, db: AsyncSession = Depends(get_db)):
    staff = await staff_service.create(db, obj_in=staff_in)
    return SuccessResponse(data=staff, message="随访员创建成功")


@router.put("/staff/{staff_id}", response_model=SuccessResponse[FollowUpStaffResponse])
async def update_staff(
    staff_id: int,
    staff_in: FollowUpStaffUpdate,
    db: AsyncSession = Depends(get_db)
):
    staff = await staff_service.get(db, staff_id)
    if not staff:
        raise HTTPException(status_code=404, detail="随访员不存在")

    updated = await staff_service.update(db, db_obj=staff, obj_in=staff_in)
    return SuccessResponse(data=updated, message="随访员更新成功")


@router.delete("/staff/{staff_id}", response_model=SuccessResponse)
async def delete_staff(staff_id: int, db: AsyncSession = Depends(get_db)):
    staff = await staff_service.get(db, staff_id)
    if not staff:
        raise HTTPException(status_code=404, detail="随访员不存在")

    await staff_service.delete(db, id=staff_id)
    return SuccessResponse(message="随访员删除成功")


@router.get("/patients", response_model=SuccessResponse[PaginationResponse[PatientResponse]])
async def get_patients(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    patient_type: Optional[str] = None,
    is_key_patient: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    filters = {}
    if patient_type:
        filters["patient_type"] = patient_type
    if is_key_patient is not None:
        filters["is_key_patient"] = is_key_patient

    skip = (page - 1) * page_size
    items, total = await patient_service.get_multi(
        db, skip=skip, limit=page_size, filters=filters
    )

    total_pages = (total + page_size - 1) // page_size
    return SuccessResponse(
        data=PaginationResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    )


@router.get("/patients/{patient_id}", response_model=SuccessResponse[PatientResponse])
async def get_patient(patient_id: int, db: AsyncSession = Depends(get_db)):
    patient = await patient_service.get(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="患者不存在")
    return SuccessResponse(data=patient)


@router.get("/patients/no/{patient_no}", response_model=SuccessResponse[PatientResponse])
async def get_patient_by_no(patient_no: str, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    result = await db.execute(select(Patient).filter(Patient.patient_no == patient_no))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="患者不存在")
    return SuccessResponse(data=patient)


@router.post("/patients", response_model=SuccessResponse[PatientResponse])
async def create_patient(patient_in: PatientCreate, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    result = await db.execute(select(Patient).filter(Patient.patient_no == patient_in.patient_no))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="患者编号已存在")

    patient = await patient_service.create(db, obj_in=patient_in)
    return SuccessResponse(data=patient, message="患者创建成功")


@router.put("/patients/{patient_id}", response_model=SuccessResponse[PatientResponse])
async def update_patient(
    patient_id: int,
    patient_in: PatientUpdate,
    db: AsyncSession = Depends(get_db)
):
    patient = await patient_service.get(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="患者不存在")

    updated = await patient_service.update(db, db_obj=patient, obj_in=patient_in)
    return SuccessResponse(data=updated, message="患者信息更新成功")


@router.delete("/patients/{patient_id}", response_model=SuccessResponse)
async def delete_patient(patient_id: int, db: AsyncSession = Depends(get_db)):
    patient = await patient_service.get(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="患者不存在")

    await patient_service.delete(db, id=patient_id)
    return SuccessResponse(message="患者删除成功")
