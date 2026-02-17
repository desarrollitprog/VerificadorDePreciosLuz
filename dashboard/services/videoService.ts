import api from '../services/axiosInstance';

export async function getVideos() {
  const response = await api.get('/banners');
  // El backend retorna { success, message, banners: [ { ...metadatos... } ] }
  if (response.data && response.data.success) {
    return response.data.banners.map((item) => ({
      id: item.IdPublicidad,
      filename: item.Url ? item.Url.split('/').pop() : '',
      url: item.Url,
      thumbnail: item.Tipo === 'image' ? item.Url : '',
      tipo: item.Tipo,
      titulo: item.Titulo,
      size: '', // Si el backend lo provee, agregarlo
      date: item.UpdatedAt || '',
      duration: item.DuracionSeg || '',
      prioridad: item.Prioridad,
    }));
  }
  return [];
}

export async function uploadMedia(file) {
  const formData = new FormData();
  formData.append('file', file);
  // Puedes agregar otros campos si tu backend los requiere
  const response = await api.post('/banners/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
}


export async function deleteVideo(videoId) {
  const response = await api.delete(`/banners/${videoId}`);
  return response.data;
}
