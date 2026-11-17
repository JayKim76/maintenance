import Layout from './components/Layout';
import Dashboard from './components/Dashboard';
import Performance from './pages/Performance';
import Alerts from './pages/Alerts';
import SqlDetails from './pages/SqlDetails';
import Settings from './pages/Settings';
import Connections from './pages/Connections';
import Editor from './pages/Editor';
import HealthCheck from './pages/HealthCheck';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConnectionProvider, useConnection } from './context/ConnectionContext';

import { AuthProvider } from './hooks/useAuth';

function AppRoutes() {
  const { connected } = useConnection();

  return (
    <Layout>
      <Routes>
        {/* Connections and Settings are always accessible */}
        <Route path="/connections" element={<Connections />} />
        <Route path="/settings" element={<Settings />} />

        {connected ? (
          <>
            <Route path="/" element={<Dashboard />} />
            <Route path="/performance" element={<Performance />} />
            <Route path="/performance/sql/:sqlId" element={<SqlDetails />} />
            <Route path="/editor" element={<Editor />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/healthcheck" element={<HealthCheck />} />
          </>
        ) : (
          /* Not connected: redirect everything else to Connections */
          <Route path="*" element={<Navigate to="/connections" replace />} />
        )}
      </Routes>
    </Layout>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ConnectionProvider>
          <AppRoutes />
        </ConnectionProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
