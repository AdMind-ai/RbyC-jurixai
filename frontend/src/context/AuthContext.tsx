// src/context/AuthContext.tsx
import { createContext, useState, useEffect } from "react";
import { login as loginService, logout as logoutService } from "../api/auth";
import { useNavigate } from "react-router-dom";

interface User {
  name: string;
}

interface AuthContextType {
  token: string | null;
  user: User | null;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [token, setToken] = useState<string | null>(localStorage.getItem("access"));
  const [user, setUser] = useState<User | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const storedUser = localStorage.getItem("user");
    if (storedUser) {
      setUser(JSON.parse(storedUser));
    }
  }, []);

  // Função logout centralizada
  const logout = () => {
    logoutService();
    setToken(null);
    setUser(null);
    localStorage.removeItem("access");
    localStorage.removeItem("refresh");
    localStorage.removeItem("user");
    navigate("/login"); 
  };

  const login = async (username: string, password: string): Promise<boolean> => {
    try {
      const data = await loginService(username, password);
      if (data?.access) {
        setToken(data.access);
        localStorage.setItem("access", data.access);
        localStorage.setItem("refresh", data.refresh);
        const userData: User = { name: username };
        setUser(userData);
        localStorage.setItem("user", JSON.stringify(userData));
        return true; 
      } else {
        return false; 
      }
    } catch (error) {
      console.log("error: ",error);
      return false; 
    }
  };

  // Verifica se há tokens presentes em cada navegação dentro do componente AuthProvider
  useEffect(() => {
    const handleCheckTokens = () => {
      const currentAccess = localStorage.getItem("access");
      const currentRefresh = localStorage.getItem("refresh");

      if (!currentAccess || !currentRefresh) {
        console.warn("Nenhum token encontrado, fazendo logout automático.");
        logout(); // Logout automático centralizado do context
      }
    };

    // Verificação inicial imediata no carregamento
    handleCheckTokens();

    // Adiciona listeners para detectar eventos de clique ou interação no app
    window.addEventListener('click', handleCheckTokens);
    window.addEventListener('focus', handleCheckTokens);

    return () => {
      // Limpa listeners quando componente desmonta
      window.removeEventListener('click', handleCheckTokens);
      window.removeEventListener('focus', handleCheckTokens);      
    };
  }, [navigate]);

  return (
    <AuthContext.Provider value={{ token, user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};