// ============================================================
// Overview Dashboard Page
// ============================================================

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileScan,
  AlertCircle,
  CheckCircle2,
  Clock,
  TrendingUp,
  ArrowRight,
  FileText,
  ChevronRight,
} from 'lucide-react';
import type { Analysis } from '@/types/domain';
import { historyService } from '@/services/demo';
import { useApp } from '@/context/AppContext';
import { EmptyState } from '@/components/ui/EmptyState';
import { Skeleton } from '@/components/ui/Skeleton';
import {
  formatRelativeTime,
  getStatusClass,
  getStatusLabel,
  getSeverityColor,
  getSourceTypeLabel,
} from '@/lib/utils';
import { cn } from '@/lib/utils';

export function OverviewPage() {
  const navigate = useNavigate();
  const { setCurrentAnalysis, historyVersion } = useApp();
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    historyService.list().then(data => {
      if (isMounted) {
        setAnalyses(data);
        setLoading(false);
      }
    });
    return () => {
      isMounted = false;
    };
  }, [historyVersion]);

  const completedAnalyses = analyses.filter(a => a.status === 'completed' || a.status === 'no_findings');
  const recentAnalyses = analyses.slice(0, 5);
  const totalFindings = analyses.reduce((acc, a) => acc + a.findings.filter(f => f.category !== 'other').length, 0);
  const pendingReview = analyses.filter(a => a.reviewStatus === 'not_started' && a.status === 'completed').length;

  function handleOpenAnalysis(analysis: Analysis) {
    setCurrentAnalysis(analysis);
    navigate('/review');
  }

  return (
    <div className="space-y-6">
      {/* Welcome section */}
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <h2 className="page-title">Welcome back</h2>
          <p className="page-description">Your content quality overview at a glance.</p>
        </div>
        <button
          onClick={() => navigate('/analyse')}
          className="btn-primary shrink-0"
        >
          <FileScan className="w-4 h-4" />
          Analyse Content
        </button>
      </div>

      {/* Summary cards */}
      {loading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="card p-4 space-y-2">
              <Skeleton className="h-3 w-24" />
              <Skeleton className="h-7 w-12" />
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <SummaryCard
            label="Total Analyses"
            value={analyses.length}
            icon={<FileText className="w-4 h-4" />}
            color="text-navy-600"
            bgColor="bg-navy-50"
          />
          <SummaryCard
            label="Issues Found"
            value={totalFindings}
            icon={<AlertCircle className="w-4 h-4" />}
            color="text-orange-600"
            bgColor="bg-orange-50"
          />
          <SummaryCard
            label="Completed"
            value={completedAnalyses.length}
            icon={<CheckCircle2 className="w-4 h-4" />}
            color="text-green-600"
            bgColor="bg-green-50"
          />
          <SummaryCard
            label="Awaiting Review"
            value={pendingReview}
            icon={<Clock className="w-4 h-4" />}
            color="text-amber-600"
            bgColor="bg-amber-50"
            onClick={pendingReview > 0 ? () => navigate('/history') : undefined}
          />
        </div>
      )}

      {/* Main content grid */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Recent analyses */}
        <div className="lg:col-span-2 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="section-title">Recent Analyses</h3>
            {analyses.length > 0 && (
              <button
                onClick={() => navigate('/history')}
                className="text-xs text-brand-600 hover:text-brand-700 font-medium flex items-center gap-1"
              >
                View all <ChevronRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {loading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="card p-4 flex items-center gap-4">
                  <Skeleton className="w-8 h-8 rounded-lg shrink-0" />
                  <div className="flex-1 space-y-1.5">
                    <Skeleton className="h-4 w-1/2" />
                    <Skeleton className="h-3 w-1/3" />
                  </div>
                  <Skeleton className="h-5 w-16 rounded-full" />
                </div>
              ))}
            </div>
          ) : recentAnalyses.length === 0 ? (
            <div className="card">
              <EmptyState
                icon={<FileScan className="w-5 h-5" />}
                title="No analyses yet"
                description="Run your first content analysis to see results here."
                action={
                  <button onClick={() => navigate('/analyse')} className="btn-primary text-sm">
                    <FileScan className="w-4 h-4" />
                    Analyse your first document
                  </button>
                }
              />
            </div>
          ) : (
            <div className="space-y-2">
              {recentAnalyses.map(analysis => (
                <AnalysisListItem
                  key={analysis.id}
                  analysis={analysis}
                  onClick={() => handleOpenAnalysis(analysis)}
                />
              ))}
            </div>
          )}
        </div>

        {/* Quick start guide */}
        <div className="space-y-3">
          <h3 className="section-title">Getting Started</h3>
          <div className="card p-5 space-y-4">
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-brand-100 flex items-center justify-center shrink-0 mt-0.5">
                <span className="text-xs font-bold text-brand-700">1</span>
              </div>
              <div>
                <p className="text-sm font-medium text-surface-800">Add your content</p>
                <p className="text-xs text-surface-500 mt-0.5">Paste text, upload a file, or drag and drop.</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-brand-100 flex items-center justify-center shrink-0 mt-0.5">
                <span className="text-xs font-bold text-brand-700">2</span>
              </div>
              <div>
                <p className="text-sm font-medium text-surface-800">Run analysis</p>
                <p className="text-xs text-surface-500 mt-0.5">BrandProof AI checks language, style and brand alignment.</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-brand-100 flex items-center justify-center shrink-0 mt-0.5">
                <span className="text-xs font-bold text-brand-700">3</span>
              </div>
              <div>
                <p className="text-sm font-medium text-surface-800">Review findings</p>
                <p className="text-xs text-surface-500 mt-0.5">Inspect issues, pick corrections and apply them selectively.</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-brand-100 flex items-center justify-center shrink-0 mt-0.5">
                <span className="text-xs font-bold text-brand-700">4</span>
              </div>
              <div>
                <p className="text-sm font-medium text-surface-800">Provide feedback</p>
                <p className="text-xs text-surface-500 mt-0.5">Mark findings as genuine errors, false positives or stylistic choices.</p>
              </div>
            </div>

            <button
              onClick={() => navigate('/analyse')}
              className="btn-primary w-full mt-2"
            >
              Start Your First Analysis
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>

          {/* Brand knowledge card */}
          <div className="card p-4 flex items-start gap-3 cursor-pointer hover:shadow-[var(--shadow-elevated)] transition-shadow"
            onClick={() => navigate('/brand')}
            role="button"
            tabIndex={0}
            onKeyDown={e => e.key === 'Enter' && navigate('/brand')}
          >
            <div className="w-8 h-8 rounded-lg bg-navy-50 flex items-center justify-center shrink-0">
              <TrendingUp className="w-4 h-4 text-navy-600" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-surface-800">Set Up Brand Guidelines</p>
              <p className="text-xs text-surface-500 mt-0.5">Define your preferred terminology, tone and writing rules.</p>
            </div>
            <ChevronRight className="w-4 h-4 text-surface-400 mt-0.5 shrink-0" />
          </div>
        </div>
      </div>
    </div>
  );
}

