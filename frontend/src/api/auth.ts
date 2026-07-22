import api from './client';

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user_id: number;
  username: string;
}

export interface MeResponse {
  id: number;
  username: string;
  created_at: string;
}

export const loginRequest = (username: string, password: string) =>
  api.post<AuthResponse>('/auth/login', { username, password }).then(res => res.data);

export const registerRequest = (username: string, password: string) =>
  api.post<AuthResponse>('/auth/register', { username, password }).then(res => res.data);

export const logoutRequest = () =>
  api.post('/auth/logout').then(res => res.data);

export const fetchMe = () =>
  api.get<MeResponse>('/auth/me').then(res => res.data);
