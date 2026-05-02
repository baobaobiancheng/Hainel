"""
虚拟数据导入脚本 — 一键填充所有数据表
使用方法（在 backend/ 目录下执行）:
    python -m scripts.seed_data
    python scripts/seed_data.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta

# ── 密码哈希 ──────────────────────────────────────────────────────────────────
try:
    from passlib.context import CryptContext
    _pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    def hash_password(p: str) -> str:
        return _pwd_ctx.hash(p)
except ImportError:
    import bcrypt as _bcrypt
    def hash_password(p: str) -> str:
        return _bcrypt.hashpw(p.encode(), _bcrypt.gensalt()).decode()

# ── 数据库 & 模型 ─────────────────────────────────────────────────────────────
from app.database.base import SessionLocal, init_db
from app.models import User, Conversation, Message, MedicalRecord
from app.models.reminder import Reminder
from app.models.enums import ReminderType, ReminderStatus, ReminderFrequency


def seed():
    print("=" * 50)
    print("  医疗健康系统 - 虚拟数据导入")
    print("=" * 50)

    print("\n[1/2] 初始化数据库表...")
    init_db()
    print("      表结构已就绪 OK")

    db = SessionLocal()
    try:
        # ── 检查是否已有数据 ────────────────────────────────────────────────────
        if db.query(User).count() > 0:
            print("\n[WARN] 数据库已有数据，跳过导入（避免重复）")
            print("       如需重新导入，请先清空相关表")
            return

        print("\n[2/2] 插入虚拟数据...", flush=True)

        # ────────────────────────────────────────────────────────────────────
        # 用户（患者 / 医生 / 管理员）
        # ────────────────────────────────────────────────────────────────────
        now = datetime.utcnow()

        patient = User(
            username="patient01",
            email="patient@test.com",
            phone="13800138001",
            hashed_password=hash_password("Test1234"),
            role="patient",
            full_name="张明华",
            is_active=True,
            is_verified=True,
            created_at=now - timedelta(days=60),
        )
        doctor = User(
            username="doctor01",
            email="doctor@test.com",
            phone="13800138002",
            hashed_password=hash_password("Test1234"),
            role="doctor",
            full_name="李晓医",
            doctor_title="主治医师",
            doctor_department="内科",
            doctor_hospital="北京协和医院",
            doctor_license="110100200001",
            is_active=True,
            is_verified=True,
            created_at=now - timedelta(days=365),
        )
        admin = User(
            username="admin",
            email="admin@test.com",
            phone="13800138000",
            hashed_password=hash_password("Admin1234"),
            role="admin",
            full_name="系统管理员",
            is_active=True,
            is_verified=True,
            created_at=now - timedelta(days=365),
        )
        db.add_all([patient, doctor, admin])
        db.flush()

        # ────────────────────────────────────────────────────────────────────
        # 会话
        # ────────────────────────────────────────────────────────────────────
        conv1 = Conversation(
            patient_id=patient.id,
            title="头痛症状咨询",
            chief_complaint="近一周频繁头痛，头部两侧及后颈部持续胀痛",
            status="completed",
            complexity_level="medium",
            collaboration_mode="pcc",
            message_count=6,
            round_count=3,
            started_at=now - timedelta(days=3),
            ended_at=now - timedelta(days=2),
            last_message_at=now - timedelta(days=2),
        )
        conv2 = Conversation(
            patient_id=patient.id,
            title="高血压用药咨询",
            chief_complaint="已确诊高血压，想了解日常用药和饮食注意事项",
            status="active",
            complexity_level="low",
            collaboration_mode="pcc",
            message_count=4,
            round_count=2,
            started_at=now - timedelta(hours=5),
            last_message_at=now - timedelta(hours=1),
        )
        conv3 = Conversation(
            patient_id=patient.id,
            title="血糖偏高饮食咨询",
            chief_complaint="最近血糖偏高（空腹7.2mmol/L），想了解饮食控制方法",
            status="pending",
            complexity_level="medium",
            collaboration_mode="mdt",
            message_count=0,
            round_count=0,
            started_at=now - timedelta(hours=1),
        )
        db.add_all([conv1, conv2, conv3])
        db.flush()

        # ────────────────────────────────────────────────────────────────────
        # 消息
        # ────────────────────────────────────────────────────────────────────
        msgs = [
            # 会话1：头痛
            Message(
                conversation_id=conv1.id, user_id=patient.id,
                role="user", message_type="text",
                content="我最近一周经常头痛，主要集中在头部两侧和后颈部，感觉像是被什么东西紧紧箍住，请问是怎么回事？",
                created_at=now - timedelta(days=3, hours=2),
            ),
            Message(
                conversation_id=conv1.id,
                role="assistant", message_type="text",
                content="您好！根据您描述的症状——头部两侧及后颈部持续紧绷感，最常见的可能是紧张性头痛。这类头痛通常与工作压力大、长时间保持固定姿势或睡眠不足有关。请问您最近工作压力如何？每天睡眠时间大概多少小时？",
                agent_name="初诊评估智能体", agent_id="pcc_agent",
                created_at=now - timedelta(days=3, hours=1, minutes=58),
            ),
            Message(
                conversation_id=conv1.id, user_id=patient.id,
                role="user", message_type="text",
                content="最近确实工作比较忙，经常加班到晚上11点，每天只睡5-6个小时，颈椎也有点不舒服。",
                created_at=now - timedelta(days=3, hours=1, minutes=50),
            ),
            Message(
                conversation_id=conv1.id,
                role="assistant", message_type="text",
                content="综合您的情况，高度考虑紧张性头痛合并颈椎劳损。建议：①每天保证7-8小时睡眠；②每工作1小时休息10分钟并做颈部伸展；③可临时服用布洛芬（400mg）缓解急性发作；④如头痛持续2周以上或伴随发烧、视力变化，请到神经内科就诊。",
                agent_name="内科专科智能体", agent_id="specialty_agent",
                created_at=now - timedelta(days=3, hours=1, minutes=48),
            ),
            # 会话2：高血压
            Message(
                conversation_id=conv2.id, user_id=patient.id,
                role="user", message_type="text",
                content="医生您好，我上周被诊断出高血压，血压约145/90mmHg，已开始服用氨氯地平5mg，请问饮食上需要注意什么？",
                created_at=now - timedelta(hours=5),
            ),
            Message(
                conversation_id=conv2.id,
                role="assistant", message_type="text",
                content="您好！高血压患者饮食管理很重要：\n①限盐：每天食盐摄入不超过6克（约一茶匙）\n②多补钾：香蕉、菠菜、土豆等含钾高，有助降压\n③限酒：男性每日酒精<25g，女性<15g\n④减少饱和脂肪：少吃肥肉、油炸食品\n⑤控制体重：BMI维持在18.5-24\n\n氨氯地平请按时服用，不要随意停药，服药期间如出现脚踝水肿请告知医生。",
                agent_name="营养健康智能体", agent_id="pcc_agent",
                created_at=now - timedelta(hours=4, minutes=55),
            ),
        ]
        db.add_all(msgs)

        # ────────────────────────────────────────────────────────────────────
        # 病历
        # ────────────────────────────────────────────────────────────────────
        records = [
            MedicalRecord(
                patient_id=patient.id,
                conversation_id=conv1.id,
                reviewed_by=doctor.id,
                title="紧张性头痛初诊病历",
                status="reviewed",
                chief_complaint="头部两侧及后颈部紧绷性头痛，持续约一周",
                present_illness="患者诉一周前开始出现头痛，位于头部两侧及后颈部，呈持续紧绷感，与近期工作压力增大、每日睡眠不足6小时密切相关。否认恶心、呕吐、发热等伴随症状。",
                past_history="否认高血压、糖尿病、心脏病等慢性病史。否认药物过敏史。",
                physical_examination="血压 118/76 mmHg，心率 76次/分，体温正常。颈部肌肉轻度紧张，压痛（+）。神经系统查体未见异常。",
                diagnosis={"primary": "紧张性头痛", "icd_code": "G44.2", "secondary": "颈椎劳损"},
                treatment_plan="1. 休息调整，改善睡眠质量；2. 颈部热敷及拉伸运动；3. 必要时布洛芬对症处理",
                medical_advice="保证充足睡眠（7-8小时/日），减轻工作压力，每小时颈部拉伸5分钟，2周后如无改善建议神经内科进一步检查。",
                follow_up="2周后复诊或症状加重随时就诊",
                agent_name="病历生成智能体",
                reviewed_at=now - timedelta(days=1),
                review_comment="病历记录完整，诊断符合临床表现，建议治疗方案合理。",
            ),
        ]
        db.add_all(records)

        # ────────────────────────────────────────────────────────────────────
        # 提醒
        # ────────────────────────────────────────────────────────────────────
        reminders = [
            Reminder(
                user_id=patient.id,
                reminder_type=ReminderType.MEDICATION,
                title="服用降压药（氨氯地平）",
                medication_name="氨氯地平片",
                dosage="5mg × 1片",
                frequency=ReminderFrequency.DAILY,
                remind_time="08:00",
                start_date=now - timedelta(days=30),
                notes="饭后服用，不可突然停药，如出现脚踝浮肿请及时复诊",
                status=ReminderStatus.ACTIVE,
            ),
            Reminder(
                user_id=patient.id,
                reminder_type=ReminderType.MEDICATION,
                title="服用阿司匹林肠溶片",
                medication_name="阿司匹林肠溶片",
                dosage="100mg × 1片",
                frequency=ReminderFrequency.DAILY,
                remind_time="21:00",
                start_date=now - timedelta(days=30),
                notes="晚饭后30分钟服用，服药期间避免空腹",
                status=ReminderStatus.ACTIVE,
            ),
            Reminder(
                user_id=patient.id,
                reminder_type=ReminderType.EXAMINATION,
                title="测量血压并记录",
                frequency=ReminderFrequency.TWICE_DAILY,
                remind_time="07:30",
                start_date=now - timedelta(days=14),
                notes="早起和晚睡前各测一次，记录收缩压/舒张压，就诊时携带记录",
                status=ReminderStatus.ACTIVE,
            ),
            Reminder(
                user_id=patient.id,
                reminder_type=ReminderType.FOLLOW_UP,
                title="心内科复诊",
                frequency=ReminderFrequency.ONCE,
                remind_time="09:00",
                start_date=now + timedelta(days=14),
                end_date=now + timedelta(days=14),
                notes="携带近两周血压记录表，预约号：HK20260325，北京协和医院心内科门诊",
                status=ReminderStatus.ACTIVE,
            ),
            Reminder(
                user_id=patient.id,
                reminder_type=ReminderType.MEDICATION,
                title="服用维生素D3",
                medication_name="维生素D3软胶囊",
                dosage="400IU × 1粒",
                frequency=ReminderFrequency.DAILY,
                remind_time="12:00",
                start_date=now - timedelta(days=60),
                end_date=now - timedelta(days=1),
                notes="已完成30日疗程",
                status=ReminderStatus.COMPLETED,
            ),
        ]
        db.add_all(reminders)

        db.commit()

        # ── 打印汇总 ──────────────────────────────────────────────────────────
        conv_count = db.query(Conversation).count()
        msg_count = db.query(Message).count()
        rec_count = db.query(MedicalRecord).count()
        rem_count = db.query(Reminder).count()
        print("\n[OK] 虚拟数据导入成功！")
        print("  登录账号:")
        print("    患者:   patient01 / Test1234")
        print("    医生:   doctor01  / Test1234")
        print("    管理员: admin     / Admin1234")
        print(f"  数据统计: 会话 {conv_count} 条 | 消息 {msg_count} 条 | 病历 {rec_count} 条 | 提醒 {rem_count} 条")

    except Exception as e:
        db.rollback()
        print(f"\n[FAIL] 数据导入失败: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
