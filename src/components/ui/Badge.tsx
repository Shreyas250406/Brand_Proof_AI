// ============================================================
// Severity Badge
// ============================================================

import { getSeverityLabel, getSeverityClass, getCategoryLabel } from '@/lib/utils';
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
