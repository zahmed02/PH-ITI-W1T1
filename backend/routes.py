from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
import os
import shutil
from datetime import datetime

from backend.database import get_db
from backend.models import Doctor, Patient, DoctorAvailability, Appointment, Review
from backend.schemas import (
    DoctorResponse, DoctorWithDetails,
    AppointmentCreate, AppointmentResponse,
    ReviewCreate, ReviewResponse
)

router = APIRouter()

# -------------------- DOCTOR ENDPOINTS --------------------
@router.get("/doctors/", response_model=List[DoctorResponse])
def get_all_doctors(
    skip: int = 0,
    limit: int = 100,
    specialty: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Doctor)
    if specialty:
        query = query.filter(Doctor.specialty.ilike(f"%{specialty}%"))
    return query.offset(skip).limit(limit).all()

@router.get("/doctors/{doctor_id}", response_model=DoctorWithDetails)
def get_doctor(doctor_id: int, db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    avg_rating = db.query(func.avg(Review.rating)).filter(Review.doctor_id == doctor_id).scalar()
    review_count = db.query(func.count(Review.id)).filter(Review.doctor_id == doctor_id).scalar()
    
    result = DoctorWithDetails.model_validate(doctor)
    result.avg_rating = float(avg_rating) if avg_rating else 0.0
    result.review_count = review_count or 0
    result.reviews = doctor.reviews
    return result

@router.get("/doctors/search/", response_model=List[DoctorResponse])
def search_doctors(
    specialty: Optional[str] = Query(None),
    min_experience: Optional[int] = Query(None),
    min_rating: Optional[float] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Doctor)
    if specialty:
        query = query.filter(Doctor.specialty.ilike(f"%{specialty}%"))
    if min_experience:
        query = query.filter(Doctor.years_of_experience >= min_experience)
    
    doctors = query.all()
    if min_rating:
        result = []
        for doc in doctors:
            avg = db.query(func.avg(Review.rating)).filter(Review.doctor_id == doc.id).scalar()
            if avg and float(avg) >= min_rating:
                result.append(doc)
            elif not avg and min_rating <= 0:
                result.append(doc)
        return result
    return doctors

@router.post("/doctors/{doctor_id}/image")
async def upload_doctor_image(
    doctor_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Create directory if not exists
    upload_dir = "static/images/doctors"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate unique filename
    ext = os.path.splitext(file.filename)[1]
    filename = f"doctor_{doctor_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
    file_path = os.path.join(upload_dir, filename)
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Update database with relative path
    doctor.profile_image = f"/static/images/doctors/{filename}"
    db.commit()
    db.refresh(doctor)
    
    return {"message": "Image uploaded successfully", "profile_image": doctor.profile_image}

@router.get("/doctors/{doctor_id}/availability")
def get_doctor_availability(doctor_id: int, db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    availability = db.query(DoctorAvailability).filter(DoctorAvailability.doctor_id == doctor_id).all()
    return availability

# -------------------- APPOINTMENT ENDPOINTS --------------------
@router.get("/appointments/", response_model=List[AppointmentResponse])
def get_all_appointments(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Appointment).offset(skip).limit(limit).all()

@router.get("/appointments/doctor/{doctor_id}", response_model=List[AppointmentResponse])
def get_appointments_by_doctor(doctor_id: int, db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return db.query(Appointment).filter(Appointment.doctor_id == doctor_id).all()

@router.get("/appointments/patient/{patient_id}", response_model=List[AppointmentResponse])
def get_appointments_by_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return db.query(Appointment).filter(Appointment.patient_id == patient_id).all()

@router.post("/appointments/", response_model=AppointmentResponse)
def create_appointment(appointment: AppointmentCreate, db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.id == appointment.doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    patient = db.query(Patient).filter(Patient.id == appointment.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    db_appointment = Appointment(**appointment.model_dump())
    db.add(db_appointment)
    db.commit()
    db.refresh(db_appointment)
    return db_appointment

# -------------------- REVIEW ENDPOINTS --------------------
@router.get("/reviews/", response_model=List[ReviewResponse])
def get_all_reviews(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Review).offset(skip).limit(limit).all()

@router.get("/reviews/doctor/{doctor_id}", response_model=List[ReviewResponse])
def get_reviews_by_doctor(doctor_id: int, db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return db.query(Review).filter(Review.doctor_id == doctor_id).all()

@router.post("/reviews/", response_model=ReviewResponse)
def create_review(review: ReviewCreate, db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.id == review.doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    patient = db.query(Patient).filter(Patient.id == review.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    db_review = Review(**review.model_dump())
    db.add(db_review)
    
    # Update doctor's average rating
    avg_rating = db.query(func.avg(Review.rating)).filter(Review.doctor_id == review.doctor_id).scalar()
    doctor.rating = float(avg_rating) if avg_rating else 0.0
    db.commit()
    db.refresh(db_review)
    return db_review