"""
为已存在的 patient01 账号插入提醒测试数据
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from app.database.base import SessionLocal
from app.models import User
from app.models.reminder import Reminder
from app.models.enums import ReminderType, ReminderStatus, ReminderFrequency


def seed_reminders():
    db = SessionLocal()
    try:
        # Find first patient user
        patient = db.query(User).filter(User.role == "patient").first()
        if not patient:
            print("[WARN] No patient user found. Run seed_data.py first.")
            return

        # Check existing reminders
        existing = db.query(Reminder).filter(Reminder.user_id == patient.id).count()
        if existing > 0:
            print(f"[WARN] Patient already has {existing} reminders, skipping.")
            return

        now = datetime.utcnow()
        reminders = [
            Reminder(
                user_id=patient.id,
                reminder_type=ReminderType.MEDICATION,
                title="服用降压药（氨氯地平）",
                medication_name="氨氯地平片",
                dosage="5mg x 1片",
                frequency=ReminderFrequency.DAILY,
                remind_time="08:00",
                start_date=now - timedelta(days=30),
                notes="饭后服用，不可突然停药",
                status=ReminderStatus.ACTIVE,
            ),
            Reminder(
                user_id=patient.id,
                reminder_type=ReminderType.MEDICATION,
                title="服用阿司匹林肠溶片",
                medication_name="阿司匹林肠溶片",
                dosage="100mg x 1片",
                frequency=ReminderFrequency.DAILY,
                remind_time="21:00",
                start_date=now - timedelta(days=30),
                notes="晚饭后30分钟服用",
                status=ReminderStatus.ACTIVE,
            ),
            Reminder(
                user_id=patient.id,
                reminder_type=ReminderType.EXAMINATION,
                title="测量血压并记录",
                frequency=ReminderFrequency.TWICE_DAILY,
                remind_time="07:30",
                start_date=now - timedelta(days=14),
                notes="早晚各测一次，记录收缩压/舒张压",
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
                notes="携带近两周血压记录，预约号：HK20260325",
                status=ReminderStatus.ACTIVE,
            ),
            Reminder(
                user_id=patient.id,
                reminder_type=ReminderType.MEDICATION,
                title="服用维生素D3（已完成）",
                medication_name="维生素D3软胶囊",
                dosage="400IU x 1粒",
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
        print(f"[OK] Inserted {len(reminders)} reminders for user: {patient.username}")
    except Exception as e:
        db.rollback()
        print(f"[FAIL] {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_reminders()
