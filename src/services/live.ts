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
  UserImprovementSuggestion,
  UserImprovementsResult,
  ApplyUserImprovementsResult,
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
    const isMedia = !!request.file && (
      request.file.type.startsWith('video/') ||
      request.file.type.startsWith('audio/') ||
      /\.(mp3|mp4|wav|m4a|webm|mov|ogg)$/i.test(request.file.name)
    );
    const isUrl = request.sourceType === 'url' || /^https?:\/\//i.test((request.content || '').trim());

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
        timestamp?: string;
        media_type?: string;
      }>;
      summary: {
        assessment?: string;
        total_findings?: number;
      };
      created_at?: string;
    };

    if (isUrl) {
      const payload = {
        url: request.content.trim(),
        max_pages: request.maxPages || 1,
        language: request.language || 'English',
        content_type: request.contentType || 'Website Copy',
        target_audience: request.targetAudience || null,
        custom_instructions: request.specialInstructions
          ? [request.specialInstructions]
          : (request.writingInstructions ? [request.writingInstructions] : []),
        brand_guidelines: request.brandGuidelines
          ? [request.brandGuidelines]
          : (request.brandProfile?.writingRules || []),
        save_history: true,
      };

      const res = await fetch(`${API_BASE}/analyze-website`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail?.message || err.message || 'Website scraping and analysis failed.');
      }
      const websiteData = await res.json();

      backendData = {
        id: websiteData.id,
        original_text: websiteData.content_summary || `Website: ${websiteData.website_url}`,
        corrected_text: websiteData.content_summary || `Website: ${websiteData.website_url}`,
        findings: (websiteData.findings || []).map((f: Record<string, unknown>, idx: number) => ({
          id: (f.id as string) || `finding-${idx + 1}`,
          category: (f.category as string) || 'clarity',
          severity: (f.severity as string) || 'medium',
          original_text: (f.original_text as string) || '',
          suggestion: (f.suggested_text as string) || '',
          explanation: (f.explanation as string) || '',
          timestamp: f.section ? `Section: ${f.section}` : undefined,
        })),
        summary: {
          assessment: websiteData.content_summary || 'Website analysis completed successfully.',
          total_findings: (websiteData.findings || []).length,
        },
        created_at: websiteData.created_at,
      };
    } else if (isMedia && request.file) {
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

      const res = await fetch(`${API_BASE}/analyze-media`, {
        method: 'POST',
        headers,
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail?.message || err.message || 'Speech & Video analysis failed.');
      }
      backendData = await res.json();
    } else if (isImage && request.file) {
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
      timestamp: f.timestamp || undefined,
      mediaType: (f.media_type as 'speech' | 'visual' | 'combined' | 'text') || undefined,
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
      timestamp: (f.timestamp as string) || undefined,
      mediaType: (f.media_type as 'speech' | 'visual' | 'combined' | 'text') || undefined,
      sourceOffset:
        f.start_offset !== undefined && f.end_offset !== undefined
          ? { start: Number(f.start_offset), end: Number(f.end_offset) }
          : undefined,
      isDemo: false,
    }));

    const createdAt = (item.created_at as string) || new Date().toISOString();
    const orig = (item.original_text as string) || '';
    const corrected = (item.corrected_text as string) || orig;
    const name = orig.slice(0, 30).trim() || 'Analysis';

    let reviewStatus: 'not_started' | 'in_progress' | 'corrections_applied' | 'completed' = 'not_started';
    if (orig && corrected && orig !== corrected) {
      reviewStatus = 'corrections_applied';
    } else if (findings.length === 0) {
      reviewStatus = 'completed';
    }

    return {
      id: item.id as string,
      name,
      sourceType: ((item.input_type as string) === 'image' ? 'file_image' : 'text'),
      originalContent: orig,
      status: findings.length === 0 ? 'no_findings' : 'completed',
      findings,
      selectedFindingIds: [],
      reviewStatus,
      correctedContent: corrected,
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
    if (!analysis.id) {
      console.warn('Cannot save analysis without an ID');
      return;
    }

    const payload = {
      corrected_text: analysis.correctedContent,
      findings: analysis.findings.map(f => ({
        id: f.id,
        category: f.category,
        severity: f.severity,
        original_text: f.originalExcerpt,
        suggestion: f.suggestedCorrection,
        explanation: f.explanation,
        confidence: f.confidence,
        start_offset: f.sourceOffset?.start,
        end_offset: f.sourceOffset?.end,
      })),
    };

    try {
      const res = await fetch(`${API_BASE}/history/${analysis.id}`, {
        method: 'PATCH',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        console.warn('Failed to update analysis history in database:', err);
      }
    } catch (err) {
      console.warn('Network error saving analysis history:', err);
    }
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
    try {
      const items = await this.list();
      await Promise.all(items.map(item => this.delete(item.id)));
    } catch (err) {
      console.warn('Failed to clear live history:', err);
    }
  },
};

