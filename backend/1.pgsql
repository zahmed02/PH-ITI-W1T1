-- 2_role_based_users.sql
--
-- Adds role-based access control to the `users` table: a role ('admin',
-- 'doctor', 'patient') and optional links to the doctors/patients tables
-- so a login resolves to "which doctor/patient am I".
--
-- RUN THIS ONCE, MANUALLY, AGAINST YOUR DATABASE (e.g. via psql or
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

-- A given doctor/patient record can only be linked to ONE login account.
-- (A UNIQUE constraint in Postgres allows multiple NULLs through, so this
-- doesn't affect admin rows or any not-yet-linked rows.)
ALTER TABLE users
    ADD CONSTRAINT users_doctor_id_unique UNIQUE (doctor_id);

ALTER TABLE users
    ADD CONSTRAINT users_patient_id_unique UNIQUE (patient_id);

COMMIT;

-- NOTE: There is deliberately NO constraint enforcing "role='patient'
-- implies patient_id IS NOT NULL" (or the doctor equivalent) at the
-- database level. Adding one here would immediately reject this
-- migration if you already have test accounts registered from before
-- this change (they'd have role='patient' but no linked patient_id yet).
-- That invariant is enforced in application code (backend/auth.py)
-- for every NEW account going forward instead.

-- ---------------------------------------------------------------------
-- OPTIONAL: check for pre-migration accounts that now need attention.
-- Any row returned here was registered under the old flow and has no
-- linked patient record, so "my appointments" etc. won't work for them
-- until either you link them manually or they re-register.
-- ---------------------------------------------------------------------
-- SELECT id, username, role, doctor_id, patient_id FROM users WHERE role = 'patient' AND patient_id IS NULL;