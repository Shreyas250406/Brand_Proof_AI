// ============================================================
// Claim Verification Domain Types
// ============================================================

export type VerificationStatusType =
  | 'SUPPORTED'
  | 'CONTRADICTED'
  | 'PARTIALLY_SUPPORTED'
  | 'UNVERIFIABLE'
  | 'CONFLICTING_EVIDENCE';

export type UserEvidenceType =
  | 'supporting'
  | 'contradicting'
  | 'neutral'
  | 'unknown';

export interface EvidenceInputItem {
  id: string;
  title: string;
  text: string;
  source_url?: string;
  publisher?: string;
  published_date?: string;
  source_type?: string;
  evidence_type?: UserEvidenceType;
}

export interface EvaluatedEvidenceItem {
  evidence_id: string;
  relationship: string;
  relevance: string;
  matched_passage?: string | null;
  explanation: string;
}

export interface ClaimVerificationResult {
  verification_status: VerificationStatusType;
  confidence: number;
  claim_summary: string;
  verdict: string;
  reasoning: string;
  evidence_analysis: EvaluatedEvidenceItem[];
  missing_information: string[];
  suggested_correction?: string | null;
}

export interface VerifyClaimApiResponse {
  success: boolean;
  id?: string | null;
  result: ClaimVerificationResult;
  saved: boolean;
  created_at?: string | null;
}

export interface ClaimVerificationRecord {
  id: string;
  user_id?: string | null;
  claim: string;
  evidence: EvidenceInputItem[];
  verification_status: VerificationStatusType;
  confidence?: number | null;
  result: ClaimVerificationResult;
  created_at: string;
}

export interface ClaimVerificationListApiResponse {
  success: boolean;
  verifications: ClaimVerificationRecord[];
  total: number;
}
