from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import database
import models
import schemas
import security
import services

router = APIRouter(prefix="/api/v1/patients", tags=["Patients"])

@router.post("", response_model=schemas.PatientResponse, status_code=status.HTTP_201_CREATED)
def create_patient(
    patient_in: schemas.PatientCreate,
    db: Session = Depends(database.get_db),
    current_user=Depends(security.get_current_user)
):
    if patient_in.doctor_id:
        doc = db.query(models.Doctor).filter(models.Doctor.id == patient_in.doctor_id).first()
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
        if not doc.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assigned doctor is inactive")

    new_patient = models.Patient(
        name=patient_in.name,
        age=patient_in.age,
        phone=patient_in.phone,
        doctor_id=patient_in.doctor_id,
        created_by=current_user.email,
        updated_by=current_user.email
    )
    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)
    return new_patient

@router.get("", response_model=schemas.PaginatedResponse[schemas.PatientResponse])
def list_patients(
    age_gt: Optional[int] = None,
    is_active: Optional[bool] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(database.get_db),
    current_user=Depends(security.get_current_user)
):
    query = db.query(models.Patient)
    if current_user.role == models.RoleEnum.DOCTOR:
        if not current_user.doctor:
            return {"total": 0, "page": page, "limit": limit, "items": []}
        query = query.filter(models.Patient.doctor_id == current_user.doctor.id)

    if age_gt is not None:
        query = query.filter(models.Patient.age > age_gt)
    if is_active is not None:
        query = query.filter(models.Patient.is_active == is_active)

    total = query.count()
    items = query.offset((page - 1) * limit).limit(limit).all()
    return {"total": total, "page": page, "limit": limit, "items": items}

@router.get("/{patient_id}", response_model=schemas.PatientResponse)
def get_patient(
    patient_id: int,
    db: Session = Depends(database.get_db),
    current_user=Depends(security.get_current_user)
):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    if current_user.role == models.RoleEnum.DOCTOR:
        if not current_user.doctor or patient.doctor_id != current_user.doctor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return patient

@router.put("/{patient_id}", response_model=schemas.PatientResponse)
@router.patch("/{patient_id}", response_model=schemas.PatientResponse)
def update_patient(
    patient_id: int,
    update_data: schemas.PatientUpdate,
    db: Session = Depends(database.get_db),
    current_user=Depends(security.get_current_user)
):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    if current_user.role == models.RoleEnum.DOCTOR:
        if not current_user.doctor or patient.doctor_id != current_user.doctor.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    data = update_data.model_dump(exclude_unset=True)
    if "doctor_id" in data and data["doctor_id"] is not None:
        doc = db.query(models.Doctor).filter(models.Doctor.id == data["doctor_id"]).first()
        if not doc or not doc.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or inactive doctor ID")

    for k, v in data.items():
        setattr(patient, k, v)
    patient.updated_by = current_user.email
    db.commit()
    db.refresh(patient)
    return patient

@router.delete("/{patient_id}", status_code=status.HTTP_200_OK)
def delete_patient(
    patient_id: int,
    db: Session = Depends(database.get_db),
    current_user=Depends(services.require_admin)
):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    patient.is_active = False
    patient.updated_by = current_user.email
    db.commit()
    return {"message": f"Patient {patient_id} soft-deleted successfully"}

@router.get("/{patient_id}/appointments", response_model=List[schemas.AppointmentResponse])
def get_patient_appointments(
    patient_id: int,
    db: Session = Depends(database.get_db),
    current_user=Depends(security.get_current_user)
):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    if current_user.role == models.RoleEnum.DOCTOR and patient.doctor_id != current_user.doctor.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return db.query(models.Appointment).filter(models.Appointment.patient_id == patient_id).all()