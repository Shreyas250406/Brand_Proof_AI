// ============================================================
// Application Router
// ============================================================

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from '@/context/AuthContext';
import { AppProvider } from '@/context/AppContext';
import { AppLayout } from '@/components/layout/AppLayout';
import { OverviewPage } from '@/pages/OverviewPage';
import { AnalysePage } from '@/pages/AnalysePage';
import { ReviewPage } from '@/pages/ReviewPage';
import { HistoryPage } from '@/pages/HistoryPage';
import { BrandPage } from '@/pages/BrandPage';
import { AuthPage } from '@/pages/AuthPage';

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppProvider>
          <Routes>
            <Route path="/login" element={<AuthPage />} />
            <Route path="/signup" element={<AuthPage />} />
            <Route element={<AppLayout />}>
              <Route path="/" element={<OverviewPage />} />
              <Route path="/analyse" element={<AnalysePage />} />
              <Route path="/review" element={<ReviewPage />} />
              <Route path="/history" element={<HistoryPage />} />
              <Route path="/brand" element={<BrandPage />} />
              {/* Catch-all redirect */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </AppProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
