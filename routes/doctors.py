from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import database
import models
import schemas
import security
import services

router = APIRouter(prefix="/api/v1/doctors", tags=["Doctors"])

@router.post("", response_model=schemas.DoctorResponse, status_code=status.HTTP_201_CREATED, summary="Create Doctor Profile")
def create_doctor(
    doctor_in: schemas.DoctorCreate,
    db: Session = Depends(database.get_db),
    current_user=Depends(services.require_admin)
):
    if db.query(models.Doctor).filter(models.Doctor.email == doctor_in.email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Doctor with this email already exists")

    new_doc = models.Doctor(
        name=doctor_in.name,
        email=doctor_in.email,
        specialization=doctor_in.specialization,
        is_active=True,
        created_by=current_user.email,
        updated_by=current_user.email
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)
    return new_doc

@router.get("", response_model=schemas.PaginatedResponse[schemas.DoctorResponse], summary="List All Doctors")
def list_doctors(
    specialization: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(database.get_db),
    current_user=Depends(security.get_current_user)
):
    query = db.query(models.Doctor)
    if specialization:
        query = query.filter(models.Doctor.specialization.ilike(f"%{specialization}%"))
    if is_active is not None:
        query = query.filter(models.Doctor.is_active == is_active)

    total = query.count()
    items = query.offset((page - 1) * limit).limit(limit).all()
    return {"total": total, "page": page, "limit": limit, "items": items}

@router.get("/{doctor_id}", response_model=schemas.DoctorResponse, summary="Get Doctor by ID")
def get_doctor(
    doctor_id: int,
    db: Session = Depends(database.get_db),
    current_user=Depends(security.get_current_user)
):
    doctor = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    return doctor

@router.put("/{doctor_id}", response_model=schemas.DoctorResponse, summary="Update Doctor Profile (PUT)")
@router.patch("/{doctor_id}", response_model=schemas.DoctorResponse, summary="Update Doctor Profile (PATCH)")
def update_doctor(
    doctor_id: int,
    update_data: schemas.DoctorUpdate,
    db: Session = Depends(database.get_db),
    current_user=Depends(services.require_admin)
):
    doctor = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    data = update_data.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(doctor, key, value)
    doctor.updated_by = current_user.email
    db.commit()
    db.refresh(doctor)
    return doctor

@router.delete("/{doctor_id}", status_code=status.HTTP_200_OK, summary="Soft Delete Doctor")
def delete_doctor(
    doctor_id: int,
    db: Session = Depends(database.get_db),
    current_user=Depends(services.require_admin)
):
    doctor = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    doctor.is_active = False
    doctor.updated_by = current_user.email
    db.commit()
    return {"message": f"Doctor {doctor_id} successfully soft-deleted"}

@router.get("/{doctor_id}/appointments", response_model=List[schemas.AppointmentResponse], summary="List Appointments for a Doctor")
def get_doctor_appointments(
    doctor_id: int,
    db: Session = Depends(database.get_db),
    current_user=Depends(security.get_current_user)
):
    doctor = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    services.verify_doctor_patient_access(current_user, doctor_id)
    return db.query(models.Appointment).filter(models.Appointment.doctor_id == doctor_id).all()