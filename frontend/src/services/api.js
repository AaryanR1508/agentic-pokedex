import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
});

export const sendMultimodalQuery = async ({ text, imageFile, audioBlob }) => {
  const formData = new FormData();

  if (text) formData.append('text', text);
  if (imageFile) formData.append('image', imageFile);
  if (audioBlob) formData.append('audio', audioBlob, 'recording.ogg');

  const response = await api.post('/api/v1/query', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });

  return response.data;
};

export default api;