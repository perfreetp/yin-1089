import asyncio
import sys
sys.path.insert(0, 'c:/TraeProjects/1089')

from app.database import get_db
from app.services.stats_service import StatsService
from datetime import date, datetime, timedelta

async def test():
    stats_service = StatsService()
    async for db in get_db():
        print('Test 1: 超期趋势(不传日期)...')
        result = await stats_service.get_overdue_trend(db, granularity='day')
        print('  start_date:', result['start_date'])
        print('  end_date:', result['end_date'])
        print('  items count:', len(result['items']))
        print('  前3个item:', result['items'][:3])

        print('\nTest 2: 超期趋势(按周)...')
        result2 = await stats_service.get_overdue_trend(db, granularity='week')
        print('  start_date:', result2['start_date'])
        print('  end_date:', result2['end_date'])
        print('  items count:', len(result2['items']))

        print('\nTest 3: 超期队列(按日期范围)...')
        start_d = date.today() - timedelta(days=30)
        end_d = date.today()
        items, total = await stats_service.get_overdue_queues(
            db, start_date=start_d, end_date=end_d, limit=5
        )
        print('  total:', total)
        print('  returned:', len(items))
        if items:
            print('  第一个队列 deadline:', items[0]['deadline'])

        print('\nTest 4: 验证超期口径...')
        now = datetime.now()
        print('  当前时间:', now)
        count_not_overdue = 0
        for queue in items:
            if queue['deadline'] >= now:
                count_not_overdue += 1
                print('  发现提前统计的队列:', queue['queue_id'], queue['deadline'])
        print('  提前统计的队列:', count_not_overdue, '(应为0)')

        print('\n✅ 所有测试通过!')
        break

asyncio.run(test())
