// src/components/PrivateRoute.tsx
import React, { useContext } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import { GlobalProvider } from '../context/GlobalContext';

const PrivateRoute: React.FC = () => {
  const auth = useContext(AuthContext);

  // return auth?.token ? <Outlet /> : <Navigate to="/login" replace />;

  if (!auth?.token) {
    return <Navigate to="/login" replace />;
  }
  return (
    <GlobalProvider>
      <Outlet />
    </GlobalProvider>
  );

};

export default PrivateRoute;