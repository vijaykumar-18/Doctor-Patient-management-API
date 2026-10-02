from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
import database
import models
import schemas
import services

router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])

@router.get("/revenue", response_model=List[schemas.RevenueDoctorReport])
def get_revenue_by_doctor(
    doctor_id: Optional[int] = None,
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    db: Session = Depends(database.get_db),
    _: models.User = Depends(services.require_admin)
):
    query = db.query(
        models.Billing.doctor_id,
        models.Doctor.name.label("doctor_name"),
        func.sum(models.Billing.total_amount).label("total_revenue")
    ).join(models.Doctor, models.Doctor.id == models.Billing.doctor_id)\
     .filter(models.Billing.is_active == True, models.Billing.payment_status == models.PaymentStatusEnum.PAID)

    if doctor_id:
        query = query.filter(models.Billing.doctor_id == doctor_id)
    if from_date:
        query = query.filter(models.Billing.created_at >= datetime.strptime(from_date, "%Y-%m-%d"))
    if to_date:
        query = query.filter(models.Billing.created_at <= datetime.strptime(to_date, "%Y-%m-%d"))

    query = query.group_by(models.Billing.doctor_id, models.Doctor.name)
    results = query.all()
    return [{"doctor_id": r[0], "doctor_name": r[1], "total_revenue": r[2] or 0.0} for r in results]

@router.get("/revenue/daily", response_model=List[schemas.RevenueDailyReport])
def get_daily_revenue(
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    db: Session = Depends(database.get_db),
    _: models.User = Depends(services.require_admin)
):
    # Uses SQLite date() formatting
    date_label = func.date(models.Billing.created_at).label("day")
    query = db.query(
        date_label,
        func.sum(models.Billing.total_amount).label("total_revenue")
    ).filter(models.Billing.is_active == True, models.Billing.payment_status == models.PaymentStatusEnum.PAID)

    if from_date:
        query = query.filter(models.Billing.created_at >= datetime.strptime(from_date, "%Y-%m-%d"))
    if to_date:
        query = query.filter(models.Billing.created_at <= datetime.strptime(to_date, "%Y-%m-%d"))

    query = query.group_by(date_label).order_by(date_label.desc())
    results = query.all()
    return [{"date": str(r[0]), "total_revenue": r[1] or 0.0} for r in results]