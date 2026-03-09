import api from './axiosInstance';
import { getToken, logout, isTokenExpired, hasValidToken, getUserName, getUserRole } from './tokenUtils';
import { decodeJwtPayload, saveToken } from './tokenUtils';

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

export { saveToken };

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
