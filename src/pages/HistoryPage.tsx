// ============================================================
// Analysis History Page
// ============================================================

import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  FileText,
  Trash2,
  RotateCcw,
  ChevronDown,
  ChevronRight,
  History,
} from 'lucide-react';
import type { Analysis, AnalysisStatus, ReviewStatus } from '@/types/domain';
import { historyService } from '@/services/demo';
import { clearAllDemoData } from '@/services/persistence';
import { useApp } from '@/context/AppContext';
import { EmptyState } from '@/components/ui/EmptyState';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import {
  formatDateTime,
  getStatusClass,
  getStatusLabel,
  getReviewStatusLabel,
  getSourceTypeLabel,
  getSeverityColor,
} from '@/lib/utils';
import { cn } from '@/lib/utils';

const STATUS_OPTIONS: AnalysisStatus[] = ['completed', 'no_findings', 'failed'];
const REVIEW_STATUS_OPTIONS: ReviewStatus[] = ['not_started', 'in_progress', 'corrections_applied', 'completed'];

export function HistoryPage() {
  const navigate = useNavigate();
  const { setCurrentAnalysis, addToast, historyVersion, triggerHistoryRefresh } = useApp();

  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatuses, setFilterStatuses] = useState<AnalysisStatus[]>([]);
  const [filterReviewStatuses, setFilterReviewStatuses] = useState<ReviewStatus[]>([]);
  const [sortBy, setSortBy] = useState<'date_desc' | 'date_asc' | 'name_asc' | 'findings_desc'>('date_desc');
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [clearDialogOpen, setClearDialogOpen] = useState(false);
  const [showFilters, setShowFilters] = useState(false);

  async function loadHistory() {
    setLoading(true);
    try {
      const data = await historyService.list();
      setAnalyses(data);
    } finally {
      setLoading(false);
    }
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { loadHistory(); }, [historyVersion]);

  // Filter and sort
  const filteredAnalyses = useMemo(() => {
    let result = [...analyses];

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(a =>
        a.name.toLowerCase().includes(q) ||
        a.sourceType.toLowerCase().includes(q) ||
        a.originalContent.toLowerCase().includes(q)
      );
    }

    if (filterStatuses.length > 0) {
      result = result.filter(a => filterStatuses.includes(a.status));
    }

    if (filterReviewStatuses.length > 0) {
      result = result.filter(a => filterReviewStatuses.includes(a.reviewStatus));
    }

    result.sort((a, b) => {
      switch (sortBy) {
        case 'date_asc': return new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
        case 'name_asc': return a.name.localeCompare(b.name);
        case 'findings_desc': return b.findings.length - a.findings.length;
        default: return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
      }
    });

    return result;
  }, [analyses, searchQuery, filterStatuses, filterReviewStatuses, sortBy]);

  function handleOpenAnalysis(analysis: Analysis) {
    setCurrentAnalysis(analysis);
    navigate('/review');
  }

  async function handleDelete(id: string) {
    try {
      await historyService.delete(id);
      triggerHistoryRefresh();
      setAnalyses(prev => prev.filter(a => a.id !== id));
      addToast({ title: 'Analysis deleted', variant: 'success' });
    } catch {
      addToast({ title: 'Failed to delete analysis', variant: 'error' });
    } finally {
      setDeleteId(null);
    }
  }

  async function handleClearAll() {
    try {
      await historyService.clear();
      clearAllDemoData();
      triggerHistoryRefresh();
      setAnalyses([]);
      addToast({ title: 'All analysis history cleared', variant: 'success' });
    } catch {
      addToast({ title: 'Failed to clear history', variant: 'error' });
    }
  }

  const activeFiltersCount = filterStatuses.length + filterReviewStatuses.length;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="page-header mb-0">
          <h2 className="page-title">Analysis History</h2>
          <p className="page-description">Browse and reopen previous content analyses.</p>
        </div>
        {analyses.length > 0 && (
          <button
            onClick={() => setClearDialogOpen(true)}
            className="btn-ghost text-sm text-red-600 hover:text-red-700 hover:bg-red-50"
          >
            <RotateCcw className="w-4 h-4" />
            Clear Demo Data
          </button>
        )}
      </div>

      {/* Search and filters */}
      <div className="space-y-3">
        <div className="flex gap-3">
          {/* Search */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-400" />
            <input
              type="search"
              placeholder="Search analyses…"
              className="input-field pl-9"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              aria-label="Search analyses"
            />
          </div>

          {/* Filter toggle */}
          <button
            onClick={() => setShowFilters(s => !s)}
            className={cn('btn-ghost text-sm shrink-0', showFilters && 'bg-surface-100')}
          >
            Filter
            {activeFiltersCount > 0 && (
              <span className="w-4 h-4 rounded-full bg-brand-600 text-white text-xs flex items-center justify-center">
                {activeFiltersCount}
              </span>
            )}
            <ChevronDown className={cn('w-4 h-4 transition-transform', showFilters && 'rotate-180')} />
          </button>

          {/* Sort */}
          <select
            className="input-field w-auto shrink-0 text-sm"
            value={sortBy}
            onChange={e => setSortBy(e.target.value as typeof sortBy)}
            aria-label="Sort analyses"
          >
            <option value="date_desc">Newest first</option>
            <option value="date_asc">Oldest first</option>
            <option value="name_asc">Name A–Z</option>
            <option value="findings_desc">Most findings</option>
          </select>
        </div>

        {/* Filter panel */}
        {showFilters && (
          <div className="card p-4 space-y-3">
            <div>
              <p className="text-xs font-medium text-surface-500 mb-2">STATUS</p>
              <div className="flex flex-wrap gap-2">
                {STATUS_OPTIONS.map(s => (
                  <button
                    key={s}
                    onClick={() => setFilterStatuses(prev =>
                      prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s]
                    )}
                    className={cn(
                      'px-2.5 py-1 rounded-full text-xs font-medium border transition-colors',
                      filterStatuses.includes(s)
                        ? 'bg-navy-700 text-white border-navy-700'
                        : 'bg-white text-surface-600 border-surface-200 hover:border-surface-300'
                    )}
                  >
                    {getStatusLabel(s)}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <p className="text-xs font-medium text-surface-500 mb-2">REVIEW STATUS</p>
              <div className="flex flex-wrap gap-2">
                {REVIEW_STATUS_OPTIONS.map(s => (
                  <button
                    key={s}
                    onClick={() => setFilterReviewStatuses(prev =>
                      prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s]
                    )}
                    className={cn(
                      'px-2.5 py-1 rounded-full text-xs font-medium border transition-colors',
                      filterReviewStatuses.includes(s)
                        ? 'bg-navy-700 text-white border-navy-700'
                        : 'bg-white text-surface-600 border-surface-200 hover:border-surface-300'
                    )}
                  >
                    {getReviewStatusLabel(s)}
                  </button>
                ))}
              </div>
            </div>
            {activeFiltersCount > 0 && (
              <button
                onClick={() => { setFilterStatuses([]); setFilterReviewStatuses([]); }}
                className="text-xs text-surface-500 hover:text-surface-700"
              >
                Clear filters
              </button>
            )}
          </div>
        )}
      </div>

      {/* Results count */}
      {!loading && analyses.length > 0 && (
        <p className="text-xs text-surface-500">
          Showing {filteredAnalyses.length} of {analyses.length} analyse{analyses.length !== 1 ? 's' : ''}
          {(searchQuery || activeFiltersCount > 0) ? ' (filtered)' : ''}
        </p>
      )}

      {/* List */}
      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="card p-4 animate-pulse">
              <div className="flex items-center gap-4">
                <div className="w-9 h-9 rounded-lg bg-surface-200" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-surface-200 rounded w-1/3" />
                  <div className="h-3 bg-surface-100 rounded w-1/4" />
                </div>
                <div className="h-5 w-20 bg-surface-200 rounded-full" />
              </div>
            </div>
          ))}
        </div>
      ) : filteredAnalyses.length === 0 ? (
        <div className="card">
          <EmptyState
            icon={<History className="w-5 h-5" />}
            title={analyses.length === 0 ? 'No analyses yet' : 'No analyses match your search'}
            description={analyses.length === 0
              ? 'Run your first content analysis to see it here.'
              : 'Try adjusting the search or filters.'
            }
            action={analyses.length === 0 ? (
              <button onClick={() => navigate('/analyse')} className="btn-primary text-sm">
                Analyse Content
              </button>
            ) : undefined}
          />
        </div>
      ) : (
        <div className="space-y-2">
          {filteredAnalyses.map(analysis => (
            <HistoryRow
              key={analysis.id}
              analysis={analysis}
              onClick={() => handleOpenAnalysis(analysis)}
              onDelete={() => setDeleteId(analysis.id)}
            />
          ))}
        </div>
      )}

      {/* Delete confirmation */}
      <ConfirmDialog
        open={deleteId !== null}
        onOpenChange={open => !open && setDeleteId(null)}
        title="Delete analysis"
        description="This will permanently delete this analysis record and its feedback from demo storage. This cannot be undone."
        confirmLabel="Delete"
        cancelLabel="Cancel"
        variant="danger"
        onConfirm={() => deleteId && handleDelete(deleteId)}
      />

      {/* Clear all confirmation */}
      <ConfirmDialog
        open={clearDialogOpen}
        onOpenChange={setClearDialogOpen}
        title="Clear all demo data"
        description="This will delete all analyses, feedback and brand settings from local demo storage. This cannot be undone."
        confirmLabel="Clear Everything"
        cancelLabel="Cancel"
        variant="danger"
        onConfirm={handleClearAll}
      />
    </div>
  );
}

