from sqlalchemy import Column, Integer, String, Text, Float, TIMESTAMP, ForeignKey, CheckConstraint, Time, Boolean, Date, UniqueConstraint
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
    notifications = relationship("Notification", back_populates="appointment", cascade="all, delete")

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


class Notification(Base):
    """
    In-app notifications for doctors about their own appointments (new
    booking, cancellation, etc). Created server-side inside
    backend/booking.py right alongside the appointment itself - never
    created directly by a route, so there's exactly one code path that
    can produce them and it can't be skipped by any booking entry point
    (AI chat, admin direct booking, or a future patient self-booking UI).
    """
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    appointment_id = Column(Integer, ForeignKey("appointments.id", ondelete="CASCADE"), nullable=True)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    doctor = relationship("Doctor")
    appointment = relationship("Appointment", back_populates="notifications")


class DoctorTimeOff(Base):
    """
    A specific date a doctor is NOT working, overriding their normal
    weekly recurring hours in doctor_availability for that one date.
    Checked by backend/availability.py::get_doctor_working_hours - the
    single choke point used by every slot-computation path (booking, the
    AI assistant, the schedule-preview endpoint), so a day off blocks new
    bookings everywhere automatically. Existing appointments on that date
    are NOT auto-deleted here - backend/appointment_actions.py bulk-
    cancels them (with patient emails) as part of creating this row.
    """
    __tablename__ = "doctor_time_off"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    off_date = Column(Date, nullable=False)
    reason = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("doctor_id", "off_date", name="doctor_time_off_doctor_date_unique"),
    )

    doctor = relationship("Doctor")


class AppointmentTransfer(Base):
    """
    Tracks a doctor-initiated transfer of a (now-cancelled) appointment to
    a colleague in the same specialty. Nothing moves until the receiving
    doctor manually confirms (backend/appointment_actions.py re-checks
    they're actually free at that date/time at confirm-time, since their
    schedule may have changed since the transfer was proposed) - only
    then is a new Appointment created and the patient emailed the new PDF.
    """
    __tablename__ = "appointment_transfers"

    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False)
    from_doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    to_doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), nullable=False, default="pending")  # pending | confirmed | declined
    new_appointment_id = Column(Integer, ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    resolved_at = Column(TIMESTAMP, nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'confirmed', 'declined')", name="appointment_transfers_status_check"),
    )

    appointment = relationship("Appointment", foreign_keys=[appointment_id])
    from_doctor = relationship("Doctor", foreign_keys=[from_doctor_id])
    to_doctor = relationship("Doctor", foreign_keys=[to_doctor_id])
    new_appointment = relationship("Appointment", foreign_keys=[new_appointment_id])