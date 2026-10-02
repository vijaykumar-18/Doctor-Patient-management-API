from datetime import datetime
from typing import Optional, List, Generic, TypeVar
from pydantic import BaseModel, EmailStr, Field, field_validator
import re
from models import RoleEnum, AppointmentStatusEnum, PaymentStatusEnum, PaymentModeEnum

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    total: int
    page: int
    limit: int
    items: List[T]

# User & Auth
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    role: RoleEnum = RoleEnum.DOCTOR

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    role: RoleEnum
    is_active: bool

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

# Doctor Schemas
class DoctorBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    specialization: str = Field(..., min_length=2, max_length=100)

class DoctorCreate(DoctorBase):
    pass

class DoctorUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    specialization: Optional[str] = Field(None, min_length=2, max_length=100)
    is_active: Optional[bool] = None

class DoctorResponse(DoctorBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Patient Schemas
class PatientBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    age: int = Field(..., gt=0, le=125)
    phone: str

    @field_validator("phone")
    def validate_phone(cls, v):
        if not re.match(r"^\d{10}$", v):
            raise ValueError("Phone number must contain exactly 10 digits")
        return v

class PatientCreate(PatientBase):
    doctor_id: Optional[int] = None

class PatientUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = Field(None, gt=0, le=125)
    phone: Optional[str] = None
    doctor_id: Optional[int] = None
    is_active: Optional[bool] = None

    @field_validator("phone")
    def validate_phone_opt(cls, v):
        if v is not None and not re.match(r"^\d{10}$", v):
            raise ValueError("Phone number must contain exactly 10 digits")
        return v

class PatientResponse(PatientBase):
    id: int
    doctor_id: Optional[int]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Appointment Schemas
class AppointmentCreate(BaseModel):
    doctor_id: int
    patient_id: int
    appointment_date: datetime

class AppointmentUpdate(BaseModel):
    appointment_date: Optional[datetime] = None
    status: Optional[AppointmentStatusEnum] = None

class AppointmentResponse(BaseModel):
    id: int
    doctor_id: int
    patient_id: int
    appointment_date: datetime
    status: AppointmentStatusEnum
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Billing Schemas
class BillingCreate(BaseModel):
    patient_id: int
    doctor_id: int
    appointment_id: Optional[int] = None
    consultation_fee: float = Field(..., ge=0)
    additional_charges: float = Field(default=0.0, ge=0)
    payment_mode: PaymentModeEnum = PaymentModeEnum.CASH

class BillingUpdate(BaseModel):
    consultation_fee: Optional[float] = Field(None, ge=0)
    additional_charges: Optional[float] = Field(None, ge=0)
    payment_status: Optional[PaymentStatusEnum] = None
    payment_mode: Optional[PaymentModeEnum] = None

class BillingResponse(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    appointment_id: Optional[int]
    consultation_fee: float
    additional_charges: float
    total_amount: float
    payment_status: PaymentStatusEnum
    payment_mode: PaymentModeEnum
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Reports
class RevenueDoctorReport(BaseModel):
    doctor_id: int
    doctor_name: str
    total_revenue: float

class RevenueDailyReport(BaseModel):
    date: str
    total_revenue: float