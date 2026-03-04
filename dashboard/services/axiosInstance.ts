import axios from 'axios';

import { getToken, logout } from './authService';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
});

api.interceptors.request.use((config) => {
  if (config.url?.includes('/status-detalle')) {
    console.info('[API] Request', config.method?.toUpperCase(), `${config.baseURL ?? ''}${config.url}`);
  }
  return config;
});

// Interceptor para agregar el token JWT si existe
api.interceptors.request.use(
  (config) => {
    const token = getToken();
    if (token) {
      if (config.headers) {
        config.headers['Authorization'] = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => {
    if (response.config.url?.includes('/status-detalle')) {
      console.info('[API] Response', response.status, response.config.url);
    }
    return response;
  },
  (error) => {
    const url = error?.config?.url as string | undefined;
    const status = error?.response?.status;

    if (status === 401) {
      logout();
      if (typeof window !== 'undefined' && window.location.pathname !== '/') {
        window.location.reload();
      }
    }

    if (url?.includes('/status-detalle')) {
      const detail = error?.response?.data;
      console.error('[API] Error status-detalle', { status, url, detail });
    }
    return Promise.reject(error);
  }
);

export default api;
