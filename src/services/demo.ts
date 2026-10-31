// ============================================================
// Demo Analysis Engine
// Produces deterministic, typed sample findings for demonstration.
// This is NOT a real AI engine. It demonstrates the workflow
// and UI with representative data before backend integration.
//
// Demo mode is always visibly identified to users.
// ============================================================

import type {
  Analysis,
  AnalysisRequest,
  Finding,
  FindingCategory,
  FindingSeverity,
  CorrectionRequest,
  CorrectionResult,
  IAnalysisService,
} from '@/types/domain';
import { generateId } from '@/lib/utils';

// -----------------------------------------------------------
// Demo finding templates — representative, deterministic data
// -----------------------------------------------------------

interface FindingTemplate {
  category: FindingCategory;
  severity: FindingSeverity;
  trigger: string; // substring that triggers this finding
  originalExcerpt: (match: string) => string;
  suggestedCorrection: (match: string) => string;
  explanation: string;
  rule: string;
}

const FINDING_TEMPLATES: FindingTemplate[] = [
  {
    category: 'grammar',
    severity: 'major',
    trigger: 'alot',
    originalExcerpt: () => 'alot',
    suggestedCorrection: () => 'a lot',
    explanation: '"alot" is not a recognised word. The correct form is "a lot" (two words) for expressing a large quantity.',
    rule: 'Grammar: Spelling of compound expressions',
  },
  {
    category: 'grammar',
    severity: 'major',
    trigger: 'their is',
    originalExcerpt: () => 'their is',
    suggestedCorrection: () => 'there is',
    explanation: '"Their" is a possessive pronoun. The correct word here is "there," which indicates location or existence.',
    rule: 'Grammar: Homophone confusion',
  },
  {
    category: 'grammar',
    severity: 'major',
    trigger: "it's",
    originalExcerpt: () => "it's",
    suggestedCorrection: () => 'its',
    explanation: '"It\'s" is a contraction of "it is." If used as a possessive (e.g. "the company and its values"), use "its" without an apostrophe.',
    rule: 'Grammar: Apostrophe use',
  },
  {
    category: 'spelling',
    severity: 'major',
    trigger: 'recieve',
    originalExcerpt: () => 'recieve',
    suggestedCorrection: () => 'receive',
    explanation: 'Common spelling error. Remember: "i before e, except after c" — the correct spelling is "receive".',
    rule: 'Spelling: Common misspelling',
  },
  {
    category: 'spelling',
    severity: 'major',
    trigger: 'occured',
    originalExcerpt: () => 'occured',
    suggestedCorrection: () => 'occurred',
    explanation: '"Occurred" requires double "c" and double "r." The correct spelling is "occurred".',
    rule: 'Spelling: Double consonant',
  },
  {
    category: 'spelling',
    severity: 'major',
    trigger: 'seperate',
    originalExcerpt: () => 'seperate',
    suggestedCorrection: () => 'separate',
    explanation: 'A frequently misspelled word. The correct spelling is "separate" — note the "par" in the middle.',
    rule: 'Spelling: Common misspelling',
  },
  {
    category: 'clarity',
    severity: 'minor',
    trigger: 'in order to',
    originalExcerpt: () => 'in order to',
    suggestedCorrection: () => 'to',
    explanation: '"In order to" is a wordy phrase. Replacing it with simply "to" makes the sentence cleaner and more direct without changing its meaning.',
    rule: 'Style: Wordiness',
  },
  {
    category: 'clarity',
    severity: 'minor',
    trigger: 'due to the fact that',
    originalExcerpt: () => 'due to the fact that',
    suggestedCorrection: () => 'because',
    explanation: '"Due to the fact that" is an unnecessarily verbose phrase. Use "because" for concise, professional writing.',
    rule: 'Style: Redundant phrasing',
  },
  {
    category: 'style',
    severity: 'minor',
    trigger: 'utilize',
    originalExcerpt: () => 'utilize',
    suggestedCorrection: () => 'use',
    explanation: '"Utilize" adds no meaning beyond "use" in most contexts and can sound unnecessarily formal. Prefer the simpler word.',
    rule: 'Style: Plain language preference',
  },
  {
    category: 'brand_voice',
    severity: 'info',
    trigger: 'leverage',
    originalExcerpt: () => 'leverage',
    suggestedCorrection: () => 'use',
    explanation: '"Leverage" as a verb is business jargon. Consider using plain language to communicate your brand voice clearly.',
    rule: 'Brand voice: Avoid business jargon',
  },
  {
    category: 'punctuation',
    severity: 'minor',
    trigger: '  ',
    originalExcerpt: () => 'double space',
    suggestedCorrection: () => 'single space',
    explanation: 'Multiple consecutive spaces were found. Standard typographic convention uses a single space between words and after punctuation.',
    rule: 'Punctuation: Spacing consistency',
  },
  {
    category: 'readability',
    severity: 'info',
    trigger: 'very very',
    originalExcerpt: () => 'very very',
    suggestedCorrection: () => 'extremely',
    explanation: 'Repeating intensifiers like "very very" weakens writing. A stronger adverb or adjective makes for more precise, professional copy.',
    rule: 'Style: Intensifier overuse',
  },
  {
    category: 'terminology',
    severity: 'minor',
    trigger: 'e-mail',
    originalExcerpt: () => 'e-mail',
    suggestedCorrection: () => 'email',
    explanation: 'The hyphenated form "e-mail" is outdated. Modern style guides and brand standards prefer the single word "email".',
    rule: 'Terminology: Modern usage',
  },
  {
    category: 'grammar',
    severity: 'major',
    trigger: "they're",
    originalExcerpt: () => "they're",
    suggestedCorrection: () => 'their',
    explanation: '"They\'re" is a contraction of "they are." If you mean to indicate possession, use "their" instead.',
    rule: 'Grammar: Homophone confusion',
  },
  {
    category: 'clarity',
    severity: 'minor',
    trigger: 'at this point in time',
    originalExcerpt: () => 'at this point in time',
    suggestedCorrection: () => 'now',
    explanation: '"At this point in time" is unnecessarily verbose. The single word "now" or "currently" conveys the same meaning more concisely.',
    rule: 'Style: Redundant phrasing',
  },
];

