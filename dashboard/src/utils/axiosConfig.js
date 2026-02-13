import axios from 'axios';

// Interceptor para agregar el token JWT a cada petición
axios.interceptors.request.use(config => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Usar la URL del .env (REACT_APP_API_URL)
const API_URL = process.env.REACT_APP_API_URL;

export const getBanners = async () => {
  try {
    const response = await axios.get(`${API_URL}/publicidad/banners`);
    return response.data;
  } catch (error) {
    console.error('Error al obtener banners:', error);
    return [];
  }
};

export const createBanner = async (banner) => {
  try {
    const response = await axios.post(`${API_URL}/publicidad/banners`, banner);
    return response.data;
  } catch (error) {
    console.error('Error al crear banner:', error);
    throw error;
  }
};

export default axios;
