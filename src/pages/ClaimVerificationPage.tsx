// ============================================================
// Claim Verification Page
// Standalone evidence-based factual and marketing claim verification
// ============================================================

import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  HelpCircle,
  Scale,
  Plus,
  Trash2,
  ExternalLink,
  Copy,
  RotateCcw,
  Sparkles,
  History,
  FileText,
  ChevronDown,
  ChevronUp,
  Info,
  ArrowRight,
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useApp } from '@/context/AppContext';
import { claimVerificationService } from '@/services/claimVerification';
import type {
  EvidenceInputItem,
  ClaimVerificationResult,
  ClaimVerificationRecord,
  VerificationStatusType,
  UserEvidenceType,
} from '@/types/claimVerification';
import { cn } from '@/lib/utils';

const MAX_CLAIM_LENGTH = 2000;
const MAX_EVIDENCE_TEXT_LENGTH = 10000;

interface PresetExample {
  label: string;
  claim: string;
  evidence: EvidenceInputItem[];
}

const PRESET_EXAMPLES: PresetExample[] = [
  {
    label: 'Battery Life (Contradicted)',
    claim: 'Our SmartWatch X provides up to 72 hours of battery life under normal daily usage.',
    evidence: [
      {
        id: 'E001',
        title: 'SmartWatch X Official User Manual & Technical Specs',
        text: 'Battery Specifications: Operating battery life is strictly up to 36 hours under standard daily usage. Continuous GPS and heart rate monitoring will reduce duration to 18 hours. Do not exceed 36 hours without recharging.',
        source_url: 'https://specs.example.com/smartwatch-x/manual.pdf',
        publisher: 'Apex Electronics Corp',
        published_date: '2026-03-15',
        source_type: 'Specification',
        evidence_type: 'contradicting',
      },
    ],
  },
  {
    label: 'Lab Durability (Supported)',
    claim: 'ApexPro Headphones feature IP68 dust and water resistance certified to 1.5 meters for 30 minutes.',
    evidence: [
      {
        id: 'E001',
        title: 'TUV Rheinland Ingress Protection Certification Report #TUV-2026-894',
        text: 'Test Conclusion: ApexPro Audio Unit meets all criteria for Ingress Protection code IP68 according to IEC 60529 standard: complete protection against dust ingress and continuous water immersion at a tested depth of 1.5 meters for 30 consecutive minutes without functional degradation.',
        source_url: 'https://certifications.example.com/tuv-apexpro-ip68.pdf',
        publisher: 'TUV Rheinland Independent Testing Laboratories',
        published_date: '2026-01-20',
        source_type: 'Test Report',
        evidence_type: 'supporting',
      },
    ],
  },
  {
    label: 'Eco Packaging (Partially Supported)',
    claim: 'All Apex deliveries arrive in 100% biodegradable and zero-plastic packaging worldwide.',
    evidence: [
      {
        id: 'E001',
        title: 'Apex Packaging Environmental Audit 2026',
        text: 'Outer shipping cartons are manufactured from 100% biodegradable recycled cardboard. However, international shipments outside North America and the EU currently utilize standard low-density polyethylene (LDPE) waterproof wrap pending regional supply chain transitions.',
        source_url: 'https://sustainability.example.com/2026-report',
        publisher: 'Apex Sustainability Office',
        published_date: '2026-02-10',
        source_type: 'Internal Document',
        evidence_type: 'neutral',
      },
    ],
  },
  {
    label: 'Display Spec (Unverifiable)',
    claim: 'Our SmartWatch X charges from 0% to 100% in under 25 minutes using HyperCharge.',
    evidence: [
      {
        id: 'E001',
        title: 'SmartWatch X Display & Audio Architecture',
        text: 'The SmartWatch X incorporates a 1.4-inch AMOLED display with 1000 nits peak brightness and dual beamforming micro-speakers for hands-free voice calls.',
        source_url: 'https://specs.example.com/display-tech',
        publisher: 'Apex Electronics Tech Notes',
        published_date: '2026-04-05',
        source_type: 'Specification',
        evidence_type: 'unknown',
      },
    ],
  },
];

