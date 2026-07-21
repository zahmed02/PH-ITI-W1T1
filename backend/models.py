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
    # IMPORTANT: matches the DB's CHECK (day_of_week BETWEEN 0 AND 6) and the
    # actual seeded data (1..5 = Monday..Friday), which means the convention
    # here is 0=Sunday, 1=Monday, ..., 6=Saturday - NOT Python's weekday().
    # See backend/availability.py:python_weekday_to_db_day() for the conversion
    # used whenever this column is queried from Python's date.weekday().
    day_of_week = Column(Integer, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    doctor = relationship("Doctor", back_populates="availability")
