import React from 'react';
import Sidebar from './components/Sidebar';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import AppRoutes from './routes';

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <div className="flex h-screen bg-[#f8fafc] overflow-hidden">
          <Sidebar />
          <div className="flex-1 flex flex-col ml-64 h-screen">
            {/* Main Content Area - Full Height, No Header */}
            <main className="flex-1 overflow-hidden relative w-full h-full">
              <AppRoutes />
            </main>
          </div>
        </div>
      </AuthProvider>
    </BrowserRouter>
  );
};

export default App;