export const liveUserImprovementsService = {
  async generate(params: {
    originalContent: string;
    userInstructions: string;
    existingFindings?: Array<Record<string, unknown>>;
    context?: {
      content_type?: string;
      target_audience?: string;
      language?: string;
      brand_guidelines?: string[];
      preserved_entities?: string[];
    };
    analysisId?: string;
  }): Promise<UserImprovementsResult> {
    const res = await fetch(`${API_BASE}/user-improvements/generate`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        original_content: params.originalContent,
        user_instructions: params.userInstructions,
        existing_findings: params.existingFindings || [],
        context: params.context || {},
        analysis_id: params.analysisId,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail?.message || err.message || 'Failed to generate improvements.');
    }
    return res.json();
  },

  async apply(params: {
    originalContent: string;
    suggestions: UserImprovementSuggestion[];
    analysisId?: string;
    saveHistory?: boolean;
  }): Promise<ApplyUserImprovementsResult> {
    const res = await fetch(`${API_BASE}/user-improvements/apply`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        original_content: params.originalContent,
        suggestions: params.suggestions,
        analysis_id: params.analysisId,
        save_history: params.saveHistory ?? true,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail?.message || err.message || 'Failed to apply improvements.');
    }
    return res.json();
  },

  async regenerate(params: {
    originalContent: string;
    newInstructions: string;
    previousSuggestions?: UserImprovementSuggestion[];
    existingFindings?: Array<Record<string, unknown>>;
    context?: {
      content_type?: string;
      target_audience?: string;
      language?: string;
      brand_guidelines?: string[];
      preserved_entities?: string[];
    };
    analysisId?: string;
  }): Promise<UserImprovementsResult> {
    const res = await fetch(`${API_BASE}/user-improvements/regenerate`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        original_content: params.originalContent,
        new_instructions: params.newInstructions,
        previous_suggestions: params.previousSuggestions || [],
        existing_findings: params.existingFindings || [],
        context: params.context || {},
        analysis_id: params.analysisId,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail?.message || err.message || 'Failed to regenerate improvements.');
    }
    return res.json();
  },
};

export const liveWebsiteService = {
  async analyzeWebsite(params: {
    url: string;
    maxPages?: number;
    timeout?: number;
    brandName?: string;
    targetAudience?: string;
    contentType?: string;
    language?: string;
    brandGuidelines?: string[];
    preferredTerminology?: string[];
    customInstructions?: string[];
  }) {
    const res = await fetch(`${API_BASE}/analyze-website`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        url: params.url,
        max_pages: params.maxPages || 1,
        timeout: params.timeout || 10.0,
        brand_name: params.brandName,
        target_audience: params.targetAudience,
        content_type: params.contentType || 'Website Copy',
        language: params.language || 'English',
        brand_guidelines: params.brandGuidelines || [],
        preferred_terminology: params.preferredTerminology || [],
        custom_instructions: params.customInstructions || [],
        save_history: true,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail?.message || err.message || 'Website analysis failed.');
    }
    return res.json();
  },
};


