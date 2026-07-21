// routes.tsx
import { Navigate, Route, Routes } from 'react-router-dom'
import Home from './pages/Home'
import Login from './pages/Login'
import ResetPassword from './pages/ResetPassword'
import ForgotPassword from './pages/ForgotPassword'
import PrivateRoute from './components/PrivateRoute'
import Dashboard from './components/SegreteriaSocietaria/Dashboard'
import CompanyList from './components/SegreteriaSocietaria/CompanyList'
import DocumentGenerator from './components/SegreteriaSocietaria/DocumentGenerator'
import Chat from './pages/Chat'
import DocSearch from './pages/DocSearch'
import TeamManagement from './pages/TeamManagement'
import CheckComplianceChat from './pages/CheckComplianceChat'
import CheckComplianceDocuments from './pages/CheckComplianceDocuments'
import AIAssistant from './components/SegreteriaSocietaria/AIAssistant'
import { DraftDocument } from './pages/DraftDocument'
import Usage from './pages/Usage'
import Newsletter from './pages/Newsletter'
import CheckComplianceLogs from './pages/CheckComplianceLogs'
import Wallet from './pages/Wallet'

const AppRoutes = () => {

    return (
      <Routes>
        {/* Public Route (login) */}
        <Route path="/login" element={<Login />} />
        {/* Public Route (password reset) - link received by email */}
        <Route path="/reset-password" element={<ResetPassword />} />
        {/* Public Route (forgot password) - request reset email */}
        <Route path="/forgot-password" element={<ForgotPassword />} />

        {/* Rotas privadas */}
        <Route element={<PrivateRoute />}>
          <Route path="/" element={<Home />} />

          {/* Tools Routes */}
          <Route path="/search" element={<DocSearch />} />
          <Route path="/draft-document" element={<DraftDocument />} />
          <Route path="/compliance" element={<Navigate to="/compliance/chat" replace />} />
          <Route path="/compliance/chat" element={<CheckComplianceChat />} />
          <Route path="/compliance/documents" element={<CheckComplianceDocuments />} />
          <Route path="/compliance/logs" element={<CheckComplianceLogs />} />
          <Route path="/chat-general" element={<Chat />} />

          {/* Newsletter Route */}
          <Route path="/newsletter" element={<Newsletter />} />

          {/* Access Routes */}
          <Route path="/accessi" element={<TeamManagement />} />

          {/* Usage Routes */}
          <Route path="/usage" element={<Navigate to="/usage/utilizzo" replace />} />
          <Route path="/usage/utilizzo" element={<Usage />} />
          <Route path="/usage/wallet" element={<Wallet />} />

          {/* Segreteria Societaria Sub-routes */}
          <Route path="/segreteria">
            <Route index element={<Navigate to="/segreteria/dashboard" replace />} />
            <Route path="dashboard" element={
              <Dashboard/>
            } />
            <Route path="companies" element={
              <CompanyList/>
            } />
            <Route path="documents" element={<DocumentGenerator />} />
            <Route path="assistant" element={<AIAssistant />} />
          </Route>

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    )
}

export default AppRoutes
