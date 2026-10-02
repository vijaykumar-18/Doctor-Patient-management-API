from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import database
import models
import schemas
import security
import services

router = APIRouter(prefix="/api/v1/billings", tags=["Billing"])

@router.post("", response_model=schemas.BillingResponse, status_code=status.HTTP_201_CREATED)
def create_billing(
    billing_in: schemas.BillingCreate,
    db: Session = Depends(database.get_db),
    current_user=Depends(services.require_admin)
):
    doctor = db.query(models.Doctor).filter(models.Doctor.id == billing_in.doctor_id).first()
    if not doctor or not doctor.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Doctor does not exist or is inactive")

    patient = db.query(models.Patient).filter(models.Patient.id == billing_in.patient_id).first()
    if not patient or not patient.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Patient does not exist or is inactive")

    appt = None
    if billing_in.appointment_id:
        appt = db.query(models.Appointment).filter(models.Appointment.id == billing_in.appointment_id).first()
        if not appt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
        if appt.doctor_id != billing_in.doctor_id or appt.patient_id != billing_in.patient_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Appointment does not match doctor & patient")
        if appt.status == models.AppointmentStatusEnum.CANCELLED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot generate bill for a cancelled appointment")

        duplicate_billing = db.query(models.Billing).filter(models.Billing.appointment_id == billing_in.appointment_id).first()
        if duplicate_billing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Billing record already exists for this appointment")

    # DB Transaction: Create billing + update appointment status
    try:
        total = billing_in.consultation_fee + billing_in.additional_charges
        billing = models.Billing(
            patient_id=billing_in.patient_id,
            doctor_id=billing_in.doctor_id,
            appointment_id=billing_in.appointment_id,
            consultation_fee=billing_in.consultation_fee,
            additional_charges=billing_in.additional_charges,
            total_amount=total,
            payment_status=models.PaymentStatusEnum.PENDING,
            payment_mode=billing_in.payment_mode,
            is_active=True,
            created_by=current_user.email,
            updated_by=current_user.email
        )
        db.add(billing)

        if appt:
            appt.status = models.AppointmentStatusEnum.COMPLETED
            appt.updated_by = current_user.email

        db.commit()
        db.refresh(billing)
        return billing
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Billing transaction failed: {str(exc)}")

@router.get("", response_model=schemas.PaginatedResponse[schemas.BillingResponse])
def list_billings(
    payment_status: Optional[models.PaymentStatusEnum] = None,
    doctor_id: Optional[int] = None,
    patient_id: Optional[int] = None,
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(database.get_db),
    current_user=Depends(security.get_current_user)
):
    query = db.query(models.Billing).filter(models.Billing.is_active == True)

    if current_user.role == models.RoleEnum.DOCTOR:
        if not current_user.doctor:
            return {"total": 0, "page": page, "limit": limit, "items": []}
        query = query.filter(models.Billing.doctor_id == current_user.doctor.id)
    elif doctor_id:
        query = query.filter(models.Billing.doctor_id == doctor_id)

    if patient_id:
        query = query.filter(models.Billing.patient_id == patient_id)
    if payment_status:
        query = query.filter(models.Billing.payment_status == payment_status)
    if from_date:
        query = query.filter(models.Billing.created_at >= datetime.strptime(from_date, "%Y-%m-%d"))
    if to_date:
        query = query.filter(models.Billing.created_at <= datetime.strptime(to_date, "%Y-%m-%d"))

    total = query.count()
    items = query.offset((page - 1) * limit).limit(limit).all()
    return {"total": total, "page": page, "limit": limit, "items": items}

@router.get("/{billing_id}", response_model=schemas.BillingResponse)
def get_billing(
    billing_id: int,
    db: Session = Depends(database.get_db),
    current_user=Depends(security.get_current_user)
):
    billing = db.query(models.Billing).filter(models.Billing.id == billing_id).first()
    if not billing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Billing record not found")

    services.verify_doctor_patient_access(current_user, billing.doctor_id)
    return billing

@router.get("/doctor/{doctor_id}", response_model=List[schemas.BillingResponse])
def get_doctor_billings(
    doctor_id: int,
    db: Session = Depends(database.get_db),
    current_user=Depends(security.get_current_user)
):
    doctor = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    services.verify_doctor_patient_access(current_user, doctor_id)
    return db.query(models.Billing).filter(
        models.Billing.doctor_id == doctor_id,
        models.Billing.is_active == True
    ).all()

@router.get("/patient/{patient_id}", response_model=List[schemas.BillingResponse])
def get_patient_billings(
    patient_id: int,
    db: Session = Depends(database.get_db),
    current_user=Depends(security.get_current_user)
):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    if current_user.role == models.RoleEnum.DOCTOR and patient.doctor_id != current_user.doctor.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return db.query(models.Billing).filter(
        models.Billing.patient_id == patient_id,
        models.Billing.is_active == True
    ).all()

@router.put("/{billing_id}", response_model=schemas.BillingResponse)
@router.patch("/{billing_id}", response_model=schemas.BillingResponse)
def update_billing(
    billing_id: int,
    update_data: schemas.BillingUpdate,
    db: Session = Depends(database.get_db),
    current_user=Depends(services.require_admin)
):
    billing = db.query(models.Billing).filter(models.Billing.id == billing_id).first()
    if not billing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Billing record not found")

    data = update_data.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(billing, k, v)

    billing.total_amount = billing.consultation_fee + billing.additional_charges
    billing.updated_by = current_user.email
    db.commit()
    db.refresh(billing)
    return billing

@router.delete("/{billing_id}")
def delete_billing(
    billing_id: int,
    db: Session = Depends(database.get_db),
    current_user=Depends(services.require_admin)
):
    billing = db.query(models.Billing).filter(models.Billing.id == billing_id).first()
    if not billing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Billing record not found")
    billing.is_active = False
    billing.updated_by = current_user.email
    db.commit()
    return {"message": "Billing soft-deleted successfully"}