// -----------------------------------------------------------
// Deterministic finding generation
// -----------------------------------------------------------

function detectFindings(content: string): Finding[] {
  const findings: Finding[] = [];
  const lowerContent = content.toLowerCase();

  for (const template of FINDING_TEMPLATES) {
    if (lowerContent.includes(template.trigger.toLowerCase())) {
      // Find the actual occurrence in original case
      const idx = lowerContent.indexOf(template.trigger.toLowerCase());
      const actualMatch = content.substring(idx, idx + template.trigger.length);

      findings.push({
        id: generateId(),
        category: template.category,
        severity: template.severity,
        originalExcerpt: template.originalExcerpt(actualMatch),
        suggestedCorrection: template.suggestedCorrection(actualMatch),
        explanation: template.explanation,
        rule: template.rule,
        // No confidence or sourceOffset in demo mode — these require backend
        isDemo: true,
      });
    }
  }

  // If no findings were detected from templates, add a single representative one
  // for content that's longer than a minimal threshold
  if (findings.length === 0 && content.trim().length > 50) {
    findings.push({
      id: generateId(),
      category: 'style',
      severity: 'info',
      originalExcerpt: 'content',
      suggestedCorrection: 'content',
      explanation: 'No significant language issues were detected in this demo analysis. The content appears well-written based on the demo checks. A real AI analysis would perform deeper semantic, brand-voice, and context-specific evaluation.',
      rule: 'Demo: No issues detected',
      isDemo: true,
    });
  }

  return findings;
}

// For very short content — return a simulated analysis with a note
function getShortContentFindings(): Finding[] {
  return [
    {
      id: generateId(),
      category: 'other',
      severity: 'info',
      originalExcerpt: '(full content)',
      suggestedCorrection: '(full content)',
      explanation: 'The provided content is very short. For best results, provide at least a paragraph of content. Demo analysis runs on available text.',
      rule: 'Demo: Content length guidance',
      isDemo: true,
    },
  ];
}

// -----------------------------------------------------------
// Demo correction algorithm
// Safe, deterministic string replacement.
// -----------------------------------------------------------

function applyCorrections(
  content: string,
  selectedFindings: Finding[]
): { correctedContent: string; appliedIds: string[]; conflictedIds: string[] } {
  let corrected = content;
  const appliedIds: string[] = [];
  const conflictedIds: string[] = [];

  for (const finding of selectedFindings) {
    const { originalExcerpt, suggestedCorrection } = finding;

    // Skip meta-findings with no real replacement
    if (
      originalExcerpt === suggestedCorrection ||
      originalExcerpt === '(full content)' ||
      originalExcerpt === 'content' ||
      originalExcerpt === 'double space'
    ) {
      // Handle double space specially
      if (originalExcerpt === 'double space') {
        corrected = corrected.replace(/  +/g, ' ');
        appliedIds.push(finding.id);
      } else {
        conflictedIds.push(finding.id);
      }
      continue;
    }

    if (corrected.includes(originalExcerpt)) {
      corrected = corrected.replace(originalExcerpt, suggestedCorrection);
      appliedIds.push(finding.id);
    } else {
      // Try case-insensitive match
      const regex = new RegExp(
        originalExcerpt.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'),
        'i'
      );
      if (regex.test(corrected)) {
        corrected = corrected.replace(regex, suggestedCorrection);
        appliedIds.push(finding.id);
      } else {
        conflictedIds.push(finding.id);
      }
    }
  }

  return { correctedContent: corrected, appliedIds, conflictedIds };
}

// -----------------------------------------------------------
// Demo Analysis Service implementation
// -----------------------------------------------------------

const DEMO_PROCESSING_DELAY_MS = 2200; // Realistic demo delay

