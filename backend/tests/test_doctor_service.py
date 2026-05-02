from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.permissions import Role
from app.database.base import Base
from app.models.conversation import Conversation, ConversationStatus
from app.models.user import User
from app.services.doctor_service import Department, DoctorService


def _make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)
    return session()


def _doctor(
    doctor_id: int,
    username: str,
    department: str,
    is_active: bool = True,
) -> User:
    return User(
        id=doctor_id,
        username=username,
        email=f"{username}@example.com",
        hashed_password="hashed",
        role=Role.DOCTOR,
        full_name=username,
        doctor_department=department,
        is_active=is_active,
        is_verified=True,
    )


def _patient(patient_id: int = 100) -> User:
    return User(
        id=patient_id,
        username=f"patient_{patient_id}",
        email=f"patient_{patient_id}@example.com",
        hashed_password="hashed",
        role=Role.PATIENT,
        is_active=True,
    )


def test_get_doctors_by_department_uses_standard_seed_doctor_accounts_only():
    db = _make_db()
    try:
        db.add_all([
            _doctor(2, "doctor1", "心内科"),
            _doctor(9, "doctor_cardiology", "心内科"),
            _doctor(18, "outside_seed_range", "心内科"),
        ])
        db.commit()

        doctors = DoctorService.get_doctors_by_department(Department.CARDIOLOGY, db)

        assert [doctor.id for doctor in doctors] == [9]
    finally:
        db.close()


def test_find_available_doctor_prefers_lower_active_session_count_with_stable_order():
    db = _make_db()
    try:
        db.add_all([
            _patient(100),
            _patient(101),
            _patient(102),
            _doctor(9, "doctor_cardiology", "心内科"),
            _doctor(17, "doctor_general_cardiology", "心内科"),
        ])
        db.flush()
        db.add_all([
            Conversation(
                id=1,
                patient_id=100,
                doctor_id=9,
                chief_complaint="胸口不舒服",
                status=ConversationStatus.ACTIVE,
            ),
            Conversation(
                id=2,
                patient_id=101,
                doctor_id=9,
                chief_complaint="心慌",
                status=ConversationStatus.PENDING,
            ),
            Conversation(
                id=3,
                patient_id=102,
                doctor_id=17,
                chief_complaint="胸闷",
                status=ConversationStatus.ACTIVE,
            ),
        ])
        db.commit()

        doctor = DoctorService.find_available_doctor(Department.CARDIOLOGY, db)

        assert doctor.id == 17
    finally:
        db.close()

