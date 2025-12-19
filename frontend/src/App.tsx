import React, { useContext, useState } from 'react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider, AuthContext } from './context/AuthContext';
import AppRoutes from './routes';
import Sidebar from './components/Sidebar';
const AppContent: React.FC = () => {
  const { token } = useContext(AuthContext) || {};
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  return (
    <div className="flex h-screen bg-[#f8fafc] overflow-hidden">
      {token && <Sidebar onCollapseChange={setSidebarCollapsed} />}
      <div className={token ? `flex-1 flex flex-col ${sidebarCollapsed ? 'ml-20' : 'ml-64'} h-screen` : "flex-1 flex flex-col h-screen"}>
        {/* Main Content Area - Full Height, No Header */}
        <main className="flex-1 overflow-y-auto relative w-full h-full">
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