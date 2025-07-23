// api.ts atualizado completamente
import axios from "axios";

const isDevelopment = import.meta.env.MODE === 'development';
const baseURL = isDevelopment ? 
    import.meta.env.VITE_API_BASE_URL_LOCAL : 
    import.meta.env.VITE_API_BASE_URL_PROD;


export const api = axios.create({
  baseURL,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshSuccess = await refreshAccessToken();

      if (refreshSuccess) {
        const newAccess = localStorage.getItem("access");
        originalRequest.headers.Authorization = `Bearer ${newAccess}`;
        return api(originalRequest);
      } else {
        window.dispatchEvent(new Event("logout"));
      }
    }

    return Promise.reject(error);
  }
);

const refreshAccessToken = async () => {
  const refresh = localStorage.getItem("refresh");
  if (!refresh) {
    console.warn("Refresh token não encontrado.");
    return false;  
  }

  try {
    const res = await axios.post(`${baseURL}/auth/refresh/`, { refresh });
    const newAccess = res.data.access;
    localStorage.setItem("access", newAccess);
    console.log("Token renovado automaticamente.");
    return true;
  } catch (error) {
    console.warn("Falha no refresh do token:", error);
    localStorage.removeItem("access");
    localStorage.removeItem("refresh");
    window.location.href = "/login"; 
    return false;
  }
};

