// routes.tsx
import { Navigate, Route, Routes } from 'react-router-dom'
import Home from './pages/Home'
import Login from './pages/Login'
import PrivateRoute from './components/PrivateRoute'
import Dashboard from './components/SegreteriaSocietaria/Dashboard'
import CompanyList from './components/SegreteriaSocietaria/CompanyList'
import DocumentGenerator from './components/SegreteriaSocietaria/DocumentGenerator'
import Chat from './pages/Chat'
import DocSearch from './pages/DocSearch'
import TeamManagement from './pages/TeamManagement'
import CheckCompliance from './pages/CheckCompliance'
import AIAssistant from './components/SegreteriaSocietaria/AIAssistant'
import { DraftDocument } from './pages/DraftDocument'

const AppRoutes = () => {

    return (
      <Routes>
        {/* Public Route (login) */}
        <Route path="/login" element={<Login />} />

        {/* Rotas privadas */}
        <Route element={<PrivateRoute />}>
          <Route path="/" element={<Home />} />

          {/* Tools Routes */}
          <Route path="/search" element={<DocSearch />} />
          <Route path="/draft-document" element={<DraftDocument />} />
          <Route path="/compliance" element={<CheckCompliance />} />
          <Route path="/chat-general" element={<Chat />} />

          {/* Access Routes */}
          <Route path="/accessi" element={<TeamManagement />} />

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
