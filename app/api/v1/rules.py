from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.models import FollowUpRule, ContactIntervalRule
from app.models.enums import PatientType, ContactResult
from app.schemas import (
    FollowUpRuleCreate, FollowUpRuleUpdate, FollowUpRuleResponse,
    ContactIntervalRuleCreate, ContactIntervalRuleUpdate, ContactIntervalRuleResponse,
    SuccessResponse, PaginationResponse, RuleTrialResponse
)
from datetime import datetime
from app.services.rule_engine_service import RuleEngineService, ContactIntervalRuleService

router = APIRouter()

rule_service = RuleEngineService()
interval_rule_service = ContactIntervalRuleService()


@router.get("/follow-up", response_model=SuccessResponse[PaginationResponse[FollowUpRuleResponse]])
async def get_follow_up_rules(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    patient_type: Optional[PatientType] = None,
    is_retest: Optional[bool] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    filters = {}
    if patient_type:
        filters["patient_type"] = patient_type
    if is_retest is not None:
        filters["is_retest"] = is_retest
    if is_active is not None:
        filters["is_active"] = is_active

    skip = (page - 1) * page_size
    items, total = await rule_service.get_multi(
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


@router.get("/follow-up/applicable", response_model=SuccessResponse[FollowUpRuleResponse])
async def get_applicable_rule(
    patient_type: PatientType,
    is_retest: bool = False,
    db: AsyncSession = Depends(get_db)
):
    rule = await rule_service.get_applicable_rule(
        db, patient_type=patient_type, is_retest=is_retest
    )
    if not rule:
        raise HTTPException(status_code=404, detail="未找到适用的随访规则")
    return SuccessResponse(data=rule)


@router.get("/follow-up/{rule_id}", response_model=SuccessResponse[FollowUpRuleResponse])
async def get_follow_up_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    rule = await rule_service.get(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="随访规则不存在")
    return SuccessResponse(data=rule)


@router.post("/follow-up", response_model=SuccessResponse[FollowUpRuleResponse])
async def create_follow_up_rule(rule_in: FollowUpRuleCreate, db: AsyncSession = Depends(get_db)):
    rule = await rule_service.create(db, obj_in=rule_in)
    return SuccessResponse(data=rule, message="随访规则创建成功")


@router.put("/follow-up/{rule_id}", response_model=SuccessResponse[FollowUpRuleResponse])
async def update_follow_up_rule(
    rule_id: int,
    rule_in: FollowUpRuleUpdate,
    db: AsyncSession = Depends(get_db)
):
    rule = await rule_service.get(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="随访规则不存在")

    updated = await rule_service.update(db, db_obj=rule, obj_in=rule_in)
    return SuccessResponse(data=updated, message="随访规则更新成功")


@router.delete("/follow-up/{rule_id}", response_model=SuccessResponse)
async def delete_follow_up_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    rule = await rule_service.get(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="随访规则不存在")

    await rule_service.delete(db, id=rule_id)
    return SuccessResponse(message="随访规则删除成功")


@router.get("/interval", response_model=SuccessResponse[PaginationResponse[ContactIntervalRuleResponse]])
async def get_interval_rules(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    hospital_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    items = await interval_rule_service.get_all_active_rules(db, hospital_id=hospital_id)

    if is_active is not None:
        items = [item for item in items if item.is_active == is_active]

    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    paginated_items = items[start:end]

    total_pages = (total + page_size - 1) // page_size
    return SuccessResponse(
        data=PaginationResponse(
            items=paginated_items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    )


@router.get("/interval/applicable", response_model=SuccessResponse[ContactIntervalRuleResponse])
async def get_applicable_interval_rule(
    contact_result: Optional[ContactResult] = None,
    hospital_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    rule = await interval_rule_service.get_applicable_rule(
        db, contact_result=contact_result, hospital_id=hospital_id
    )
    if not rule:
        raise HTTPException(status_code=404, detail="未找到适用的联系间隔规则")
    return SuccessResponse(data=rule)


@router.get("/interval/{rule_id}", response_model=SuccessResponse[ContactIntervalRuleResponse])
async def get_interval_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    rule = await interval_rule_service.get(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="联系间隔规则不存在")
    return SuccessResponse(data=rule)


@router.post("/interval", response_model=SuccessResponse[ContactIntervalRuleResponse])
async def create_interval_rule(rule_in: ContactIntervalRuleCreate, db: AsyncSession = Depends(get_db)):
    rule = await interval_rule_service.create(db, obj_in=rule_in)
    return SuccessResponse(data=rule, message="联系间隔规则创建成功")


@router.put("/interval/{rule_id}", response_model=SuccessResponse[ContactIntervalRuleResponse])
async def update_interval_rule(
    rule_id: int,
    rule_in: ContactIntervalRuleUpdate,
    db: AsyncSession = Depends(get_db)
):
    rule = await interval_rule_service.get(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="联系间隔规则不存在")

    updated = await interval_rule_service.update(db, db_obj=rule, obj_in=rule_in)
    return SuccessResponse(data=updated, message="联系间隔规则更新成功")


@router.delete("/interval/{rule_id}", response_model=SuccessResponse)
async def delete_interval_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    rule = await interval_rule_service.get(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="联系间隔规则不存在")

    await interval_rule_service.delete(db, id=rule_id)
    return SuccessResponse(message="联系间隔规则删除成功")


@router.get("/frequency/calculate", response_model=SuccessResponse)
async def calculate_follow_up_frequency(
    patient_type: PatientType,
    is_retest: bool = False,
    clinical_priority: int = 0,
    db: AsyncSession = Depends(get_db)
):
    frequency = await rule_service.determine_follow_up_frequency(
        db,
        patient_type=patient_type,
        is_retest=is_retest,
        clinical_priority=clinical_priority
    )
    return SuccessResponse(data=frequency)


@router.get("/trial", response_model=SuccessResponse[RuleTrialResponse])
async def trial_rule(
    patient_type: PatientType,
    is_retest: bool = False,
    hospital_id: Optional[int] = None,
    last_contact_result: Optional[ContactResult] = None,
    last_contact_time: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db)
):
    result = await rule_service.trial_calculate(
        db,
        patient_type=patient_type,
        is_retest=is_retest,
        hospital_id=hospital_id,
        last_contact_result=last_contact_result,
        last_contact_time=last_contact_time
    )
    return SuccessResponse(data=result, message="规则试算完成")
