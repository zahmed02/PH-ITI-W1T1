-- pgAdmin) BEFORE restarting the backend with the updated models.py.
-- SQLAlchemy's Base.metadata.create_all() only creates tables that don't
-- exist yet - it does NOT add new columns to a table that's already
-- there - so this migration will not run itself.

BEGIN;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS role VARCHAR(10) NOT NULL DEFAULT 'patient';

ALTER TABLE users
    ADD CONSTRAINT users_role_check CHECK (role IN ('admin', 'doctor', 'patient'));

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS doctor_id INTEGER REFERENCES doctors(id) ON DELETE SET NULL;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS patient_id INTEGER REFERENCES patients(id) ON DELETE SET NULL;

ALTER TABLE users
    ADD CONSTRAINT users_doctor_id_unique UNIQUE (doctor_id);

ALTER TABLE users
    ADD CONSTRAINT users_patient_id_unique UNIQUE (patient_id);

COMMIT;

SELECT id, username, role, doctor_id, patient_id FROM users WHERE role = 'patient' AND patient_id IS NULL;