import Layout from './components/Layout';
import Dashboard from './components/Dashboard';
import Performance from './pages/Performance';
import Alerts from './pages/Alerts';
import SqlDetails from './pages/SqlDetails';
import Settings from './pages/Settings';
import Editor from './pages/Editor';
import { BrowserRouter, Routes, Route } from 'react-router-dom';

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/performance" element={<Performance />} />
          <Route path="/performance/sql/:sqlId" element={<SqlDetails />} />
          <Route path="/editor" element={<Editor />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
