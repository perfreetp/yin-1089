from fastapi import APIRouter

from app.api.v1.base import router as base_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.rules import router as rules_router
from app.api.v1.queues import router as queues_router
from app.api.v1.alerts import router as alerts_router
from app.api.v1.results import router as results_router
from app.api.v1.stats import router as stats_router

api_router = APIRouter()

api_router.include_router(base_router, prefix="/base", tags=["基础数据管理"])
api_router.include_router(tasks_router, prefix="/tasks", tags=["任务接入"])
api_router.include_router(rules_router, prefix="/rules", tags=["规则引擎"])
api_router.include_router(queues_router, prefix="/queues", tags=["随访队列"])
api_router.include_router(alerts_router, prefix="/alerts", tags=["告警中心"])
api_router.include_router(results_router, prefix="/results", tags=["结果回传"])
api_router.include_router(stats_router, prefix="/stats", tags=["统计分析"])

__all__ = ["api_router"]
