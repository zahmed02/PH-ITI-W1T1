"""
One-time backfill script: creates a login account (User row) for every
existing Doctor and Patient record that doesn't already have one.

Your doctors/patients tables were seeded before role-based login existed,
so none of them have a linked User yet - only the admin and one stray
test account do. This script closes that gap.

USERNAME: first.last, lowercased (e.g. "emily.johnson"). If that's taken,
a numeric suffix is appended (e.g. "emily.johnson2").

PASSWORD: a fresh cryptographically random password PER ACCOUNT - never
hardcoded, never reused. Only the bcrypt hash is stored in the database.
The plaintext passwords are written ONCE to a CSV file so you can
distribute them, then that file should be deleted/secured - it is the
only place the plaintext ever exists.

Run from the project root, after the 2_role_based_users.sql migration
and after backend/scripts/create_admin.py:

    python -m backend.scripts.create_accounts_for_existing_records

Safe to re-run: it only creates accounts for doctors/patients that don't
already have one, and skips (with a message) anything already linked.
"""
import csv
import secrets
import string
import sys
from pathlib import Path

from backend.database import SessionLocal
from backend.models import Doctor, Patient, User
from backend.auth import hash_password

OUTPUT_CSV = Path(__file__).resolve().parent.parent.parent / "generated_credentials.csv"


def generate_password(length: int = 14) -> str:
    # Cryptographically secure, not just random.choice - this is a real
    # credential, not a placeholder.
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def unique_username(db, base: str) -> str:
    username = base
    suffix = 1
    while db.query(User).filter(User.username == username).first():
        suffix += 1
        username = f"{base}{suffix}"
    return username


def main():
    db = SessionLocal()
    generated_rows = []

    try:
        # ---- Doctors ----
        doctors_without_login = (
            db.query(Doctor)
            .filter(~Doctor.id.in_(db.query(User.doctor_id).filter(User.doctor_id.isnot(None))))
            .all()
        )
        print(f"Found {len(doctors_without_login)} doctor(s) without a login account.")

        for doctor in doctors_without_login:
            base_username = f"{doctor.first_name}.{doctor.last_name}".lower().replace(" ", "")
            username = unique_username(db, base_username)
            password = generate_password()

            user = User(
                username=username,
                hashed_password=hash_password(password),
                role="doctor",
                doctor_id=doctor.id,
            )
            db.add(user)
            db.flush()

            generated_rows.append({
                "role": "doctor",
                "name": f"Dr. {doctor.first_name} {doctor.last_name}",
                "specialty": doctor.specialty,
                "email": "",
                "username": username,
                "password": password,
            })
            print(f"  created login for Dr. {doctor.first_name} {doctor.last_name} -> username: {username}")

        # ---- Patients ----
        patients_without_login = (
            db.query(Patient)
            .filter(~Patient.id.in_(db.query(User.patient_id).filter(User.patient_id.isnot(None))))
            .all()
        )
        print(f"\nFound {len(patients_without_login)} patient(s) without a login account.")

        for patient in patients_without_login:
            base_username = f"{patient.first_name}.{patient.last_name}".lower().replace(" ", "")
            username = unique_username(db, base_username)
            password = generate_password()

            user = User(
                username=username,
                hashed_password=hash_password(password),
                role="patient",
                patient_id=patient.id,
            )
            db.add(user)
            db.flush()

            generated_rows.append({
                "role": "patient",
                "name": f"{patient.first_name} {patient.last_name}",
                "specialty": "",
                "email": patient.email,
                "username": username,
                "password": password,
            })
            print(f"  created login for {patient.first_name} {patient.last_name} -> username: {username}")

        if not generated_rows:
            print("\nNothing to do - every doctor and patient already has a login account.")
            db.rollback()
            return

        db.commit()

        with open(OUTPUT_CSV, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["role", "name", "specialty", "email", "username", "password"])
            writer.writeheader()
            writer.writerows(generated_rows)

        print(f"\n{len(generated_rows)} account(s) created.")
        print(f"Plaintext credentials written ONCE to: {OUTPUT_CSV}")
        print(
            "\nIMPORTANT: this file contains real plaintext passwords. Distribute "
            "each row to the corresponding doctor/patient securely, then DELETE "
            "this file. It is not regenerable - the database only ever stores "
            "the bcrypt hash, so if you lose this file before distributing it, "
            "use the password-reset flow (once built) instead of re-running this script."
        )

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())