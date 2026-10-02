from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import database
import models
import schemas
import security
import services

router = APIRouter(prefix="/api/v1/appointments", tags=["Appointments"])

@router.post("", response_model=schemas.AppointmentResponse, status_code=status.HTTP_201_CREATED)
def create_appointment(
    appt_in: schemas.AppointmentCreate,
    db: Session = Depends(database.get_db),
    current_user=Depends(security.get_current_user)
):
    doctor = db.query(models.Doctor).filter(models.Doctor.id == appt_in.doctor_id).first()
    if not doctor or not doctor.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Doctor not found or inactive")

    patient = db.query(models.Patient).filter(models.Patient.id == appt_in.patient_id).first()
    if not patient or not patient.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Patient not found or inactive")

    # Prevent overlapping appointments for the same doctor
    existing_overlap = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == appt_in.doctor_id,
        models.Appointment.appointment_date == appt_in.appointment_date,
        models.Appointment.status != models.AppointmentStatusEnum.CANCELLED
    ).first()
    if existing_overlap:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Overlapping appointment: Doctor is already booked at this exact time"
        )

    appt = models.Appointment(
        doctor_id=appt_in.doctor_id,
        patient_id=appt_in.patient_id,
        appointment_date=appt_in.appointment_date,
        status=models.AppointmentStatusEnum.SCHEDULED,
        created_by=current_user.email,
        updated_by=current_user.email
    )
    db.add(appt)
    try:
        db.commit()
        db.refresh(appt)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Appointment slot conflict")
    return appt

@router.get("", response_model=schemas.PaginatedResponse[schemas.AppointmentResponse])
def list_appointments(
    status: Optional[models.AppointmentStatusEnum] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(database.get_db),
    current_user=Depends(security.get_current_user)
):
    query = db.query(models.Appointment)
    if current_user.role == models.RoleEnum.DOCTOR:
        if not current_user.doctor:
            return {"total": 0, "page": page, "limit": limit, "items": []}
        query = query.filter(models.Appointment.doctor_id == current_user.doctor.id)

    if status:
        query = query.filter(models.Appointment.status == status)

    total = query.count()
    items = query.offset((page - 1) * limit).limit(limit).all()
    return {"total": total, "page": page, "limit": limit, "items": items}

@router.get("/{appointment_id}", response_model=schemas.AppointmentResponse)
def get_appointment(
    appointment_id: int,
    db: Session = Depends(database.get_db),
    current_user=Depends(security.get_current_user)
):
    appt = db.query(models.Appointment).filter(models.Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    services.verify_doctor_patient_access(current_user, appt.doctor_id)
    return appt

@router.put("/{appointment_id}", response_model=schemas.AppointmentResponse)
def update_appointment(
    appointment_id: int,
    update_data: schemas.AppointmentUpdate,
    db: Session = Depends(database.get_db),
    current_user=Depends(security.get_current_user)
):
    appt = db.query(models.Appointment).filter(models.Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    services.verify_doctor_patient_access(current_user, appt.doctor_id)

    data = update_data.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(appt, k, v)
    appt.updated_by = current_user.email
    db.commit()
    db.refresh(appt)
    return appt

@router.delete("/{appointment_id}")
def cancel_appointment(
    appointment_id: int,
    db: Session = Depends(database.get_db),
    current_user=Depends(security.get_current_user)
):
    appt = db.query(models.Appointment).filter(models.Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    services.verify_doctor_patient_access(current_user, appt.doctor_id)
    appt.status = models.AppointmentStatusEnum.CANCELLED
    appt.updated_by = current_user.email
    db.commit()
    return {"message": "Appointment cancelled successfully"}