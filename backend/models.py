from sqlalchemy import Column, Integer, String, Text, Float, TIMESTAMP, ForeignKey, CheckConstraint, Time
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.database import Base

class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    specialty = Column(String(100), nullable=False)
    years_of_experience = Column(Integer, nullable=False)
    bio = Column(Text)
    profile_image = Column(String(255), nullable=True)
    rating = Column(Float, default=0.0)
    created_at = Column(TIMESTAMP, server_default=func.now())

    reviews = relationship("Review", back_populates="doctor", cascade="all, delete")
    appointments = relationship("Appointment", back_populates="doctor", cascade="all, delete")
    availability = relationship("DoctorAvailability", back_populates="doctor", cascade="all, delete")
    # One-to-one: the login account for this doctor, if one has been created.
    login_account = relationship("User", back_populates="doctor", uselist=False)

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    phone = Column(String(20))
    created_at = Column(TIMESTAMP, server_default=func.now())

    reviews = relationship("Review", back_populates="patient", cascade="all, delete")
    appointments = relationship("Appointment", back_populates="patient", cascade="all, delete")
    # One-to-one: the login account for this patient, if one has been created.
    login_account = relationship("User", back_populates="patient", uselist=False)

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    appointment_time = Column(TIMESTAMP, nullable=False)
    status = Column(String(20), default="scheduled")
    notes = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())

    doctor = relationship("Doctor", back_populates="appointments")
    patient = relationship("Patient", back_populates="appointments")

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    rating = Column(Integer, CheckConstraint("rating >= 1 AND rating <= 5"), nullable=False)
    comment = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())

    doctor = relationship("Doctor", back_populates="reviews")
    patient = relationship("Patient", back_populates="reviews")

class DoctorAvailability(Base):
    __tablename__ = "doctor_availability"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    # 0=Sunday ... 6=Saturday (matches the CHECK(0..6) constraint and the
    # actual seeded data). See backend/availability.py for the conversion
    # used whenever this column is queried from Python's date.weekday().
    day_of_week = Column(Integer, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    doctor = relationship("Doctor", back_populates="availability")


class User(Base):
    """
    Login accounts for the portal, with role-based access:

    - role="admin"   -> doctor_id and patient_id are both NULL. Full access
                        to everything (see backend/auth.py for the checks).
    - role="doctor"  -> doctor_id links to exactly one Doctor row. This
                        account can only see/manage that doctor's own data.
    - role="patient" -> patient_id links to exactly one Patient row. This
                        account can only see/manage that patient's own data.

    Enforcing "role X must have the matching link set" is done in
    application code (backend/auth.py), not a DB CHECK constraint - see
    the migration file (2_role_based_users.sql) for why.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(10), nullable=False, default="patient")
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="SET NULL"), unique=True, nullable=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="SET NULL"), unique=True, nullable=True)
    # Incremented on logout. A JWT is only valid if its embedded "tv" claim
    # matches the current value here - this is what makes logout actually
    # revoke the token server-side instead of merely deleting it client-side.
    token_version = Column(Integer, nullable=False, default=0)
    created_at = Column(TIMESTAMP, server_default=func.now())

    __table_args__ = (
        CheckConstraint("role IN ('admin', 'doctor', 'patient')", name="users_role_check"),
    )

    doctor = relationship("Doctor", back_populates="login_account")
    patient = relationship("Patient", back_populates="login_account")