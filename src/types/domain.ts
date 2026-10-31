// ============================================================
// BrandProof AI — Domain Models
// These types define the core data contracts for the application.
// They serve as the shared interface between UI components,
// demo services, and future backend adapters.
// ============================================================

// -----------------------------------------------------------
// Severity and Category Enums
// -----------------------------------------------------------

export type FindingSeverity = 'critical' | 'major' | 'minor' | 'info';

export type FindingCategory =
  | 'grammar'
  | 'spelling'
  | 'punctuation'
  | 'style'
  | 'clarity'
  | 'brand_voice'
  | 'terminology'
  | 'prohibited'
  | 'readability'
  | 'consistency'
  | 'factual_claim'
  | 'seo'
  | 'other';

export type SourceType =
  | 'text'
  | 'file_text'
  | 'file_pdf'
  | 'file_word'
  | 'file_image'
  | 'file_video'
  | 'file_audio'
  | 'url';

export type AnalysisStatus =
  | 'pending'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'no_findings';

export type ReviewStatus =
  | 'not_started'
  | 'in_progress'
  | 'corrections_applied'
  | 'completed';

export type FeedbackCategory =
  | 'genuine_error'
  | 'false_positive'
  | 'stylistic_choice'
  | 'unsure';

// -----------------------------------------------------------
// Source Offsets — only trust when provided by backend
// -----------------------------------------------------------

export interface SourceOffset {
  start: number;
  end: number;
  line?: number;
  column?: number;
}

// -----------------------------------------------------------
// Finding — a single detected issue
// -----------------------------------------------------------

export interface Finding {
  id: string;
  category: FindingCategory;
  severity: FindingSeverity;
  originalExcerpt: string;
  suggestedCorrection: string;
  explanation: string;
  rule?: string;
  confidence?: number; // 0–1, only if provided by the analysis service
  sourceOffset?: SourceOffset; // Only include if the backend provides reliable offsets
  timestamp?: string; // e.g. "00:15" where the error occurs in media
  mediaType?: 'speech' | 'visual' | 'combined' | 'text';
  isDemo: boolean;
}

// -----------------------------------------------------------
// Analysis — a single content analysis session
// -----------------------------------------------------------

export interface Analysis {
  id: string;
  name: string;
  sourceType: SourceType;
  originalContent: string;
  fileName?: string;
  fileSize?: number;
  contentType?: string;
  targetAudience?: string;
  language?: string;
  writingInstructions?: string;
  brandProfileId?: string;
  status: AnalysisStatus;
  findings: Finding[];
  selectedFindingIds: string[];
  correctedContent?: string;
  reviewStatus: ReviewStatus;
  isDemo: boolean;
  createdAt: string; // ISO 8601
  updatedAt: string; // ISO 8601
  summary?: string;
  errorMessage?: string;
}

// -----------------------------------------------------------
// Feedback — human review of a single finding
// -----------------------------------------------------------

export interface FindingFeedback {
  id: string;
  analysisId: string;
  findingId: string;
  originalContent: string;
  selectedCorrection?: string;
  category: FeedbackCategory;
  comment?: string;
  submittedAt: string; // ISO 8601
  updatedAt?: string; // ISO 8601
}

// -----------------------------------------------------------
// Brand Profile — editable brand knowledge
// -----------------------------------------------------------

export interface BrandProfile {
  id: string;
  name: string;
  description?: string;
  voiceAndTone?: string;
  targetAudience?: string;
  preferredTerminology: string[];
  prohibitedPhrases: string[];
  writingRules: string[];
  brandInstructions?: string;
  guidelineNotes?: string;
  createdAt: string; // ISO 8601
  updatedAt: string; // ISO 8601
}

// -----------------------------------------------------------
// Analysis Request — what the UI sends to the analysis service
// -----------------------------------------------------------

export interface AnalysisRequest {
  content: string;
  sourceType: SourceType;
  file?: File;
  fileName?: string;
  contentType?: string;
  targetAudience?: string;
  language?: string;
  writingInstructions?: string;
  specialInstructions?: string;
  brandGuidelines?: string;
  brandProfile?: BrandProfile;
}

// -----------------------------------------------------------
// Correction Request
// -----------------------------------------------------------

export interface CorrectionRequest {
  analysisId: string;
  selectedFindingIds: string[];
  originalContent: string;
  findings: Finding[];
}

export interface CorrectionResult {
  correctedContent: string;
  appliedFindingIds: string[];
  conflictedFindingIds: string[];
  hasConflicts: boolean;
}

// -----------------------------------------------------------
// Service Interfaces — implemented by demo adapters and
// future live API adapters. UI components depend only on these.
// -----------------------------------------------------------

export interface IAnalysisService {
  analyze(request: AnalysisRequest): Promise<Analysis>;
  correct(request: CorrectionRequest): Promise<CorrectionResult>;
  getAnalysis(id: string): Promise<Analysis | null>;
}

export interface IHistoryService {
  list(): Promise<Analysis[]>;
  save(analysis: Analysis): Promise<void>;
  delete(id: string): Promise<void>;
  clear(): Promise<void>;
}

export interface IFeedbackService {
  save(feedback: FindingFeedback): Promise<void>;
  getForAnalysis(analysisId: string): Promise<FindingFeedback[]>;
  delete(id: string): Promise<void>;
}

export interface IBrandService {
  get(): Promise<BrandProfile | null>;
  save(profile: BrandProfile): Promise<void>;
  reset(): Promise<void>;
}

// -----------------------------------------------------------
// UI State Types (not persisted, only in-memory/session)
// -----------------------------------------------------------

export interface AnalysisFilters {
  categories: FindingCategory[];
  severities: FindingSeverity[];
  searchQuery: string;
}

export interface HistoryFilters {
  searchQuery: string;
  sourceTypes: SourceType[];
  statuses: AnalysisStatus[];
  reviewStatuses: ReviewStatus[];
  sortBy: 'date_desc' | 'date_asc' | 'name_asc' | 'findings_desc';
}

// -----------------------------------------------------------
// Storage Schema Version
// -----------------------------------------------------------

export const STORAGE_SCHEMA_VERSION = '1.0.0';

export interface StoredData<T> {
  version: string;
  data: T;
  savedAt: string;
}
