import api from './axiosInstance';

export interface LoginStartResponse {
  requires_2fa: boolean;
  message: string;
  temp_token: string;
  masked_email: string;
  expires_in: number;
}

export interface LoginVerifyResponse {
  access_token: string;
  token_type: string;
}

export interface ResendTwoFactorResponse {
  success: boolean;
  message: string;
  masked_email: string;
  expires_in: number;
}

export async function loginStart(username: string, correo: string, contrasena: string): Promise<LoginStartResponse> {
  try {
    const response = await api.post('/auth/login', {
      username,
      correo,
      contrasena,
    });
    return response.data;
  } catch (error: any) {
    if (error.response && error.response.data && error.response.data.detail) {
      throw new Error(error.response.data.detail);
    }
    throw new Error('Error de autenticación');
  }
}

export async function verifyTwoFactor(tempToken: string, code: string): Promise<LoginVerifyResponse> {
  try {
    const response = await api.post('/auth/verify-2fa', {
      temp_token: tempToken,
      code,
    });
    return response.data;
  } catch (error: any) {
    if (error.response && error.response.data && error.response.data.detail) {
      throw new Error(error.response.data.detail);
    }
    throw new Error('No se pudo verificar el código');
  }
}

export async function resendTwoFactor(tempToken: string): Promise<ResendTwoFactorResponse> {
  try {
    const response = await api.post('/auth/resend-2fa', {
      temp_token: tempToken,
    });
    return response.data;
  } catch (error: any) {
    if (error.response && error.response.data && error.response.data.detail) {
      throw new Error(error.response.data.detail);
    }
    throw new Error('No se pudo reenviar el código');
  }
}

export async function login(username: string, correo: string, contrasena: string): Promise<LoginVerifyResponse> {
  const challenge = await loginStart(username, correo, contrasena);
  if (challenge.requires_2fa) {
    throw new Error('Se requiere verificación de dos factores');
  }
  return challenge as unknown as LoginVerifyResponse;
}

export function saveToken(token: string) {
  localStorage.setItem('token', token);
}

export function getToken(): string | null {
  return localStorage.getItem('token');
}

function decodeJwtPayload(token: string): Record<string, any> | null {
  try {
    const payloadBase64 = token.split('.')[1];
    if (!payloadBase64) return null;
    const base64 = payloadBase64.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}

export function isTokenExpired(token: string): boolean {
  const payload = decodeJwtPayload(token);
  if (!payload || typeof payload.exp !== 'number') {
    return true;
  }
  const nowInSeconds = Math.floor(Date.now() / 1000);
  return nowInSeconds >= payload.exp;
}

export function hasValidToken(): boolean {
  const token = getToken();
  if (!token) return false;
  if (isTokenExpired(token)) {
    logout();
    return false;
  }
  return true;
}

export function logout() {
  localStorage.removeItem('token');
}
export function getUserName(): string | null {
  const token = getToken();
  if (!token) return null;
  const payload = decodeJwtPayload(token);
  if (!payload) {
    return null;
  }
  return payload.nombre || payload.sub || null;
}
export function getUserRole(): 'ADMIN' | 'CLIENTE' | null {
  const token = getToken();
  if (!token) return null;
  const payload = decodeJwtPayload(token);
  if (!payload) return null;
  if (typeof payload.rol === 'string' && (payload.rol === 'ADMIN' || payload.rol === 'CLIENTE')) {
    return payload.rol as 'ADMIN' | 'CLIENTE';
  }
  return null;
}

export function getTokenExpiryMs(): number | null {
  const token = getToken();
  if (!token) return null;
  const payload = decodeJwtPayload(token);
  if (!payload || typeof payload.exp !== 'number') {
    return null;
  }
  return payload.exp * 1000;
}
