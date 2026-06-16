import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, Base, AsyncSessionLocal
from app.models.enums import (
    HospitalZone, PatientType, TaskStatus, QueueStatus,
    ContactChannel, ContactResult, AlertLevel, AssignmentStrategy, ContactResult
)
from app.models import (
    Hospital, FollowUpStaff, Patient, FollowUpRule, ContactIntervalRule
)


async def create_tables():
    print("正在创建数据库表...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("数据库表创建完成")


async def insert_sample_data():
    print("正在插入示例数据...")
    async with AsyncSessionLocal() as db:
        hospitals = [
            Hospital(
                code="HOSP-001",
                name="总院睡眠医学中心",
                zone=HospitalZone.EAST,
                address="浦东新区张江高科技园区123号",
                contact_phone="021-12345678",
                department="睡眠医学中心",
                is_active=True
            ),
            Hospital(
                code="HOSP-002",
                name="西院睡眠门诊",
                zone=HospitalZone.WEST,
                address="徐汇区淮海中路456号",
                contact_phone="021-87654321",
                department="睡眠门诊",
                is_active=True
            ),
            Hospital(
                code="HOSP-003",
                name="南院睡眠中心",
                zone=HospitalZone.SOUTH,
                address="闵行区莲花路789号",
                contact_phone="021-11112222",
                department="睡眠中心",
                is_active=True
            ),
            Hospital(
                code="HOSP-004",
                name="北院睡眠专科",
                zone=HospitalZone.NORTH,
                address="静安区共和新路1011号",
                contact_phone="021-33334444",
                department="睡眠专科",
                is_active=True
            )
        ]
        db.add_all(hospitals)
        await db.flush()

        staffs = [
            FollowUpStaff(
                staff_no="STAFF-001",
                name="张医生",
                phone="13800000001",
                hospital_id=hospitals[0].id,
                department="睡眠医学中心",
                title="主治医师",
                skills=["OSA", "失眠", "PSQI评估"],
                max_tasks_per_day=20,
                is_active=True
            ),
            FollowUpStaff(
                staff_no="STAFF-002",
                name="李医生",
                phone="13800000002",
                hospital_id=hospitals[0].id,
                department="睡眠医学中心",
                title="副主任医师",
                skills=["OSA", "睡眠呼吸暂停"],
                max_tasks_per_day=20,
                is_active=True
            ),
            FollowUpStaff(
                staff_no="STAFF-003",
                name="王护士",
                phone="13800000003",
                hospital_id=hospitals[1].id,
                department="睡眠门诊",
                title="主管护师",
                skills=["失眠", "焦虑"],
                max_tasks_per_day=25,
                is_active=True
            ),
            FollowUpStaff(
                staff_no="STAFF-004",
                name="赵护师",
                phone="13800000004",
                hospital_id=hospitals[2].id,
                department="睡眠中心",
                title="护师",
                skills=["PSQI评估", "儿童睡眠"],
                max_tasks_per_day=25,
                is_active=True
            ),
            FollowUpStaff(
                staff_no="STAFF-005",
                name="陈医生",
                phone="13800000005",
                hospital_id=hospitals[3].id,
                department="睡眠专科",
                title="主任医师",
                skills=["OSA", "老年睡眠"],
                max_tasks_per_day=15,
                is_active=True
            )
        ]
        db.add_all(staffs)
        await db.flush()

        patients = [
            Patient(
                patient_no="P20240001",
                name="张三",
                gender="男",
                age=45,
                phone="13900000001",
                patient_type=PatientType.OSA,
                is_key_patient=False
            ),
            Patient(
                patient_no="P20240002",
                name="李四",
                gender="女",
                age=38,
                phone="13900000002",
                patient_type=PatientType.INSOMNIA,
                is_key_patient=True,
                key_patient_reason="严重失眠，PSQI评分18分"
            ),
            Patient(
                patient_no="P20240003",
                name="王五",
                gender="男",
                age=52,
                phone="13900000003",
                patient_type=PatientType.OSA,
                is_key_patient=False
            ),
            Patient(
                patient_no="P20240004",
                name="赵六",
                gender="女",
                age=28,
                phone="13900000004",
                patient_type=PatientType.RESTLESS_LEG,
                is_key_patient=False
            ),
            Patient(
                patient_no="P20240005",
                name="钱七",
                gender="男",
                age=65,
                phone="13900000005",
                patient_type=PatientType.OTHER,
                is_key_patient=True,
                key_patient_reason="老年患者，合并多种基础疾病"
            )
        ]
        db.add_all(patients)
        await db.flush()

        rules = [
            FollowUpRule(
                name="OSA首次评估随访规则",
                description="阻塞性睡眠呼吸暂停首次PSQI评估",
                patient_type=PatientType.OSA,
                is_retest=False,
                follow_up_frequency_days=7,
                total_follow_up_count=3,
                first_follow_up_hours=24,
                overdue_hours=72,
                escalation_hours=120,
                max_attempts=5,
                assignment_strategy=AssignmentStrategy.LOAD_BALANCE,
                priority=3,
                is_active=True
            ),
            FollowUpRule(
                name="OSA复测随访规则",
                description="阻塞性睡眠呼吸暂停PSQI复测",
                patient_type=PatientType.OSA,
                is_retest=True,
                follow_up_frequency_days=14,
                total_follow_up_count=2,
                first_follow_up_hours=48,
                overdue_hours=96,
                escalation_hours=168,
                max_attempts=3,
                assignment_strategy=AssignmentStrategy.LOAD_BALANCE,
                priority=2,
                is_active=True
            ),
            FollowUpRule(
                name="失眠首次评估随访规则",
                description="失眠症首次PSQI评估",
                patient_type=PatientType.INSOMNIA,
                is_retest=False,
                follow_up_frequency_days=3,
                total_follow_up_count=4,
                first_follow_up_hours=12,
                overdue_hours=48,
                escalation_hours=96,
                max_attempts=7,
                assignment_strategy=AssignmentStrategy.SKILL_BASED,
                priority=4,
                is_active=True
            ),
            FollowUpRule(
                name="失眠复测随访规则",
                description="失眠症PSQI复测",
                patient_type=PatientType.INSOMNIA,
                is_retest=True,
                follow_up_frequency_days=7,
                total_follow_up_count=3,
                first_follow_up_hours=24,
                overdue_hours=72,
                escalation_hours=120,
                max_attempts=5,
                assignment_strategy=AssignmentStrategy.SKILL_BASED,
                priority=3,
                is_active=True
            ),
            FollowUpRule(
                name="不宁腿综合征首次评估随访规则",
                description="不宁腿综合征首次PSQI评估",
                patient_type=PatientType.RESTLESS_LEG,
                is_retest=False,
                follow_up_frequency_days=14,
                total_follow_up_count=2,
                first_follow_up_hours=48,
                overdue_hours=96,
                escalation_hours=168,
                max_attempts=4,
                assignment_strategy=AssignmentStrategy.ROUND_ROBIN,
                priority=2,
                is_active=True
            ),
            FollowUpRule(
                name="其他睡眠障碍首次评估随访规则",
                description="其他睡眠障碍首次PSQI评估",
                patient_type=PatientType.OTHER,
                is_retest=False,
                follow_up_frequency_days=7,
                total_follow_up_count=2,
                first_follow_up_hours=24,
                overdue_hours=72,
                escalation_hours=120,
                max_attempts=4,
                assignment_strategy=AssignmentStrategy.ROUND_ROBIN,
                priority=2,
                is_active=True
            )
        ]
        db.add_all(rules)

        interval_rules = [
            ContactIntervalRule(
                name="默认联系间隔规则",
                description="适用于大多数情况的默认规则",
                min_interval_hours=24,
                max_daily_attempts=3,
                max_total_attempts=10,
                time_window_start="09:00",
                time_window_end="21:00",
                apply_to_all=True,
                is_active=True
            ),
            ContactIntervalRule(
                name="未接来电重拨规则",
                description="患者未接听时的重拨规则",
                contact_result=ContactResult.NO_ANSWER.value,
                min_interval_hours=2,
                max_daily_attempts=5,
                max_total_attempts=10,
                time_window_start="09:00",
                time_window_end="21:00",
                apply_to_all=True,
                is_active=True
            ),
            ContactIntervalRule(
                name="患者忙规则",
                description="患者表示忙时的联系规则",
                contact_result=ContactResult.PATIENT_BUSY.value,
                min_interval_hours=48,
                max_daily_attempts=1,
                max_total_attempts=5,
                time_window_start="10:00",
                time_window_end="18:00",
                apply_to_all=True,
                is_active=True
            ),
            ContactIntervalRule(
                name="号码错误规则",
                description="联系号码错误时的规则",
                contact_result=ContactResult.WRONG_NUMBER.value,
                min_interval_hours=72,
                max_daily_attempts=1,
                max_total_attempts=3,
                time_window_start="09:00",
                time_window_end="17:00",
                apply_to_all=True,
                is_active=True
            )
        ]
        db.add_all(interval_rules)

        await db.commit()
        print("示例数据插入完成")
        print(f"  - 院区: {len(hospitals)} 家")
        print(f"  - 随访员: {len(staffs)} 名")
        print(f"  - 患者: {len(patients)} 名")
        print(f"  - 随访规则: {len(rules)} 条")
        print(f"  - 联系间隔规则: {len(interval_rules)} 条")


async def main():
    await create_tables()
    await insert_sample_data()
    print("\n数据库初始化完成！")
    print("\n启动命令:")
    print("  python -m app.main")
    print("\nAPI文档:")
    print("  Swagger UI: http://localhost:8000/docs")
    print("  ReDoc: http://localhost:8000/redoc")


if __name__ == "__main__":
    asyncio.run(main())
