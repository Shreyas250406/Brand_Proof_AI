// ============================================================
// Live AI & Database Adapters for BrandProof AI
// Connects frontend to FastAPI Backend + Supabase PostgreSQL
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
  IHistoryService,
} from '@/types/domain';
import { generateId } from '@/lib/utils';
import { authService } from './auth';

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');
const API_BASE = `${BASE_URL}/api/v1/ai`;

function getAuthHeaders(): HeadersInit {
  const token = authService.getToken();
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

function mapBackendSeverity(sev: string): FindingSeverity {
  const s = (sev || 'medium').toLowerCase();
  if (s === 'high' || s === 'critical') return 'critical';
  if (s === 'medium' || s === 'major') return 'major';
  if (s === 'low' || s === 'minor') return 'minor';
  return 'info';
}

function mapBackendCategory(cat: string): FindingCategory {
  const c = (cat || 'grammar').toLowerCase().replace('-', '_');
  const valid: FindingCategory[] = [
    'grammar',
    'spelling',
    'punctuation',
    'style',
    'clarity',
    'brand_voice',
    'terminology',
    'prohibited',
    'readability',
    'consistency',
    'factual_claim',
    'seo',
    'other',
  ];
  return valid.includes(c as FindingCategory) ? (c as FindingCategory) : 'other';
}

export const liveAnalysisService: IAnalysisService = {
  async analyze(request: AnalysisRequest): Promise<Analysis> {
    const isImage = !!request.file && request.file.type.startsWith('image/');

    let backendData: {
      id?: string;
      original_text: string;
      corrected_text: string;
      findings: Array<{
        id: string;
        category: string;
        severity: string;
        original_text: string;
        suggestion: string;
        explanation: string;
        confidence?: number;
        start_offset?: number;
        end_offset?: number;
      }>;
      summary: {
        assessment: string;
        total_findings?: number;
      };
      created_at?: string;
    };

    if (isImage && request.file) {
      const formData = new FormData();
      formData.append('file', request.file);
      if (request.language) formData.append('language', request.language);
      if (request.contentType) formData.append('content_type', request.contentType);
      if (request.targetAudience) formData.append('target_audience', request.targetAudience);
      if (request.specialInstructions) formData.append('instructions', request.specialInstructions);
      if (request.brandGuidelines) formData.append('brand_context', request.brandGuidelines);

      const token = authService.getToken();
      const headers: HeadersInit = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const res = await fetch(`${API_BASE}/analyze-image`, {
        method: 'POST',
        headers,
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail?.message || err.message || 'Image analysis failed.');
      }
      backendData = await res.json();
    } else {
      const payload = {
        text: request.content,
        language: request.language || 'English',
        content_type: request.contentType || null,
        target_audience: request.targetAudience || null,
        instructions: request.specialInstructions || null,
        brand_context: request.brandGuidelines || null,
      };

      const res = await fetch(`${API_BASE}/analyze-text`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail?.message || err.message || 'Text analysis failed.');
      }
      backendData = await res.json();
    }

    const findings: Finding[] = (backendData.findings || []).map((f, idx) => ({
      id: f.id || `finding-${idx + 1}`,
      category: mapBackendCategory(f.category),
      severity: mapBackendSeverity(f.severity),
      originalExcerpt: f.original_text,
      suggestedCorrection: f.suggestion,
      explanation: f.explanation,
      confidence: f.confidence,
      sourceOffset:
        f.start_offset !== undefined && f.end_offset !== undefined
          ? { start: f.start_offset, end: f.end_offset }
          : undefined,
      isDemo: false,
    }));

    const now = new Date().toISOString();
    const name = request.fileName
      ? request.fileName.replace(/\.[^.]+$/, '')
      : `Analysis — ${new Date().toLocaleString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}`;

    const analysis: Analysis = {
      id: backendData.id || generateId(),
      name,
      sourceType: request.sourceType,
      originalContent: backendData.original_text || request.content,
      fileName: request.file?.name,
      fileSize: request.file?.size,
      contentType: request.contentType,
      targetAudience: request.targetAudience,
      language: request.language,
      writingInstructions: request.writingInstructions || request.specialInstructions,
      status: findings.length === 0 ? 'no_findings' : 'completed',
      findings,
      selectedFindingIds: [],
      reviewStatus: 'not_started',
      correctedContent: backendData.corrected_text || request.content,
      isDemo: false,
      createdAt: backendData.created_at || now,
      updatedAt: now,
    };

    return analysis;
  },

  async correct(request: CorrectionRequest): Promise<CorrectionResult> {
    const selectedFindings = request.findings.filter(f =>
      request.selectedFindingIds.includes(f.id)
    );

    let corrected = request.originalContent;
    const appliedFindingIds: string[] = [];
    const conflictedFindingIds: string[] = [];

    for (const finding of selectedFindings) {
      const { originalExcerpt, suggestedCorrection } = finding;
      if (!originalExcerpt || !suggestedCorrection) {
        conflictedFindingIds.push(finding.id);
        continue;
      }
      if (corrected.includes(originalExcerpt)) {
        corrected = corrected.replace(originalExcerpt, suggestedCorrection);
        appliedFindingIds.push(finding.id);
      } else {
        const regex = new RegExp(
          originalExcerpt.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'),
          'i'
        );
        if (regex.test(corrected)) {
          corrected = corrected.replace(regex, suggestedCorrection);
          appliedFindingIds.push(finding.id);
        } else {
          conflictedFindingIds.push(finding.id);
        }
      }
    }

    return {
      correctedContent: corrected,
      appliedFindingIds,
      conflictedFindingIds,
      hasConflicts: conflictedFindingIds.length > 0,
    };
  },

  async getAnalysis(id: string): Promise<Analysis | null> {
    try {
      const res = await fetch(`${API_BASE}/history/${id}`, {
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        const item = await res.json();
        return liveHistoryService.convertHistoryItem(item);
      }
    } catch {
      // Fallback
    }
    return null;
  },
};

export const liveHistoryService: IHistoryService & {
  convertHistoryItem: (item: Record<string, unknown>) => Analysis;
} = {
  convertHistoryItem(item: Record<string, unknown>): Analysis {
    const rawFindings = (item.findings as Array<Record<string, unknown>>) || [];
    const findings: Finding[] = rawFindings.map((f, idx) => ({
      id: (f.id as string) || `finding-${idx + 1}`,
      category: mapBackendCategory(f.category as string),
      severity: mapBackendSeverity(f.severity as string),
      originalExcerpt: (f.original_text as string) || '',
      suggestedCorrection: (f.suggestion as string) || '',
      explanation: (f.explanation as string) || '',
      confidence: f.confidence as number | undefined,
      isDemo: false,
    }));

    const createdAt = (item.created_at as string) || new Date().toISOString();
    const orig = (item.original_text as string) || '';
    const name = orig.slice(0, 30).trim() || 'Analysis';

    return {
      id: item.id as string,
      name,
      sourceType: ((item.input_type as string) === 'image' ? 'file_image' : 'text'),
      originalContent: orig,
      status: findings.length === 0 ? 'no_findings' : 'completed',
      findings,
      selectedFindingIds: [],
      reviewStatus: 'not_started',
      correctedContent: (item.corrected_text as string) || orig,
      isDemo: false,
      createdAt,
      updatedAt: createdAt,
    };
  },

  async list(): Promise<Analysis[]> {
    try {
      const res = await fetch(`${API_BASE}/history?limit=50`, {
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        const items = data.items || [];
        return items.map((i: Record<string, unknown>) => this.convertHistoryItem(i));
      }
    } catch (err) {
      console.warn('Could not load history from backend:', err);
    }
    return [];
  },

  async save(analysis: Analysis): Promise<void> {
    // The backend automatically saves upon /analyze-text and /analyze-image
    console.info('Analysis saved to live database:', analysis.id);
  },

  async delete(id: string): Promise<void> {
    try {
      await fetch(`${API_BASE}/history/${id}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      });
    } catch (err) {
      console.error('Failed to delete analysis from backend:', err);
    }
  },

  async clear(): Promise<void> {
    // Handled per item
  },
};
