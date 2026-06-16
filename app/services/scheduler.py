from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

scheduler: AsyncIOScheduler | None = None


async def run_alert_checks():
    from app.database import AsyncSessionLocal
    from app.services.alert_service import AlertService

    logger.info("开始执行告警检测任务...")
    async with AsyncSessionLocal() as db:
        alert_service = AlertService()
        result = await alert_service.run_alert_checks(db)
        logger.info(f"告警检测完成，创建告警: {result}")

    logger.info("告警检测任务执行完成")


async def generate_daily_queues():
    from app.database import AsyncSessionLocal
    from app.services.queue_service import QueueService

    logger.info("开始生成每日待办队列...")
    async with AsyncSessionLocal() as db:
        queue_service = QueueService()
        count = await queue_service.generate_daily_queues(db)

    logger.info(f"每日待办队列生成完成，共生成 {count} 个队列")


async def retry_failed_tasks():
    from app.database import AsyncSessionLocal
    from app.services.stats_service import StatsService

    logger.info("开始重试失败任务...")
    async with AsyncSessionLocal() as db:
        stats_service = StatsService()
        retried = await stats_service.retry_failed_tasks(db)

    logger.info(f"失败任务重试完成，共重试 {retried} 个任务")


async def batch_transmit_results():
    from app.database import AsyncSessionLocal
    from app.services.result_service import ResultService

    logger.info("开始批量回传结果...")
    async with AsyncSessionLocal() as db:
        result_service = ResultService()
        transmitted = await result_service.batch_transmit(db)

    logger.info(f"结果批量回传完成，共回传 {transmitted} 个结果")


async def start_scheduler():
    global scheduler
    from app.config import settings

    scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

    scheduler.add_job(
        run_alert_checks,
        trigger=IntervalTrigger(minutes=settings.ALERT_CHECK_INTERVAL_MINUTES),
        id="alert_checks",
        name="告警检测",
        replace_existing=True,
        next_run_time=datetime.now(timezone.utc)
    )

    scheduler.add_job(
        generate_daily_queues,
        trigger=CronTrigger(hour=settings.DAILY_QUEUE_GENERATION_HOUR, minute=0),
        id="daily_queues",
        name="生成每日队列",
        replace_existing=True
    )

    scheduler.add_job(
        retry_failed_tasks,
        trigger=CronTrigger(hour="*/6", minute=0),
        id="retry_failed_tasks",
        name="重试失败任务",
        replace_existing=True
    )

    scheduler.add_job(
        batch_transmit_results,
        trigger=CronTrigger(hour="*/4", minute=30),
        id="batch_transmit_results",
        name="批量回传结果",
        replace_existing=True
    )

    scheduler.start()

    for job in scheduler.get_jobs():
        logger.info(f"定时任务已注册: {job.name} (ID: {job.id}, 下次执行: {job.next_run_time})")


async def stop_scheduler():
    global scheduler
    if scheduler:
        scheduler.shutdown(wait=False)
        scheduler = None
        logger.info("定时任务调度器已关闭")
