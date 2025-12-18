// src/context/AuthContext.tsx
import { createContext, useState, useEffect } from "react";
import { login as loginService, logout as logoutService, fetchUserData } from "../api/auth";
import { useNavigate, useLocation } from "react-router-dom";
import { toast } from "react-toastify";

interface User {
  email: string;
  username: string;
  first_name?: string;
  last_name?: string;
  is_admin: boolean;
}

interface AuthContextType {
  token: string | null;
  user: User | null;
  login: (email: string, password: string) => Promise<User | null>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const storedToken = localStorage.getItem("access");
  const storedUser = localStorage.getItem("user");

  const [token, setToken] = useState<string | null>(storedToken);
  const [user, setUser] = useState<User | null>(storedUser ? JSON.parse(storedUser) as User : null);
  const navigate = useNavigate();
  const location = useLocation();

  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    setInitialized(true);
  }, []);

  // useEffect(() => {
  //   const storedUser = localStorage.getItem("user");
  //   if (storedUser) {
  //     setUser(JSON.parse(storedUser));
  //   }
  // }, []);

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

  const login = async (email: string, password: string): Promise<User | null> => {
    try {
      const data = await loginService(email, password);

      if (data?.access) {
        setToken(data.access);
        localStorage.setItem("access", data.access);
        localStorage.setItem("refresh", data.refresh);

        const userData = await fetchUserData();

        const formattedUser: User = {
          email: userData.email,
          username: userData.username,
          first_name: userData.first_name,
          last_name: userData.last_name,
          is_admin: !!userData.is_company_admin,
        };

        setUser(formattedUser);
        localStorage.setItem("user", JSON.stringify(formattedUser));

        return formattedUser; 
      } else {
        return null; 
      }
    } catch (error) {
      console.log("error: ",error);
      return null; 
    }
  };

  useEffect(() => {
    if (!initialized) return;

    const PUBLIC_PATHS = ["/login"];
    const isPublicPath = PUBLIC_PATHS.includes(location.pathname);

    if (!isPublicPath && !token) {
      toast.warning("effettuare l'accesso");
      logout();
    }
  }, [initialized, location.pathname, token]);

  return (
    <AuthContext.Provider value={{ token, user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};