import asyncio
from datetime import datetime, timedelta
from app.database import AsyncSessionLocal
from app.models import (
    Hospital, FollowUpStaff, Patient, AssessmentTask, FollowUpQueue,
    FollowUpRule, ContactIntervalRule, PSQIResult
)
from app.models.enums import PatientType, TaskStatus, QueueStatus, ContactResult
from app.services.stats_service import StatsService
from app.services.rule_engine_service import RuleEngineService
from app.services.result_service import ResultService
from app.services.task_service import TaskService
import sys

async def test_overdue_queues():
    print("=" * 60)
    print("测试1: 超期队列明细查询")
    print("=" * 60)
    
    async with AsyncSessionLocal() as db:
        stats_service = StatsService()
        
        # 获取超期队列列表
        queues, total = await stats_service.get_overdue_queues(
            db, skip=0, limit=10
        )
        print(f"超期队列总数: {total}")
        print(f"当前页队列数: {len(queues)}")
        for q in queues[:3]:
            print(f"  - 队列号: {q['queue_no']}, 患者: {q['patient_name']}, 超期小时: {q['overdue_hours']:.1f}")
        
        print()

async def test_overdue_breakdown():
    print("=" * 60)
    print("测试2: 超期分布统计（按院区、患者类型、随访员）")
    print("=" * 60)
    
    async with AsyncSessionLocal() as db:
        stats_service = StatsService()
        
        # 按院区分
        hospital_breakdown = await stats_service.get_overdue_breakdown_by_hospital(db)
        print(f"按院区分: {len(hospital_breakdown)} 个院区")
        for item in hospital_breakdown[:3]:
            print(f"  - {item['dimension_value']}: {item['overdue_count']} 个超期队列, 超期率 {item['overdue_rate']}%")
        
        print()
        
        # 按患者类型分
        patient_type_breakdown = await stats_service.get_overdue_breakdown_by_patient_type(db)
        print(f"按患者类型分: {len(patient_type_breakdown)} 种类型")
        for item in patient_type_breakdown:
            print(f"  - {item['dimension_value']}: {item['overdue_count']} 个超期队列, 超期率 {item['overdue_rate']}%")
        
        print()
        
        # 按随访员分
        staff_breakdown = await stats_service.get_overdue_breakdown_by_staff(db)
        print(f"按随访员分: {len(staff_breakdown)} 个随访员")
        for item in staff_breakdown[:3]:
            print(f"  - {item['dimension_value'] or '未分配'}: {item['overdue_count']} 个超期队列, 超期率 {item['overdue_rate']}%")
        
        print()

async def test_rule_trial():
    print("=" * 60)
    print("测试3: 规则试算")
    print("=" * 60)
    
    async with AsyncSessionLocal() as db:
        rule_service = RuleEngineService()
        
        # 测试首次患者
        result = await rule_service.trial_calculate(
            db,
            patient_type=PatientType.OSA,
            is_retest=False,
            hospital_id=1,
            last_contact_result=ContactResult.SUCCESS,
            last_contact_time=datetime.now() - timedelta(days=2)
        )
        
        print(f"患者类型: OSA, 首次就诊")
        print(f"  匹配随访规则: {result.get('matched_rule', '未找到')}")
        print(f"  随访频次: {result.get('follow_up_frequency_days', 'N/A')} 天")
        print(f"  下次可联系时间: {result.get('next_allowed_time')}")
        print(f"  现在可以联系: {result.get('can_contact_now')}")
        print(f"  试算原因: {result.get('trial_reason')}")
        
        print()

async def test_pending_transmission():
    print("=" * 60)
    print("测试4: 待回传数据筛选")
    print("=" * 60)
    
    async with AsyncSessionLocal() as db:
        result_service = ResultService()
        
        # 获取待回传列表
        results, total = await result_service.get_pending_transmission_list(
            db, skip=0, limit=10
        )
        print(f"待回传结果总数: {total}")
        print(f"当前页结果数: {len(results)}")
        for r in results[:3]:
            print(f"  - 结果ID: {r.id}, 任务号: {r.task_no}, 状态: {r.transmission_status}")
        
        print()

async def test_overdue_tasks():
    print("=" * 60)
    print("测试5: 超期任务列表（与队列对齐）")
    print("=" * 60)
    
    async with AsyncSessionLocal() as db:
        task_service = TaskService()
        
        tasks = await task_service.get_overdue_tasks(db)
        print(f"超期任务数: {len(tasks)}")
        for t in tasks[:3]:
            print(f"  - 任务号: {t.task_no}, 患者: {t.patient_name}")
        
        print()

async def test_executive_dashboard():
    print("=" * 60)
    print("测试6: 高管驾驶舱（验证超期口径）")
    print("=" * 60)
    
    async with AsyncSessionLocal() as db:
        stats_service = StatsService()
        
        dashboard = await stats_service.get_executive_dashboard(db)
        print(f"总任务数: {dashboard.total_tasks}")
        print(f"进行中任务: {dashboard.in_progress_tasks}")
        print(f"已完成任务: {dashboard.completed_tasks}")
        print(f"超期任务数: {dashboard.overdue_tasks}")
        print(f"超期率: {dashboard.overdue_rate * 100:.1f}%")
        
        print()
        print("院区级超期数据:")
        for h in dashboard.hospital_stats[:3]:
            print(f"  - {h.hospital_name}: 超期 {h.overdue_tasks} 个, 超期率 {h.overdue_rate * 100:.1f}%")

async def main():
    try:
        print("\n" + "=" * 60)
        print("第三阶段新功能测试")
        print("=" * 60 + "\n")
        
        await test_rule_trial()
        await test_overdue_tasks()
        await test_overdue_queues()
        await test_overdue_breakdown()
        await test_pending_transmission()
        await test_executive_dashboard()
        
        print("=" * 60)
        print("所有测试完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
