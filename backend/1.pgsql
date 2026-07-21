SELECT 
    a.id,
    a.doctor_id,
    a.appointment_time,
    a.status,
    d.first_name || ' ' || d.last_name AS doctor_name,
    p.first_name || ' ' || p.last_name AS patient_name
FROM appointments a
JOIN doctors d ON a.doctor_id = d.id
JOIN patients p ON a.patient_id = p.id
WHERE a.id = 42;