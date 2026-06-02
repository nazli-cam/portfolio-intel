#!/usr/bin/env python3
"""
Create an admin user from the command line.

Usage (from backend/ directory):
    python scripts/create_admin.py admin@yourfirm.com "Your Name" secretpassword

The script is idempotent: if the email already exists it prints a message and exits 0.
"""
import sys
import os

# Allow running from the backend/ directory without installing the package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, create_tables
from app.models.user import User
from app.routers.auth import hash_password


def main():
    if len(sys.argv) != 4:
        print("Usage: python scripts/create_admin.py <email> <name> <password>")
        sys.exit(1)

    email, name, password = sys.argv[1], sys.argv[2], sys.argv[3]

    if len(password) < 8:
        print("Error: password must be at least 8 characters")
        sys.exit(1)

    create_tables()
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"User {email} already exists (role: {existing.role})")
            sys.exit(0)

        user = User(
            email=email,
            name=name,
            hashed_password=hash_password(password),
            role="admin",
        )
        db.add(user)
        db.commit()
        print(f"Admin user created: {email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
