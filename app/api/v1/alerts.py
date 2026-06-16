from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import date, datetime

from app.database import get_db
from app.models.enums import AlertLevel, AlertType
from app.schemas import (
    AlertCreate, AlertUpdate, AlertResponse, AlertEscalationLogResponse,
    SuccessResponse, PaginationResponse
)
from app.services.alert_service import AlertService

router = APIRouter()
alert_service = AlertService()


@router.get("", response_model=SuccessResponse[PaginationResponse[AlertResponse]])
async def get_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    hospital_id: Optional[int] = None,
    alert_type: Optional[AlertType] = None,
    alert_level: Optional[AlertLevel] = None,
    is_read: Optional[bool] = None,
    is_handled: Optional[bool] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db)
):
    start_datetime = datetime.combine(start_date, datetime.min.time()) if start_date else None
    end_datetime = datetime.combine(end_date, datetime.max.time()) if end_date else None

    filters = {}
    if hospital_id:
        filters["hospital_id"] = hospital_id
    if alert_type:
        filters["alert_type"] = alert_type
    if alert_level:
        filters["alert_level"] = alert_level
    if is_read is not None:
        filters["is_read"] = is_read
    if is_handled is not None:
        filters["is_handled"] = is_handled

    skip = (page - 1) * page_size
    items, total = await alert_service.get_multi(
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


@router.get("/unhandled", response_model=SuccessResponse[PaginationResponse[AlertResponse]])
async def get_unhandled_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    hospital_id: Optional[int] = None,
    min_level: Optional[AlertLevel] = None,
    db: AsyncSession = Depends(get_db)
):
    skip = (page - 1) * page_size
    items, total = await alert_service.get_unhandled_alerts(
        db,
        hospital_id=hospital_id,
        min_level=min_level,
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


@router.get("/{alert_id}", response_model=SuccessResponse[AlertResponse])
async def get_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    alert = await alert_service.get(db, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")
    return SuccessResponse(data=alert)


@router.post("", response_model=SuccessResponse[AlertResponse])
async def create_alert(alert_in: AlertCreate, db: AsyncSession = Depends(get_db)):
    alert = await alert_service.create(db, obj_in=alert_in)
    return SuccessResponse(data=alert, message="告警创建成功")


@router.put("/{alert_id}", response_model=SuccessResponse[AlertResponse])
async def update_alert(
    alert_id: int,
    alert_in: AlertUpdate,
    db: AsyncSession = Depends(get_db)
):
    alert = await alert_service.get(db, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")

    updated = await alert_service.update(db, db_obj=alert, obj_in=alert_in)
    return SuccessResponse(data=updated, message="告警更新成功")


@router.post("/{alert_id}/read", response_model=SuccessResponse[AlertResponse])
async def mark_alert_read(
    alert_id: int,
    read_by: str,
    db: AsyncSession = Depends(get_db)
):
    alert = await alert_service.mark_as_read(db, alert_id=alert_id, read_by=read_by)
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")
    return SuccessResponse(data=alert, message="告警已标记为已读")


@router.post("/{alert_id}/handle", response_model=SuccessResponse[AlertResponse])
async def mark_alert_handled(
    alert_id: int,
    handled_by: str,
    handle_note: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    alert = await alert_service.mark_as_handled(
        db, alert_id=alert_id, handled_by=handled_by, handle_note=handle_note)
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")
    return SuccessResponse(data=alert, message="告警已标记为已处理")


@router.post("/{alert_id}/escalate", response_model=SuccessResponse[AlertResponse])
async def escalate_alert(
    alert_id: int,
    escalation_reason: str,
    escalated_by: str,
    new_level: Optional[AlertLevel] = None,
    db: AsyncSession = Depends(get_db)
):
    alert = await alert_service.escalate_alert(
        db,
        alert_id=alert_id,
        escalation_reason=escalation_reason,
        escalated_by=escalated_by,
        new_level=new_level
    )
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")
    return SuccessResponse(data=alert, message="告警已升级")


@router.get("/{alert_id}/escalation-history", response_model=SuccessResponse[list[AlertEscalationLogResponse]])
async def get_alert_escalation_history(alert_id: int, db: AsyncSession = Depends(get_db)):
    alert = await alert_service.get(db, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")

    history = await alert_service.get_alert_escalation_history(db, alert_id=alert_id)
    return SuccessResponse(data=history)


@router.post("/run-checks", response_model=SuccessResponse)
async def run_alert_checks(db: AsyncSession = Depends(get_db)):
    result = await alert_service.run_alert_checks(db)
    return SuccessResponse(data=result, message="告警检测完成")