// -----------------------------------------------------------
// History Row
// -----------------------------------------------------------

interface HistoryRowProps {
  analysis: Analysis;
  onClick: () => void;
  onDelete: () => void;
}

function HistoryRow({ analysis, onClick, onDelete }: HistoryRowProps) {
  const criticalCount = analysis.findings.filter(f => f.severity === 'critical').length;
  const majorCount = analysis.findings.filter(f => f.severity === 'major').length;
  const minorCount = analysis.findings.filter(f => f.severity === 'minor').length;

  return (
    <div className="card p-4 flex items-center gap-4 group hover:shadow-[var(--shadow-elevated)] transition-shadow">
      {/* Icon */}
      <div className="w-9 h-9 rounded-lg bg-surface-100 flex items-center justify-center shrink-0">
        <FileText className="w-4 h-4 text-surface-500" />
      </div>

      {/* Info */}
      <button
        onClick={onClick}
        className="flex-1 min-w-0 text-left"
      >
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="text-sm font-medium text-surface-900 truncate group-hover:text-brand-600 transition-colors">
              {analysis.name}
            </p>
            <div className="flex items-center gap-2 mt-0.5 flex-wrap">
              <span className="text-xs text-surface-400">{getSourceTypeLabel(analysis.sourceType)}</span>
              <span className="text-surface-300 text-xs">·</span>
              <span className="text-xs text-surface-400">{formatDateTime(analysis.createdAt)}</span>
              {analysis.findings.length > 0 && (
                <>
                  <span className="text-surface-300 text-xs">·</span>
                  <span className="text-xs flex gap-1.5">
                    {criticalCount > 0 && <span className={cn('font-medium', getSeverityColor('critical'))}>{criticalCount}C</span>}
                    {majorCount > 0 && <span className={cn('font-medium', getSeverityColor('major'))}>{majorCount}M</span>}
                    {minorCount > 0 && <span className={cn('font-medium', getSeverityColor('minor'))}>{minorCount}m</span>}
                    {analysis.findings.length === 0 && <span className="text-surface-400">0 findings</span>}
                  </span>
                </>
              )}
            </div>
          </div>
        </div>
      </button>

      {/* Status badges */}
      <div className="flex items-center gap-2 shrink-0">
        <span className={getStatusClass(analysis.status)}>
          {getStatusLabel(analysis.status)}
        </span>
        <span className="badge-neutral hidden sm:inline-flex">
          {getReviewStatusLabel(analysis.reviewStatus)}
        </span>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={onClick}
          className="btn-ghost p-2"
          aria-label="Open analysis"
          title="Open"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); onDelete(); }}
          className="btn-ghost p-2 text-surface-400 hover:text-red-600"
          aria-label="Delete analysis"
          title="Delete"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
