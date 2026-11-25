
from datetime import date, datetime, time, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from models import Doctor, Slot


# ==========================================
# CONFIGURATION
# ==========================================

DAYS_TO_GENERATE = 60

WORKING_DAYS = [0, 1, 2, 3, 4, 5]

SLOT_DURATION = 30

WORKING_SESSIONS = [
    ("09:00", "13:00"),
    ("14:00", "18:00"),
]


# ==========================================
# DOCTOR DATA
# ==========================================

DOCTORS = [
    ("Dr Ananya Sharma", "Cardiologist", 14, 1200),
    ("Dr Rahul Mehta", "Dermatologist", 11, 900),
    ("Dr Priya Nair", "Neurologist", 16, 1500),
    ("Dr Arjun Rao", "Orthopedic", 12, 1100),
    ("Dr Sneha Kapoor", "Pediatrician", 10, 800),
    ("Dr Vikram Singh", "General Physician", 18, 600),
    ("Dr Neha Iyer", "Dentist", 9, 700),
    ("Dr Karan Malhotra", "ENT Specialist", 13, 950),
]


# ==========================================
# SPEECH FRIENDLY FORMATTING
# ==========================================

def clean_text(value):
    """Remove unwanted symbols and normalize text."""

    if not value:
        return ""

    return " ".join(
        str(value)
        .replace("&", " and ")
        .replace("_", " ")
        .replace("-", " ")
        .replace("/", " ")
        .split()
    )


def format_date_for_speech(value):
    """Convert date into a natural spoken format."""

    if isinstance(value, str):
        value = date.fromisoformat(value)

    return value.strftime("%A, %d %B %Y")


def format_time_for_speech(value):
    """Convert 24-hour time into natural spoken format."""

    if isinstance(value, str):
        value = datetime.strptime(value[:5], "%H:%M").time()

    return value.strftime("%I:%M %p").lstrip("0")


def normalize_time(value):
    """Normalize time for duplicate checking."""

    if isinstance(value, time):
        return value.strftime("%H:%M")

    return str(value)[:5]


# ==========================================
# GENERATE DAILY SLOTS
# ==========================================

def generate_daily_slots():

    slots = []

    for session_start, session_end in WORKING_SESSIONS:

        current = datetime.strptime(
            session_start, "%H:%M"
        )

        end = datetime.strptime(
            session_end, "%H:%M"
        )

        while current + timedelta(minutes=SLOT_DURATION) <= end:

            start_time = current.strftime("%H:%M")

            finish_time = (
                current + timedelta(minutes=SLOT_DURATION)
            ).strftime("%H:%M")

            slots.append((start_time, finish_time))

            current += timedelta(minutes=SLOT_DURATION)

    return slots


# ==========================================
# SEED DOCTORS
# ==========================================

def seed_doctors(db: Session):

    existing_names = {
        doctor.name
        for doctor in db.query(Doctor).all()
    }

    new_doctors = []

    for name, speciality, experience, fee in DOCTORS:

        if name not in existing_names:

            new_doctors.append(
                Doctor(
                    name=clean_text(name),
                    speciality=clean_text(speciality),
                    experience=experience,
                    consultation_fee=fee
                )
            )

    if new_doctors:
        db.add_all(new_doctors)
        db.flush()

    print("New doctors added:", len(new_doctors))


# ==========================================
# SEED APPOINTMENT SLOTS
# ==========================================

def seed_appointment_slots(db: Session):

    today = date.today()

    current_time = datetime.now().time()

    end_date = today + timedelta(days=DAYS_TO_GENERATE)

    doctors = db.query(Doctor).all()

    existing_slots = db.query(Slot).filter(
        Slot.date >= today,
        Slot.date <= end_date
    ).all()

    existing_keys = {
        (
            slot.doctor_id,
            slot.date,
            normalize_time(slot.start_time)
        )
        for slot in existing_slots
    }

    daily_slots = generate_daily_slots()

    new_slots = []

    for doctor in doctors:

        for offset in range(DAYS_TO_GENERATE + 1):

            appointment_date = today + timedelta(days=offset)

            if appointment_date.weekday() not in WORKING_DAYS:
                continue

            for start_time, end_time in daily_slots:

                slot_time = datetime.strptime(
                    start_time, "%H:%M"
                ).time()

                if appointment_date == today and slot_time <= current_time:
                    continue

                slot_key = (
                    doctor.id,
                    appointment_date,
                    start_time
                )

                if slot_key in existing_keys:
                    continue

                new_slots.append(
                    Slot(
                        doctor_id=doctor.id,
                        date=appointment_date,
                        start_time=start_time,
                        end_time=end_time
                    )
                )

                existing_keys.add(slot_key)

    if new_slots:
        db.add_all(new_slots)

    db.flush()

    print("New appointment slots:", len(new_slots))
    print("Availability through:", format_date_for_speech(end_date))

    return len(new_slots)


# ==========================================
# MAIN SEED FUNCTION
# ==========================================

def seed_database(db: Session):

    try:

        seed_doctors(db)

        new_slots = seed_appointment_slots(db)

        db.commit()

        print("\nDatabase seeding completed")
        print("Total doctors:", db.query(Doctor).count())
        print("Total appointment slots:", db.query(Slot).count())
        print("New slots created:", new_slots)

    except SQLAlchemyError as error:

        db.rollback()

        print("Database seeding failed:", str(error))

        raise
