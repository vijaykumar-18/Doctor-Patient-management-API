# Doctor Patient Management System (DPMS)

Production-ready backend API built with FastAPI, SQLAlchemy, SQLite, and JWT.

## Features
- **Authentication & RBAC**: Admin and Doctor roles using OAuth2 bearer tokens.
- **Doctor & Patient CRUD**: Soft-deletes, 10-digit phone regex validation, and relationship binding.
- **Appointments**: Real-time slot conflict prevention.
- **Billing & Revenue**: Multi-item pricing calculations, status checks, and revenue aggregation by doctor and date.

## Execution
```bash
# Seed initial administrator
python admin.py

# Launch development server
uvicorn main:app --reload