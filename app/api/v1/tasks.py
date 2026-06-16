from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime, date

from app.database import get_db
from app.models import AssessmentTask
from app.models.enums import TaskStatus, PatientType
from app.schemas import (
    AssessmentTaskCreate, AssessmentTaskUpdate, AssessmentTaskResponse,
    SuccessResponse, PaginationResponse
)
from app.services.task_service import TaskService

router = APIRouter()
task_service = TaskService()


@router.get("", response_model=SuccessResponse[PaginationResponse[AssessmentTaskResponse]])
async def get_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    hospital_id: Optional[int] = None,
    status: Optional[TaskStatus] = None,
    patient_type: Optional[PatientType] = None,
    is_retest: Optional[bool] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db)
):
    start_datetime = datetime.combine(start_date, datetime.min.time()) if start_date else None
    end_datetime = datetime.combine(end_date, datetime.max.time()) if end_date else None

    skip = (page - 1) * page_size
    items, total = await task_service.get_task_list(
        db,
        hospital_id=hospital_id,
        status=status,
        patient_type=patient_type,
        is_retest=is_retest,
        start_date=start_datetime,
        end_date=end_datetime,
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


@router.get("/{task_id}", response_model=SuccessResponse[AssessmentTaskResponse])
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await task_service.get(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return SuccessResponse(data=task)


@router.get("/no/{task_no}", response_model=SuccessResponse[AssessmentTaskResponse])
async def get_task_by_no(task_no: str, db: AsyncSession = Depends(get_db)):
    task = await task_service.get_by_task_no(db, task_no)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return SuccessResponse(data=task)


@router.post("", response_model=SuccessResponse[AssessmentTaskResponse])
async def create_task(task_in: AssessmentTaskCreate, db: AsyncSession = Depends(get_db)):
    task = await task_service.create_task(db, obj_in=task_in)
    return SuccessResponse(data=task, message="评估任务创建成功")


@router.put("/{task_id}", response_model=SuccessResponse[AssessmentTaskResponse])
async def update_task(
    task_id: int,
    task_in: AssessmentTaskUpdate,
    db: AsyncSession = Depends(get_db)
):
    task = await task_service.get(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    updated = await task_service.update(db, db_obj=task, obj_in=task_in)
    return SuccessResponse(data=updated, message="任务更新成功")


@router.patch("/{task_id}/status", response_model=SuccessResponse[AssessmentTaskResponse])
async def update_task_status(
    task_id: int,
    status: TaskStatus,
    notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    task = await task_service.update_task_status(
        db, task_id=task_id, status=status, notes=notes)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return SuccessResponse(data=task, message="任务状态更新成功")


@router.post("/{task_id}/cancel", response_model=SuccessResponse[AssessmentTaskResponse])
async def cancel_task(
    task_id: int,
    reason: str,
    db: AsyncSession = Depends(get_db)
):
    task = await task_service.cancel_task(db, task_id=task_id, reason=reason)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return SuccessResponse(data=task, message="任务已取消")


@router.post("/{task_id}/complete", response_model=SuccessResponse[AssessmentTaskResponse])
async def complete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await task_service.mark_task_completed(db, task_id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return SuccessResponse(data=task, message="任务已标记完成")


@router.post("/{task_id}/reassign", response_model=SuccessResponse[AssessmentTaskResponse])
async def reassign_task(
    task_id: int,
    reason: str,
    db: AsyncSession = Depends(get_db)
):
    task = await task_service.reassign_failed_task(
        db, task_id=task_id, reason=reason)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return SuccessResponse(data=task, message="任务已重新分派")


@router.get("/overdue", response_model=SuccessResponse[list[AssessmentTaskResponse]])
async def get_overdue_tasks(db: AsyncSession = Depends(get_db)):
    tasks = await task_service.get_overdue_tasks(db)
    return SuccessResponse(data=tasks)


@router.get("/patient/{patient_id}", response_model=SuccessResponse[list[AssessmentTaskResponse]])
async def get_patient_tasks(patient_id: int, db: AsyncSession = Depends(get_db)):
    tasks = await task_service.get_by_patient(db, patient_id=patient_id)
    return SuccessResponse(data=tasks)
