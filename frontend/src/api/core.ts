import { api } from './api';

interface HelloResponse {
  message: string;
}

export const fetchHello = async (): Promise<HelloResponse> => {
  const response = await api.get('/hello/');
  return response.data;
};