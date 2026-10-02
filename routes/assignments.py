from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import database
import models
import schemas
import security
import services

router = APIRouter(prefix="/api/v1/assignments", tags=["Doctor-Patient Assignment"])

@router.post(
    "/doctors/{doctor_id}/patients/{patient_id}",
    response_model=schemas.PatientResponse,
    status_code=status.HTTP_200_OK,
    summary="Assign Patient to Doctor"
)
def assign_patient_to_doctor(
    doctor_id: int,
    patient_id: int,
    db: Session = Depends(database.get_db),
    current_user=Depends(services.require_admin)
):
    doctor = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    if not doctor.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot assign patient to an inactive doctor")

    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient or not patient.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found or inactive")

    patient.doctor_id = doctor_id
    patient.updated_by = current_user.email
    db.commit()
    db.refresh(patient)
    return patient

@router.get(
    "/doctors/{doctor_id}/patients",
    response_model=schemas.PaginatedResponse[schemas.PatientResponse],
    summary="List All Patients Assigned to a Doctor"
)
def get_doctor_patients(
    doctor_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(database.get_db),
    current_user=Depends(security.get_current_user)
):
    doctor = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    if not doctor.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Doctor is currently inactive")

    services.verify_doctor_patient_access(current_user, doctor_id)

    query = db.query(models.Patient).filter(models.Patient.doctor_id == doctor_id, models.Patient.is_active == True)
    total = query.count()
    items = query.offset((page - 1) * limit).limit(limit).all()
    return {"total": total, "page": page, "limit": limit, "items": items}