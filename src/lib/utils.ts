// ============================================================
// Utility Functions
// ============================================================

import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import type { FindingCategory, FindingSeverity, AnalysisStatus, ReviewStatus, FeedbackCategory, SourceType } from '@/types/domain';

// -----------------------------------------------------------
// Class merging
// -----------------------------------------------------------

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// -----------------------------------------------------------
// ID generation
// -----------------------------------------------------------

export function generateId(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

// -----------------------------------------------------------
// Date formatting
// -----------------------------------------------------------

export function formatDate(isoString: string): string {
  try {
    const d = new Date(isoString);
    return d.toLocaleDateString('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return '—';
  }
}

export function formatDateTime(isoString: string): string {
  try {
    const d = new Date(isoString);
    return d.toLocaleDateString('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '—';
  }
}

export function formatRelativeTime(isoString: string): string {
  try {
    const now = Date.now();
    const then = new Date(isoString).getTime();
    const diffMs = now - then;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return formatDate(isoString);
  } catch {
    return '—';
  }
}

// -----------------------------------------------------------
// File utilities
// -----------------------------------------------------------

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function getFileExtension(filename: string): string {
  // Normalize the final suffix so file-type checks are case-insensitive.
  return filename.split('.').pop()?.toLowerCase() ?? '';
}

export function isSupportedTextFile(filename: string): boolean {
  const ext = getFileExtension(filename);
  return ['txt', 'md', 'csv'].includes(ext);
}

export function isSupportedDocFile(filename: string): boolean {
  const ext = getFileExtension(filename);
  return ['pdf', 'doc', 'docx'].includes(ext);
}

export function isSupportedImageFile(filename: string): boolean {
  const ext = getFileExtension(filename);
  return ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'].includes(ext);
}

export function isSupportedVideoFile(filename: string): boolean {
  const ext = getFileExtension(filename);
  return ['mp4', 'mov', 'avi', 'webm', 'mkv'].includes(ext);
}

// -----------------------------------------------------------
// Label helpers
// -----------------------------------------------------------

export function getSeverityLabel(severity: FindingSeverity): string {
  const map: Record<FindingSeverity, string> = {
    critical: 'Critical',
    major: 'Major',
    minor: 'Minor',
    info: 'Info',
  };
  return map[severity];
}

export function getSeverityClass(severity: FindingSeverity): string {
  const map: Record<FindingSeverity, string> = {
    critical: 'badge-critical',
    major: 'badge-major',
    minor: 'badge-minor',
    info: 'badge-info',
  };
  return map[severity];
}

export function getSeverityColor(severity: FindingSeverity): string {
  const map: Record<FindingSeverity, string> = {
    critical: 'text-red-600',
    major: 'text-orange-600',
    minor: 'text-amber-600',
    info: 'text-blue-600',
  };
  return map[severity];
}

export function getCategoryLabel(category: FindingCategory): string {
  const map: Record<FindingCategory, string> = {
    grammar: 'Grammar',
    spelling: 'Spelling',
    punctuation: 'Punctuation',
    style: 'Style',
    clarity: 'Clarity',
    brand_voice: 'Brand Voice',
    terminology: 'Terminology',
    prohibited: 'Prohibited',
    readability: 'Readability',
    consistency: 'Consistency',
    factual_claim: 'Factual Claim',
    seo: 'SEO',
    other: 'Other',
  };
  return map[category] ?? category;
}

export function getStatusLabel(status: AnalysisStatus): string {
  const map: Record<AnalysisStatus, string> = {
    pending: 'Pending',
    processing: 'Processing',
    completed: 'Completed',
    failed: 'Failed',
    no_findings: 'No Issues',
  };
  return map[status];
}

export function getStatusClass(status: AnalysisStatus): string {
  const map: Record<AnalysisStatus, string> = {
    pending: 'badge-neutral',
    processing: 'badge-info',
    completed: 'badge-success',
    failed: 'badge-critical',
    no_findings: 'badge-success',
  };
  return map[status];
}

export function getReviewStatusLabel(status: ReviewStatus): string {
  const map: Record<ReviewStatus, string> = {
    not_started: 'Not Started',
    in_progress: 'In Progress',
    corrections_applied: 'Corrections Applied',
    completed: 'Completed',
  };
  return map[status];
}

export function getFeedbackLabel(category: FeedbackCategory): string {
  const map: Record<FeedbackCategory, string> = {
    genuine_error: 'Genuine Error',
    false_positive: 'False Positive',
    stylistic_choice: 'Stylistic Choice',
    unsure: 'Unsure',
  };
  return map[category];
}

export function getSourceTypeLabel(type: SourceType): string {
  const map: Record<SourceType, string> = {
    text: 'Text',
    file_text: 'Text File',
    file_pdf: 'PDF',
    file_word: 'Word Doc',
    file_image: 'Image',
    file_video: 'Video',
    file_audio: 'Audio / Speech',
    url: 'URL',
  };
  return map[type];
}

// -----------------------------------------------------------
// Text utilities
// -----------------------------------------------------------

export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength - 3) + '...';
}

export function countWords(text: string): number {
  return text.trim() ? text.trim().split(/\s+/).length : 0;
}

export function countChars(text: string): number {
  return text.length;
}

// -----------------------------------------------------------
// Copy to clipboard
// -----------------------------------------------------------

export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard) {
      await navigator.clipboard.writeText(text);
      return true;
    }
    // Fallback
    const el = document.createElement('textarea');
    el.value = text;
    el.style.position = 'fixed';
    el.style.opacity = '0';
    document.body.appendChild(el);
    el.select();
    document.execCommand('copy');
    document.body.removeChild(el);
    return true;
  } catch {
    return false;
  }
}

// -----------------------------------------------------------
// Download as file
// -----------------------------------------------------------

export function downloadTextFile(content: string, filename: string): void {
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

// -----------------------------------------------------------
// Severity order for sorting
// -----------------------------------------------------------

export const SEVERITY_ORDER: Record<FindingSeverity, number> = {
  critical: 0,
  major: 1,
  minor: 2,
  info: 3,
};
