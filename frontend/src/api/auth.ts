// src/api/auth.ts
import { api } from "./api";

interface LoginResponse {
  access: string;
  refresh: string;
}

export const login = async (username: string, password: string): Promise<LoginResponse> => {
  const response = await api.post("/auth/login/", { username, password });

  // Salve tokens no localStorage para uso do Interceptor
  localStorage.setItem("access", response.data.access);
  localStorage.setItem("refresh", response.data.refresh);

  return response.data;
};

export const fetchUserData = async () => {
  const response = await api.get("/auth/me/");
  return response.data;
};

export const logout = () => {
  localStorage.removeItem("access");
  localStorage.removeItem("refresh");
};