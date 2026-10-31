import { useState } from 'react';
import {
  Sparkles,
  CheckCircle2,
  XCircle,
  Edit3,
  RotateCcw,
  AlertTriangle,
  Loader2,
  Wand2,
  Check,
  X,
  PlusCircle,
} from 'lucide-react';
import type { Finding, UserImprovementSuggestion } from '@/types/domain';
import { userImprovementsService } from '@/services/demo';
import { cn } from '@/lib/utils';

interface ImprovementsTabProps {
  originalContent: string;
  analysisId?: string;
  existingFindings?: Finding[];
  context?: {
    contentType?: string;
    targetAudience?: string;
    language?: string;
    writingInstructions?: string;
  };
  onApplySuccess: (finalContent: string) => void;
  addToast: (toast: { title: string; description?: string; variant: 'success' | 'error' | 'warning' | 'info' }) => void;
}

const PRESET_INSTRUCTIONS = [
  { label: 'Executive Tone', text: 'Make this copy authoritative, polished, and suitable for enterprise decision-makers.' },
  { label: 'Concise & Punchy', text: 'Trim unnecessary filler and make the sentences punchy without losing factual points.' },
  { label: 'High Persuasion', text: 'Strengthen the value proposition and emphasize compelling customer outcomes.' },
  { label: 'Clarity & Flow', text: 'Simplify convoluted sentences and ensure smooth transitions between ideas.' },
  { label: 'Action-Oriented', text: 'Incorporate vibrant active verbs and a clearer, more direct call-to-action.' },
];

