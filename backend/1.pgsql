SELECT 
    a.id,
    a.doctor_id,
    a.patient_id,
    a.appointment_time,
    a.status,
    d.first_name || ' ' || d.last_name AS doctor_name
FROM appointments a
JOIN doctors d ON a.doctor_id = d.id
WHERE a.patient_id = 1
  AND a.appointment_time = '2026-07-22 08:00:00';

SELECT 
    a.id,
    a.doctor_id,
    a.appointment_time,
    a.status,
    d.first_name || ' ' || d.last_name AS doctor_name
FROM appointments a
JOIN doctors d ON a.doctor_id = d.id
WHERE a.patient_id = 1
  AND a.appointment_time >= '2026-07-22 00:00:00'
  AND a.appointment_time < '2026-07-23 00:00:00'
ORDER BY a.appointment_time;

SELECT 
    a.id,
    a.patient_id,
    a.appointment_time,
    a.status,
    p.first_name || ' ' || p.last_name AS patient_name
FROM appointments a
LEFT JOIN patients p ON a.patient_id = p.id
WHERE a.doctor_id = 35
  AND a.appointment_time = '2026-07-22 08:00:00';

  SELECT 
    a.id,
    a.patient_id,
    a.appointment_time,
    a.status,
    p.first_name || ' ' || p.last_name AS patient_name
FROM appointments a
LEFT JOIN patients p ON a.patient_id = p.id
WHERE a.doctor_id = 35
  AND a.appointment_time >= '2026-07-22 00:00:00'
  AND a.appointment_time < '2026-07-23 00:00:00'
ORDER BY a.appointment_time;

SELECT 
    a.id,
    a.doctor_id,
    a.appointment_time,
    a.status,
    d.first_name || ' ' || d.last_name AS doctor_name
FROM appointments a
JOIN doctors d ON a.doctor_id = d.id
WHERE a.patient_id = 1
  AND a.appointment_time >= NOW()
ORDER BY a.appointment_time;

-- Check working hours for Dr. Sarah Thompson on Wednesday (day_of_week = 3)
SELECT * FROM doctor_availability WHERE doctor_id = 35 AND day_of_week = 3;

-- Check if any appointment exists at exactly 8 AM on 22 July for this doctor
SELECT COUNT(*) FROM appointments 
WHERE doctor_id = 35 
  AND appointment_time = '2026-07-22 08:00:00';

SELECT * FROM appointments 
WHERE appointment_time = '2026-07-22 08:00:00';

SELECT 
    a.id,
    a.doctor_id,
    a.appointment_time,
    EXTRACT(HOUR FROM a.appointment_time) AS hour,
    d.first_name || ' ' || d.last_name AS doctor_name
FROM appointments a
JOIN doctors d ON a.doctor_id = d.id
WHERE a.patient_id = 1
  AND DATE(a.appointment_time) = '2026-07-22'
ORDER BY a.appointment_time;