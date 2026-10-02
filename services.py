from fastapi import Depends, HTTPException, status
import models
import security

def get_current_active_user(
    current_user=Depends(security.get_current_user)
):
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )
    return current_user

def require_admin(
    current_user=Depends(get_current_active_user)
):
    if current_user.role != models.RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user

def require_doctor_or_admin(
    current_user=Depends(get_current_active_user)
):
    if current_user.role not in [models.RoleEnum.ADMIN, models.RoleEnum.DOCTOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to doctors and administrators"
        )
    return current_user

def verify_doctor_patient_access(current_user, doctor_id: int):
    if current_user.role == models.RoleEnum.DOCTOR:
        if not current_user.doctor or current_user.doctor.id != doctor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You can only view your own records"
            )