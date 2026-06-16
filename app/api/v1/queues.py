from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import date, datetime

from app.database import get_db
from app.models.enums import QueueStatus
from app.schemas import (
    FollowUpQueueCreate, FollowUpQueueUpdate, FollowUpQueueResponse,
    ContactRecordCreate, ContactRecordResponse,
    SuccessResponse, PaginationResponse
)
from app.services.queue_service import QueueService

router = APIRouter()
queue_service = QueueService()


@router.get("", response_model=SuccessResponse[PaginationResponse[FollowUpQueueResponse]])
async def get_queues(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    hospital_id: Optional[int] = None,
    status: Optional[QueueStatus] = None,
    patient_id: Optional[int] = None,
    assigned_staff_id: Optional[int] = None,
    is_escalated: Optional[bool] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db)
):
    start_datetime = datetime.combine(start_date, datetime.min.time()) if start_date else None
    end_datetime = datetime.combine(end_date, datetime.max.time()) if end_date else None

    filters = {}
    if hospital_id:
        filters["hospital_id"] = hospital_id
    if status:
        filters["status"] = status
    if patient_id:
        filters["patient_id"] = patient_id
    if assigned_staff_id:
        filters["assigned_staff_id"] = assigned_staff_id
    if is_escalated is not None:
        filters["is_escalated"] = is_escalated

    skip = (page - 1) * page_size
    items, total = await queue_service.get_multi(
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


@router.get("/pending", response_model=SuccessResponse[PaginationResponse[FollowUpQueueResponse]])
async def get_pending_queues(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    hospital_id: Optional[int] = None,
    staff_id: Optional[int] = None,
    priority: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    skip = (page - 1) * page_size
    items, total = await queue_service.get_pending_queues(
        db,
        hospital_id=hospital_id,
        staff_id=staff_id,
        priority=priority,
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


@router.get("/overdue", response_model=SuccessResponse[list[FollowUpQueueResponse]])
async def get_overdue_queues(
    hospital_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    queues = await queue_service.get_overdue_queues(db, hospital_id=hospital_id)
    return SuccessResponse(data=queues)


@router.post("/generate-daily", response_model=SuccessResponse)
async def generate_daily_queues(db: AsyncSession = Depends(get_db)):
    count = await queue_service.generate_daily_queues(db)
    return SuccessResponse(data={"generated_count": count}, message=f"成功生成 {count} 条每日队列")


@router.post("", response_model=SuccessResponse[FollowUpQueueResponse])
async def create_queue(queue_in: FollowUpQueueCreate, db: AsyncSession = Depends(get_db)):
    queue = await queue_service.create(db, obj_in=queue_in)
    return SuccessResponse(data=queue, message="队列创建成功")


@router.get("/{queue_id}", response_model=SuccessResponse[FollowUpQueueResponse])
async def get_queue(queue_id: int, db: AsyncSession = Depends(get_db)):
    queue = await queue_service.get(db, queue_id)
    if not queue:
        raise HTTPException(status_code=404, detail="队列不存在")
    return SuccessResponse(data=queue)


@router.put("/{queue_id}", response_model=SuccessResponse[FollowUpQueueResponse])
async def update_queue(
    queue_id: int,
    queue_in: FollowUpQueueUpdate,
    db: AsyncSession = Depends(get_db)
):
    queue = await queue_service.get(db, queue_id)
    if not queue:
        raise HTTPException(status_code=404, detail="队列不存在")

    updated = await queue_service.update(db, db_obj=queue, obj_in=queue_in)
    return SuccessResponse(data=updated, message="队列更新成功")


@router.post("/{queue_id}/start", response_model=SuccessResponse[FollowUpQueueResponse])
async def start_follow_up(
    queue_id: int,
    staff_id: int,
    db: AsyncSession = Depends(get_db)
):
    queue = await queue_service.start_follow_up(db, queue_id=queue_id, staff_id=staff_id)
    if not queue:
        raise HTTPException(status_code=404, detail="队列不存在")
    return SuccessResponse(data=queue, message="随访已开始")


@router.post("/{queue_id}/complete", response_model=SuccessResponse[FollowUpQueueResponse])
async def complete_queue(
    queue_id: int,
    staff_id: int,
    completion_note: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    queue = await queue_service.complete_queue(
        db, queue_id=queue_id, staff_id=staff_id, completion_note=completion_note)
    if not queue:
        raise HTTPException(status_code=404, detail="队列不存在")
    return SuccessResponse(data=queue, message="随访已完成")


@router.post("/{queue_id}/escalate", response_model=SuccessResponse[FollowUpQueueResponse])
async def escalate_queue(
    queue_id: int,
    reason: str,
    db: AsyncSession = Depends(get_db)
):
    queue = await queue_service.escalate_queue(db, queue_id=queue_id, reason=reason)
    if not queue:
        raise HTTPException(status_code=404, detail="队列不存在")
    return SuccessResponse(data=queue, message="队列已升级")


@router.post("/{queue_id}/reassign", response_model=SuccessResponse[FollowUpQueueResponse])
async def reassign_queue(
    queue_id: int,
    new_staff_id: int,
    reason: str,
    db: AsyncSession = Depends(get_db)
):
    queue = await queue_service.reassign_queue(
        db, queue_id=queue_id, new_staff_id=new_staff_id, reason=reason)
    if not queue:
        raise HTTPException(status_code=404, detail="队列不存在")
    return SuccessResponse(data=queue, message="队列已重新分配")


@router.post("/{queue_id}/contact", response_model=SuccessResponse[ContactRecordResponse])
async def record_contact(
    queue_id: int,
    contact_data: ContactRecordCreate,
    db: AsyncSession = Depends(get_db)
):
    if contact_data.queue_id != queue_id:
        raise HTTPException(
            status_code=400,
            detail=f"请求体中的队列ID({contact_data.queue_id})与URL中的队列ID({queue_id})不一致"
        )

    queue = await queue_service.get(db, queue_id)
    if not queue:
        raise HTTPException(status_code=404, detail="队列不存在")

    contact = await queue_service.record_contact(db, contact_data=contact_data, expected_queue_id=queue_id)
    return SuccessResponse(data=contact, message="联系结果已记录")


@router.get("/{queue_id}/contacts", response_model=SuccessResponse[list[ContactRecordResponse]])
async def get_queue_contacts(queue_id: int, db: AsyncSession = Depends(get_db)):
    queue = await queue_service.get(db, queue_id)
    if not queue:
        raise HTTPException(status_code=404, detail="队列不存在")

    contacts = await queue_service.get_contact_history(db, queue_id=queue_id)
    return SuccessResponse(data=contacts)


@router.get("/patient/{patient_id}", response_model=SuccessResponse[list[ContactRecordResponse]])
async def get_patient_contact_history(patient_id: int, db: AsyncSession = Depends(get_db)):
    contacts = await queue_service.get_patient_contact_history(db, patient_id=patient_id)
    return SuccessResponse(data=contacts)
