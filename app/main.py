from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from datetime import datetime

from app.config import settings
from app.database import init_db
from app.api import api_router
from app.services.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("正在初始化数据库...")
    await init_db()
    logger.info("数据库初始化完成")

    if settings.SCHEDULER_ENABLED:
        logger.info("正在启动定时任务调度器...")
        await start_scheduler()
        logger.info("定时任务调度器启动完成")

    yield

    if settings.SCHEDULER_ENABLED:
        logger.info("正在关闭定时任务调度器...")
        await stop_scheduler()
        logger.info("定时任务调度器已关闭")

    logger.info("应用已关闭")


app = FastAPI(
    title=settings.APP_NAME,
    description="""
    医院集团随访中心PSQI管理系统后端API

    ## 功能模块

    - **基础数据管理**: 院区、随访员、患者信息管理
    - **任务接入**: 接收门诊开立的PSQI评估任务，自动识别首次/复测场景
    - **规则引擎**: 按患者类型配置随访频次、联系间隔控制、超期升级规则
    - **随访队列**: 自动生成待办队列、智能分配、状态流转、联系记录
    - **告警中心**: 超期检测、升级提醒、重点患者告警
    - **结果回传**: PSQI评分计算、分数变化判定、结果回传门诊视图
    - **统计分析**: 院区执行率、随访员绩效、PSQI趋势分析

    ## 系统特点

    - 多院区统一运营管理
    - 智能任务分配策略（轮询、负载均衡、技能匹配、优先级）
    - 灵活的规则配置引擎
    - 完善的告警和升级机制
    - PSQI评分自动计算和变化趋势分析
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/", tags=["系统"])
async def root():
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "status": "running",
        "time": datetime.now().isoformat(),
        "docs": "/docs",
        "api_prefix": "/api/v1"
    }


@app.get("/health", tags=["系统"])
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "scheduler_enabled": settings.SCHEDULER_ENABLED
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.APP_DEBUG
    )
