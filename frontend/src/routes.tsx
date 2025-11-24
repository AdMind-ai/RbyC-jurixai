// routes.tsx
import { Navigate, Route, Routes } from 'react-router-dom'
import Home from './components/newLayout/Home'
import Login from './pages/Login'

import PrivateRoute from './components/PrivateRoute'
import { useState } from 'react'
import { Company, Deadline } from './types/types'
import { MOCK_COMPANIES, MOCK_DEADLINES } from './constants'
import UserAccess from './components/newLayout/UserAccess'
import Dashboard from './components/newLayout/Dashboard'
import CompanyList from './components/newLayout/CompanyList'
import DocumentGenerator from './components/newLayout/DocumentGenerator'
import AIAssistant from './components/newLayout/AIAssistant'
import SearchView from './components/newLayout/SearchView'
import ComplianceView from './components/newLayout/ComplianceView'
import Chat from './pages/Chat'

const AppRoutes = () => {

  // Global State for the Corporate Secretary Module
  const [companies, setCompanies] = useState<Company[]>(MOCK_COMPANIES);
  const [deadlines, setDeadlines] = useState<Deadline[]>(MOCK_DEADLINES);

  const handleAddCompany = (companyData: Company) => {
    setCompanies(prev => {
      const exists = prev.find(c => c.id === companyData.id);
      if (exists) {
        return prev.map(c => c.id === companyData.id ? companyData : c);
      }
      return [...prev, companyData];
    });
  };

  const handleAddDeadline = (newDeadline: Deadline) => {
    setDeadlines(prev => [...prev, newDeadline]);
  };

    return (
      <Routes>
        {/* Public Route (login) */}
        <Route path="/login" element={<Login />} />

        {/* Rotas privadas */}
        <Route element={<PrivateRoute />}>
          <Route path="/" element={<Home />} />

          {/* Tools Routes */}
          <Route path="/search" element={<SearchView />} />
          <Route path="/compliance" element={<ComplianceView />} />
          <Route path="/chat-general" element={<Chat />} />

          {/* Access Routes */}
          <Route path="/accessi" element={<UserAccess />} />

          {/* Segreteria Societaria Sub-routes */}
          <Route path="/segreteria">
            <Route index element={<Navigate to="/segreteria/dashboard" replace />} />
            <Route path="dashboard" element={
              <Dashboard
                companies={companies}
                deadlines={deadlines}
                onAddDeadline={handleAddDeadline}
              />
            } />
            <Route path="companies" element={
              <CompanyList
                companies={companies}
                onAddCompany={handleAddCompany}
                onAddDeadline={handleAddDeadline}
              />
            } />
            <Route path="documents" element={<DocumentGenerator companies={companies} />} />
            <Route path="assistant" element={<AIAssistant companies={companies} deadlines={deadlines} />} />
          </Route>

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    )
}

export default AppRoutes
