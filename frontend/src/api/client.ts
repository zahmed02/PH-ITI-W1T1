import axios from 'axios';
import { getStoredAuth, clearStoredAuth } from '../auth/authStorage';

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
});

// Attach the bearer token (if any) to every outgoing request.
api.interceptors.request.use((config) => {
  const auth = getStoredAuth();
  if (auth?.token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${auth.token}`;
  }
  return config;
});

// If the backend ever rejects a token (expired, or revoked via logout on
// another tab/device), clear it locally so the UI reflects "logged out"
// instead of silently failing requests forever.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      clearStoredAuth();
    }
    return Promise.reject(error);
  }
);

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

export default api;
