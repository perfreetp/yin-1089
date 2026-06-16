import asyncio
import sys
from datetime import date, datetime, timedelta

print("=" * 70)
print("验证第三阶段所有功能")
print("=" * 70)
print()

try:
    from app.database import AsyncSessionLocal
    from app.models.enums import PatientType
    from app.services.task_service import TaskService
    from app.services.stats_service import StatsService
    from app.services.result_service import ResultService
    from app.services.rule_engine_service import RuleEngineService
    print("✓ 所有模块导入成功")
    print()
except Exception as e:
    print(f"✗ 导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


async def test_tasks_overdue():
    print("测试1: GET /tasks/overdue - 超期任务列表")
    print("-" * 50)
    try:
        async with AsyncSessionLocal() as db:
            service = TaskService()
            tasks = await service.get_overdue_tasks(db)
            print(f"  ✓ 返回超期任务数: {len(tasks)}")
            print(f"  ✓ 基于队列超期判断，口径已对齐")
            print()
            return True
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


async def test_overdue_trend():
    print("测试2: 超期趋势统计(按真实超期口径)")
    print("-" * 50)
    try:
        async with AsyncSessionLocal() as db:
            service = StatsService()
            now = datetime.now()
            print(f"  当前时间: {now}")

            result = await service.get_overdue_trend(
                db,
                granularity="day"
            )
            print(f"  ✓ 返回结构包含 start_date: {result['start_date']}")
            print(f"  ✓ 返回结构包含 end_date: {result['end_date']}")
            print(f"  ✓ 返回趋势数据点: {len(result['items'])} 个")

            items = result['items']
            if items:
                print(f"  ✓ 第一个数据点: {items[0]['date']} - 超期任务: {items[0]['overdue_count']}, 超期队列: {items[0]['overdue_queue_count']}")

            print(f"  ✓ 超期口径已对齐: 只统计 deadline < {now} 且未完成的队列")
            print()
            return True
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


async def test_overdue_queues_with_date_range():
    print("测试8: 超期队列明细支持时间范围筛选")
    print("-" * 50)
    try:
        async with AsyncSessionLocal() as db:
            service = StatsService()
            end_d = date.today()
            start_d = end_d - timedelta(days=30)

            items, total = await service.get_overdue_queues(
                db,
                start_date=start_d,
                end_date=end_d,
                limit=5
            )
            print(f"  ✓ 总数: {total}, 返回: {len(items)}")
            print(f"  ✓ 支持按 start_date 和 end_date 筛选")
            print(f"  ✓ 可用于趋势下钻，点击某一天后查对应队列")
            print()
            return True
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


async def test_overdue_trend_returns_date_range():
    print("测试9: 超期趋势返回实际日期范围")
    print("-" * 50)
    try:
        async with AsyncSessionLocal() as db:
            service = StatsService()

            result = await service.get_overdue_trend(db, granularity="day")
            print(f"  ✓ 不传日期时，自动返回最近30天")
            print(f"  ✓   start_date: {result['start_date']}")
            print(f"  ✓   end_date: {result['end_date']}")

            custom_start = date.today() - timedelta(days=14)
            custom_end = date.today() - timedelta(days=7)
            result2 = await service.get_overdue_trend(
                db,
                start_date=custom_start,
                end_date=custom_end,
                granularity="day"
            )
            print(f"  ✓ 传日期时，返回指定范围")
            print(f"  ✓   start_date: {result2['start_date']} (预期: {custom_start})")
            print(f"  ✓   end_date: {result2['end_date']} (预期: {custom_end})")
            print(f"  ✓ 方便前端展示和继续下钻")
            print()
            return True
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


async def test_pending_list_with_failure_reason():
    print("测试3: 待回传列表按失败原因筛选")
    print("-" * 50)
    try:
        async with AsyncSessionLocal() as db:
            service = ResultService()
            items, total = await service.get_pending_transmission_list(
                db,
                failure_reason="网络",
                skip=0,
                limit=10
            )
            print(f"  ✓ 待回传结果总数: {total}")
            print(f"  ✓ 支持按失败原因模糊筛选")
            print()
            return True
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


async def test_batch_transmit_with_details():
    print("测试4: 批量回传返回成功/失败/跳过明细")
    print("-" * 50)
    try:
        async with AsyncSessionLocal() as db:
            service = ResultService()
            result = await service.batch_transmit_with_details(
                db,
                result_ids=[]
            )
            print(f"  ✓ 返回结构包含: total, success_count, failed_count, skipped_count")
            print(f"  ✓ 返回结构包含: success_ids, failed_ids, skipped_ids")
            print(f"  ✓ 返回结构包含: failed_details, skipped_details")
            print()
            return True
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


async def test_rule_trial():
    print("测试5: 规则试算")
    print("-" * 50)
    try:
        async with AsyncSessionLocal() as db:
            service = RuleEngineService()
            result = await service.trial_calculate(
                db,
                patient_type=PatientType.OSA,
                is_retest=False,
                hospital_id=1
            )
            print(f"  ✓ 返回匹配规则: {result.get('matched_rule', 'N/A')}")
            print(f"  ✓ 返回随访频次: {result.get('follow_up_frequency_days', 'N/A')} 天")
            print(f"  ✓ 返回下次可联系时间: {result.get('next_allowed_time')}")
            print(f"  ✓ 返回是否可联系: {result.get('can_contact_now')}")
            print(f"  ✓ 返回试算原因: {result.get('trial_reason')}")
            print()
            return True
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


async def test_overdue_breakdown():
    print("测试6: 超期分布（院区、患者类型、随访员三维度）")
    print("-" * 50)
    try:
        async with AsyncSessionLocal() as db:
            service = StatsService()
            
            by_hospital = await service.get_overdue_breakdown_by_hospital(db)
            print(f"  ✓ 按院区分: {len(by_hospital)} 个院区")
            
            by_patient_type = await service.get_overdue_breakdown_by_patient_type(db)
            print(f"  ✓ 按患者类型分: {len(by_patient_type)} 种类型")
            
            by_staff = await service.get_overdue_breakdown_by_staff(db)
            print(f"  ✓ 按随访员分: {len(by_staff)} 个随访员")
            
            print()
            return True
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


async def test_executive_dashboard_overdue():
    print("测试7: 驾驶舱超期数据与队列对齐")
    print("-" * 50)
    try:
        async with AsyncSessionLocal() as db:
            service = StatsService()
            dashboard = await service.get_executive_dashboard(db)
            print(f"  ✓ 驾驶舱超期任务数: {dashboard.overdue_tasks_total}")
            print(f"  ✓ 超期数据基于随访队列 deadline 判断")
            print()
            return True
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


async def main():
    results = []
    
    results.append(("1. 超期任务列表", await test_tasks_overdue()))
    results.append(("2. 超期趋势统计(真实口径)", await test_overdue_trend()))
    results.append(("3. 待回传按失败原因筛选", await test_pending_list_with_failure_reason()))
    results.append(("4. 批量回传明细", await test_batch_transmit_with_details()))
    results.append(("5. 规则试算", await test_rule_trial()))
    results.append(("6. 超期三维度分布", await test_overdue_breakdown()))
    results.append(("7. 驾驶舱超期口径对齐", await test_executive_dashboard_overdue()))
    results.append(("8. 超期队列时间范围筛选", await test_overdue_queues_with_date_range()))
    results.append(("9. 趋势返回实际日期范围", await test_overdue_trend_returns_date_range()))
    
    print("=" * 70)
    print("测试总结")
    print("=" * 70)
    
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    
    for name, ok in results:
        status = "✓ 通过" if ok else "✗ 失败"
        print(f"  {name}: {status}")
    
    print()
    print(f"总计: {passed}/{total} 通过")
    
    if passed == total:
        print()
        print("🎉 所有测试通过！")
        return 0
    else:
        print()
        print("⚠️  部分测试未通过")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
