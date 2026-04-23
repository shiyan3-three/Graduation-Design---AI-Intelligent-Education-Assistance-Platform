import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthPage } from './pages/AuthPage.jsx';
import { ChatPage } from './pages/ChatPage.jsx';
import { HomePage } from './pages/HomePage/index.jsx';
import { LearningPage } from './pages/LearningPage/index.jsx';
import { RecommendPage } from './pages/RecommendPage/index.jsx';
import { AdminPage } from './pages/AdminPage/index.jsx';
import { AppLayout } from './components/Layout/AppLayout.jsx';
import { ProtectedRoute } from './components/ProtectedRoute.jsx';

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<AuthPage />} />
        <Route path="/register" element={<AuthPage />} />
        
        <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
          <Route path="/" element={<HomePage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/learning" element={<LearningPage />} />
          <Route path="/recommend" element={<RecommendPage />} />
          <Route path="/admin" element={<AdminPage />} />
        </Route>
        
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}