export function ImprovementsTab({
  originalContent,
  analysisId,
  existingFindings = [],
  context = {},
  onApplySuccess,
  addToast,
}: ImprovementsTabProps) {
  const [instructions, setInstructions] = useState('');
  const [suggestions, setSuggestions] = useState<UserImprovementSuggestion[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState('');
  const [conflicts, setConflicts] = useState<Array<{ suggestion_id?: string; original_text?: string; reason?: string }>>([]);

  const acceptedCount = suggestions.filter(s => s.status === 'accepted').length;
  const pendingCount = suggestions.filter(s => s.status === 'pending').length;
  const rejectedCount = suggestions.filter(s => s.status === 'rejected').length;

  const handleGenerate = async () => {
    if (!instructions.trim()) {
      addToast({
        variant: 'error',
        title: 'Instructions required',
        description: 'Please provide instructions or select a preset before generating suggestions.',
      });
      return;
    }

    setIsGenerating(true);
    setConflicts([]);
    try {
      const findingsPayload = existingFindings.map(f => ({
        id: f.id,
        category: f.category,
        original_text: f.originalExcerpt,
        suggestion: f.suggestedCorrection,
        explanation: f.explanation,
      }));

      const res = await userImprovementsService.generate({
        originalContent,
        userInstructions: instructions.trim(),
        existingFindings: findingsPayload,
        context: {
          content_type: context.contentType || 'Marketing Copy',
          target_audience: context.targetAudience || 'Business Professionals',
          language: context.language || 'English',
        },
        analysisId,
      });

      if (res.status === 'success') {
        setSuggestions(res.suggestions || []);
        addToast({
          variant: 'success',
          title: 'Suggestions generated',
          description: `Generated ${res.suggestions?.length || 0} personalized improvement proposals.`,
        });
      } else {
        throw new Error(res.message || 'Failed to generate suggestions.');
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Suggestion generation failed';
      addToast({
        variant: 'error',
        title: 'Generation failed',
        description: msg,
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const handleRegenerate = async () => {
    if (!instructions.trim()) {
      addToast({
        variant: 'error',
        title: 'Instructions required',
        description: 'Please enter updated instructions to regenerate suggestions.',
      });
      return;
    }

    setIsGenerating(true);
    setConflicts([]);
    try {
      const findingsPayload = existingFindings.map(f => ({
        id: f.id,
        category: f.category,
        original_text: f.originalExcerpt,
        suggestion: f.suggestedCorrection,
        explanation: f.explanation,
      }));

      const res = await userImprovementsService.regenerate({
        originalContent,
        newInstructions: instructions.trim(),
        previousSuggestions: suggestions,
        existingFindings: findingsPayload,
        context: {
          content_type: context.contentType || 'Marketing Copy',
          target_audience: context.targetAudience || 'Business Professionals',
          language: context.language || 'English',
        },
        analysisId,
      });

      if (res.status === 'success') {
        // Keep accepted previous suggestions, append or update fresh ones
        const keptPrevious = suggestions.filter(s => s.status === 'accepted');
        setSuggestions([...keptPrevious, ...(res.suggestions || [])]);
        addToast({
          variant: 'success',
          title: 'Fresh suggestions generated',
          description: `Produced ${res.suggestions?.length || 0} fresh suggestions while preserving your accepted edits.`,
        });
      } else {
        throw new Error(res.message || 'Regeneration failed.');
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Regeneration failed';
      addToast({
        variant: 'error',
        title: 'Regeneration failed',
        description: msg,
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const handleAccept = (id: string) => {
    setSuggestions(prev =>
      prev.map(s => (s.id === id ? { ...s, status: 'accepted' as const } : s))
    );
  };

  const handleReject = (id: string) => {
    setSuggestions(prev =>
      prev.map(s => (s.id === id ? { ...s, status: 'rejected' as const } : s))
    );
  };

  const handleResetStatus = (id: string) => {
    setSuggestions(prev =>
      prev.map(s => (s.id === id ? { ...s, status: 'pending' as const } : s))
    );
  };

  const startEdit = (suggestion: UserImprovementSuggestion) => {
    setEditingId(suggestion.id);
    setEditText(suggestion.suggested_text);
  };

  const saveEdit = (id: string) => {
    if (!editText.trim()) return;
    setSuggestions(prev =>
      prev.map(s => (s.id === id ? { ...s, suggested_text: editText.trim() } : s))
    );
    setEditingId(null);
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditText('');
  };

  const handleAcceptAll = () => {
    setSuggestions(prev =>
      prev.map(s => (s.status === 'pending' ? { ...s, status: 'accepted' as const } : s))
    );
  };

  const handleApply = async () => {
    if (acceptedCount === 0) {
      addToast({
        variant: 'info',
        title: 'No accepted suggestions',
        description: 'Accept at least one suggestion before applying improvements.',
      });
      return;
    }

    setIsApplying(true);
    setConflicts([]);
    try {
      const res = await userImprovementsService.apply({
        originalContent,
        suggestions,
        analysisId,
        saveHistory: true,
      });

      if (res.conflicts && res.conflicts.length > 0) {
        setConflicts(res.conflicts);
        addToast({
          variant: 'warning',
          title: 'Applied with warnings',
          description: `${res.applied_suggestions.length} suggestions applied; ${res.conflicts.length} conflicted or overlapping suggestions skipped.`,
        });
      } else {
        addToast({
          variant: 'success',
          title: 'Improvements applied',
          description: `Successfully applied ${res.applied_suggestions.length} improvements and synced with database history.`,
        });
      }

      onApplySuccess(res.final_content);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Application failed';
      addToast({
        variant: 'error',
        title: 'Application failed',
        description: msg,
      });
    } finally {
      setIsApplying(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Input guidance header card */}
      <div className="card p-5 border border-surface-200 bg-white">
        <div className="flex items-center gap-2 mb-2">
          <Sparkles className="w-4 h-4 text-brand-600" />
          <h3 className="text-base font-semibold text-surface-900">User-Driven Content Improvements</h3>
        </div>
        <p className="text-xs text-surface-500 mb-4">
          Provide your custom instructions below to personalize tone, clarity, conciseness, or brand impact.
          Gemini will generate selective, non-destructive suggestions for you to accept, reject, or edit individually.
        </p>

        {/* Preset chips */}
        <div className="flex flex-wrap gap-1.5 mb-3">
          {PRESET_INSTRUCTIONS.map(preset => (
            <button
              key={preset.label}
              type="button"
              onClick={() => setInstructions(preset.text)}
              className="text-xs px-2.5 py-1 rounded-full bg-surface-100 hover:bg-brand-50 hover:text-brand-700 text-surface-700 border border-surface-200 transition-colors"
            >
              + {preset.label}
            </button>
          ))}
        </div>

        {/* User instructions textarea */}
        <div className="relative">
          <textarea
            value={instructions}
            onChange={e => setInstructions(e.target.value)}
            placeholder="e.g. Make this copy more persuasive, concise, and professional for enterprise prospects..."
            rows={3}
            className="w-full text-sm p-3 rounded-lg border border-surface-300 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 outline-none resize-none"
          />
        </div>

        {/* Action buttons */}
        <div className="flex items-center justify-between gap-3 mt-3">
          <div className="text-xs text-surface-500 flex items-center gap-2">
            <span>Content length: {originalContent.length} chars</span>
            {existingFindings.length > 0 && (
              <span>• Incorporating {existingFindings.length} prior findings</span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {suggestions.length > 0 && (
              <button
                type="button"
                onClick={handleRegenerate}
                disabled={isGenerating || isApplying}
                className="btn-ghost text-xs flex items-center gap-1.5"
              >
                {isGenerating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RotateCcw className="w-3.5 h-3.5" />}
                Regenerate
              </button>
            )}
            <button
              type="button"
              onClick={handleGenerate}
              disabled={isGenerating || isApplying}
              className="btn-primary text-xs flex items-center gap-1.5"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Generating Suggestions...
                </>
              ) : (
                <>
                  <Wand2 className="w-3.5 h-3.5" />
                  Generate Improvement Suggestions
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Conflicts warning alert */}
      {conflicts.length > 0 && (
        <div className="p-4 rounded-xl border border-amber-300 bg-amber-50 text-amber-900 text-xs space-y-1">
          <div className="flex items-center gap-2 font-semibold text-amber-800">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
            <span>Overlap or Match Conflicts Detected ({conflicts.length})</span>
          </div>
          <p className="text-amber-700">
            The following suggestions were safely skipped to prevent overwriting conflicting changes:
          </p>
          <ul className="list-disc list-inside mt-1 space-y-0.5 text-amber-800">
            {conflicts.map((c, i) => (
              <li key={i}>
                <span className="font-medium">{c.suggestion_id || 'Suggestion'}:</span> {c.reason}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Suggestions Workspace */}
      {suggestions.length > 0 && (
        <div className="space-y-4">
          {/* Header toolbar */}
          <div className="flex items-center justify-between gap-3 bg-surface-50 p-3 rounded-xl border border-surface-200">
            <div className="flex items-center gap-3 text-xs font-medium">
              <span className="text-surface-700 font-semibold">Proposals ({suggestions.length})</span>
              <span className="text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-full">{acceptedCount} Accepted</span>
              <span className="text-amber-700 bg-amber-100 px-2 py-0.5 rounded-full">{pendingCount} Pending</span>
              <span className="text-surface-600 bg-surface-200 px-2 py-0.5 rounded-full">{rejectedCount} Rejected</span>
            </div>

            <div className="flex items-center gap-2">
              {pendingCount > 0 && (
                <button
                  type="button"
                  onClick={handleAcceptAll}
                  className="btn-ghost text-xs flex items-center gap-1 text-surface-600 hover:text-surface-900"
                >
                  <PlusCircle className="w-3.5 h-3.5" />
                  Accept All Pending
                </button>
              )}
              <button
                type="button"
                onClick={handleApply}
                disabled={isApplying || acceptedCount === 0}
                className="btn-primary text-xs flex items-center gap-1.5 shadow-sm"
              >
                {isApplying ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    Applying...
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Apply {acceptedCount} Accepted {acceptedCount === 1 ? 'Edit' : 'Edits'}
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Cards List */}
          <div className="grid gap-3">
            {suggestions.map((s, idx) => (
              <div
                key={s.id || idx}
                className={cn(
                  'card p-4 border transition-all duration-150',
                  s.status === 'accepted' ? 'border-emerald-300 bg-emerald-50/20 ring-1 ring-emerald-200' : '',
                  s.status === 'rejected' ? 'border-surface-200 bg-surface-50/50 opacity-60' : '',
                  s.status === 'pending' ? 'border-surface-200 bg-white' : ''
                )}
              >
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-brand-100 text-brand-700">
                      {s.category}
                    </span>
                    <span className="text-xs font-mono text-surface-400">#{s.id}</span>
                  </div>

                  <div className="flex items-center gap-1">
                    {s.status === 'pending' && (
                      <>
                        <button
                          type="button"
                          onClick={() => handleAccept(s.id)}
                          className="px-2.5 py-1 text-xs rounded-md bg-emerald-600 text-white hover:bg-emerald-700 flex items-center gap-1 font-medium transition-colors"
                          title="Accept suggestion"
                        >
                          <Check className="w-3 h-3" />
                          Accept
                        </button>
                        <button
                          type="button"
                          onClick={() => startEdit(s)}
                          className="px-2 py-1 text-xs rounded-md border border-surface-300 text-surface-700 hover:bg-surface-100 flex items-center gap-1 font-medium transition-colors"
                          title="Edit suggested replacement"
                        >
                          <Edit3 className="w-3 h-3" />
                          Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => handleReject(s.id)}
                          className="px-2 py-1 text-xs rounded-md border border-surface-300 text-rose-600 hover:bg-rose-50 flex items-center gap-1 font-medium transition-colors"
                          title="Reject suggestion"
                        >
                          <X className="w-3 h-3" />
                          Reject
                        </button>
                      </>
                    )}

                    {s.status === 'accepted' && (
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-emerald-700 flex items-center gap-1">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Accepted
                        </span>
                        <button
                          type="button"
                          onClick={() => startEdit(s)}
                          className="text-xs text-surface-500 hover:text-surface-700 underline"
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => handleResetStatus(s.id)}
                          className="text-xs text-surface-500 hover:text-surface-700 underline"
                        >
                          Undo
                        </button>
                      </div>
                    )}

                    {s.status === 'rejected' && (
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-surface-500 flex items-center gap-1">
                          <XCircle className="w-3.5 h-3.5" /> Rejected
                        </span>
                        <button
                          type="button"
                          onClick={() => handleResetStatus(s.id)}
                          className="text-xs text-surface-500 hover:text-surface-700 underline"
                        >
                          Undo
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                {/* Excerpt Comparison */}
                <div className="space-y-1.5 text-sm my-2">
                  <div className="p-2 rounded bg-rose-50/60 border border-rose-100 text-rose-900 font-mono text-xs">
                    <span className="text-rose-500 font-bold mr-2">Original:</span>
                    <span className="line-through">{s.original_text}</span>
                  </div>

                  {editingId === s.id ? (
                    <div className="space-y-2 mt-2">
                      <textarea
                        value={editText}
                        onChange={e => setEditText(e.target.value)}
                        rows={2}
                        className="w-full text-xs p-2 rounded border border-brand-400 focus:ring-1 focus:ring-brand-500 outline-none"
                      />
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => saveEdit(s.id)}
                          className="px-2.5 py-1 text-xs rounded bg-brand-600 text-white font-medium hover:bg-brand-700"
                        >
                          Save Edit
                        </button>
                        <button
                          type="button"
                          onClick={cancelEdit}
                          className="px-2 py-1 text-xs rounded border border-surface-300 text-surface-600 hover:bg-surface-100"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="p-2 rounded bg-emerald-50/60 border border-emerald-100 text-emerald-950 font-mono text-xs">
                      <span className="text-emerald-600 font-bold mr-2">Suggested:</span>
                      <span className="font-semibold">{s.suggested_text}</span>
                    </div>
                  )}
                </div>

                {/* Explanation */}
                {s.explanation && (
                  <p className="text-xs text-surface-600 italic mt-2">
                    💡 {s.explanation}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
