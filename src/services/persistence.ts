// ============================================================
// Local Persistence Layer
// Provides versioned, validated browser storage for demo mode.
// All storage operations are isolated from UI components.
// ============================================================

import type { Analysis, FindingFeedback, BrandProfile, StoredData } from '@/types/domain';
import { STORAGE_SCHEMA_VERSION } from '@/types/domain';

// Storage Keys
const KEYS = {
  ANALYSES: 'brandproof_analyses_v1',
  FEEDBACK: 'brandproof_feedback_v1',
  BRAND_PROFILE: 'brandproof_brand_profile_v1',
} as const;

// -----------------------------------------------------------
// Low-level storage helpers
// -----------------------------------------------------------

function store<T>(key: string, data: T): void {
  try {
    const wrapped: StoredData<T> = {
      version: STORAGE_SCHEMA_VERSION,
      data,
      savedAt: new Date().toISOString(),
    };
    localStorage.setItem(key, JSON.stringify(wrapped));
  } catch (err) {
    console.warn('[BrandProof] Storage write failed:', err);
  }
}

function retrieve<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    const parsed: StoredData<T> = JSON.parse(raw);
    if (!parsed || !parsed.version || parsed.data === undefined) {
      return fallback;
    }
    return parsed.data;
  } catch (err) {
    console.warn('[BrandProof] Storage read failed:', err);
    return fallback;
  }
}

function remove(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch (err) {
    console.warn('[BrandProof] Storage remove failed:', err);
  }
}

// -----------------------------------------------------------
// Analysis History Storage
// -----------------------------------------------------------

export const analysisStorage = {
  list(): Analysis[] {
    return retrieve<Analysis[]>(KEYS.ANALYSES, []);
  },

  save(analysis: Analysis): void {
    const current = this.list();
    const index = current.findIndex(a => a.id === analysis.id);
    if (index >= 0) {
      current[index] = analysis;
    } else {
      current.unshift(analysis);
    }
    store(KEYS.ANALYSES, current);
  },

  delete(id: string): void {
    const current = this.list().filter(a => a.id !== id);
    store(KEYS.ANALYSES, current);
  },

  clear(): void {
    remove(KEYS.ANALYSES);
  },

  getById(id: string): Analysis | null {
    return this.list().find(a => a.id === id) ?? null;
  },
};

// -----------------------------------------------------------
// Feedback Storage
// -----------------------------------------------------------

export const feedbackStorage = {
  list(): FindingFeedback[] {
    return retrieve<FindingFeedback[]>(KEYS.FEEDBACK, []);
  },

  save(feedback: FindingFeedback): void {
    const current = this.list();
    const index = current.findIndex(f => f.id === feedback.id);
    if (index >= 0) {
      current[index] = { ...feedback, updatedAt: new Date().toISOString() };
    } else {
      current.push(feedback);
    }
    store(KEYS.FEEDBACK, current);
  },

  getForAnalysis(analysisId: string): FindingFeedback[] {
    return this.list().filter(f => f.analysisId === analysisId);
  },

  delete(id: string): void {
    const current = this.list().filter(f => f.id !== id);
    store(KEYS.FEEDBACK, current);
  },

  clearForAnalysis(analysisId: string): void {
    const current = this.list().filter(f => f.analysisId !== analysisId);
    store(KEYS.FEEDBACK, current);
  },

  clearAll(): void {
    remove(KEYS.FEEDBACK);
  },
};

// -----------------------------------------------------------
// Brand Profile Storage
// -----------------------------------------------------------

export const brandStorage = {
  get(): BrandProfile | null {
    return retrieve<BrandProfile | null>(KEYS.BRAND_PROFILE, null);
  },

  save(profile: BrandProfile): void {
    store(KEYS.BRAND_PROFILE, profile);
  },

  reset(): void {
    remove(KEYS.BRAND_PROFILE);
  },
};

// -----------------------------------------------------------
// Full Reset (for demo management)
// -----------------------------------------------------------

export function clearAllDemoData(): void {
  analysisStorage.clear();
  feedbackStorage.clearAll();
  brandStorage.reset();
}
