import React, { useContext } from 'react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider, AuthContext } from './context/AuthContext';
import Sidebar from './components/newLayout/Sidebar';
import AppRoutes from './routes';
const AppContent: React.FC = () => {
  const { token } = useContext(AuthContext) || {};
  return (
    <div className="flex h-screen bg-[#f8fafc] overflow-hidden">
      {token && <Sidebar />}
      <div className={token ? "flex-1 flex flex-col ml-64 h-screen" : "flex-1 flex flex-col h-screen"}>
        {/* Main Content Area - Full Height, No Header */}
        <main className="flex-1 overflow-hidden relative w-full h-full">
          <AppRoutes />
        </main>
      </div>
    </div>
  );
};

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </BrowserRouter>
  );
};

export default App;