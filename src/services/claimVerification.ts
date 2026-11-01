// ============================================================
// Claim Verification API Service
// Communicates with FastAPI /api/v1/ai/verify-claim and history endpoints
// ============================================================

import { authService } from './auth';
import type {
  EvidenceInputItem,
  VerifyClaimApiResponse,
  ClaimVerificationRecord,
  ClaimVerificationListApiResponse,
} from '@/types/claimVerification';

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

export const claimVerificationService = {
  /**
   * Evaluates a claim strictly against supplied evidence via FastAPI & Gemini.
   */
  async verifyClaim(
    claim: string,
    evidence: EvidenceInputItem[]
  ): Promise<VerifyClaimApiResponse> {
    const cleanClaim = claim.trim();
    if (!cleanClaim) {
      throw new Error('Please enter a claim to verify.');
    }
    if (!evidence || evidence.length === 0) {
      throw new Error('Please provide at least one piece of evidence.');
    }

    const payload = {
      claim: cleanClaim,
      evidence: evidence.map((e, idx) => ({
        id: e.id || `E${String(idx + 1).padStart(3, '0')}`,
        title: (e.title || 'Untitled Evidence').trim(),
        text: (e.text || '').trim(),
        source_url: e.source_url ? e.source_url.trim() : null,
        publisher: e.publisher ? e.publisher.trim() : null,
        published_date: e.published_date ? e.published_date.trim() : null,
        evidence_type: e.evidence_type || 'unknown',
      })),
    };

    const res = await fetch(`${API_BASE}/verify-claim`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const message =
        err.detail?.message ||
        err.message ||
        `Verification request failed with status ${res.status}`;
      throw new Error(message);
    }

    return (await res.json()) as VerifyClaimApiResponse;
  },

  /**
   * Retrieves previous claim verification records for the current user.
   */
  async listHistory(limit = 50, offset = 0): Promise<ClaimVerificationRecord[]> {
    const token = authService.getToken();
    if (!token) {
      return [];
    }

    const res = await fetch(
      `${API_BASE}/claim-verifications?limit=${limit}&offset=${offset}`,
      {
        method: 'GET',
        headers: getAuthHeaders(),
      }
    );

    if (!res.ok) {
      if (res.status === 401) {
        return [];
      }
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail?.message || 'Failed to load verification history.');
    }

    const data = (await res.json()) as ClaimVerificationListApiResponse;
    return data.verifications || [];
  },

  /**
   * Retrieves a single claim verification record by ID.
   */
  async getVerificationById(id: string): Promise<ClaimVerificationRecord> {
    const res = await fetch(`${API_BASE}/claim-verifications/${id}`, {
      method: 'GET',
      headers: getAuthHeaders(),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail?.message || 'Verification record not found.');
    }

    return (await res.json()) as ClaimVerificationRecord;
  },

  /**
   * Deletes a claim verification record by ID.
   */
  async deleteVerification(id: string): Promise<boolean> {
    const res = await fetch(`${API_BASE}/claim-verifications/${id}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail?.message || 'Failed to delete verification record.');
    }

    return true;
  },
};
