import sys, os
sys.path.insert(0, 'D:\IT-Project-1')
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['JWT_SECRET_KEY'] = 'test-secret'

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import backend.database as database
database.engine = create_engine('sqlite:///:memory:', connect_args={"check_same_thread": False})
database.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=database.engine)

from backend.models import Base, Doctor, Patient, User
Base.metadata.create_all(bind=database.engine)

db = database.SessionLocal()

# Seed with data matching the real doctors.csv / patients.csv
doctors_data = [
    ("Emily","Johnson","Cardiology",15),("Michael","Chen","Neurology",22),
    ("Sarah","Patel","Pediatrics",10),("David","Martinez","Orthopedics",18),
    ("James","Wilson","Cardiology",20),("Lisa","Kim","Neurology",12),
    ("Robert","Brown","Pediatrics",8),("Maria","Garcia","Orthopedics",25),
    ("John","Smith","Dermatology",15),("David","Lee","Cardiology",7),
    ("Anna","Martinez","Neurology",18),("Thomas","Anderson","Pediatrics",5),
    ("Sarah","Thompson","Orthopedics",14),("Mark","Davis","Dermatology",9),
]
for fn, ln, spec, yrs in doctors_data:
    db.add(Doctor(first_name=fn, last_name=ln, specialty=spec, years_of_experience=yrs))

patients_data = [
    ("Alice","Brown","alice.b@email.com"),("Bob","White","bob.w@email.com"),
    ("Charlie","Green","charlie.g@email.com"),("Emma","Davis","emma.davis@email.com"),
    ("Daniel","Miller","daniel.miller@email.com"),("Olivia","Wilson","olivia.wilson@email.com"),
    ("Liam","Garcia","liam.garcia@email.com"),("Sophia","Brown","sophia.brown@email.com"),
    ("Ethan","Wilson","ethan.wilson@email.com"),("Ava","Martinez","ava.martinez@email.com"),
]
for fn, ln, em in patients_data:
    db.add(Patient(first_name=fn, last_name=ln, email=em))

db.commit()
db.close()

# monkeypatch OUTPUT_CSV so it doesn't write to real project path
import backend.scripts.create_accounts_for_existing_records as script
script.OUTPUT_CSV = __import__('pathlib').Path('D:/IT-Project-1/test_generated_credentials.csv')

script.main()

# Verify results
db2 = database.SessionLocal()
users = db2.query(User).all()
print(f"\nTotal users now: {len(users)}")
usernames = [u.username for u in users]
print("Duplicate usernames?", len(usernames) != len(set(usernames)))

# verify every doctor and patient got exactly one linked account
doctors = db2.query(Doctor).all()
patients = db2.query(Patient).all()
linked_doctor_ids = {u.doctor_id for u in users if u.doctor_id}
linked_patient_ids = {u.patient_id for u in users if u.patient_id}
print(f"Doctors linked: {len(linked_doctor_ids)}/{len(doctors)}")
print(f"Patients linked: {len(linked_patient_ids)}/{len(patients)}")

# check password hashes actually verify against the exported plaintext
import csv
from backend.auth import verify_password
with open('D:/IT-Project-1/test_generated_credentials.csv') as f:
    rows = list(csv.DictReader(f))
print(f"\nCSV rows exported: {len(rows)}")
all_verify = True
for row in rows:
    u = db2.query(User).filter(User.username == row['username']).first()
    if not verify_password(row['password'], u.hashed_password):
        all_verify = False
        print(f"MISMATCH for {row['username']}")
print("All exported passwords verify against stored hashes:", all_verify)

# re-run idempotency check
print("\n--- Re-running script (should create nothing new) ---")
script.main()
