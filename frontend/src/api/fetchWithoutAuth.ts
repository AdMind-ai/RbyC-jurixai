type FetchOptions = {
  method?: string;
  headers?: Record<string, string>;
  body?: BodyInit | null;
};

const isDevelopment = import.meta.env.MODE === 'development';
const baseURL = isDevelopment 
    ? import.meta.env.VITE_API_BASE_URL_LOCAL 
    : import.meta.env.VITE_API_BASE_URL_PROD;

export const fetchWithoutAuth = async (endpoint: string, options: FetchOptions = {}) => {
  // Caso precise, defina content-type para JSON exceto se for FormData
  const isJsonRequest = !(options.body instanceof FormData);
  const headers = {
    ...(isJsonRequest && { 'Content-Type': 'application/json' }),
    ...options.headers,
  };

  return fetch(`${baseURL}${endpoint}`, { ...options, headers });
};