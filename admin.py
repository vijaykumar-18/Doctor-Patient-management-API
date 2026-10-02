"""
Interactive CLI script to create an administrator account.
Run from terminal: python admin.py
"""
import getpass
import re
from database import SessionLocal
import models
import security

EMAIL_REGEX = r"^[\w\.-]+@[\w\.-]+\.\w+$"

def prompt_admin_creation():
    db = SessionLocal()
    print("=" * 45)
    print("      DPMS Admin Account Setup")
    print("=" * 45)

    # 1. Admin Name
    while True:
        name = input("Enter Admin Name: ").strip()
        if len(name) >= 2:
            break
        print("Name must be at least 2 characters long.")

    # 2. Admin Email
    while True:
        email = input("Enter Admin Email: ").strip().lower()
        if not re.match(EMAIL_REGEX, email):
            print("Invalid email format. Try again.")
            continue
        existing = db.query(models.User).filter(models.User.email == email).first()
        if existing:
            print(f"A user with email '{email}' already exists. Choose a different email.")
            continue
        break

    # 3. Password & Confirm Password
    while True:
        password = getpass.getpass("Enter Password: ")
        if len(password) < 6:
            print("Password must be at least 6 characters long.")
            continue

        confirm_password = getpass.getpass("Confirm Password: ")
        if password != confirm_password:
            print("Passwords do not match. Try again.\n")
            continue
        break

    # 4. Save to Database
    hashed_password = security.get_password_hash(password)
    admin_user = models.User(
        email=email,
        hashed_password=hashed_password,
        role=models.RoleEnum.ADMIN,
        is_active=True
    )
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)

    print("\n" + "-" * 45)
    print(f"Admin account created successfully!")
    print(f"Name : {name}")
    print(f"Email: {email}")
    print(f"Role : {admin_user.role.value}")
    print("-" * 45)
    db.close()

if __name__ == "__main__":
    prompt_admin_creation()