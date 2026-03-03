import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ErrorBoundary } from './components/common';
import { MainLayout } from './components/layout';
import { Dashboard } from './pages/dashboard';
import { MCPList, MCPDetail, MCPCreate, MCPEdit } from './pages/mcp';
import { AgentList, AgentDetail, AgentForm } from './pages/agent';
import { KBList, KBCreate, KBDetail, KBEdit } from './pages/kb';
import { Playground } from './pages/playground';
import { Settings } from './pages/settings';
import { ToastProvider } from './contexts/ToastContext';

function App() {
  return (
    <ErrorBoundary>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            {/* Main Routes */}
            <Route path="/" element={<MainLayout />}>
              <Route index element={<Dashboard />} />
              <Route path="mcps" element={<MCPList />} />
              <Route path="mcps/create" element={<MCPCreate />} />
              <Route path="mcps/:id" element={<MCPDetail />} />
              <Route path="mcps/:id/edit" element={<MCPEdit />} />
              <Route path="agents" element={<AgentList />} />
              <Route path="agents/create" element={<AgentForm mode="create" />} />
              <Route path="agents/:id" element={<AgentDetail />} />
              <Route path="agents/:id/edit" element={<AgentForm mode="edit" />} />
              <Route path="knowledge-bases" element={<KBList />} />
              <Route path="knowledge-bases/create" element={<KBCreate />} />
              <Route path="knowledge-bases/:id" element={<KBDetail />} />
              <Route path="knowledge-bases/:id/edit" element={<KBEdit />} />
              <Route path="playground" element={<Playground />} />
              <Route path="settings" element={<Settings />} />
            </Route>

            {/* 404 Route */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </ErrorBoundary>
  );
}

export default App;
