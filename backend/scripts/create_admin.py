"""
One-time CLI script to create the very first admin account.

Every other admin, doctor, and patient account is created either through
self-registration (patients, via POST /api/auth/register) or by an
existing admin (doctors and additional admins, via POST
/api/auth/admin/doctors and /api/auth/admin/admins). But the very FIRST
admin can't be created either way - there's no admin yet to authorize it.
This script creates that first one directly against the database.

Run this ONCE, from the project root (the folder containing run.py),
AFTER running the 2_role_based_users.sql migration and before (or after)
starting the server:

    python -m backend.scripts.create_admin

Safe to leave in the repo and re-run by accident - it refuses to do
anything if an admin account already exists.
"""
import getpass
import sys

from backend.database import SessionLocal
from backend.models import User
from backend.auth import hash_password


def main():
    db = SessionLocal()
    try:
        existing_admin = db.query(User).filter(User.role == "admin").first()
        if existing_admin:
            print(f"An admin account already exists ('{existing_admin.username}'). Refusing to create another via this script.")
            print("To add more admins, log in as an admin and use POST /api/auth/admin/admins instead.")
            sys.exit(1)

        print("Creating the first admin account for Stellaris General Hospital.\n")

        username = input("Admin username: ").strip()
        if len(username) < 3:
            print("Username must be at least 3 characters.")
            sys.exit(1)
        if db.query(User).filter(User.username == username).first():
            print("That username is already taken.")
            sys.exit(1)

        password = getpass.getpass("Admin password (min 8 characters): ")
        if len(password) < 8:
            print("Password must be at least 8 characters.")
            sys.exit(1)
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Passwords do not match.")
            sys.exit(1)

        admin = User(username=username, hashed_password=hash_password(password), role="admin")
        db.add(admin)
        db.commit()

        print(f"\nAdmin account '{username}' created successfully. You can now log in at /login.")
    finally:
        db.close()


if __name__ == "__main__":
    main()