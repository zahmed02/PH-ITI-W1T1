// frontend/src/api/auth.ts
import api from './client';

export type Role = 'admin' | 'doctor' | 'patient';

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user_id: number;
  username: string;
  role: Role;
  doctor_id: number | null;
  patient_id: number | null;
}

export interface MeResponse {
  id: number;
  username: string;
  role: Role;
  doctor_id: number | null;
  patient_id: number | null;
  created_at: string;
}

export interface RegisterPayload {
  username: string;
  password: string;
  first_name: string;
  last_name: string;
  email: string;
  phone?: string;
}

export const loginRequest = (username: string, password: string) =>
  api.post<AuthResponse>('/auth/login', { username, password }).then(res => res.data);

// Public registration always creates a "patient" account - it also needs
// enough info (name/email) to create the linked Patient record, since a
// logged-in patient should resolve to real patient data automatically.
export const registerRequest = (payload: RegisterPayload) =>
  api.post<AuthResponse>('/auth/register', payload).then(res => res.data);

export const logoutRequest = () =>
  api.post('/auth/logout').then(res => res.data);

export const fetchMe = () =>
  api.get<MeResponse>('/auth/me').then(res => res.data);

// -------------------- admin-only account management --------------------

export interface CreateDoctorPayload {
  username: string;
  password: string;
  first_name: string;
  last_name: string;
  specialty: string;
  years_of_experience: number;
  bio?: string;
  availability?: { day_of_week: number; start_time: string; end_time: string }[];
}

export interface CreateAdminPayload {
  username: string;
  password: string;
}

export interface CreatePatientPayload {
  username: string;
  password: string;
  first_name: string;
  last_name: string;
  email: string;
  phone?: string;
}

export interface AdminUserRow {
  id: number;
  username: string;
  role: Role;
  doctor_id: number | null;
  patient_id: number | null;
  created_at: string;
}

export const adminListUsers = () =>
  api.get<AdminUserRow[]>('/auth/admin/users').then(res => res.data);

export const adminCreateDoctor = (payload: CreateDoctorPayload) =>
  api.post<AdminUserRow>('/auth/admin/doctors', payload).then(res => res.data);

export const adminCreateAdmin = (payload: CreateAdminPayload) =>
  api.post<AdminUserRow>('/auth/admin/admins', payload).then(res => res.data);

export const adminCreatePatient = (payload: CreatePatientPayload) =>
  api.post<AdminUserRow>('/auth/admin/patients', payload).then(res => res.data);