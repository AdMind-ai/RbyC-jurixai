// Used to make authenticated requests to the API when axios cant be used
// Example: streaming responses from the backend

type FetchOptions = {
  method?: string;
  headers?: Record<string, string>;
  body?: BodyInit | null;
};

// Vite proxies /api → localhost:8000 in dev; same path works in production.
const baseURL = "/api";

export const fetchWithAuth = async (endpoint: string, options: FetchOptions = {}) => {
  const token = localStorage.getItem("access");
  const isJsonRequest = !(options.body instanceof FormData);
  const headers = {
    ...(isJsonRequest && { 'Content-Type': 'application/json' }),
    ...options.headers,
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  const res = await fetch(`${baseURL}${endpoint}`, { ...options, headers });

  if (res.status === 401) {
    const refreshSuccess = await refreshAccessToken();

    if (refreshSuccess) {
      const newAccess = localStorage.getItem("access");
      const retryHeaders = {
        ...headers,
        Authorization: `Bearer ${newAccess}`,
      };
      return fetch(`${baseURL}${endpoint}`, { ...options, headers: retryHeaders });
    } else {
      window.location.href = "/login"; 
    }
  }

  return res;
};


const refreshAccessToken = async (): Promise<boolean> => {
  const refresh = localStorage.getItem("refresh");
  if (!refresh) {
    console.warn("Refresh token não encontrado (fetchWithAuth).");
    return false;
  }

  try {
    const res = await fetch(`${baseURL}/auth/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh })
    });

    if (!res.ok) throw new Error('Refresh request failed');

    const resData = await res.json();
    const newAccess = resData.access;

    if (newAccess) {
      localStorage.setItem("access", newAccess);
      console.log("Token JWT renovado automaticamente via fetchWithAuth.");
      return true;
    }

    throw new Error('Refresh falhou');

  } catch (error) {
    console.warn("Falha no refresh token (fetchWithAuth):", error);
    window.dispatchEvent(new Event("logout"));
    return false;
  }
};

