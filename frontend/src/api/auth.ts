// src/api/auth.ts
import { api } from "./api";

interface LoginResponse {
  access: string;
  refresh: string;
}

export const login = async (email: string, password: string): Promise<LoginResponse> => {
  const response = await api.post("/auth/login/", { email, password });

  // Salve tokens no localStorage para uso do Interceptor
  localStorage.setItem("access", response.data.access);
  localStorage.setItem("refresh", response.data.refresh);

  return response.data;
};

export const fetchUserData = async () => {
  const response = await api.get("/auth/users/me/");
  console.log("User data fetched:", response.data);
  return response.data;
};

export const logout = () => {
  localStorage.removeItem("access");
  localStorage.removeItem("refresh");
};