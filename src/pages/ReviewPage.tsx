// ============================================================
// Analysis Review Page
// Findings workspace + Selective correction + Feedback
// ============================================================

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  CheckSquare,
  Square,
  Copy,
  Download,
  Edit3,
  CheckCircle2,
  AlertCircle,
  Loader2,
  RotateCcw,
  MessageSquare,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Filter,
  X,
} from 'lucide-react';
import * as Tabs from '@radix-ui/react-tabs';
import type {
  Finding,
  FindingCategory,
  FindingSeverity,
  FindingFeedback,
  FeedbackCategory,
} from '@/types/domain';
import { analysisService, historyService, feedbackService } from '@/services/demo';
import { useApp } from '@/context/AppContext';
import { DemoAlert } from '@/components/ui/DemoBanner';
import { SeverityBadge, CategoryBadge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import {
  getCategoryLabel,
  getSeverityLabel,
  SEVERITY_ORDER,
  copyToClipboard,
  downloadTextFile,
  generateId,
  formatDateTime,
  getFeedbackLabel,
} from '@/lib/utils';
import { cn } from '@/lib/utils';

const ALL_CATEGORIES: FindingCategory[] = [
  'grammar', 'spelling', 'punctuation', 'style', 'clarity',
  'brand_voice', 'terminology', 'prohibited', 'readability', 'other',
];

const ALL_SEVERITIES: FindingSeverity[] = ['critical', 'major', 'minor', 'info'];

// ============================================================
// Main Review Page
// ============================================================

export function ReviewPage() {
  const navigate = useNavigate();
  const { currentAnalysis, updateCurrentAnalysis, feedbackMap, setFeedbackForFinding, addToast } = useApp();

  // Correction state
  const [isApplying, setIsApplying] = useState(false);
  const [correctedContent, setCorrectedContent] = useState<string | null>(
    currentAnalysis?.correctedContent ?? null
  );
  const [editedContent, setEditedContent] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [conflictedIds, setConflictedIds] = useState<string[]>([]);

  // Filters
  const [filterCategories, setFilterCategories] = useState<FindingCategory[]>([]);
  const [filterSeverities, setFilterSeverities] = useState<FindingSeverity[]>([]);
  const [showFilters, setShowFilters] = useState(false);

  // UI state
  const [activeTab, setActiveTab] = useState<'findings' | 'corrected' | 'feedback'>('findings');
  const [expandedFindingId, setExpandedFindingId] = useState<string | null>(null);
  const [resetDialogOpen, setResetDialogOpen] = useState(false);

  // Load saved feedback
  const analysisId = currentAnalysis?.id;
  useEffect(() => {
    if (!analysisId) return;
    feedbackService.getForAnalysis(analysisId).then(savedFeedback => {
      savedFeedback.forEach(fb => setFeedbackForFinding(fb.findingId, fb));
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [analysisId]);

  // Sync corrected content from analysis (initializes local state from saved analysis)
  const savedCorrectedContent = currentAnalysis?.correctedContent;
  useEffect(() => {
    if (savedCorrectedContent && !correctedContent) {
      setCorrectedContent(savedCorrectedContent);
      setEditedContent(savedCorrectedContent);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [savedCorrectedContent]);

  if (!currentAnalysis) {
    return (
      <div className="max-w-2xl mx-auto">
        <EmptyState
          title="No analysis selected"
          description="Return to the dashboard or history to open an analysis."
          action={
            <button onClick={() => navigate('/')} className="btn-primary">
              <ArrowLeft className="w-4 h-4" />
              Back to Overview
            </button>
          }
        />
      </div>
    );
  }

  const { findings, selectedFindingIds, originalContent } = currentAnalysis;

  // Filtered findings
  const filteredFindings = findings
    .filter(f => filterCategories.length === 0 || filterCategories.includes(f.category))
    .filter(f => filterSeverities.length === 0 || filterSeverities.includes(f.severity))
    .sort((a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity]);

  const selectedFindings = findings.filter(f => selectedFindingIds.includes(f.id));
  const feedbackCount = Object.keys(feedbackMap).length;
  const totalFindings = findings.filter(f => f.category !== 'other' || f.rule !== 'Demo: No issues detected').length;

  // -----------------------------------------------------------
  // Selection handlers
  // -----------------------------------------------------------

  function toggleSelection(id: string) {
    const next = selectedFindingIds.includes(id)
      ? selectedFindingIds.filter(s => s !== id)
      : [...selectedFindingIds, id];
    updateCurrentAnalysis({ selectedFindingIds: next, reviewStatus: 'in_progress' });
  }

  function selectAll() {
    updateCurrentAnalysis({
      selectedFindingIds: filteredFindings.map(f => f.id),
      reviewStatus: 'in_progress',
    });
  }

  function deselectAll() {
    updateCurrentAnalysis({ selectedFindingIds: [] });
  }

  // -----------------------------------------------------------
  // Apply corrections
  // -----------------------------------------------------------

  async function handleApplyCorrections() {
    if (!currentAnalysis || selectedFindingIds.length === 0) return;
    setIsApplying(true);

    try {
      const result = await analysisService.correct({
        analysisId: currentAnalysis.id,
        selectedFindingIds,
        originalContent,
        findings,
      });

      setCorrectedContent(result.correctedContent);
      setEditedContent(result.correctedContent);
      setConflictedIds(result.conflictedFindingIds);

      const updated = {
        correctedContent: result.correctedContent,
        reviewStatus: 'corrections_applied' as const,
        updatedAt: new Date().toISOString(),
      };
      updateCurrentAnalysis(updated);
      await historyService.save({ ...currentAnalysis, ...updated } as import('@/types/domain').Analysis);

      setActiveTab('corrected');

      if (result.hasConflicts) {
        addToast({
          title: 'Corrections applied with notes',
          description: `${result.appliedFindingIds.length} applied. ${result.conflictedFindingIds.length} could not be applied automatically — please review the result.`,
          variant: 'warning',
        });
      } else {
        addToast({
          title: `${result.appliedFindingIds.length} correction${result.appliedFindingIds.length !== 1 ? 's' : ''} applied`,
          variant: 'success',
        });
      }
    } catch {
      addToast({ title: 'Failed to apply corrections', variant: 'error' });
    } finally {
      setIsApplying(false);
    }
  }

  // -----------------------------------------------------------
  // Copy / Download
  // -----------------------------------------------------------

  async function handleCopy() {
    const content = isEditing ? editedContent : correctedContent;
    if (!content) return;
    const ok = await copyToClipboard(content);
    addToast({ title: ok ? 'Copied to clipboard' : 'Copy failed', variant: ok ? 'success' : 'error' });
  }

  function handleDownload() {
    if (!currentAnalysis) return;
    const content = isEditing ? editedContent : correctedContent;
    if (!content) return;
    const name = currentAnalysis.name.replace(/[^a-z0-9_-]/gi, '_');
    downloadTextFile(content, `${name}_corrected.txt`);
    addToast({ title: 'Downloaded', variant: 'success' });
  }

  // -----------------------------------------------------------
  // Save edited content
  // -----------------------------------------------------------

  async function handleSaveEdit() {
    if (!editedContent || !currentAnalysis) return;
    updateCurrentAnalysis({ correctedContent: editedContent });
    await historyService.save({ ...currentAnalysis, correctedContent: editedContent } as import('@/types/domain').Analysis);
    setCorrectedContent(editedContent);
    setIsEditing(false);
    addToast({ title: 'Changes saved', variant: 'success' });
  }

  // -----------------------------------------------------------
  // Reset
  // -----------------------------------------------------------

  function handleReset() {
    setCorrectedContent(null);
    setEditedContent(null);
    setConflictedIds([]);
    setIsEditing(false);
    setActiveTab('findings');
    updateCurrentAnalysis({
      selectedFindingIds: [],
      correctedContent: undefined,
      reviewStatus: 'not_started',
    });
  }

  // -----------------------------------------------------------
  // Render
  // -----------------------------------------------------------

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/history')}
            className="btn-ghost p-2"
            aria-label="Back to history"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <h2 className="page-title text-xl">{currentAnalysis.name}</h2>
            <p className="text-xs text-surface-400 mt-0.5">
              {formatDateTime(currentAnalysis.createdAt)} · {findings.length} finding{findings.length !== 1 ? 's' : ''}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {correctedContent && (
            <button onClick={() => setResetDialogOpen(true)} className="btn-ghost text-sm">
              <RotateCcw className="w-4 h-4" />
              Reset
            </button>
          )}
        </div>
      </div>

      <DemoAlert />

      {/* Main tabs */}
      <Tabs.Root value={activeTab} onValueChange={v => setActiveTab(v as typeof activeTab)}>
        <Tabs.List className="flex gap-1 bg-surface-100 rounded-xl p-1 w-fit">
          {[
            { value: 'findings', label: `Findings (${totalFindings})`, icon: <AlertCircle className="w-3.5 h-3.5" /> },
            { value: 'corrected', label: 'Corrected', icon: <CheckCircle2 className="w-3.5 h-3.5" />, disabled: !correctedContent },
            { value: 'feedback', label: `Feedback (${feedbackCount}/${findings.length})`, icon: <MessageSquare className="w-3.5 h-3.5" /> },
          ].map(tab => (
            <Tabs.Trigger
              key={tab.value}
              value={tab.value}
              disabled={tab.disabled}
              className={cn(
                'flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-sm font-medium transition-colors',
                activeTab === tab.value
                  ? 'bg-white text-surface-900 shadow-[var(--shadow-card)]'
                  : 'text-surface-500 hover:text-surface-700 disabled:opacity-40 disabled:cursor-not-allowed'
              )}
            >
              {tab.icon}
              <span className="hidden sm:inline">{tab.label}</span>
              <span className="sm:hidden">{tab.label.split(' ')[0]}</span>
            </Tabs.Trigger>
          ))}
        </Tabs.List>

        {/* ============================================================ */}
        {/* FINDINGS TAB */}
        {/* ============================================================ */}
        <Tabs.Content value="findings" className="mt-5">
          <div className="grid lg:grid-cols-3 gap-5">
            {/* Findings list */}
            <div className="lg:col-span-2 space-y-3">
              {/* Toolbar */}
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <button
                    onClick={showFilters ? () => setShowFilters(false) : () => setShowFilters(true)}
                    className={cn('btn-ghost text-sm', showFilters && 'bg-surface-100')}
                  >
                    <Filter className="w-3.5 h-3.5" />
                    Filter
                    {(filterCategories.length + filterSeverities.length) > 0 && (
                      <span className="w-4 h-4 rounded-full bg-brand-600 text-white text-xs flex items-center justify-center">
                        {filterCategories.length + filterSeverities.length}
                      </span>
                    )}
                  </button>
                  {(filterCategories.length + filterSeverities.length) > 0 && (
                    <button
                      onClick={() => { setFilterCategories([]); setFilterSeverities([]); }}
                      className="text-xs text-surface-500 hover:text-surface-700"
                    >
                      Clear filters
                    </button>
                  )}
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <button onClick={selectAll} className="text-brand-600 hover:text-brand-700 text-xs font-medium">Select all</button>
                  <span className="text-surface-300">·</span>
                  <button onClick={deselectAll} className="text-surface-500 hover:text-surface-700 text-xs font-medium">None</button>
                </div>
              </div>

              {/* Filter panel */}
              {showFilters && (
                <div className="card p-4 space-y-3">
                  <div>
                    <p className="text-xs font-medium text-surface-500 mb-2">SEVERITY</p>
                    <div className="flex flex-wrap gap-2">
                      {ALL_SEVERITIES.map(s => (
                        <button
                          key={s}
                          onClick={() => setFilterSeverities(prev =>
                            prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s]
                          )}
                          className={cn(
                            'px-2.5 py-1 rounded-full text-xs font-medium border transition-colors',
                            filterSeverities.includes(s)
                              ? 'bg-navy-700 text-white border-navy-700'
                              : 'bg-white text-surface-600 border-surface-200 hover:border-surface-300'
                          )}
                        >
                          {getSeverityLabel(s)}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-surface-500 mb-2">CATEGORY</p>
                    <div className="flex flex-wrap gap-2">
                      {ALL_CATEGORIES.filter(c => findings.some(f => f.category === c)).map(c => (
                        <button
                          key={c}
                          onClick={() => setFilterCategories(prev =>
                            prev.includes(c) ? prev.filter(x => x !== c) : [...prev, c]
                          )}
                          className={cn(
                            'px-2.5 py-1 rounded-full text-xs font-medium border transition-colors',
                            filterCategories.includes(c)
                              ? 'bg-navy-700 text-white border-navy-700'
                              : 'bg-white text-surface-600 border-surface-200 hover:border-surface-300'
                          )}
                        >
                          {getCategoryLabel(c)}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Finding cards */}
              {filteredFindings.length === 0 ? (
                <div className="card">
                  <EmptyState
                    icon={<CheckCircle2 className="w-5 h-5" />}
                    title={findings.length === 0 ? 'No issues detected' : 'No findings match filters'}
                    description={findings.length === 0 ? 'The content passed all available checks.' : 'Try clearing the filters to see all findings.'}
                  />
                </div>
              ) : (
                <div className="space-y-2">
                  {filteredFindings.map(finding => (
                    <FindingCard
                      key={finding.id}
                      finding={finding}
                      selected={selectedFindingIds.includes(finding.id)}
                      expanded={expandedFindingId === finding.id}
                      onToggleSelect={() => toggleSelection(finding.id)}
                      onToggleExpand={() => setExpandedFindingId(
                        expandedFindingId === finding.id ? null : finding.id
                      )}
                      hasConflict={conflictedIds.includes(finding.id)}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Correction sidebar */}
            <div className="space-y-4">
              <div className="card p-4 space-y-4">
                <div>
                  <h3 className="text-sm font-semibold text-surface-800">Apply Corrections</h3>
                  <p className="text-xs text-surface-500 mt-1">
                    Select findings above, then apply them to generate corrected content.
                  </p>
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between text-xs">
                    <span className="text-surface-500">Selected</span>
                    <span className="font-medium text-surface-800">{selectedFindingIds.length} of {findings.length}</span>
                  </div>
                  {/* Progress bar */}
                  <div className="h-1.5 bg-surface-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-brand-500 rounded-full transition-all duration-300"
                      style={{ width: findings.length > 0 ? `${(selectedFindingIds.length / findings.length) * 100}%` : '0%' }}
                    />
                  </div>
                </div>

                <button
                  onClick={handleApplyCorrections}
                  disabled={selectedFindingIds.length === 0 || isApplying}
                  className="btn-primary w-full"
                >
                  {isApplying
                    ? <><Loader2 className="w-4 h-4 animate-spin" /> Applying…</>
                    : <><CheckSquare className="w-4 h-4" /> Apply {selectedFindingIds.length} Correction{selectedFindingIds.length !== 1 ? 's' : ''}</>
                  }
                </button>

                {correctedContent && (
                  <button
                    onClick={() => setActiveTab('corrected')}
                    className="btn-secondary w-full text-sm"
                  >
                    View Corrected Content
                    <ChevronRight className="w-4 h-4" />
                  </button>
                )}
              </div>

              {/* Feedback progress */}
              <div className="card p-4 space-y-3">
                <h3 className="text-sm font-semibold text-surface-800">Feedback</h3>
                <div className="space-y-1.5">
                  {findings.map(f => {
                    const fb = feedbackMap[f.id];
                    return (
                      <div key={f.id} className="flex items-center gap-2">
                        <div className={cn('w-2 h-2 rounded-full shrink-0', fb ? 'bg-green-500' : 'bg-surface-200')} />
                        <p className="text-xs text-surface-600 truncate flex-1">{f.originalExcerpt}</p>
                        {fb && <span className="text-xs text-green-600 font-medium shrink-0">{getFeedbackLabel(fb.category).split(' ')[0]}</span>}
                      </div>
                    );
                  })}
                </div>
                <button
                  onClick={() => setActiveTab('feedback')}
                  className="btn-secondary w-full text-xs"
                >
                  <MessageSquare className="w-3.5 h-3.5" />
                  Provide Feedback
                </button>
              </div>
            </div>
          </div>
        </Tabs.Content>

        {/* ============================================================ */}
        {/* CORRECTED CONTENT TAB */}
        {/* ============================================================ */}
        <Tabs.Content value="corrected" className="mt-5">
          {correctedContent ? (
            <div className="space-y-4">
              {/* Toolbar */}
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-semibold text-surface-800">Corrected Content</h3>
                  {conflictedIds.length > 0 && (
                    <span className="badge-minor">
                      {conflictedIds.length} manual review needed
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {isEditing ? (
                    <>
                      <button onClick={() => { setIsEditing(false); setEditedContent(correctedContent); }} className="btn-ghost text-sm">
                        <X className="w-4 h-4" />
                        Cancel
                      </button>
                      <button onClick={handleSaveEdit} className="btn-primary text-sm">
                        <CheckCircle2 className="w-4 h-4" />
                        Save
                      </button>
                    </>
                  ) : (
                    <>
                      <button onClick={() => setIsEditing(true)} className="btn-ghost text-sm">
                        <Edit3 className="w-4 h-4" />
                        Edit
                      </button>
                      <button onClick={handleCopy} className="btn-ghost text-sm">
                        <Copy className="w-4 h-4" />
                        Copy
                      </button>
                      <button onClick={handleDownload} className="btn-secondary text-sm">
                        <Download className="w-4 h-4" />
                        Download
                      </button>
                    </>
                  )}
                </div>
              </div>

              {/* Content comparison */}
              <div className="grid lg:grid-cols-2 gap-4">
                <div className="card p-4 space-y-2">
                  <p className="text-xs font-medium text-surface-500 uppercase tracking-wide">Original</p>
                  <div className="text-sm text-surface-700 leading-relaxed whitespace-pre-wrap max-h-[500px] overflow-y-auto">
                    {originalContent}
                  </div>
                </div>

                <div className="card p-4 space-y-2 border-brand-200">
                  <p className="text-xs font-medium text-brand-600 uppercase tracking-wide">Corrected</p>
                  {isEditing ? (
                    <textarea
                      className="textarea-field w-full min-h-[400px] text-sm leading-relaxed font-mono"
                      value={editedContent ?? correctedContent}
                      onChange={e => setEditedContent(e.target.value)}
                      aria-label="Editable corrected content"
                    />
                  ) : (
                    <div className="text-sm text-surface-700 leading-relaxed whitespace-pre-wrap max-h-[500px] overflow-y-auto">
                      {editedContent ?? correctedContent}
                    </div>
                  )}
                </div>
              </div>

              {/* Applied findings summary */}
              <div className="card p-4">
                <p className="text-xs font-medium text-surface-500 mb-3">APPLIED CORRECTIONS</p>
                <div className="space-y-2">
                  {selectedFindings.map(f => (
                    <div key={f.id} className={cn(
                      'flex items-start gap-2.5 text-xs py-1.5',
                      conflictedIds.includes(f.id) ? 'opacity-60' : ''
                    )}>
                      {conflictedIds.includes(f.id)
                        ? <AlertCircle className="w-3.5 h-3.5 text-amber-500 shrink-0 mt-0.5" />
                        : <CheckCircle2 className="w-3.5 h-3.5 text-green-500 shrink-0 mt-0.5" />
                      }
                      <div className="min-w-0">
                        <span className="line-through text-surface-400 mr-2">{f.originalExcerpt}</span>
                        <span className="text-surface-700">→ {f.suggestedCorrection}</span>
                        {conflictedIds.includes(f.id) && (
                          <span className="text-amber-600 ml-2">(review manually)</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="card">
              <EmptyState
                icon={<CheckSquare className="w-5 h-5" />}
                title="No corrections applied yet"
                description="Select findings in the Findings tab and apply corrections."
                action={
                  <button onClick={() => setActiveTab('findings')} className="btn-primary text-sm">
                    Go to Findings
                  </button>
                }
              />
            </div>
          )}
        </Tabs.Content>

        {/* ============================================================ */}
        {/* FEEDBACK TAB */}
        {/* ============================================================ */}
        <Tabs.Content value="feedback" className="mt-5">
          <FeedbackTab
            findings={findings}
            analysisId={currentAnalysis.id}
            originalContent={originalContent}
            feedbackMap={feedbackMap}
            onFeedbackSaved={(findingId, fb) => setFeedbackForFinding(findingId, fb)}
            addToast={addToast}
          />
        </Tabs.Content>
      </Tabs.Root>

      {/* Reset dialog */}
      <ConfirmDialog
        open={resetDialogOpen}
        onOpenChange={setResetDialogOpen}
        title="Reset corrections"
        description="This will clear the corrected content and reset all selections. The original content is preserved."
        confirmLabel="Reset"
        cancelLabel="Keep"
        variant="danger"
        onConfirm={handleReset}
      />
    </div>
  );
}

// ============================================================
// Finding Card Component
// ============================================================

interface FindingCardProps {
  finding: Finding;
  selected: boolean;
  expanded: boolean;
  onToggleSelect: () => void;
  onToggleExpand: () => void;
  hasConflict: boolean;
}

function FindingCard({ finding, selected, expanded, onToggleSelect, onToggleExpand, hasConflict }: FindingCardProps) {
  return (
    <div
      className={cn(
        'card transition-all duration-150',
        selected ? 'border-brand-300 ring-1 ring-brand-200' : '',
        hasConflict ? 'border-amber-300' : ''
      )}
    >
      {/* Card header */}
      <div className="flex items-start gap-3 p-4">
        {/* Checkbox */}
        <button
          onClick={onToggleSelect}
          className="mt-0.5 shrink-0 text-surface-400 hover:text-brand-600 transition-colors"
          aria-label={selected ? 'Deselect finding' : 'Select finding'}
          aria-pressed={selected}
        >
          {selected
            ? <CheckSquare className="w-4.5 h-4.5 text-brand-600" />
            : <Square className="w-4.5 h-4.5" />
          }
        </button>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-2">
            <SeverityBadge severity={finding.severity} />
            <CategoryBadge category={finding.category} />
            {hasConflict && (
              <span className="badge-minor">Review manually</span>
            )}
          </div>

          {/* Excerpt */}
          <div className="flex items-start gap-2 text-sm">
            <span className="line-through text-surface-400 bg-red-50 px-1.5 py-0.5 rounded text-xs font-mono">
              {finding.originalExcerpt}
            </span>
            <ChevronRight className="w-4 h-4 text-surface-300 shrink-0 mt-0.5" />
            <span className="text-green-700 bg-green-50 px-1.5 py-0.5 rounded text-xs font-mono">
              {finding.suggestedCorrection}
            </span>
          </div>

          {/* Short explanation (always visible) */}
          {!expanded && (
            <p className="text-xs text-surface-500 mt-2 line-clamp-2">
              {finding.explanation}
            </p>
          )}
        </div>

        {/* Expand toggle */}
        <button
          onClick={onToggleExpand}
          className="btn-ghost p-1.5 shrink-0 text-surface-400"
          aria-label={expanded ? 'Collapse details' : 'Expand details'}
          aria-expanded={expanded}
        >
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="px-4 pb-4 border-t border-surface-100 pt-3 space-y-3">
          <div>
            <p className="text-xs font-medium text-surface-500 mb-1">EXPLANATION</p>
            <p className="text-sm text-surface-700 leading-relaxed">{finding.explanation}</p>
          </div>
          {finding.rule && (
            <div>
              <p className="text-xs font-medium text-surface-500 mb-1">RULE</p>
              <p className="text-xs text-surface-600 font-mono bg-surface-50 px-2 py-1 rounded">{finding.rule}</p>
            </div>
          )}
          <p className="text-xs text-amber-700 bg-amber-50 px-2.5 py-1.5 rounded border border-amber-100">
            ⚠ Demo result — generated by the demo engine, not a real AI model.
          </p>
        </div>
      )}
    </div>
  );
}

// ============================================================
// Feedback Tab Component
// ============================================================

const FEEDBACK_OPTIONS: { value: FeedbackCategory; label: string; description: string }[] = [
  { value: 'genuine_error', label: 'Genuine Error', description: 'This is a real mistake that should be corrected.' },
  { value: 'false_positive', label: 'False Positive', description: 'This is not actually an issue.' },
  { value: 'stylistic_choice', label: 'Stylistic Choice', description: 'This is intentional and acceptable in context.' },
  { value: 'unsure', label: 'Unsure', description: 'I am not certain — needs review.' },
];

interface FeedbackTabProps {
  findings: Finding[];
  analysisId: string;
  originalContent: string;
  feedbackMap: Record<string, FindingFeedback>;
  onFeedbackSaved: (findingId: string, feedback: FindingFeedback) => void;
  addToast: (toast: { title: string; variant: 'success' | 'error' | 'warning' | 'info'; description?: string }) => void;
}

function FeedbackTab({ findings, analysisId, originalContent, feedbackMap, onFeedbackSaved, addToast }: FeedbackTabProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="section-title">Finding Feedback</h3>
          <p className="text-xs text-surface-500 mt-0.5">
            Classify each finding to help improve future analysis quality.
          </p>
        </div>
        <span className="badge-neutral">
          {Object.keys(feedbackMap).length} of {findings.length} reviewed
        </span>
      </div>

      {findings.length === 0 ? (
        <div className="card">
          <EmptyState
            title="No findings to review"
            description="Findings appear after running an analysis."
          />
        </div>
      ) : (
        <div className="space-y-4">
          {findings.map(finding => (
            <FeedbackCard
              key={finding.id}
              finding={finding}
              analysisId={analysisId}
              originalContent={originalContent}
              existingFeedback={feedbackMap[finding.id] ?? null}
              onSaved={(fb) => onFeedbackSaved(finding.id, fb)}
              addToast={addToast}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ============================================================
// Individual Feedback Card
// ============================================================

interface FeedbackCardProps {
  finding: Finding;
  analysisId: string;
  originalContent: string;
  existingFeedback: FindingFeedback | null;
  onSaved: (feedback: FindingFeedback) => void;
  addToast: (toast: { title: string; variant: 'success' | 'error' | 'warning' | 'info' }) => void;
}

function FeedbackCard({ finding, analysisId, originalContent, existingFeedback, onSaved, addToast }: FeedbackCardProps) {
  const [selected, setSelected] = useState<FeedbackCategory | null>(existingFeedback?.category ?? null);
  const [comment, setComment] = useState(existingFeedback?.comment ?? '');
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(!existingFeedback);

  async function handleSubmit() {
    if (!selected) return;
    setSaving(true);
    try {
      const fb: FindingFeedback = {
        id: existingFeedback?.id ?? generateId(),
        analysisId,
        findingId: finding.id,
        originalContent,
        category: selected,
        comment: comment.trim() || undefined,
        submittedAt: existingFeedback?.submittedAt ?? new Date().toISOString(),
        updatedAt: existingFeedback ? new Date().toISOString() : undefined,
      };
      await feedbackService.save(fb);
      onSaved(fb);
      setEditing(false);
      addToast({ title: 'Feedback saved', variant: 'success' });
    } catch {
      addToast({ title: 'Failed to save feedback', variant: 'error' });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className={cn('card p-4 space-y-3', existingFeedback && !editing ? 'bg-surface-50/50' : '')}>
      {/* Finding summary */}
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1.5">
            <SeverityBadge severity={finding.severity} />
            <CategoryBadge category={finding.category} />
            {existingFeedback && !editing && (
              <span className="badge-success">Reviewed</span>
            )}
          </div>
          <p className="text-xs text-surface-500 font-mono">
            <span className="line-through text-surface-400">{finding.originalExcerpt}</span>
            {' → '}
            <span className="text-green-700">{finding.suggestedCorrection}</span>
          </p>
          <p className="text-xs text-surface-600 mt-1.5 leading-relaxed">{finding.explanation}</p>
        </div>

        {existingFeedback && !editing && (
          <button
            onClick={() => setEditing(true)}
            className="btn-ghost text-xs shrink-0"
          >
            Edit
          </button>
        )}
      </div>

      {/* Feedback options */}
      {editing && (
        <>
          <div className="grid grid-cols-2 gap-2">
            {FEEDBACK_OPTIONS.map(opt => (
              <button
                key={opt.value}
                onClick={() => setSelected(opt.value)}
                className={cn(
                  'flex flex-col items-start p-3 rounded-lg border text-left transition-colors',
                  selected === opt.value
                    ? 'border-brand-500 bg-brand-50 text-brand-800'
                    : 'border-surface-200 hover:border-surface-300 text-surface-700'
                )}
                aria-pressed={selected === opt.value}
              >
                <span className="text-xs font-semibold">{opt.label}</span>
                <span className="text-xs text-surface-500 mt-0.5">{opt.description}</span>
              </button>
            ))}
          </div>

          {/* Comment */}
          <div>
            <label className="label text-xs">Comment <span className="text-surface-400 font-normal">(optional)</span></label>
            <textarea
              className="textarea-field h-16 text-xs"
              placeholder="Add a note about this finding…"
              value={comment}
              onChange={e => setComment(e.target.value)}
              aria-label="Feedback comment"
            />
          </div>

          <div className="flex gap-2 justify-end">
            {existingFeedback && (
              <button onClick={() => setEditing(false)} className="btn-ghost text-sm">Cancel</button>
            )}
            <button
              onClick={handleSubmit}
              disabled={!selected || saving}
              className="btn-primary text-sm"
            >
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
              {existingFeedback ? 'Update' : 'Submit'} Feedback
            </button>
          </div>
        </>
      )}

      {/* Submitted feedback display */}
      {existingFeedback && !editing && (
        <div className="flex items-center gap-2 text-xs text-surface-500">
          <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
          <span>
            <span className="font-medium text-surface-700">{getFeedbackLabel(existingFeedback.category)}</span>
            {existingFeedback.comment && ` · "${existingFeedback.comment}"`}
          </span>
        </div>
      )}
    </div>
  );
}