// -----------------------------------------------------------
// Summary Card
// -----------------------------------------------------------

interface SummaryCardProps {
  label: string;
  value: number;
  icon: React.ReactNode;
  color: string;
  bgColor: string;
  onClick?: () => void;
}

function SummaryCard({ label, value, icon, color, bgColor, onClick }: SummaryCardProps) {
  return (
    <div
      className={cn('card p-4', onClick && 'cursor-pointer hover:shadow-[var(--shadow-elevated)] transition-shadow')}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => e.key === 'Enter' && onClick() : undefined}
    >
      <div className="flex items-center gap-2.5">
        <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center shrink-0', bgColor, color)}>
          {icon}
        </div>
        <div className="min-w-0">
          <p className="text-xs text-surface-500 truncate">{label}</p>
          <p className="text-xl font-bold text-surface-900 leading-tight">{value}</p>
        </div>
      </div>
    </div>
  );
}

// -----------------------------------------------------------
// Analysis list item
// -----------------------------------------------------------

function AnalysisListItem({
  analysis,
  onClick,
}: {
  analysis: Analysis;
  onClick: () => void;
}) {
  const criticalCount = analysis.findings.filter(f => f.severity === 'critical').length;
  const majorCount = analysis.findings.filter(f => f.severity === 'major').length;

  return (
    <button
      onClick={onClick}
      className="card w-full text-left p-4 flex items-center gap-4 hover:shadow-[var(--shadow-elevated)] transition-shadow group"
    >
      <div className="w-8 h-8 rounded-lg bg-surface-100 flex items-center justify-center shrink-0">
        <FileText className="w-4 h-4 text-surface-500" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-surface-900 truncate group-hover:text-brand-600 transition-colors">
          {analysis.name}
        </p>
        <p className="text-xs text-surface-400 mt-0.5 flex items-center gap-2">
          <span>{getSourceTypeLabel(analysis.sourceType)}</span>
          <span>·</span>
          <span>{formatRelativeTime(analysis.createdAt)}</span>
          {analysis.findings.length > 0 && (
            <>
              <span>·</span>
              <span>
                {criticalCount > 0 && <span className={cn('font-medium', getSeverityColor('critical'))}>{criticalCount} critical</span>}
                {criticalCount > 0 && majorCount > 0 && ', '}
                {majorCount > 0 && <span className={cn('font-medium', getSeverityColor('major'))}>{majorCount} major</span>}
                {criticalCount === 0 && majorCount === 0 && `${analysis.findings.length} findings`}
              </span>
            </>
          )}
        </p>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <span className={getStatusClass(analysis.status)}>
          {getStatusLabel(analysis.status)}
        </span>
        <ChevronRight className="w-4 h-4 text-surface-300 group-hover:text-brand-500 transition-colors" />
      </div>
    </button>
  );
}
