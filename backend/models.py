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
    Login accounts for the portal. Separate from Patient - a User is who
    logs in to the website; a Patient is a clinical record the chat/booking
    system operates on. Wiring a User to a specific Patient record is a
    reasonable next step, but keeping them separate for now avoids forcing
    every login to already have a patient profile.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    # Incremented on logout. A JWT is only valid if its embedded "tv" claim
    # matches the current value here - this is what makes logout actually
    # revoke the token server-side instead of merely deleting it client-side.
    token_version = Column(Integer, nullable=False, default=0)
    created_at = Column(TIMESTAMP, server_default=func.now())
