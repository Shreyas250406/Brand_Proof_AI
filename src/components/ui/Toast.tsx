// ============================================================
// Toast Notifications Component
// ============================================================

import { X, CheckCircle, AlertCircle, AlertTriangle, Info } from 'lucide-react';
import { useApp, type ToastVariant } from '@/context/AppContext';
import { cn } from '@/lib/utils';

const ICONS: Record<ToastVariant, React.ReactNode> = {
  success: <CheckCircle className="w-4 h-4 shrink-0 text-green-500" />,
  error: <AlertCircle className="w-4 h-4 shrink-0 text-red-500" />,
  warning: <AlertTriangle className="w-4 h-4 shrink-0 text-amber-500" />,
  info: <Info className="w-4 h-4 shrink-0 text-blue-500" />,
};

const STYLES: Record<ToastVariant, string> = {
  success: 'border-green-200 bg-white',
  error: 'border-red-200 bg-white',
  warning: 'border-amber-200 bg-white',
  info: 'border-blue-200 bg-white',
};

export function ToastContainer() {
  const { toasts, removeToast } = useApp();

  if (toasts.length === 0) return null;

  return (
    <div
      role="region"
      aria-label="Notifications"
      aria-live="polite"
      className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full"
    >
      {toasts.map(toast => (
        <div
          key={toast.id}
          role="alert"
          className={cn(
            'flex items-start gap-3 p-3.5 rounded-xl border shadow-[var(--shadow-elevated)]',
            'animate-in slide-in-from-bottom-2 duration-200',
            STYLES[toast.variant]
          )}
        >
          {ICONS[toast.variant]}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-surface-900">{toast.title}</p>
            {toast.description && (
              <p className="text-xs text-surface-500 mt-0.5">{toast.description}</p>
            )}
          </div>
          <button
            onClick={() => removeToast(toast.id)}
            className="shrink-0 text-surface-400 hover:text-surface-600 transition-colors"
            aria-label="Dismiss notification"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      ))}
    </div>
  );
}
