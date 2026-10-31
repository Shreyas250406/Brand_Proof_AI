// ============================================================
// Brand Knowledge Page
// Manages brand guidelines and terminology configuration.
// ============================================================

import { useState, useEffect, useMemo } from 'react';
import {
  Save,
  X,
  Plus,
  Trash2,
  BookOpen,
  AlertTriangle,
  Loader2,
  RotateCcw,
} from 'lucide-react';
import type { BrandProfile } from '@/types/domain';
import { demoBrandService } from '@/services/demo';
import { useApp } from '@/context/AppContext';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { cn } from '@/lib/utils';

export function BrandPage() {
  const { addToast } = useApp();

  const [profile, setProfile] = useState<BrandProfile | null>(null);
  const [draft, setDraft] = useState<BrandProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [resetDialogOpen, setResetDialogOpen] = useState(false);

  // Temporary field inputs
  const [newTerm, setNewTerm] = useState('');
  const [newProhibited, setNewProhibited] = useState('');
  const [newRule, setNewRule] = useState('');

  useEffect(() => {
    demoBrandService.get().then(p => {
      setProfile(p);
      setDraft(p ? { ...p } : null);
      setLoading(false);
    });
  }, []);

  // Derived dirty flag — no effect needed
  const isDirty = useMemo(() => {
    if (!profile || !draft) return false;
    return (
      draft.name !== profile.name ||
      draft.description !== profile.description ||
      draft.voiceAndTone !== profile.voiceAndTone ||
      draft.targetAudience !== profile.targetAudience ||
      draft.brandInstructions !== profile.brandInstructions ||
      draft.guidelineNotes !== profile.guidelineNotes ||
      JSON.stringify(draft.preferredTerminology) !== JSON.stringify(profile.preferredTerminology) ||
      JSON.stringify(draft.prohibitedPhrases) !== JSON.stringify(profile.prohibitedPhrases) ||
      JSON.stringify(draft.writingRules) !== JSON.stringify(profile.writingRules)
    );
  }, [draft, profile]);

  function updateDraft(updates: Partial<BrandProfile>) {
    setDraft(prev => prev ? { ...prev, ...updates } : null);
  }

  async function handleSave() {
    if (!draft) return;
    setSaving(true);
    try {
      await demoBrandService.save(draft);
      setProfile({ ...draft });
      addToast({ title: 'Brand profile saved', variant: 'success' });
    } catch {
      addToast({ title: 'Failed to save profile', variant: 'error' });
    } finally {
      setSaving(false);
    }
  }

  function handleCancel() {
    setDraft(profile ? { ...profile } : null);
  }

  async function handleReset() {
    await demoBrandService.reset();
    const fresh = await demoBrandService.get();
    setProfile(fresh);
    setDraft(fresh ? { ...fresh } : null);
    addToast({ title: 'Brand profile reset to defaults', variant: 'info' });
  }

  // List field helpers
  function addItem(field: 'preferredTerminology' | 'prohibitedPhrases' | 'writingRules', value: string, clear: () => void) {
    const trimmed = value.trim();
    if (!trimmed || !draft) return;
    if (draft[field].includes(trimmed)) { clear(); return; }
    updateDraft({ [field]: [...draft[field], trimmed] });
    clear();
  }

  function removeItem(field: 'preferredTerminology' | 'prohibitedPhrases' | 'writingRules', idx: number) {
    if (!draft) return;
    const next = [...draft[field]];
    next.splice(idx, 1);
    updateDraft({ [field]: next });
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-6 h-6 animate-spin text-surface-400" />
      </div>
    );
  }

  if (!draft) return null;

  return (
    <div className="max-w-3xl mx-auto space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="page-header mb-0">
          <h2 className="page-title">Brand Knowledge</h2>
          <p className="page-description">Define your brand guidelines, terminology and writing standards.</p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => setResetDialogOpen(true)}
            className="btn-ghost text-sm"
          >
            <RotateCcw className="w-4 h-4" />
            Reset
          </button>
          {isDirty && (
            <button onClick={handleCancel} className="btn-ghost text-sm">
              <X className="w-4 h-4" />
              Cancel
            </button>
          )}
          <button
            onClick={handleSave}
            disabled={!isDirty || saving}
            className="btn-primary"
          >
            {saving
              ? <><Loader2 className="w-4 h-4 animate-spin" /> Saving…</>
              : <><Save className="w-4 h-4" /> {isDirty ? 'Save Changes' : 'Saved'}</>
            }
          </button>
        </div>
      </div>

      {/* Brand guidelines info */}
      <div className="flex items-start gap-2.5 px-3.5 py-3 rounded-lg bg-brand-50 border border-brand-200">
        <BookOpen className="w-4 h-4 text-brand-600 shrink-0 mt-0.5" />
        <p className="text-xs text-brand-800">
          <span className="font-semibold">Brand Guidelines.</span>{' '}
          Configure your brand voice, tone, and prohibited terms to maintain consistent communication across all analyses.
        </p>
      </div>

      {/* Unsaved changes banner */}
      {isDirty && (
        <div className="flex items-center gap-2.5 px-3.5 py-2.5 rounded-lg bg-blue-50 border border-blue-200">
          <AlertTriangle className="w-4 h-4 text-blue-600 shrink-0" />
          <p className="text-xs text-blue-800 font-medium">You have unsaved changes.</p>
        </div>
      )}

      {/* Brand Identity */}
      <Section title="Brand Identity" icon={<BookOpen className="w-4 h-4" />}>
        <div className="space-y-4">
          <Field label="Brand Name" required>
            <input
              className="input-field"
              value={draft.name}
              onChange={e => updateDraft({ name: e.target.value })}
              placeholder="Your Brand Name"
              aria-label="Brand name"
              maxLength={100}
            />
          </Field>
          <Field label="Brand Description">
            <textarea
              className="textarea-field h-20"
              value={draft.description ?? ''}
              onChange={e => updateDraft({ description: e.target.value })}
              placeholder="A brief description of your brand and its purpose."
              aria-label="Brand description"
            />
          </Field>
        </div>
      </Section>

      {/* Voice & Tone */}
      <Section title="Voice & Tone">
        <div className="space-y-4">
          <Field label="Voice and Tone Guidelines">
            <textarea
              className="textarea-field h-24"
              value={draft.voiceAndTone ?? ''}
              onChange={e => updateDraft({ voiceAndTone: e.target.value })}
              placeholder="e.g. Professional, clear and approachable. We communicate with confidence and warmth, avoiding jargon."
              aria-label="Voice and tone"
            />
          </Field>
          <Field label="Target Audience">
            <textarea
              className="textarea-field h-20"
              value={draft.targetAudience ?? ''}
              onChange={e => updateDraft({ targetAudience: e.target.value })}
              placeholder="Describe who your content is aimed at."
              aria-label="Target audience"
            />
          </Field>
        </div>
      </Section>

      {/* Terminology */}
      <Section title="Preferred Terminology">
        <p className="text-xs text-surface-500 mb-3">Words and phrases your brand prefers to use.</p>
        <ListEditor
          items={draft.preferredTerminology}
          inputValue={newTerm}
          onInputChange={setNewTerm}
          onAdd={() => addItem('preferredTerminology', newTerm, () => setNewTerm(''))}
          onRemove={idx => removeItem('preferredTerminology', idx)}
          placeholder="Add preferred term…"
          tagClass="bg-green-50 text-green-700 border-green-200"
          aria-label="Add preferred term"
        />
      </Section>

      {/* Prohibited phrases */}
      <Section title="Prohibited Phrases">
        <p className="text-xs text-surface-500 mb-3">Words and phrases your brand discourages or prohibits.</p>
        <ListEditor
          items={draft.prohibitedPhrases}
          inputValue={newProhibited}
          onInputChange={setNewProhibited}
          onAdd={() => addItem('prohibitedPhrases', newProhibited, () => setNewProhibited(''))}
          onRemove={idx => removeItem('prohibitedPhrases', idx)}
          placeholder="Add prohibited phrase…"
          tagClass="bg-red-50 text-red-700 border-red-200"
          aria-label="Add prohibited phrase"
        />
      </Section>

      {/* Writing Rules */}
      <Section title="Writing Rules">
        <p className="text-xs text-surface-500 mb-3">Specific writing standards your content should follow.</p>
        <div className="space-y-3">
          {draft.writingRules.map((rule, idx) => (
            <div key={idx} className="flex items-start gap-2">
              <span className="w-5 h-5 rounded-full bg-navy-100 text-navy-700 text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">
                {idx + 1}
              </span>
              <p className="text-sm text-surface-700 flex-1">{rule}</p>
              <button
                onClick={() => removeItem('writingRules', idx)}
                className="btn-ghost p-1 text-surface-400 hover:text-red-600 shrink-0"
                aria-label={`Remove rule ${idx + 1}`}
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
          <div className="flex gap-2">
            <input
              className="input-field flex-1 text-sm"
              value={newRule}
              onChange={e => setNewRule(e.target.value)}
              placeholder="Add a writing rule…"
              aria-label="New writing rule"
              onKeyDown={e => e.key === 'Enter' && addItem('writingRules', newRule, () => setNewRule(''))}
            />
            <button
              onClick={() => addItem('writingRules', newRule, () => setNewRule(''))}
              disabled={!newRule.trim()}
              className="btn-secondary text-sm"
            >
              <Plus className="w-4 h-4" />
              Add
            </button>
          </div>
        </div>
      </Section>

      {/* Additional instructions */}
      <Section title="Additional Instructions">
        <div className="space-y-4">
          <Field label="Brand-Specific Instructions">
            <textarea
              className="textarea-field h-24"
              value={draft.brandInstructions ?? ''}
              onChange={e => updateDraft({ brandInstructions: e.target.value })}
              placeholder="Any specific instructions for the analysis engine regarding your brand…"
              aria-label="Brand instructions"
            />
          </Field>
          <Field label="Guideline Notes">
            <textarea
              className="textarea-field h-20"
              value={draft.guidelineNotes ?? ''}
              onChange={e => updateDraft({ guidelineNotes: e.target.value })}
              placeholder="Internal notes or context for these guidelines…"
              aria-label="Guideline notes"
            />
          </Field>
        </div>
      </Section>

      {/* Save footer */}
      <div className="flex justify-end gap-3 pb-4">
        {isDirty && (
          <button onClick={handleCancel} className="btn-ghost">
            <X className="w-4 h-4" />
            Cancel
          </button>
        )}
        <button
          onClick={handleSave}
          disabled={!isDirty || saving}
          className="btn-primary"
        >
          {saving
            ? <><Loader2 className="w-4 h-4 animate-spin" /> Saving…</>
            : <><Save className="w-4 h-4" /> {isDirty ? 'Save Changes' : 'All Saved'}</>
          }
        </button>
      </div>

      <ConfirmDialog
        open={resetDialogOpen}
        onOpenChange={setResetDialogOpen}
        title="Reset brand profile"
        description="This will reset the brand profile to defaults and clear all custom guidelines from demo storage."
        confirmLabel="Reset"
        variant="danger"
        onConfirm={handleReset}
      />
    </div>
  );
}

// -----------------------------------------------------------
// Helper components
// -----------------------------------------------------------

function Section({ title, icon, children }: { title: string; icon?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="card p-5 space-y-4">
      <h3 className="flex items-center gap-2 text-sm font-semibold text-surface-800">
        {icon && <span className="text-surface-400">{icon}</span>}
        {title}
      </h3>
      {children}
    </div>
  );
}

function Field({
  label,
  required,
  children,
}: {
  label: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="label">
        {label}
        {required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      {children}
    </div>
  );
}

interface ListEditorProps {
  items: string[];
  inputValue: string;
  onInputChange: (v: string) => void;
  onAdd: () => void;
  onRemove: (idx: number) => void;
  placeholder: string;
  tagClass: string;
  'aria-label': string;
}

function ListEditor({ items, inputValue, onInputChange, onAdd, onRemove, placeholder, tagClass, 'aria-label': ariaLabel }: ListEditorProps) {
  return (
    <div className="space-y-3">
      {items.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {items.map((item, idx) => (
            <span
              key={idx}
              className={cn('badge border flex items-center gap-1.5 pr-1.5', tagClass)}
            >
              {item}
              <button
                onClick={() => onRemove(idx)}
                className="hover:opacity-70 transition-opacity"
                aria-label={`Remove ${item}`}
              >
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}
        </div>
      )}
      <div className="flex gap-2">
        <input
          className="input-field flex-1 text-sm"
          value={inputValue}
          onChange={e => onInputChange(e.target.value)}
          placeholder={placeholder}
          aria-label={ariaLabel}
          onKeyDown={e => e.key === 'Enter' && onAdd()}
        />
        <button
          onClick={onAdd}
          disabled={!inputValue.trim()}
          className="btn-secondary text-sm"
        >
          <Plus className="w-4 h-4" />
          Add
        </button>
      </div>
    </div>
  );
}
