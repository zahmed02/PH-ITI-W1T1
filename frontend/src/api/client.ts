// frontend/src/api/client.ts
import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
});

// Doctors
export const getDoctors = (params?: { specialty?: string; min_experience?: number; min_rating?: number }) =>
  api.get('/doctors/search/', { params }).then(res => res.data);

export const getDoctor = (id: number) =>
  api.get(`/doctors/${id}`).then(res => res.data);

// Appointments
export const getAppointments = () =>
  api.get('/appointments/').then(res => res.data);

export const getAppointmentsByPatient = (patientId: number) =>
  api.get(`/appointments/patient/${patientId}`).then(res => res.data);

// Chat (will be proxied to /api/chat)
export const sendChatMessage = (query: string, patientId?: number) =>
  api.post('/chat/', null, { params: { query, patient_id: patientId } }).then(res => res.data);

// Reviews
export const getReviewsByDoctor = (doctorId: number) =>
  api.get(`/reviews/doctor/${doctorId}`).then(res => res.data);

// Get appointments by doctor
export const getAppointmentsByDoctor = (doctorId: number) =>
  api.get(`/appointments/doctor/${doctorId}`).then(res => res.data);

// Get doctor availability (working hours)
export const getDoctorAvailability = (doctorId: number) =>
  api.get(`/doctors/${doctorId}/availability`).then(res => res.data);

export const uploadDoctorImage = (doctorId: number, file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post(`/doctors/${doctorId}/image`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(res => res.data);
};