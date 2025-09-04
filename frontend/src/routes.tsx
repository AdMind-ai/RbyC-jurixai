// routes.tsx
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import Home from './pages/Home'
import Login from './pages/Login'
import DocDraft from './pages/DocDraft'
import DocSearch from './pages/DocSearch'
// import CheckCompliance from './pages/CheckCompliance'
import DocTranslator from './pages/DocTranslator'
// import LawConsultant from './pages/LawConsultant'
// import Usage from './pages/Usage'
import TeamManagement from './pages/TeamManagement'
import { AuthProvider } from './context/AuthContext'
import PrivateRoute from './components/PrivateRoute'
import Chat from './pages/Chat'

const AppRoutes = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public Route (login) */}
          <Route path="/login" element={<Login />} />

          {/* Rotas privadas */}
          <Route element={<PrivateRoute />}>
            <Route path="/" element={<Home />} />
            <Route path="/doc-draft" element={<DocDraft />} />
            <Route path="/doc-search" element={<DocSearch />} />
            {/* <Route path="/check-compliance" element={<CheckCompliance />} /> */}
            <Route path="/doc-translator" element={<DocTranslator />} />
            <Route path="/chat-assistant" element={<Chat />} />
            {/* <Route path="/usage" element={<Usage />} /> */}
            <Route path="/access" element={<TeamManagement />} />
            {/* <Route path="*" element={<Home />} /> */}
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default AppRoutes
