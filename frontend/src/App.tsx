// import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';

import Dashboard from './pages/Dashboard';
// Placeholder Pages for now
import CaseList from './pages/CaseList';
import CaseDetail from './pages/CaseDetail';

import AdminReview from './pages/AdminReview';
import SystemLogs from './pages/SystemLogs';
import SiemSettings from './pages/SiemSettings';
import UserManagement from './pages/UserManagement';
import EnvManagement from './pages/EnvManagement';
import AuthCallbackPage from './pages/AuthCallbackPage';
import SystemJobs from './pages/SystemJobs';
import RolePermissions from './pages/RolePermissions';
import IntegrationSettings from './pages/IntegrationSettings';


function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/auth-callback" element={<AuthCallbackPage />} />

          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/cases" element={<CaseList />} />
              <Route path="/cases/:id" element={<CaseDetail />} />
              <Route path="/reviews" element={<AdminReview />} />
              <Route path="/logs" element={<SystemLogs />} />
              <Route path="/siem" element={<SiemSettings />} />
              <Route path="/users" element={<UserManagement />} />
              <Route path="/env" element={<EnvManagement />} />
              <Route path="/jobs" element={<SystemJobs />} />
              <Route path="/permissions" element={<RolePermissions />} />
              <Route path="/integrations" element={<IntegrationSettings />} />
            </Route>
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
