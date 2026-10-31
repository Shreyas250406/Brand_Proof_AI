// ============================================================
// Application Context
// Manages current analysis state, navigation, and toast notifications.
// ============================================================

import React, { createContext, useContext, useState, useCallback, useRef } from 'react';
import type { Analysis, FindingFeedback } from '@/types/domain';

// -----------------------------------------------------------
// Toast system
// -----------------------------------------------------------

export type ToastVariant = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
  id: string;
  title: string;
  description?: string;
  variant: ToastVariant;
}

// -----------------------------------------------------------
// App Context Shape
// -----------------------------------------------------------

interface AppContextValue {
  // Current analysis (active session)
  currentAnalysis: Analysis | null;
  setCurrentAnalysis: (analysis: Analysis | null) => void;
  updateCurrentAnalysis: (updates: Partial<Analysis>) => void;

  // History versioning for reactive UI updates
  historyVersion: number;
  triggerHistoryRefresh: () => void;

  // Feedback for current analysis
  feedbackMap: Record<string, FindingFeedback>;
  setFeedbackForFinding: (findingId: string, feedback: FindingFeedback) => void;
  clearFeedback: () => void;

  // Toast notifications
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;

  // Sidebar state
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (collapsed: boolean) => void;
}

const AppContext = createContext<AppContextValue | null>(null);

const SESSION_ANALYSIS_KEY = 'brandproof_current_analysis';

function loadStoredAnalysis(): Analysis | null {
  try {
    const raw = sessionStorage.getItem(SESSION_ANALYSIS_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

// -----------------------------------------------------------
// Provider
// -----------------------------------------------------------

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [currentAnalysis, setCurrentAnalysisState] = useState<Analysis | null>(loadStoredAnalysis);
  const [historyVersion, setHistoryVersion] = useState<number>(0);
  const [feedbackMap, setFeedbackMap] = useState<Record<string, FindingFeedback>>({});
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const toastCounter = useRef(0);

  const triggerHistoryRefresh = useCallback(() => {
    setHistoryVersion(v => v + 1);
  }, []);

  const setCurrentAnalysis = useCallback((analysis: Analysis | null) => {
    setCurrentAnalysisState(analysis);
    setFeedbackMap({});
    try {
      if (analysis) {
        sessionStorage.setItem(SESSION_ANALYSIS_KEY, JSON.stringify(analysis));
      } else {
        sessionStorage.removeItem(SESSION_ANALYSIS_KEY);
      }
    } catch {
      // Ignore quota error
    }
  }, []);

  const updateCurrentAnalysis = useCallback((updates: Partial<Analysis>) => {
    setCurrentAnalysisState(prev => {
      if (!prev) return null;
      const next = { ...prev, ...updates, updatedAt: new Date().toISOString() };
      try {
        sessionStorage.setItem(SESSION_ANALYSIS_KEY, JSON.stringify(next));
      } catch {
        // Ignore quota error
      }
      return next;
    });
  }, []);

  const setFeedbackForFinding = useCallback((findingId: string, feedback: FindingFeedback) => {
    setFeedbackMap(prev => ({ ...prev, [findingId]: feedback }));
  }, []);

  const clearFeedback = useCallback(() => {
    setFeedbackMap({});
  }, []);

  const addToast = useCallback((toast: Omit<Toast, 'id'>) => {
    const id = `toast-${++toastCounter.current}`;
    const newToast = { ...toast, id };
    setToasts(prev => [...prev, newToast]);
    // Auto-dismiss after 5s
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 5000);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  return (
    <AppContext.Provider value={{
      currentAnalysis,
      setCurrentAnalysis,
      updateCurrentAnalysis,
      historyVersion,
      triggerHistoryRefresh,
      feedbackMap,
      setFeedbackForFinding,
      clearFeedback,
      toasts,
      addToast,
      removeToast,
      sidebarCollapsed,
      setSidebarCollapsed,
    }}>
      {children}
    </AppContext.Provider>
  );
}

// -----------------------------------------------------------
// Hook
// -----------------------------------------------------------

// eslint-disable-next-line react/only-export-components
export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used within AppProvider');
  return ctx;
}
