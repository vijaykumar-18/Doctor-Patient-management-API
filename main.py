import time
from collections import defaultdict
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from database import engine, Base
import models
from routes import auth, doctors, patients, assignments, appointments, billing, reports

# Automatically build tables in SQLite
Base.metadata.create_all(bind=engine)

# Explicitly enforce the display order in Swagger UI
tags_metadata = [
    {"name": "Authentication", "description": "User registration, token issuance, and login."},
    {"name": "Doctors", "description": "Doctor profile lifecycle and scheduling lookups."},
    {"name": "Patients", "description": "Patient records and medical history lookups."},
    {"name": "Doctor-Patient Assignment", "description": "Allocate patients to primary physicians and inspect caseloads."},
    {"name": "Appointments", "description": "Manage appointment scheduling and collisions."},
    {"name": "Billing", "description": "Invoicing, payment processing, and transaction management."},
    {"name": "Reports", "description": "Revenue and business analytics."},
    {"name": "System Health", "description": "Server health status and root probes."}
]

app = FastAPI(
    title="Doctor-Patient Management System",
    version="1.0.0",
    description="End-to-End Enterprise API with RBAC, Appointment scheduling, and Transactions",
    openapi_tags=tags_metadata
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory Rate Limiting (60 requests/minute per IP)
RATE_LIMIT = 60
rate_limit_records = defaultdict(list)

@app.middleware("http")
async def rate_limiting_and_timing_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    current_time = time.time()

    rate_limit_records[client_ip] = [
        t for t in rate_limit_records[client_ip] if current_time - t < 60
    ]

    if len(rate_limit_records[client_ip]) >= RATE_LIMIT:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"success": False, "detail": "Rate limit exceeded. Max 60 requests per minute."}
        )
    rate_limit_records[client_ip].append(current_time)

    # Response time tracking header
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}s"
    return response

# Standardized Error Handling
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [{"loc": err["loc"], "msg": err["msg"], "type": err["type"]} for err in exc.errors()]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"success": False, "errors": errors}
    )

# Database Error Handling
@app.exception_handler(IntegrityError)
async def integrity_exception_handler(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"success": False, "detail": "Database constraint violation. Duplicate entry or foreign key conflict."}
    )

@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"success": False, "detail": "An internal database error occurred."}
    )

# Register routers in sequence
app.include_router(auth.router)
app.include_router(doctors.router)
app.include_router(patients.router)
app.include_router(assignments.router)
app.include_router(appointments.router)
app.include_router(billing.router)
app.include_router(reports.router)

@app.get("/", tags=["System Health"])
def root():
    return {
        "status": "Online",
        "documentation": "/docs",
        "system": "Doctor-Patient Management API"
    }