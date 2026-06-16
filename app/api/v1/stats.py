from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import date

from app.database import get_db
from app.schemas import (
    HospitalStatsResponse, StaffPerformanceResponse, ScoreTrendResponse,
    SuccessResponse, PaginationResponse, PatientResponse
)
from app.schemas.stats import ExecutiveDashboardResponse
from app.services.stats_service import StatsService

router = APIRouter()
stats_service = StatsService()


@router.get("/dashboard", response_model=SuccessResponse[ExecutiveDashboardResponse])
async def get_executive_dashboard(db: AsyncSession = Depends(get_db)):
    dashboard = await stats_service.get_executive_dashboard(db)
    return SuccessResponse(data=dashboard)


@router.get("/hospital/{hospital_id}", response_model=SuccessResponse[HospitalStatsResponse])
async def get_hospital_stats(
    hospital_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db)
):
    try:
        stats = await stats_service.get_hospital_stats(
            db,
            hospital_id=hospital_id,
            start_date=start_date,
            end_date=end_date
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return SuccessResponse(data=stats)


@router.get("/staff/{staff_id}", response_model=SuccessResponse[StaffPerformanceResponse])
async def get_staff_performance(
    staff_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db)
):
    try:
        stats = await stats_service.get_staff_performance(
            db,
            staff_id=staff_id,
            start_date=start_date,
            end_date=end_date
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return SuccessResponse(data=stats)


@router.get("/score-trend", response_model=SuccessResponse[ScoreTrendResponse])
async def get_score_trend(
    hospital_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db)
):
    trend = await stats_service.get_score_trend(
        db,
        hospital_id=hospital_id,
        start_date=start_date,
        end_date=end_date
    )
    return SuccessResponse(data=trend)


@router.get("/key-patients", response_model=SuccessResponse[PaginationResponse[PatientResponse]])
async def get_key_patients(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    hospital_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    skip = (page - 1) * page_size
    items, total = await stats_service.get_key_patients(
        db,
        hospital_id=hospital_id,
        skip=skip,
        limit=page_size
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


@router.post("/key-patients/{patient_id}", response_model=SuccessResponse[PatientResponse])
async def mark_key_patient(
    patient_id: int,
    is_key: bool,
    reason: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    patient = await stats_service.mark_key_patient(
        db,
        patient_id=patient_id,
        is_key=is_key,
        reason=reason
    )
    if not patient:
        raise HTTPException(status_code=404, detail="患者不存在")

    message = "已标记为重点患者" if is_key else "已取消重点患者标记"
    return SuccessResponse(data=patient, message=message)


@router.post("/retry-failed-tasks", response_model=SuccessResponse)
async def retry_failed_tasks(
    hospital_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    count = await stats_service.retry_failed_tasks(db, hospital_id=hospital_id)
    return SuccessResponse(data={"retried_count": count}, message=f"成功重试 {count} 条失败任务")