export const demoAnalysisService: IAnalysisService = {
  async analyze(request: AnalysisRequest): Promise<Analysis> {
    // Simulate async processing
    await new Promise(resolve => setTimeout(resolve, DEMO_PROCESSING_DELAY_MS));

    const { content, sourceType, fileName, contentType, targetAudience, language, writingInstructions } = request;
    const id = generateId();
    const now = new Date().toISOString();

    const trimmedContent = content.trim();
    const findings =
      trimmedContent.length < 20
        ? getShortContentFindings()
        : detectFindings(trimmedContent);

    const hasRealFindings = findings.some(f => f.category !== 'other' && f.rule !== 'Demo: Content length guidance');

    const analysis: Analysis = {
      id,
      name: fileName
        ? fileName.replace(/\.[^.]+$/, '')
        : `Analysis — ${new Date().toLocaleString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}`,
      sourceType,
      originalContent: content,
      fileName,
      contentType,
      targetAudience,
      language,
      writingInstructions,
      status: hasRealFindings ? 'completed' : 'no_findings',
      findings,
      selectedFindingIds: [],
      reviewStatus: 'not_started',
      isDemo: true,
      createdAt: now,
      updatedAt: now,
    };

    return analysis;
  },

  async correct(request: CorrectionRequest): Promise<CorrectionResult> {
    await new Promise(resolve => setTimeout(resolve, 600));

    const selectedFindings = request.findings.filter(f =>
      request.selectedFindingIds.includes(f.id)
    );

    const { correctedContent, appliedIds, conflictedIds } = applyCorrections(
      request.originalContent,
      selectedFindings
    );

    return {
      correctedContent,
      appliedFindingIds: appliedIds,
      conflictedFindingIds: conflictedIds,
      hasConflicts: conflictedIds.length > 0,
    };
  },

  async getAnalysis(id: string): Promise<Analysis | null> {
    return analysisStorage.getById(id);
  },
};

// -----------------------------------------------------------
// Demo History Service
// -----------------------------------------------------------

import type { IHistoryService } from '@/types/domain';
import { analysisStorage } from './persistence';

export const demoHistoryService: IHistoryService = {
  async list(): Promise<Analysis[]> {
    return analysisStorage.list();
  },

  async save(analysis: Analysis): Promise<void> {
    analysisStorage.save(analysis);
  },

  async delete(id: string): Promise<void> {
    analysisStorage.delete(id);
  },

  async clear(): Promise<void> {
    analysisStorage.clear();
  },
};

// -----------------------------------------------------------
// Demo Feedback Service
// -----------------------------------------------------------

import type { FindingFeedback, IFeedbackService } from '@/types/domain';
import { feedbackStorage } from './persistence';

export const demoFeedbackService: IFeedbackService = {
  async save(feedback: FindingFeedback): Promise<void> {
    feedbackStorage.save(feedback);
  },

  async getForAnalysis(analysisId: string): Promise<FindingFeedback[]> {
    return feedbackStorage.getForAnalysis(analysisId);
  },

  async delete(id: string): Promise<void> {
    feedbackStorage.delete(id);
  },
};

// -----------------------------------------------------------
// Demo Brand Service
// -----------------------------------------------------------

import type { BrandProfile, IBrandService } from '@/types/domain';
import { brandStorage } from './persistence';

const DEFAULT_BRAND_PROFILE: BrandProfile = {
  id: 'default',
  name: 'My Brand',
  description: 'Enter a brief description of your brand and what it stands for.',
  voiceAndTone: 'Professional, clear, and approachable. We communicate with confidence and warmth.',
  targetAudience: 'Business professionals and decision-makers in mid-market and enterprise organizations.',
  preferredTerminology: ['email', 'use', 'build', 'customer'],
  prohibitedPhrases: ['leverage', 'synergy', 'disruptive', 'paradigm shift'],
  writingRules: [
    'Use active voice wherever possible.',
    'Keep sentences under 25 words.',
    'Avoid jargon and corporate buzzwords.',
    'Use plain, direct language.',
  ],
  brandInstructions: '',
  guidelineNotes: '',
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
};

export const demoBrandService: IBrandService = {
  async get(): Promise<BrandProfile | null> {
    return brandStorage.get() ?? DEFAULT_BRAND_PROFILE;
  },

  async save(profile: BrandProfile): Promise<void> {
    brandStorage.save({ ...profile, updatedAt: new Date().toISOString() });
  },

  async reset(): Promise<void> {
    brandStorage.reset();
  },
};

// -----------------------------------------------------------
// Service registry — switch between demo and live adapters
// -----------------------------------------------------------

import { liveAnalysisService, liveHistoryService } from './live';

export const IS_DEMO_MODE = false; // Live AI & Supabase Database Mode

export const analysisService: IAnalysisService = IS_DEMO_MODE ? demoAnalysisService : liveAnalysisService;
export const historyService: IHistoryService = IS_DEMO_MODE ? demoHistoryService : liveHistoryService;
export const feedbackService: IFeedbackService = demoFeedbackService;
export const brandService: IBrandService = demoBrandService;
