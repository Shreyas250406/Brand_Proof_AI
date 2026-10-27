// ============================================================
// Severity Badge
// ============================================================

import { cn, getSeverityLabel, getSeverityClass, getCategoryLabel } from '@/lib/utils';
import type { FindingSeverity, FindingCategory } from '@/types/domain';

export function SeverityBadge({ severity }: { severity: FindingSeverity }) {
  return (
    <span className={getSeverityClass(severity)}>
      {getSeverityLabel(severity)}
    </span>
  );
}

export function CategoryBadge({ category }: { category: FindingCategory }) {
  return (
    <span className="badge bg-surface-100 text-surface-600 border border-surface-200">
      {getCategoryLabel(category)}
    </span>
  );
}

interface StatusDotProps {
  active?: boolean;
  className?: string;
}

export function StatusDot({ active = true, className }: StatusDotProps) {
  return (
    <span
      className={cn(
        'inline-block w-2 h-2 rounded-full',
        active ? 'bg-green-500' : 'bg-surface-300',
        className
      )}
    />
  );
}
