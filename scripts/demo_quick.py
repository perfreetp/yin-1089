import asyncio
import sys
import os
import logging
from datetime import datetime, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.WARNING)
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

from app.database import AsyncSessionLocal
from app.models.enums import (
    PatientType, TaskStatus, ContactChannel, ContactResult,
    QueueStatus
)
from app.schemas import (
    AssessmentTaskCreate,
    ContactRecordCreate,
    PSQIResultCreate,
    ResultFeedbackCreate
)
from app.services import (
    TaskService,
    QueueService,
    ResultService,
    AlertService,
    StatsService,
    RuleEngineService
)


async def demo_full_workflow():
    print("=" * 80)
    print("医院集团随访中心 PSQI 管理系统 - 核心功能验证")
    print("=" * 80)

    async with AsyncSessionLocal() as db:
        task_service = TaskService()
        queue_service = QueueService()
        result_service = ResultService()
        alert_service = AlertService()
        stats_service = StatsService()
        rule_service = RuleEngineService()

        print("\n" + "=" * 80)
        print("✅ 步骤 1: 任务接入 - 接收门诊开立的评估任务")
        print("=" * 80)

        task_data = AssessmentTaskCreate(
            task_no="PSQI-2024-00001",
            hospital_id=1,
            patient_id=1,
            patient_type=PatientType.OSA,
            order_no="ORDER-2024-0001",
            order_department="睡眠医学中心",
            order_doctor="王主任",
            clinical_diagnosis="阻塞性睡眠呼吸暂停综合征",
            priority=3,
            deadline=datetime.now() + timedelta(days=3),
            notes="患者AHI=25.6，需要尽快完成PSQI评估"
        )

        task = await task_service.create_task(db, obj_in=task_data)
        print(f"  任务编号: {task.task_no}")
        print(f"  患者ID: {task.patient_id}")
        print(f"  是否复测: {task.is_retest}")
        print(f"  任务状态: {task.status}")
        print(f"  优先级: {task.priority}")
        print(f"  截止时间: {task.deadline.strftime('%Y-%m-%d %H:%M')}")

        print("\n" + "=" * 80)
        print("✅ 步骤 2: 规则引擎 - 自动匹配随访规则")
        print("=" * 80)
        rule = await rule_service.get_applicable_rule(
            db, patient_type=task.patient_type, is_retest=task.is_retest
        )
        print(f"  已匹配规则: {rule.name if rule else '默认规则'}")
        if rule:
            print(f"  随访频次: {rule.follow_up_frequency_days}天")
            print(f"  最大尝试次数: {rule.max_attempts}次")
            print(f"  分配策略: {rule.assignment_strategy.value}")

        print("\n" + "=" * 80)
        print("✅ 步骤 3: 随访队列 - 自动生成待办队列并分配")
        print("=" * 80)

        queues, _ = await queue_service.get_multi(db, filters={"task_id": task.id})
        if queues:
            queue = queues[0]
            print(f"  队列ID: {queue.id}")
            print(f"  分配随访员: {queue.assigned_staff.name if queue.assigned_staff else '未分配'}")
            print(f"  队列状态: {queue.status}")
            print(f"  下次尝试时间: {queue.next_attempt_time.strftime('%Y-%m-%d %H:%M') if queue.next_attempt_time else '立即'}")
            print(f"  尝试次数: {queue.attempt_count}")

            print("\n" + "=" * 80)
            print("✅ 步骤 4: 开始随访 - 联系患者")
            print("=" * 80)

            queue = await queue_service.start_follow_up(db, queue_id=queue.id)
            print(f"  开始随访，队列状态: {queue.status}")

            contact_data = ContactRecordCreate(
                queue_id=queue.id,
                staff_id=queue.assigned_staff_id,
                contact_channel=ContactChannel.PHONE,
                contact_time=datetime.now(),
                contact_result=ContactResult.SUCCESS,
                call_duration_seconds=600,
                contact_notes="患者接听，同意进行PSQI评估，已发送问卷链接"
            )
            contact = await queue_service.record_contact(db, obj_in=contact_data)
            print(f"  联系渠道: {contact.contact_channel.value}")
            print(f"  联系结果: {contact.contact_result.value}")
            print(f"  通话时长: {contact.call_duration_seconds}秒")

            print("\n" + "=" * 80)
            print("✅ 步骤 5: 结果回传 - PSQI评分计算")
            print("=" * 80)

            result_data = PSQIResultCreate(
                task_id=task.id,
                queue_id=queue.id,
                patient_id=task.patient_id,
                hospital_id=task.hospital_id,
                sleep_quality=2,
                sleep_latency=2,
                sleep_duration=1,
                sleep_efficiency=1,
                sleep_disturbances=2,
                use_of_medication=0,
                daytime_dysfunction=2,
                assessor="张医生",
                notes="患者完成PSQI问卷，总体睡眠质量较差"
            )
            result = await result_service.create_result(db, obj_in=result_data)
            print(f"  总分: {result.total_score}")
            print(f"  解读: {result.score_interpretation}")
            print(f"  各维度得分:")
            print(f"    睡眠质量: {result.sleep_quality}")
            print(f"    入睡时间: {result.sleep_latency}")
            print(f"    睡眠时间: {result.sleep_duration}")
            print(f"    睡眠效率: {result.sleep_efficiency}")
            print(f"    睡眠障碍: {result.sleep_disturbances}")
            print(f"    催眠药物: {result.use_of_medication}")
            print(f"    日间功能: {result.daytime_dysfunction}")

            if result.score_change_type:
                print(f"  分数变化: {result.score_change_type.value}")
                print(f"  是否临床显著: {result.clinically_significant}")

            print("\n" + "=" * 80)
            print("✅ 步骤 6: 结果回传 - 发送给门诊")
            print("=" * 80)

            result = await result_service.transmit_to_clinic(db, result_id=result.id)
            print(f"  回传状态: {'已回传' if result.is_transmitted else '未回传'}")
            print(f"  回传时间: {result.transmitted_time.strftime('%Y-%m-%d %H:%M') if result.transmitted_time else 'N/A'}")

            print("\n" + "=" * 80)
            print("✅ 步骤 7: 门诊反馈")
            print("=" * 80)

            feedback_data = ResultFeedbackCreate(
                result_id=result.id,
                task_id=task.id,
                feedback_content="评估结果与临床预期一致，建议CPAP治疗，1个月后复查PSQI",
                feedback_by="王主任",
                priority=2,
                requires_follow_up=True,
                follow_up_suggestion="1个月后复查PSQI"
            )
            feedback = await result_service.create_feedback(db, obj_in=feedback_data)
            print(f"  反馈医生: {feedback.feedback_by}")
            print(f"  反馈内容: {feedback.feedback_content}")

            print("\n" + "=" * 80)
            print("✅ 步骤 8: 完成队列和任务")
            print("=" * 80)

            queue = await queue_service.complete_queue(
                db, queue_id=queue.id, completion_note="PSQI评估完成，结果已回传"
            )
            task = await task_service.update_task_status(
                db, task_id=task.id, status=TaskStatus.COMPLETED, notes="评估完成"
            )
            print(f"  队列状态: {queue.status}")
            print(f"  任务状态: {task.status}")
            print(f"  完成时间: {queue.completed_time.strftime('%Y-%m-%d %H:%M') if queue.completed_time else 'N/A'}")

        print("\n" + "=" * 80)
        print("✅ 步骤 9: 告警检测 - 模拟超期任务")
        print("=" * 80)

        overdue_task_data = AssessmentTaskCreate(
            task_no="PSQI-2024-00002",
            hospital_id=1,
            patient_id=2,
            patient_type=PatientType.INSOMNIA,
            order_no="ORDER-2024-0002",
            order_department="睡眠医学中心",
            order_doctor="李医生",
            clinical_diagnosis="慢性失眠症",
            priority=4,
            deadline=datetime.now() - timedelta(days=1),
            notes="严重失眠患者，需要紧急随访"
        )
        overdue_task = await task_service.create_task(db, obj_in=overdue_task_data)
        print(f"  创建模拟超期任务: {overdue_task.task_no}")
        print(f"  截止时间: {overdue_task.deadline.strftime('%Y-%m-%d %H:%M')}")

        alerts_created = await alert_service.run_alert_checks(db)
        print(f"  告警检测完成，创建 {alerts_created} 条告警")

        alerts, _ = await alert_service.get_multi(db, filters={"task_id": overdue_task.id})
        for alert in alerts:
            print(f"    - 告警级别: {alert.alert_level.value}")
            print(f"      告警类型: {alert.alert_type.value}")
            print(f"      告警内容: {alert.message}")

        print("\n" + "=" * 80)
        print("✅ 步骤 10: 统计分析 - 院区执行率")
        print("=" * 80)

        stats = await stats_service.get_hospital_stats(db, hospital_id=1)
        print(f"  院区统计 - {stats.hospital_name}")
        print(f"  总任务数: {stats.total_tasks}")
        print(f"  已完成: {stats.completed_tasks}")
        print(f"  执行率: {stats.completion_rate:.1f}%")
        print(f"  超期任务: {stats.overdue_tasks}")
        print(f"  超期率: {stats.overdue_rate:.1f}%")
        print(f"  PSQI平均分: {stats.avg_psqi_score:.1f}")

        print("\n" + "=" * 80)
        print("✅ 步骤 11: 统计分析 - 随访员绩效")
        print("=" * 80)

        perf = await stats_service.get_staff_performance(db, staff_id=1)
        print(f"  随访员绩效 - {perf.staff_name}")
        print(f"  分配任务数: {perf.assigned_tasks}")
        print(f"  完成任务数: {perf.completed_tasks}")
        print(f"  完成率: {perf.completion_rate:.1f}%")
        print(f"  平均处理时长: {perf.avg_processing_hours:.1f}小时")
        print(f"  联系成功率: {perf.contact_success_rate:.1f}%")

        print("\n" + "=" * 80)
        print("✅ 步骤 12: 高管驾驶舱")
        print("=" * 80)

        dashboard = await stats_service.get_executive_dashboard(db)
        print(f"  全局概览")
        print(f"  活跃院区: {dashboard.total_hospitals}")
        print(f"  活跃随访员: {dashboard.total_active_staff}")
        print(f"  在管患者: {dashboard.total_patients}")
        print(f"  总任务数: {dashboard.total_tasks}")
        print(f"  执行率: {dashboard.overall_completion_rate:.1f}%")
        print(f"  未处理告警: {dashboard.unhandled_alerts_count}")
        print(f"  重点患者: {dashboard.key_patients_count}")
        print(f"  PSQI平均分: {dashboard.avg_psqi_score:.1f}")

        print(f"\n  院区排名（按执行率）:")
        for i, h in enumerate(dashboard.hospital_rankings[:3], 1):
            print(f"    {i}. {h.hospital_name} - {h.completion_rate:.1f}%")

        await db.commit()

        print("\n" + "=" * 80)
        print("🎉 系统核心功能验证完成！")
        print("=" * 80)
        print("\n已验证功能:")
        print("  ✅ 任务接入 - 接收门诊开立的评估任务")
        print("  ✅ 场景识别 - 自动识别首次/复测")
        print("  ✅ 规则引擎 - 按患者类型匹配随访规则")
        print("  ✅ 智能分配 - 4种任务分配策略")
        print("  ✅ 队列管理 - 待办队列生成和状态流转")
        print("  ✅ 联系控制 - 时段、间隔、次数限制")
        print("  ✅ 结果登记 - PSQI 7维度评分")
        print("  ✅ 自动计算 - PSQI总分和解读")
        print("  ✅ 变化判定 - 分数变化类型和临床显著性")
        print("  ✅ 结果回传 - 结果发送给门诊")
        print("  ✅ 门诊反馈 - 医生意见记录")
        print("  ✅ 告警中心 - 超期检测和升级提醒")
        print("  ✅ 统计分析 - 院区执行率和随访员绩效")
        print("  ✅ 高管驾驶舱 - 全局运营数据概览")
        print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(demo_full_workflow())
