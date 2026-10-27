// ============================================================
// Confirmation Dialog
// ============================================================

import * as Dialog from '@radix-ui/react-dialog';
import { AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'danger' | 'default';
  onConfirm: () => void;
}

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'default',
  onConfirm,
}: ConfirmDialogProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/40 backdrop-blur-[2px] z-40 animate-in fade-in duration-150" />
        <Dialog.Content
          className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-sm
                     bg-white rounded-2xl shadow-[var(--shadow-modal)] p-6 animate-in fade-in zoom-in-95 duration-150"
          aria-describedby="dialog-desc"
        >
          <div className="flex flex-col gap-4">
            {variant === 'danger' && (
              <div className="w-10 h-10 rounded-full bg-red-50 flex items-center justify-center">
                <AlertTriangle className="w-5 h-5 text-red-600" />
              </div>
            )}
            <div>
              <Dialog.Title className="text-base font-semibold text-surface-900">
                {title}
              </Dialog.Title>
              <Dialog.Description id="dialog-desc" className="text-sm text-surface-500 mt-1.5">
                {description}
              </Dialog.Description>
            </div>
            <div className="flex gap-3 justify-end">
              <Dialog.Close asChild>
                <button className="btn-secondary text-sm">{cancelLabel}</button>
              </Dialog.Close>
              <button
                onClick={() => {
                  onConfirm();
                  onOpenChange(false);
                }}
                className={cn(
                  'text-sm',
                  variant === 'danger' ? 'btn-danger' : 'btn-primary'
                )}
              >
                {confirmLabel}
              </button>
            </div>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