export function ClaimVerificationPage() {
  const { isAuthenticated } = useAuth();
  const { addToast } = useApp();

  // Tab navigation: 'verify' or 'history'
  const [activeTab, setActiveTab] = useState<'verify' | 'history'>('verify');

  // Input states
  const [claim, setClaim] = useState('');
  const [evidenceList, setEvidenceList] = useState<EvidenceInputItem[]>([
    {
      id: 'E001',
      title: '',
      text: '',
      source_url: '',
      publisher: '',
      published_date: '',
      source_type: 'Specification',
      evidence_type: 'unknown',
    },
  ]);

  // Loading & results
  const [isVerifying, setIsVerifying] = useState(false);
  const [verificationResult, setVerificationResult] = useState<ClaimVerificationResult | null>(null);
  const [lastVerifiedClaim, setLastVerifiedClaim] = useState('');
  const [lastVerifiedEvidence, setLastVerifiedEvidence] = useState<EvidenceInputItem[]>([]);
  const [persistedId, setPersistedId] = useState<string | null>(null);

  // History state
  const [historyList, setHistoryList] = useState<ClaimVerificationRecord[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // Collapsible metadata for each evidence item
  const [expandedMeta, setExpandedMeta] = useState<Record<string, boolean>>({});

  const toggleMeta = (id: string) => {
    setExpandedMeta(prev => ({ ...prev, [id]: !prev[id] }));
  };

  // Load history on mount or when switching to history tab
  const fetchHistory = async () => {
    if (!isAuthenticated) return;
    setIsLoadingHistory(true);
    try {
      const records = await claimVerificationService.listHistory();
      setHistoryList(records);
    } catch {
      // Soft fail for history loading
    } finally {
      setIsLoadingHistory(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'history') {
      fetchHistory();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, isAuthenticated]);

  // Handle Preset Selection
  const applyPreset = (preset: PresetExample) => {
    setClaim(preset.claim);
    setEvidenceList(
      preset.evidence.map((e, idx) => ({
        ...e,
        id: `E${String(idx + 1).padStart(3, '0')}`,
      }))
    );
    setVerificationResult(null);
    addToast({
      title: 'Example Loaded',
      description: `Loaded: ${preset.label}`,
      variant: 'info',
    });
  };

  // Evidence list handlers
  const handleAddEvidence = () => {
    if (evidenceList.length >= 10) {
      addToast({
        title: 'Limit Reached',
        description: 'You can provide up to 10 evidence items per verification.',
        variant: 'warning',
      });
      return;
    }
    const nextId = `E${String(evidenceList.length + 1).padStart(3, '0')}`;
    setEvidenceList(prev => [
      ...prev,
      {
        id: nextId,
        title: '',
        text: '',
        source_url: '',
        publisher: '',
        published_date: '',
        source_type: 'Specification',
        evidence_type: 'unknown',
      },
    ]);
  };

  const handleRemoveEvidence = (index: number) => {
    if (evidenceList.length <= 1) {
      addToast({
        title: 'Required',
        description: 'At least one evidence item is required.',
        variant: 'warning',
      });
      return;
    }
    setEvidenceList(prev => prev.filter((_, i) => i !== index));
  };

  const handleEvidenceChange = (
    index: number,
    field: keyof EvidenceInputItem,
    value: string
  ) => {
    setEvidenceList(prev => {
      const copy = [...prev];
      copy[index] = { ...copy[index], [field]: value };
      return copy;
    });
  };

  const handleClearClaim = () => {
    setClaim('');
    setVerificationResult(null);
  };

  // Execution: Submit to FastAPI /api/v1/ai/verify-claim
  const handleVerifyClaim = async () => {
    const cleanClaim = claim.trim();
    if (!cleanClaim) {
      addToast({
        title: 'Missing Claim',
        description: 'Please enter the claim you want to verify.',
        variant: 'warning',
      });
      return;
    }

    const validEvidence = evidenceList.filter(e => e.text && e.text.trim().length > 0);
    if (validEvidence.length === 0) {
      addToast({
        title: 'Missing Evidence',
        description: 'Please provide at least one evidence item with text/passages.',
        variant: 'warning',
      });
      return;
    }

    setIsVerifying(true);
    setVerificationResult(null);

    try {
      const response = await claimVerificationService.verifyClaim(cleanClaim, validEvidence);
      if (response && response.result) {
        setVerificationResult(response.result);
        setLastVerifiedClaim(cleanClaim);
        setLastVerifiedEvidence(validEvidence);
        setPersistedId(response.id || null);

        if (response.saved) {
          addToast({
            title: 'Verification Complete',
            description: `Verdict: ${response.result.verification_status}. Saved to your history.`,
            variant: 'success',
          });
        } else {
          addToast({
            title: 'Verification Complete',
            description: `Verdict: ${response.result.verification_status}.`,
            variant: 'info',
          });
        }
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Claim verification failed.';
      addToast({
        title: 'Verification Failed',
        description: msg,
        variant: 'error',
      });
    } finally {
      setIsVerifying(false);
    }
  };

  // Reopen a previous verification result from history
  const handleReopenHistory = (record: ClaimVerificationRecord) => {
    setClaim(record.claim);
    setEvidenceList(
      record.evidence && record.evidence.length > 0
        ? record.evidence
        : [
            {
              id: 'E001',
              title: 'Attached Evidence',
              text: 'Reopened from historical verification.',
            },
          ]
    );
    setVerificationResult(record.result);
    setLastVerifiedClaim(record.claim);
    setLastVerifiedEvidence(record.evidence || []);
    setPersistedId(record.id);
    setActiveTab('verify');
    addToast({
      title: 'Record Loaded',
      description: 'Loaded historical verification result.',
      variant: 'info',
    });
  };

  // Delete history item
  const handleDeleteHistory = async (id: string) => {
    setDeletingId(id);
    try {
      await claimVerificationService.deleteVerification(id);
      setHistoryList(prev => prev.filter(r => r.id !== id));
      addToast({
        title: 'Record Deleted',
        description: 'Verification record removed from your history.',
        variant: 'info',
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to delete record.';
      addToast({
        title: 'Deletion Failed',
        description: msg,
        variant: 'error',
      });
    } finally {
      setDeletingId(null);
    }
  };

  // Copy result text to clipboard
  const handleCopyResult = () => {
    if (!verificationResult) return;
    const text = [
      `=== BrandProof AI Claim Verification Report ===`,
      `Status: ${verificationResult.verification_status}`,
      `AI Confidence Estimate: ${(verificationResult.confidence * 100).toFixed(0)}%`,
      `Claim: "${lastVerifiedClaim}"`,
      `Verdict: ${verificationResult.verdict}`,
      `Reasoning: ${verificationResult.reasoning}`,
      verificationResult.suggested_correction
        ? `Suggested Correction: "${verificationResult.suggested_correction}"`
        : '',
      verificationResult.missing_information && verificationResult.missing_information.length > 0
        ? `Missing Information:\n${verificationResult.missing_information.map(m => ` - ${m}`).join('\n')}`
        : '',
    ]
      .filter(Boolean)
      .join('\n\n');

    navigator.clipboard.writeText(text);
    addToast({
      title: 'Copied to Clipboard',
      description: 'Verification summary copied to clipboard.',
      variant: 'success',
    });
  };

  // Visual Styling for Statuses
  const getStatusBadge = (status: VerificationStatusType) => {
    switch (status) {
      case 'SUPPORTED':
        return {
          label: 'Supported',
          icon: <CheckCircle2 className="w-5 h-5 text-emerald-600" />,
          badgeClass: 'bg-emerald-50 text-emerald-700 border-emerald-200',
          headerBg: 'bg-emerald-50/60 border-emerald-200',
          textClass: 'text-emerald-700',
        };
      case 'CONTRADICTED':
        return {
          label: 'Contradicted',
          icon: <XCircle className="w-5 h-5 text-rose-600" />,
          badgeClass: 'bg-rose-50 text-rose-700 border-rose-200',
          headerBg: 'bg-rose-50/60 border-rose-200',
          textClass: 'text-rose-700',
        };
      case 'PARTIALLY_SUPPORTED':
        return {
          label: 'Partially Supported',
          icon: <AlertTriangle className="w-5 h-5 text-amber-600" />,
          badgeClass: 'bg-amber-50 text-amber-700 border-amber-200',
          headerBg: 'bg-amber-50/60 border-amber-200',
          textClass: 'text-amber-700',
        };
      case 'CONFLICTING_EVIDENCE':
        return {
          label: 'Conflicting Evidence',
          icon: <Scale className="w-5 h-5 text-purple-600" />,
          badgeClass: 'bg-purple-50 text-purple-700 border-purple-200',
          headerBg: 'bg-purple-50/60 border-purple-200',
          textClass: 'text-purple-700',
        };
      case 'UNVERIFIABLE':
      default:
        return {
          label: 'Unverifiable / Insufficient Evidence',
          icon: <HelpCircle className="w-5 h-5 text-surface-600" />,
          badgeClass: 'bg-surface-100 text-surface-700 border-surface-300',
          headerBg: 'bg-surface-100/70 border-surface-200',
          textClass: 'text-surface-700',
        };
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-surface-200 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-navy-900 text-white shadow-sm">
              <ShieldCheck className="w-5 h-5 text-brand-400" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-navy-950">Claim Verification</h1>
              <p className="text-xs sm:text-sm text-surface-500">
                Standalone evidence-based evaluation of factual and marketing claims using Gemini AI
              </p>
            </div>
          </div>
        </div>

        {/* Tab switchers */}
        <div className="flex items-center bg-surface-100 p-1 rounded-lg border border-surface-200 text-sm font-medium">
          <button
            onClick={() => setActiveTab('verify')}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-all',
              activeTab === 'verify'
                ? 'bg-white text-navy-900 shadow-sm font-semibold'
                : 'text-surface-600 hover:text-navy-900'
            )}
          >
            <Sparkles className="w-4 h-4 text-brand-500" />
            <span>Verify Claim</span>
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-all',
              activeTab === 'history'
                ? 'bg-white text-navy-900 shadow-sm font-semibold'
                : 'text-surface-600 hover:text-navy-900'
            )}
          >
            <History className="w-4 h-4 text-surface-500" />
            <span>Verification History</span>
            {historyList.length > 0 && (
              <span className="ml-1 px-1.5 py-0.2 text-xs bg-navy-100 text-navy-800 rounded-full font-semibold">
                {historyList.length}
              </span>
            )}
          </button>
        </div>
      </div>

      {activeTab === 'verify' ? (
        <div className="space-y-6">
          {/* Preset Examples Pill Bar */}
          <div className="bg-white border border-surface-200 rounded-xl p-3.5 shadow-card">
            <div className="flex flex-col sm:flex-row sm:items-center gap-2 text-xs">
              <span className="font-semibold text-surface-700 flex items-center gap-1.5 whitespace-nowrap">
                <Info className="w-3.5 h-3.5 text-brand-500" />
                Quick Test Scenarios:
              </span>
              <div className="flex flex-wrap gap-2">
                {PRESET_EXAMPLES.map(preset => (
                  <button
                    key={preset.label}
                    onClick={() => applyPreset(preset)}
                    className="px-2.5 py-1 rounded-md bg-surface-100 hover:bg-brand-50 hover:text-brand-700 hover:border-brand-300 text-surface-700 border border-surface-200 font-medium transition-colors cursor-pointer text-xs"
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Column: Claim & Evidence Inputs */}
            <div className="lg:col-span-7 space-y-6">
              {/* SECTION A: Claim Input */}
              <div className="bg-white rounded-xl border border-surface-200 shadow-card p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-semibold text-navy-950 flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-brand-500" />
                    Marketing or Factual Claim to Verify
                    <span className="text-rose-500 text-xs">*</span>
                  </label>
                  {claim && (
                    <button
                      onClick={handleClearClaim}
                      className="text-xs text-surface-500 hover:text-rose-600 transition-colors flex items-center gap-1 cursor-pointer"
                    >
                      <RotateCcw className="w-3 h-3" />
                      Clear
                    </button>
                  )}
                </div>

                <div className="relative">
                  <textarea
                    value={claim}
                    onChange={e => setClaim(e.target.value)}
                    maxLength={MAX_CLAIM_LENGTH}
                    rows={3}
                    placeholder="Enter the factual or promotional claim to evaluate, e.g.: 'Our SmartWatch X provides up to 72 hours of battery life under normal daily usage.'"
                    className="w-full text-sm rounded-lg border border-surface-300 p-3 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 text-navy-900 placeholder:text-surface-400 resize-y"
                  />
                  <div className="flex justify-between items-center mt-1 text-xs text-surface-500 px-0.5">
                    <span>Specific metrics, durations, and conditions will be checked.</span>
                    <span
                      className={cn(
                        claim.length >= MAX_CLAIM_LENGTH ? 'text-rose-500 font-bold' : ''
                      )}
                    >
                      {claim.length} / {MAX_CLAIM_LENGTH}
                    </span>
                  </div>
                </div>
              </div>

              {/* SECTION B: Evidence Input */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-sm font-semibold text-navy-950 flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-navy-600" />
                      Supplied Evidence & Proof Documents
                      <span className="text-xs text-surface-500 font-normal">
                        ({evidenceList.length} item{evidenceList.length !== 1 ? 's' : ''})
                      </span>
                    </h2>
                    <p className="text-xs text-surface-500 mt-0.5">
                      Gemini evaluates relationship strictly against this evidence without internet browsing.
                    </p>
                  </div>
                  <button
                    onClick={handleAddEvidence}
                    disabled={evidenceList.length >= 10}
                    className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-navy-50 hover:bg-navy-100 text-navy-800 text-xs font-medium border border-navy-200 transition-colors cursor-pointer disabled:opacity-50"
                  >
                    <Plus className="w-3.5 h-3.5 text-navy-700" />
                    Add Evidence
                  </button>
                </div>

                {evidenceList.map((item, index) => {
                  const isMetaOpen = expandedMeta[item.id] || false;
                  return (
                    <div
                      key={item.id}
                      className="bg-white rounded-xl border border-surface-200 shadow-card p-4.5 space-y-3.5 transition-all"
                    >
                      {/* Evidence Card Header */}
                      <div className="flex items-center justify-between pb-2 border-b border-surface-100">
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 bg-surface-100 text-surface-700 rounded text-xs font-mono font-bold">
                            {item.id}
                          </span>
                          <span className="text-xs font-semibold text-surface-700">
                            Evidence Item #{index + 1}
                          </span>
                        </div>

                        {evidenceList.length > 1 && (
                          <button
                            onClick={() => handleRemoveEvidence(index)}
                            className="text-surface-400 hover:text-rose-600 transition-colors p-1 rounded hover:bg-rose-50 cursor-pointer"
                            title="Remove this evidence item"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>

                      {/* Evidence Title Input */}
                      <div>
                        <label className="block text-xs font-medium text-surface-700 mb-1">
                          Evidence Title / Document Name
                        </label>
                        <input
                          type="text"
                          value={item.title}
                          onChange={e => handleEvidenceChange(index, 'title', e.target.value)}
                          placeholder="e.g. Official Product Specifications Sheet, Lab Report #804, User Manual"
                          className="w-full text-xs rounded-md border border-surface-300 px-3 py-2 focus:outline-none focus:ring-1 focus:ring-brand-500 text-navy-900"
                        />
                      </div>

                      {/* Evidence Text / Passage */}
                      <div>
                        <div className="flex justify-between items-center mb-1">
                          <label className="text-xs font-medium text-surface-700">
                            Evidence Text or Extracted Quote Passage
                            <span className="text-rose-500 text-xs ml-0.5">*</span>
                          </label>
                          <span className="text-[11px] text-surface-400">
                            {item.text.length} / {MAX_EVIDENCE_TEXT_LENGTH}
                          </span>
                        </div>
                        <textarea
                          value={item.text}
                          onChange={e => handleEvidenceChange(index, 'text', e.target.value)}
                          maxLength={MAX_EVIDENCE_TEXT_LENGTH}
                          rows={4}
                          placeholder="Paste the relevant passage, quote, specification row, or test finding that either supports or conflicts with the claim..."
                          className="w-full text-xs font-sans rounded-md border border-surface-300 p-2.5 focus:outline-none focus:ring-1 focus:ring-brand-500 text-navy-900 placeholder:text-surface-400 resize-y"
                        />
                      </div>

                      {/* User-Selected Evidence Relationship (Optional) */}
                      <div className="pt-1">
                        <label className="block text-xs font-medium text-surface-700 mb-1.5">
                          User-Stated Relationship (Optional)
                        </label>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                          {[
                            { value: 'supporting', label: 'Supporting' },
                            { value: 'contradicting', label: 'Contradicting' },
                            { value: 'neutral', label: 'Neutral/Context' },
                            { value: 'unknown', label: 'Unknown' },
                          ].map(option => (
                            <button
                              key={option.value}
                              type="button"
                              onClick={() =>
                                handleEvidenceChange(
                                  index,
                                  'evidence_type',
                                  option.value as UserEvidenceType
                                )
                              }
                              className={cn(
                                'text-xs py-1.5 px-2 rounded-md border text-center transition-all cursor-pointer font-medium',
                                item.evidence_type === option.value
                                  ? 'bg-brand-50 border-brand-400 text-brand-700 font-semibold shadow-xs'
                                  : 'bg-surface-50 border-surface-200 text-surface-600 hover:bg-surface-100'
                              )}
                            >
                              {option.label}
                            </button>
                          ))}
                        </div>
                        <p className="text-[11px] text-surface-500 mt-1">
                          * Gemini independently checks and verifies the true relationship.
                        </p>
                      </div>

                      {/* Collapsible Metadata (URL, Publisher, Date, Source Type) */}
                      <div className="pt-2 border-t border-surface-100">
                        <button
                          type="button"
                          onClick={() => toggleMeta(item.id)}
                          className="flex items-center gap-1.5 text-xs text-surface-600 hover:text-navy-900 font-medium cursor-pointer"
                        >
                          {isMetaOpen ? (
                            <ChevronUp className="w-3.5 h-3.5" />
                          ) : (
                            <ChevronDown className="w-3.5 h-3.5" />
                          )}
                          <span>
                            {isMetaOpen
                              ? 'Hide citation metadata'
                              : 'Add citation metadata (URL, publisher, date)'}
                          </span>
                        </button>

                        {isMetaOpen && (
                          <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3 p-3 bg-surface-50 rounded-lg border border-surface-200">
                            <div>
                              <label className="block text-[11px] font-medium text-surface-700 mb-0.5">
                                Source URL (optional)
                              </label>
                              <input
                                type="url"
                                value={item.source_url || ''}
                                onChange={e =>
                                  handleEvidenceChange(index, 'source_url', e.target.value)
                                }
                                placeholder="https://example.com/spec-sheet"
                                className="w-full text-xs rounded border border-surface-300 px-2.5 py-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-brand-500"
                              />
                            </div>
                            <div>
                              <label className="block text-[11px] font-medium text-surface-700 mb-0.5">
                                Publisher / Source Name (optional)
                              </label>
                              <input
                                type="text"
                                value={item.publisher || ''}
                                onChange={e =>
                                  handleEvidenceChange(index, 'publisher', e.target.value)
                                }
                                placeholder="e.g. Apex Electronics Corp"
                                className="w-full text-xs rounded border border-surface-300 px-2.5 py-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-brand-500"
                              />
                            </div>
                            <div>
                              <label className="block text-[11px] font-medium text-surface-700 mb-0.5">
                                Document Date (optional)
                              </label>
                              <input
                                type="text"
                                value={item.published_date || ''}
                                onChange={e =>
                                  handleEvidenceChange(index, 'published_date', e.target.value)
                                }
                                placeholder="e.g. 2026-03-15 or March 2026"
                                className="w-full text-xs rounded border border-surface-300 px-2.5 py-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-brand-500"
                              />
                            </div>
                            <div>
                              <label className="block text-[11px] font-medium text-surface-700 mb-0.5">
                                Source Type (optional)
                              </label>
                              <select
                                value={item.source_type || 'Specification'}
                                onChange={e =>
                                  handleEvidenceChange(index, 'source_type', e.target.value)
                                }
                                className="w-full text-xs rounded border border-surface-300 px-2 py-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-brand-500"
                              >
                                <option value="Specification">Product Specification</option>
                                <option value="Test Report">Lab / Certification Report</option>
                                <option value="Press Release">Official Press Release</option>
                                <option value="User Manual">User Manual / Guide</option>
                                <option value="Internal Document">Internal Document</option>
                                <option value="Third-Party Review">Third-Party Benchmark</option>
                                <option value="Other">Other</option>
                              </select>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* SECTION C: Primary Verify Action Button */}
              <div className="pt-2">
                <button
                  onClick={handleVerifyClaim}
                  disabled={isVerifying || !claim.trim()}
                  className={cn(
                    'w-full py-3 px-5 rounded-xl text-white font-semibold text-sm transition-all shadow-md',
                    'flex items-center justify-center gap-2 cursor-pointer',
                    isVerifying || !claim.trim()
                      ? 'bg-surface-300 cursor-not-allowed opacity-75'
                      : 'bg-navy-900 hover:bg-navy-800 active:scale-[0.99] hover:shadow-lg'
                  )}
                >
                  {isVerifying ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      <span>Evaluating Evidence with Gemini AI...</span>
                    </>
                  ) : (
                    <>
                      <ShieldCheck className="w-4.5 h-4.5 text-brand-400" />
                      <span>Verify Claim Against Evidence</span>
                      <ArrowRight className="w-4 h-4 ml-1 opacity-70" />
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Right Column: Verification Results Display */}
            <div className="lg:col-span-5 space-y-6">
              {verificationResult ? (
                /* SECTION D: Result Card */
                <div className="bg-white rounded-xl border border-surface-200 shadow-card overflow-hidden">
                  {/* Status Banner */}
                  {(() => {
                    const badge = getStatusBadge(verificationResult.verification_status);
                    return (
                      <div className={cn('p-5 border-b', badge.headerBg)}>
                        <div className="flex items-center justify-between gap-3">
                          <div className="flex items-center gap-2">
                            {badge.icon}
                            <span className={cn('text-sm font-bold uppercase tracking-wide', badge.textClass)}>
                              {badge.label}
                            </span>
                          </div>
                          <div className="text-right">
                            <span className="text-[11px] font-semibold text-surface-500 block">
                              AI Estimate
                            </span>
                            <span className="text-xs font-bold text-navy-950 font-mono">
                              {(verificationResult.confidence * 100).toFixed(0)}% Confidence
                            </span>
                          </div>
                        </div>

                        <div className="mt-3">
                          <h3 className="text-sm font-bold text-navy-950 leading-snug">
                            {verificationResult.verdict}
                          </h3>
                        </div>
                      </div>
                    );
                  })()}

                  <div className="p-5 space-y-5">
                    {/* Tested Claim Summary */}
                    <div>
                      <h4 className="text-xs font-semibold text-surface-500 uppercase tracking-wider mb-1.5">
                        Evaluated Claim
                      </h4>
                      <div className="p-3 bg-surface-50 rounded-lg border border-surface-200 text-xs text-navy-900 italic font-serif">
                        "{lastVerifiedClaim}"
                      </div>
                    </div>

                    {/* Detailed Reasoning */}
                    <div>
                      <h4 className="text-xs font-semibold text-surface-500 uppercase tracking-wider mb-1.5">
                        Reasoning & Findings
                      </h4>
                      <p className="text-xs text-surface-800 leading-relaxed bg-surface-50/50 p-3 rounded-lg border border-surface-200/60">
                        {verificationResult.reasoning}
                      </p>
                    </div>

                    {/* Suggested Correction (if provided) */}
                    {verificationResult.suggested_correction && (
                      <div className="p-3.5 bg-amber-50/80 rounded-lg border border-amber-200 space-y-1">
                        <div className="flex items-center gap-1.5 text-xs font-bold text-amber-900">
                          <CheckCircle2 className="w-3.5 h-3.5 text-amber-700" />
                          <span>Accurate Evidence-Backed Phrasing:</span>
                        </div>
                        <p className="text-xs text-amber-950 font-medium italic">
                          "{verificationResult.suggested_correction}"
                        </p>
                      </div>
                    )}

                    {/* Evidence-by-Evidence Breakdown */}
                    {verificationResult.evidence_analysis &&
                      verificationResult.evidence_analysis.length > 0 && (
                        <div>
                          <h4 className="text-xs font-semibold text-surface-500 uppercase tracking-wider mb-2">
                            Evidence Analysis Breakdown ({verificationResult.evidence_analysis.length})
                          </h4>
                          <div className="space-y-3">
                            {verificationResult.evidence_analysis.map((analysis, idx) => {
                              const matchingInput = lastVerifiedEvidence.find(
                                e => e.id === analysis.evidence_id
                              );
                              return (
                                <div
                                  key={idx}
                                  className="p-3 bg-white rounded-lg border border-surface-200 shadow-2xs space-y-2 text-xs"
                                >
                                  <div className="flex items-center justify-between gap-2">
                                    <span className="font-semibold text-navy-900 truncate">
                                      {matchingInput?.title || `Evidence ${analysis.evidence_id}`}
                                    </span>
                                    <div className="flex items-center gap-1.5">
                                      <span
                                        className={cn(
                                          'px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider',
                                          analysis.relationship === 'SUPPORTS'
                                            ? 'bg-emerald-100 text-emerald-800'
                                            : analysis.relationship === 'CONTRADICTS'
                                            ? 'bg-rose-100 text-rose-800'
                                            : analysis.relationship === 'PARTIALLY_SUPPORTS'
                                            ? 'bg-amber-100 text-amber-800'
                                            : 'bg-surface-100 text-surface-700'
                                        )}
                                      >
                                        {analysis.relationship}
                                      </span>
                                    </div>
                                  </div>

                                  {matchingInput?.publisher && (
                                    <div className="text-[11px] text-surface-500">
                                      Source: {matchingInput.publisher}
                                    </div>
                                  )}

                                  {matchingInput?.source_url && (
                                    <a
                                      href={matchingInput.source_url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="inline-flex items-center gap-1 text-[11px] text-brand-600 hover:underline"
                                    >
                                      <span>View citation document</span>
                                      <ExternalLink className="w-3 h-3" />
                                    </a>
                                  )}

                                  {analysis.matched_passage && (
                                    <div className="p-2 bg-surface-50 rounded border-l-2 border-brand-500 text-[11px] text-surface-700 italic">
                                      "{analysis.matched_passage}"
                                    </div>
                                  )}

                                  <p className="text-[11px] text-surface-700 leading-normal">
                                    {analysis.explanation}
                                  </p>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}

                    {/* Missing Information / Gaps */}
                    {verificationResult.missing_information &&
                      verificationResult.missing_information.length > 0 && (
                        <div>
                          <h4 className="text-xs font-semibold text-surface-500 uppercase tracking-wider mb-1.5">
                            Information Gaps / Missing Proof
                          </h4>
                          <ul className="list-disc pl-4 space-y-1 text-xs text-surface-700">
                            {verificationResult.missing_information.map((item, idx) => (
                              <li key={idx}>{item}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                    {/* Authentication / Persistence Note */}
                    <div className="pt-2 border-t border-surface-100 text-[11px] text-surface-400">
                      Disclaimer: BrandProof AI verifies claims solely against provided text. User-supplied sources are not independently authenticated.
                    </div>

                    {/* Action Buttons */}
                    <div className="flex flex-col sm:flex-row items-center gap-2 pt-2">
                      <button
                        onClick={handleCopyResult}
                        className="w-full sm:w-auto flex-1 py-2 px-3 rounded-lg border border-surface-300 hover:bg-surface-50 text-surface-700 text-xs font-medium flex items-center justify-center gap-1.5 cursor-pointer transition-colors"
                      >
                        <Copy className="w-3.5 h-3.5" />
                        <span>Copy Summary</span>
                      </button>

                      <button
                        onClick={() => {
                          setVerificationResult(null);
                          setClaim('');
                        }}
                        className="w-full sm:w-auto py-2 px-3 rounded-lg bg-navy-50 hover:bg-navy-100 text-navy-800 text-xs font-medium flex items-center justify-center gap-1.5 cursor-pointer transition-colors"
                      >
                        <RotateCcw className="w-3.5 h-3.5" />
                        <span>Verify Another Claim</span>
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                /* Initial Empty State / Instructions */
                <div className="bg-white rounded-xl border border-surface-200 shadow-card p-6 text-center space-y-4">
                  <div className="w-12 h-12 mx-auto rounded-full bg-brand-50 flex items-center justify-center text-brand-600">
                    <ShieldCheck className="w-6 h-6" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-navy-950">Awaiting Verification Request</h3>
                    <p className="text-xs text-surface-500 max-w-sm mx-auto mt-1 leading-relaxed">
                      Enter a marketing statement or product claim on the left along with technical evidence, specifications, or citations to run Gemini verification.
                    </p>
                  </div>

                  <div className="pt-3 border-t border-surface-100 text-left space-y-2.5 text-xs text-surface-600">
                    <span className="font-semibold text-navy-950 block text-xs">
                      Possible Verification Statuses:
                    </span>
                    <div className="grid grid-cols-1 gap-1.5 text-[11px]">
                      <div className="flex items-center gap-2 text-emerald-800">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                        <span><strong>SUPPORTED:</strong> Direct, sufficient proof exists.</span>
                      </div>
                      <div className="flex items-center gap-2 text-rose-800">
                        <XCircle className="w-3.5 h-3.5 text-rose-600 shrink-0" />
                        <span><strong>CONTRADICTED:</strong> Evidence directly conflicts with claim.</span>
                      </div>
                      <div className="flex items-center gap-2 text-amber-800">
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                        <span><strong>PARTIALLY_SUPPORTED:</strong> Only certain conditions or specs match.</span>
                      </div>
                      <div className="flex items-center gap-2 text-surface-700">
                        <HelpCircle className="w-3.5 h-3.5 text-surface-500 shrink-0" />
                        <span><strong>UNVERIFIABLE:</strong> Evidence lacks necessary data to judge.</span>
                      </div>
                      <div className="flex items-center gap-2 text-purple-800">
                        <Scale className="w-3.5 h-3.5 text-purple-600 shrink-0" />
                        <span><strong>CONFLICTING_EVIDENCE:</strong> Provided sources disagree.</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
        /* SECTION E: Verification History Tab */
        <div className="bg-white rounded-xl border border-surface-200 shadow-card p-6 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-surface-200">
            <div>
              <h2 className="text-base font-bold text-navy-950">Claim Verification History</h2>
              <p className="text-xs text-surface-500">
                Browse and reopen your previous standalone claim verification evaluations
              </p>
            </div>
            {isAuthenticated && (
              <button
                onClick={fetchHistory}
                disabled={isLoadingHistory}
                className="text-xs text-brand-600 hover:text-brand-700 font-medium cursor-pointer"
              >
                Refresh
              </button>
            )}
          </div>

          {!isAuthenticated ? (
            <div className="p-8 text-center space-y-3">
              <ShieldCheck className="w-10 h-10 text-surface-400 mx-auto" />
              <h3 className="text-sm font-semibold text-navy-900">Sign in to save verification history</h3>
              <p className="text-xs text-surface-500 max-w-md mx-auto">
                Completed verifications are permanently saved to your isolated Supabase account when signed in.
              </p>
            </div>
          ) : isLoadingHistory ? (
            <div className="p-12 text-center space-y-2">
              <div className="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto" />
              <p className="text-xs text-surface-500">Loading history records from Supabase...</p>
            </div>
          ) : historyList.length === 0 ? (
            <div className="p-12 text-center space-y-3">
              <FileText className="w-10 h-10 text-surface-300 mx-auto" />
              <h3 className="text-sm font-semibold text-navy-900">No Claim Verifications Yet</h3>
              <p className="text-xs text-surface-500 max-w-sm mx-auto">
                Your completed claim verifications will be recorded here so you can revisit them anytime.
              </p>
              <button
                onClick={() => setActiveTab('verify')}
                className="px-4 py-2 rounded-lg bg-navy-900 text-white text-xs font-semibold hover:bg-navy-800 transition-colors cursor-pointer"
              >
                Verify First Claim
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {historyList.map(record => {
                const badge = getStatusBadge(record.verification_status);
                const dateStr = record.created_at
                  ? new Date(record.created_at).toLocaleDateString(undefined, {
                      month: 'short',
                      day: 'numeric',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })
                  : 'Recent';

                return (
                  <div
                    key={record.id}
                    className="p-4 rounded-xl border border-surface-200 hover:border-surface-300 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-surface-50/40"
                  >
                    <div className="space-y-1.5 flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span
                          className={cn(
                            'px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border',
                            badge.badgeClass
                          )}
                        >
                          {badge.label}
                        </span>
                        {record.confidence && (
                          <span className="text-[11px] text-surface-500 font-mono">
                            {(record.confidence * 100).toFixed(0)}% AI estimate
                          </span>
                        )}
                        <span className="text-[11px] text-surface-400">• {dateStr}</span>
                      </div>

                      <h4 className="text-xs font-bold text-navy-950 truncate">
                        "{record.claim}"
                      </h4>

                      {record.result?.verdict && (
                        <p className="text-xs text-surface-600 line-clamp-1">
                          {record.result.verdict}
                        </p>
                      )}
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        onClick={() => handleReopenHistory(record)}
                        className="px-3 py-1.5 rounded-lg bg-white border border-surface-300 hover:bg-brand-50 hover:text-brand-700 hover:border-brand-300 text-surface-700 text-xs font-semibold transition-colors cursor-pointer"
                      >
                        Reopen
                      </button>
                      <button
                        onClick={() => handleDeleteHistory(record.id)}
                        disabled={deletingId === record.id}
                        className="p-1.5 rounded-lg text-surface-400 hover:text-rose-600 hover:bg-rose-50 transition-colors cursor-pointer"
                        title="Delete record"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
