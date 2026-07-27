// frontend/src/api/client.ts
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

// Patients (admin-only - the patient list is sensitive, unlike doctors)
export interface PatientRow {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  phone: string | null;
  created_at: string;
}

export const adminListPatients = (): Promise<PatientRow[]> =>
  api.get('/patients/').then(res => res.data);

// Appointments
export const getAppointments = () =>
  api.get('/appointments/').then(res => res.data);

export const getAppointmentsByPatient = (patientId: number) =>
  api.get(`/appointments/patient/${patientId}`).then(res => res.data);

export const getAppointmentsByDoctor = (doctorId: number) =>
  api.get(`/appointments/doctor/${doctorId}`).then(res => res.data);

// Direct booking (no AI) - validated server-side (working hours,
// double-booking), and automatically creates a doctor notification +
// patient confirmation email, same as the AI's booking path.
export interface BookAppointmentPayload {
  doctor_id: number;
  patient_id: number;
  date: string; // YYYY-MM-DD
  time: string; // HH:MM (24-hour)
}

export interface BookAppointmentResult {
  success: boolean;
  message: string;
  ambiguous?: boolean;
  appointment_id?: number;
  doctor_id?: number;
  doctor_name?: string;
  patient_id?: number;
  date?: string;
  time?: string;
  confirmation_email_sent?: boolean;
}

export const bookAppointment = (payload: BookAppointmentPayload): Promise<BookAppointmentResult> =>
  api.post('/appointments/book', payload).then(res => res.data);

// Chat (will be proxied to /api/chat)
export const sendChatMessage = (query: string, patientId?: number) =>
  api.post('/chat/', null, { params: { query, patient_id: patientId } }).then(res => res.data);

// Reviews
export const getReviewsByDoctor = (doctorId: number) =>
  api.get(`/reviews/doctor/${doctorId}`).then(res => res.data);

export interface CreateReviewPayload {
  doctor_id: number;
  patient_id: number;
  rating: number;
  comment?: string;
}

// Backend enforces: a patient may only review a doctor after an
// appointment time with them has actually passed. A 403 here means that
// rule was violated (or it isn't their own review) - surface the
// server's message rather than guessing.
export const createReview = (payload: CreateReviewPayload) =>
  api.post('/reviews/', payload).then(res => res.data);

// Get doctor availability (working hours)
export const getDoctorAvailability = (doctorId: number) =>
  api.get(`/doctors/${doctorId}/availability`).then(res => res.data);

// Privacy-safe booking view: available/booked per slot, WITHOUT patient
// identities. weekStart must be an ISO date string (YYYY-MM-DD).
export const getDoctorSchedulePreview = (doctorId: number, weekStart: string) =>
  api.get(`/doctors/${doctorId}/schedule-preview`, { params: { week_start: weekStart } }).then(res => res.data);

export const uploadDoctorImage = (doctorId: number, file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post(`/doctors/${doctorId}/image`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(res => res.data);
};

// Notifications (doctor-only inbox - see backend/booking.py, created
// automatically on every successful booking regardless of which path
// created it)
export interface NotificationRow {
  id: number;
  appointment_id: number | null;
  message: string;
  is_read: boolean;
  created_at: string;
}

export const getMyNotifications = (unreadOnly = false): Promise<NotificationRow[]> =>
  api.get('/notifications/me', { params: { unread_only: unreadOnly } }).then(res => res.data);

export const markNotificationRead = (notificationId: number) =>
  api.post(`/notifications/${notificationId}/read`).then(res => res.data);

export default api;