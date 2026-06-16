from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import date, datetime

from app.database import get_db
from app.schemas import (
    PSQIResultCreate, PSQIResultUpdate, PSQIResultResponse,
    ScoreHistoryResponse, ResultFeedbackCreate, ResultFeedbackResponse,
    SuccessResponse, PaginationResponse, BatchTransmitResponse
)
from app.services.result_service import ResultService

router = APIRouter()
result_service = ResultService()


@router.get("", response_model=SuccessResponse[PaginationResponse[PSQIResultResponse]])
async def get_results(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    hospital_id: Optional[int] = None,
    patient_id: Optional[int] = None,
    is_transmitted: Optional[bool] = None,
    clinically_significant: Optional[bool] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db)
):
    start_datetime = datetime.combine(start_date, datetime.min.time()) if start_date else None
    end_datetime = datetime.combine(end_date, datetime.max.time()) if end_date else None

    filters = {}
    if hospital_id:
        filters["hospital_id"] = hospital_id
    if patient_id:
        filters["patient_id"] = patient_id
    if is_transmitted is not None:
        filters["is_transmitted"] = is_transmitted
    if clinically_significant is not None:
        filters["clinically_significant"] = clinically_significant

    skip = (page - 1) * page_size
    items, total = await result_service.get_multi(
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


@router.get("/untransmitted", response_model=SuccessResponse[PaginationResponse[PSQIResultResponse]])
async def get_untransmitted_results(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    hospital_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    skip = (page - 1) * page_size
    items, total = await result_service.get_untransmitted_results(
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


@router.get("/pending/list", response_model=SuccessResponse[PaginationResponse[PSQIResultResponse]])
async def get_pending_transmission_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    hospital_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    transmission_status: Optional[str] = None,
    failure_reason: Optional[str] = None,
    include_failed: bool = True,
    db: AsyncSession = Depends(get_db)
):
    skip = (page - 1) * page_size
    items, total = await result_service.get_pending_transmission_list(
        db,
        hospital_id=hospital_id,
        start_date=start_date,
        end_date=end_date,
        transmission_status=transmission_status,
        failure_reason=failure_reason,
        include_failed=include_failed,
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


@router.get("/patient/{patient_id}/history", response_model=SuccessResponse[list[ScoreHistoryResponse]])
async def get_patient_score_history(
    patient_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    history = await result_service.get_patient_score_history(
        db,
        patient_id=patient_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )
    return SuccessResponse(data=history)


@router.get("/patient/{patient_id}/latest", response_model=SuccessResponse[PSQIResultResponse])
async def get_patient_latest_result(patient_id: int, db: AsyncSession = Depends(get_db)):
    result = await result_service.get_patient_latest_result(db, patient_id=patient_id)
    if not result:
        raise HTTPException(status_code=404, detail="未找到该患者的评估结果")
    return SuccessResponse(data=result)


@router.get("/{result_id}", response_model=SuccessResponse[PSQIResultResponse])
async def get_result(result_id: int, db: AsyncSession = Depends(get_db)):
    result = await result_service.get(db, result_id)
    if not result:
        raise HTTPException(status_code=404, detail="结果不存在")
    return SuccessResponse(data=result)


@router.get("/{result_id}/feedbacks", response_model=SuccessResponse[list[ResultFeedbackResponse]])
async def get_result_feedbacks(result_id: int, db: AsyncSession = Depends(get_db)):
    result = await result_service.get(db, result_id)
    if not result:
        raise HTTPException(status_code=404, detail="结果不存在")

    feedbacks = await result_service.get_result_feedbacks(db, result_id=result_id)
    return SuccessResponse(data=feedbacks)


@router.post("", response_model=SuccessResponse[PSQIResultResponse])
async def create_result(result_in: PSQIResultCreate, db: AsyncSession = Depends(get_db)):
    result = await result_service.create_result(db, obj_in=result_in)
    return SuccessResponse(data=result, message="PSQI结果创建成功")


@router.post("/batch-transmit", response_model=SuccessResponse)
async def batch_transmit_results(
    result_ids: Optional[List[int]] = None,
    hospital_id: Optional[int] = None,
    include_failed: bool = True,
    db: AsyncSession = Depends(get_db)
):
    count = await result_service.batch_transmit(
        db, result_ids=result_ids, include_failed=include_failed
    )
    return SuccessResponse(data={"transmitted_count": count}, message=f"成功批量回传 {count} 条结果")


@router.post("/batch-transmit/detailed", response_model=SuccessResponse[BatchTransmitResponse])
async def batch_transmit_with_details(
    result_ids: Optional[List[int]] = None,
    hospital_id: Optional[int] = None,
    failure_reason: Optional[str] = None,
    include_failed: bool = True,
    db: AsyncSession = Depends(get_db)
):
    result = await result_service.batch_transmit_with_details(
        db, result_ids=result_ids, hospital_id=hospital_id, failure_reason=failure_reason, include_failed=include_failed
    )
    return SuccessResponse(data=result, message="批量回传完成")


@router.post("/retry-failed", response_model=SuccessResponse)
async def retry_failed_transmissions(
    hospital_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    count = await result_service.retry_failed_transmissions(db, hospital_id=hospital_id)
    return SuccessResponse(data={"retried_count": count}, message=f"成功重试 {count} 条失败回传")


@router.post("/batch-retry/detailed", response_model=SuccessResponse[BatchTransmitResponse])
async def batch_retry_failed_detailed(
    hospital_id: Optional[int] = None,
    failure_reason: Optional[str] = None,
    result_ids: Optional[List[int]] = None,
    db: AsyncSession = Depends(get_db)
):
    result = await result_service.batch_retry_failed(
        db, hospital_id=hospital_id, failure_reason=failure_reason, result_ids=result_ids
    )
    return SuccessResponse(data=result, message="批量重试完成")


@router.post("/feedback", response_model=SuccessResponse[ResultFeedbackResponse])
async def create_feedback(feedback_in: ResultFeedbackCreate, db: AsyncSession = Depends(get_db)):
    result = await result_service.get(db, feedback_in.result_id)
    if not result:
        raise HTTPException(status_code=404, detail="结果不存在")

    feedback = await result_service.create_feedback(db, obj_in=feedback_in)
    return SuccessResponse(data=feedback, message="结果反馈创建成功")


@router.post("/feedback/{feedback_id}/read", response_model=SuccessResponse[ResultFeedbackResponse])
async def mark_feedback_read(
    feedback_id: int,
    doctor_response: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    feedback = await result_service.mark_feedback_read(
        db, feedback_id=feedback_id, doctor_response=doctor_response)
    if not feedback:
        raise HTTPException(status_code=404, detail="反馈不存在")
    return SuccessResponse(data=feedback, message="反馈已标记为已读")


@router.put("/{result_id}", response_model=SuccessResponse[PSQIResultResponse])
async def update_result(
    result_id: int,
    result_in: PSQIResultUpdate,
    db: AsyncSession = Depends(get_db)
):
    result = await result_service.get(db, result_id)
    if not result:
        raise HTTPException(status_code=404, detail="结果不存在")

    updated = await result_service.update(db, db_obj=result, obj_in=result_in)
    return SuccessResponse(data=updated, message="结果更新成功")


@router.post("/{result_id}/transmit", response_model=SuccessResponse[PSQIResultResponse])
async def transmit_result(result_id: int, db: AsyncSession = Depends(get_db)):
    result = await result_service.transmit_to_clinic(db, result_id=result_id)
    if not result:
        raise HTTPException(status_code=404, detail="结果不存在")
    return SuccessResponse(data=result, message="结果已回传门诊")
