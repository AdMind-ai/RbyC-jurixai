// routes.tsx
import { Navigate, Route, Routes } from 'react-router-dom'
import Home from './components/newLayout/Home'
import Login from './pages/Login'
import PrivateRoute from './components/PrivateRoute'
import UserAccess from './components/newLayout/UserAccess'
import Dashboard from './components/newLayout/Dashboard'
import CompanyList from './components/newLayout/CompanyList'
import DocumentGenerator from './components/newLayout/DocumentGenerator'
import AIAssistant from './components/newLayout/AIAssistant'
import SearchView from './components/newLayout/SearchView'
import ComplianceView from './components/newLayout/ComplianceView'
import Chat from './pages/Chat'

const AppRoutes = () => {

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
