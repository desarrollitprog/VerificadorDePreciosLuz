import api from './axiosInstance';

export async function login(username: string, password: string) {
  try {
    const response = await api.post('/auth/login', new URLSearchParams({
      username,
      password,
    }), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    });
    return response.data;
  } catch (error: any) {
    if (error.response && error.response.data && error.response.data.detail) {
      throw new Error(error.response.data.detail);
    }
    throw new Error('Error de autenticación');
  }
}

export function saveToken(token: string) {
  localStorage.setItem('token', token);
}

export function getToken(): string | null {
  return localStorage.getItem('token');
}

export function logout() {
  localStorage.removeItem('token');
}
export function getUserName(): string | null {
  const token = getToken();
  if (!token) return null;
  try {
    const payloadBase64 = token.split('.')[1];
    if (!payloadBase64) return null;
    const base64 = payloadBase64.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    const payload = JSON.parse(jsonPayload);
    return payload.sub || null;
  } catch {
    return null;
  }
}
export function getUserRole(): 'ADMIN' | 'CLIENTE' | null {
  const token = getToken();
  if (!token) return null;
  try {
    // JWT formato: header.payload.signature
    const payloadBase64 = token.split('.')[1];
    if (!payloadBase64) return null;
    // Corrige padding base64
    const base64 = payloadBase64.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    const payload = JSON.parse(jsonPayload);
    if (typeof payload.rol === 'string' && (payload.rol === 'ADMIN' || payload.rol === 'CLIENTE')) {
      return payload.rol as 'ADMIN' | 'CLIENTE';
    }
    return null;
  } catch (e) {
    return null;
  }
}
