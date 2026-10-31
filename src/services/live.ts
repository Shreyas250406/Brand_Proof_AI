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

const API_BASE = '/api/v1/ai';

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
    let rawFindings: Array<Record<string, unknown>> = [];
    if (typeof item.findings === 'string') {
      try {
        rawFindings = JSON.parse(item.findings);
      } catch {
        rawFindings = [];
      }
    } else if (Array.isArray(item.findings)) {
      rawFindings = item.findings as Array<Record<string, unknown>>;
    }

    const findings: Finding[] = rawFindings.map((f, idx) => ({
      id: (f.id as string) || `finding-${idx + 1}`,
      category: mapBackendCategory((f.category as string) || 'grammar'),
      severity: mapBackendSeverity((f.severity as string) || 'medium'),
      originalExcerpt: (f.original_text as string) || (f.originalExcerpt as string) || '',
      suggestedCorrection: (f.suggestion as string) || (f.suggestedCorrection as string) || '',
      explanation: (f.explanation as string) || '',
      confidence: f.confidence as number | undefined,
      sourceOffset:
        f.start_offset !== undefined && f.end_offset !== undefined
          ? { start: Number(f.start_offset), end: Number(f.end_offset) }
          : undefined,
      isDemo: false,
    }));

    const createdAt = (item.created_at as string) || new Date().toISOString();
    const orig = (item.original_text as string) || '';
    const corrected = (item.corrected_text as string) || orig;

    let title = orig.slice(0, 30).trim() || 'Analysis';
    let reviewStatus: 'not_started' | 'in_progress' | 'corrections_applied' | 'completed' = 'not_started';
    let status: 'completed' | 'no_findings' | 'failed' = findings.length === 0 ? 'no_findings' : 'completed';
    let selectedFindingIds: string[] = [];
    let contentType: string | undefined = undefined;
    let targetAudience: string | undefined = undefined;
    let language: string | undefined = undefined;
    let fileName: string | undefined = undefined;

    if (typeof item.summary === 'string' && item.summary.trim().startsWith('{')) {
      try {
        const meta = JSON.parse(item.summary);
        if (meta.title) title = meta.title;
        if (meta.reviewStatus) reviewStatus = meta.reviewStatus;
        if (meta.status) status = meta.status;
        if (Array.isArray(meta.selectedFindingIds)) selectedFindingIds = meta.selectedFindingIds;
        if (meta.contentType) contentType = meta.contentType;
        if (meta.targetAudience) targetAudience = meta.targetAudience;
        if (meta.language) language = meta.language;
        if (meta.fileName) fileName = meta.fileName;
      } catch {
        // Not a JSON summary string
      }
    }

    if (reviewStatus === 'not_started' && corrected !== orig) {
      reviewStatus = 'corrections_applied';
    }

    return {
      id: String(item.id || ''),
      name: title,
      sourceType: ((item.input_type as string) === 'image' ? 'file_image' : 'text'),
      originalContent: orig,
      fileName,
      contentType,
      targetAudience,
      language,
      status,
      findings,
      selectedFindingIds,
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
      console.warn('Could not load history from backend API, attempting direct Supabase query:', err);
    }

    // Direct Supabase REST API fallback
    const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
    const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;
    if (supabaseUrl && supabaseAnonKey) {
      try {
        const token = authService.getToken();
        const user = authService.getStoredUser();
        const headers: Record<string, string> = {
          'apikey': supabaseAnonKey,
          'Authorization': `Bearer ${token || supabaseAnonKey}`,
        };
        let queryParams = 'order=created_at.desc&limit=50';
        if (user?.id) {
          queryParams += `&user_id=eq.${user.id}`;
        } else {
          queryParams += '&user_id=is.null';
        }

        const sbRes = await fetch(
          `${supabaseUrl.replace(/\/$/, '')}/rest/v1/analysis_history?${queryParams}`,
          { headers }
        );
        if (sbRes.ok) {
          const items = await sbRes.json();
          if (Array.isArray(items)) {
            return items.map((i: Record<string, unknown>) => this.convertHistoryItem(i));
          }
        }
      } catch (sbErr) {
        console.warn('Direct Supabase history query failed:', sbErr);
      }
    }

    return [];
  },

  async save(analysis: Analysis): Promise<void> {
    const summaryPayload = JSON.stringify({
      title: analysis.name,
      contentType: analysis.contentType,
      targetAudience: analysis.targetAudience,
      language: analysis.language,
      reviewStatus: analysis.reviewStatus,
      selectedFindingIds: analysis.selectedFindingIds,
      status: analysis.status,
      fileName: analysis.fileName,
    });

    const findingsPayload = (analysis.findings || []).map(f => ({
      id: f.id,
      category: f.category,
      severity: f.severity,
      original_text: f.originalExcerpt,
      suggestion: f.suggestedCorrection,
      explanation: f.explanation,
      confidence: f.confidence,
      start_offset: f.sourceOffset?.start,
      end_offset: f.sourceOffset?.end,
    }));

    // 1. Try PUT /api/v1/ai/history/{id} to update existing record
    try {
      const putRes = await fetch(`${API_BASE}/history/${analysis.id}`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          corrected_text: analysis.correctedContent,
          findings: findingsPayload,
          summary: summaryPayload,
        }),
      });
      if (putRes.ok) {
        return;
      }
      if (putRes.status !== 404) {
        const errData = await putRes.json().catch(() => ({}));
        throw new Error(errData.detail?.message || errData.message || 'Failed to update analysis.');
      }
    } catch (putErr: any) {
      if (putErr.message && !putErr.message.includes('404')) {
        console.warn('PUT /history failed, attempting POST:', putErr);
      }
    }

    // 2. Try POST /api/v1/ai/history to create or upsert record
    try {
      const postRes = await fetch(`${API_BASE}/history`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          id: analysis.id,
          input_type: analysis.sourceType === 'file_image' ? 'image' : 'text',
          original_text: analysis.originalContent,
          corrected_text: analysis.correctedContent,
          findings: findingsPayload,
          summary: summaryPayload,
        }),
      });
      if (postRes.ok) {
        return;
      }
      const errData = await postRes.json().catch(() => ({}));
      throw new Error(errData.detail?.message || errData.message || 'Failed to persist analysis to database.');
    } catch (postErr: any) {
      // 3. Fallback to direct Supabase REST API if backend is unreachable
      const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
      const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;
      if (supabaseUrl && supabaseAnonKey) {
        try {
          const token = authService.getToken();
          const user = authService.getStoredUser();
          const headers: Record<string, string> = {
            'apikey': supabaseAnonKey,
            'Authorization': `Bearer ${token || supabaseAnonKey}`,
            'Content-Type': 'application/json',
            'Prefer': 'resolution=merge-duplicates',
          };
          const sbPayload: Record<string, unknown> = {
            id: analysis.id,
            input_type: analysis.sourceType === 'file_image' ? 'image' : 'text',
            original_text: analysis.originalContent,
            corrected_text: analysis.correctedContent,
            findings: findingsPayload,
            summary: summaryPayload,
          };
          if (user?.id) {
            sbPayload.user_id = user.id;
          }
          const sbRes = await fetch(`${supabaseUrl.replace(/\/$/, '')}/rest/v1/analysis_history`, {
            method: 'POST',
            headers,
            body: JSON.stringify(sbPayload),
          });
          if (sbRes.ok) {
            return;
          }
        } catch (sbErr) {
          console.error('Supabase direct REST save failed:', sbErr);
        }
      }
      throw new Error(postErr.message || 'Database persistence failed.');
    }
  },

  async delete(id: string): Promise<void> {
    try {
      const res = await fetch(`${API_BASE}/history/${id}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      });
      if (res.ok) return;
    } catch (err) {
      console.warn('Backend delete failed, trying Supabase REST:', err);
    }

    const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
    const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;
    if (supabaseUrl && supabaseAnonKey) {
      try {
        const token = authService.getToken();
        const headers: Record<string, string> = {
          'apikey': supabaseAnonKey,
          'Authorization': `Bearer ${token || supabaseAnonKey}`,
        };
        await fetch(`${supabaseUrl.replace(/\/$/, '')}/rest/v1/analysis_history?id=eq.${id}`, {
          method: 'DELETE',
          headers,
        });
      } catch (sbErr) {
        console.error('Failed to delete via Supabase direct REST:', sbErr);
      }
    }
  },

  async clear(): Promise<void> {
    const items = await this.list();
    await Promise.all(items.map(i => this.delete(i.id)));
  },
};
