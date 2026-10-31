// ============================================================
// Report Service for BrandProof AI
// Handles PDF Report generation & download with red-underlined errors
// on Page 1 and corrected text with AI guideline proofs on Page 2.
// ============================================================

import type { Analysis, Finding } from '@/types/domain';
import { authService } from './auth';

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');
const API_BASE = `${BASE_URL}/api/v1/ai`;

/**
 * Escapes HTML characters for safe client-side markup injection.
 */
function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

/**
 * Formats original text highlighting flagged error excerpts with red underlines
 * and footnote anchors [1], [2], etc.
 */
function formatOriginalTextWithRedUnderlines(text: string, findings: Finding[]): string {
  if (!text) return '';
  let html = escapeHtml(text);

  findings.forEach((finding, idx) => {
    const target = finding.originalExcerpt?.trim();
    if (!target) return;

    const escapedTarget = escapeHtml(target);
    const replacement = `<span class="error-underlined"><u>${escapedTarget}</u><sup class="error-sup">[${idx + 1}]</sup></span>`;

    // Replace first occurrence
    html = html.replace(escapedTarget, replacement);
  });

  return html.replace(/\r\n/g, '\n').replace(/\n/g, '<br/><br/>');
}

/**
 * Generates and triggers download of a 2-page PDF / printable audit report.
 * Uses FastAPI backend ReportLab generator with seamless client-side print fallback.
 */
export async function downloadAnalysisReport(
  analysis: Analysis,
  onToast?: (msg: { title: string; variant: 'success' | 'error' | 'warning' | 'info'; description?: string }) => void
): Promise<void> {
  const safeName = (analysis.name || 'Analysis')
    .replace(/[^a-zA-Z0-9_-]/g, '_')
    .replace(/_+/g, '_');

  const payload = {
    title: analysis.name || 'BrandProof AI Content Audit Report',
    original_text: analysis.originalContent || '',
    corrected_text: analysis.correctedContent || analysis.originalContent || '',
    findings: (analysis.findings || []).map((f) => ({
      id: f.id,
      category: f.category || 'grammar',
      severity: f.severity || 'medium',
      original_text: f.originalExcerpt || '',
      suggestion: f.suggestedCorrection || '',
      explanation: f.explanation || '',
      rule: f.rule || undefined,
      confidence: f.confidence || undefined,
    })),
    summary: analysis.summary || null,
    content_type: analysis.sourceType || 'document',
    model_name: 'Gemini 3.5 Flash',
    created_at: analysis.createdAt,
  };

  try {
    const token = authService.getToken();
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(`${API_BASE}/generate-report`, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
    });

    if (res.ok && res.headers.get('content-type')?.includes('application/pdf')) {
      const blob = await res.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = `BrandProof_Report_${safeName}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(blobUrl);

      onToast?.({ title: 'Audit report downloaded (PDF)', variant: 'success' });
      return;
    }
  } catch (err) {
    console.warn('Backend PDF generator unavailable, using client-side printable report fallback:', err);
  }

  // Fallback: Open high-fidelity formatted printable report
  openPrintableAuditReport(analysis);
  onToast?.({ title: 'Report generated for printing / PDF export', variant: 'success' });
}

/**
 * Fallback client-side printable report with exact 2-page pagination:
 * - Page 1: Original text with errors underlined in red + findings breakdown
 * - Page 2: Corrected copy + AI guideline proofs + reviewer sign-off block
 */
export function openPrintableAuditReport(analysis: Analysis): void {
  const printWindow = window.open('', '_blank');
  if (!printWindow) return;

  const originalMarked = formatOriginalTextWithRedUnderlines(
    analysis.originalContent || '',
    analysis.findings || []
  );

  const correctedHtml = escapeHtml(analysis.correctedContent || analysis.originalContent || '')
    .replace(/\r\n/g, '\n')
    .replace(/\n/g, '<br/><br/>');

  const summaryText = analysis.summary || 'Analysis complete. Verified by BrandProof AI.';

  const docDate = new Date(analysis.createdAt).toLocaleString('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });

  const findingsRows = (analysis.findings || [])
    .map(
      (f, idx) => `
    <tr>
      <td style="font-weight: 700; width: 32px;">[${idx + 1}]</td>
      <td style="color: #dc2626; font-weight: 600; text-decoration: underline; text-decoration-color: #dc2626;">${escapeHtml(f.originalExcerpt)}</td>
      <td><span class="badge ${f.category}">${escapeHtml(f.category)}</span></td>
      <td><span class="badge ${f.severity}">${escapeHtml(f.severity.toUpperCase())}</span></td>
      <td>${escapeHtml(f.explanation)}</td>
    </tr>`
    )
    .join('');

  const proofsRows = (analysis.findings || [])
    .map(
      (f, idx) => `
    <tr>
      <td style="font-weight: 700; width: 32px;">[${idx + 1}]</td>
      <td style="color: #dc2626; text-decoration: line-through;">${escapeHtml(f.originalExcerpt)}</td>
      <td style="color: #15803d; font-weight: 600;">${escapeHtml(f.suggestedCorrection)}</td>
      <td><strong>${escapeHtml(f.rule || `Brand ${f.category} Standard`)}</strong></td>
      <td>${escapeHtml(f.explanation)}</td>
    </tr>`
    )
    .join('');

  const htmlDoc = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>BrandProof AI Audit Report - ${escapeHtml(analysis.name)}</title>
  <style>
    @page {
      size: letter;
      margin: 0.5in;
    }
    @media print {
      body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
      .page-break { page-break-before: always; break-before: page; }
      .no-print { display: none !important; }
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: #0f172a;
      background: #ffffff;
      margin: 0;
      padding: 24px;
      line-height: 1.5;
      font-size: 13px;
    }
    .print-actions {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
      margin-bottom: 20px;
      padding-bottom: 12px;
      border-bottom: 1px solid #e2e8f0;
    }
    .btn {
      padding: 8px 16px;
      font-size: 13px;
      font-weight: 600;
      border-radius: 6px;
      cursor: pointer;
      border: 1px solid #cbd5e1;
      background: #f8fafc;
      color: #1e293b;
    }
    .btn-primary {
      background: #2563eb;
      color: #ffffff;
      border-color: #2563eb;
    }
    .header-table {
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 12px;
      border-bottom: 2px solid #0f172a;
      padding-bottom: 8px;
    }
    .header-table td { vertical-align: top; }
    h1 { margin: 0 0 4px 0; font-size: 20px; color: #0f172a; }
    .subtitle { color: #475569; font-size: 11px; }
    .meta-box { text-align: right; font-size: 11px; color: #334155; }
    .meta-box strong { color: #0f172a; }
    .summary-card {
      background: #f8fafc;
      border: 1px solid #cbd5e1;
      border-radius: 6px;
      padding: 10px 14px;
      margin-bottom: 16px;
      font-size: 12px;
    }
    .section-title {
      font-size: 14px;
      font-weight: 700;
      margin: 16px 0 6px 0;
      color: #1e293b;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .section-desc { font-size: 11px; color: #64748b; margin-bottom: 8px; }
    .original-box {
      background: #fff5f5;
      border: 1px solid #fecaca;
      border-radius: 6px;
      padding: 14px;
      font-size: 13px;
      line-height: 1.7;
      margin-bottom: 16px;
    }
    .corrected-box {
      background: #f0fdf4;
      border: 1px solid #86efac;
      border-radius: 6px;
      padding: 14px;
      font-size: 13px;
      line-height: 1.7;
      color: #065f46;
      margin-bottom: 16px;
    }
    .error-underlined {
      color: #dc2626 !important;
      font-weight: 600;
      text-decoration: underline !important;
      text-decoration-color: #dc2626 !important;
      text-decoration-thickness: 2px !important;
      text-underline-offset: 3px !important;
    }
    .error-sup {
      color: #dc2626;
      font-size: 10px;
      font-weight: 700;
      margin-left: 2px;
    }
    table.data-table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 8px;
      font-size: 11px;
    }
    table.data-table th {
      background: #f1f5f9;
      color: #0f172a;
      text-align: left;
      padding: 7px 10px;
      border: 1px solid #cbd5e1;
      font-weight: 700;
    }
    table.data-table td {
      padding: 7px 10px;
      border: 1px solid #cbd5e1;
      vertical-align: top;
    }
    .badge {
      display: inline-block;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 9px;
      font-weight: 700;
      text-transform: uppercase;
    }
    .badge.critical, .badge.high { background: #fee2e2; color: #991b1b; }
    .badge.major, .badge.medium { background: #fef3c7; color: #92400e; }
    .badge.minor, .badge.low { background: #dbeafe; color: #1e40af; }
    .badge.info { background: #f1f5f9; color: #475569; }
    .gov-box {
      background: #f8fafc;
      border: 1px solid #94a3b8;
      border-radius: 6px;
      padding: 12px;
      margin-top: 20px;
      font-size: 11px;
    }
    .footer-rule {
      margin-top: 24px;
      border-top: 1px solid #e2e8f0;
      padding-top: 8px;
      display: flex;
      justify-content: space-between;
      font-size: 10px;
      color: #64748b;
    }
  </style>
</head>
<body>
  <div class="print-actions no-print">
    <button class="btn" onclick="window.close()">Close</button>
    <button class="btn btn-primary" onclick="window.print()">Print / Save as PDF</button>
  </div>

  <!-- ================= PAGE 1 ================= -->
  <table class="header-table">
    <tr>
      <td>
        <h1>BrandProof AI™ — Content Quality Audit</h1>
        <div class="subtitle">Marketing Compliance, Language Quality & Evidential Review</div>
      </td>
      <td class="meta-box">
        <div><strong>Document:</strong> ${escapeHtml(analysis.name)}</div>
        <div><strong>Date:</strong> ${escapeHtml(docDate)}</div>
        <div><strong>Model:</strong> Gemini 3.5 Flash</div>
        <div><strong>Issues Found:</strong> ${analysis.findings.length}</div>
      </td>
    </tr>
  </table>

  <div class="summary-card">
    <strong>Executive Assessment:</strong> ${escapeHtml(summaryText)}
    <div style="font-size: 11px; color: #64748b; margin-top: 4px;">Status: Automated inspection complete. Pending human approval.</div>
  </div>

  <div class="section-title">1. Original Marketing Content</div>
  <div class="section-desc">Identified grammar, spelling, compliance, and stylistic issues are highlighted below with <span style="color: #dc2626; font-weight: 700; text-decoration: underline;">red underline markings</span>:</div>
  <div class="original-box">
    ${originalMarked}
  </div>

  <div class="section-title">2. Flagged Errors & Rule Violations</div>
  <table class="data-table">
    <thead>
      <tr>
        <th>#</th>
        <th>Flagged Excerpt</th>
        <th>Category</th>
        <th>Severity</th>
        <th>Explanation & Guideline Context</th>
      </tr>
    </thead>
    <tbody>
      ${findingsRows || '<tr><td colspan="5" style="text-align: center; color: #64748b;">No issues detected. Content complies fully with brand standards.</td></tr>'}
    </tbody>
  </table>

  <div class="footer-rule">
    <div>BrandProof AI — Brand Compliance & Language Quality Audit</div>
    <div>Page 1 of 2</div>
  </div>

  <!-- ================= PAGE 2 ================= -->
  <div class="page-break" style="height: 1px;"></div>

  <table class="header-table" style="margin-top: 16px;">
    <tr>
      <td>
        <h1>Corrected Content & AI Guideline Proofs</h1>
        <div class="subtitle">Publication-Ready Text Verified Against Brand Guidelines & Evidential Standards</div>
      </td>
      <td class="meta-box">
        <div><strong>Engine:</strong> Gemini 3.5 Flash</div>
        <div><strong>Verification Status:</strong> Ready for Sign-off</div>
      </td>
    </tr>
  </table>

  <div class="section-title">3. Publication-Ready Corrected Copy</div>
  <div class="section-desc">The revised marketing copy below incorporates all approved grammatical, stylistic, and brand consistency adjustments:</div>
  <div class="corrected-box">
    ${correctedHtml}
  </div>

  <div class="section-title">4. AI Guideline Proofs & Alignment Evidence</div>
  <div class="section-desc">Traceability matrix connecting each correction to its specific brand guideline, grammar rule, or evidence proof:</div>
  <table class="data-table">
    <thead>
      <tr>
        <th>#</th>
        <th>Flagged Phrase</th>
        <th>Approved Correction</th>
        <th>Guideline / Proof</th>
        <th>AI Reasoning & Evidence</th>
      </tr>
    </thead>
    <tbody>
      ${proofsRows || '<tr><td colspan="5" style="text-align: center; color: #64748b;">No corrections required.</td></tr>'}
    </tbody>
  </table>

  <div class="gov-box">
    <strong>5. Governance Checkpoint & Reviewer Sign-off:</strong><br/><br/>
    Decision: &nbsp; [ &nbsp; ] <strong>Approved for Publication</strong> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
    [ &nbsp; ] <strong>Revisions Requested</strong> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
    [ &nbsp; ] <strong>Rejected</strong><br/><br/>
    Reviewer Signature: _____________________________________________ &nbsp;&nbsp;&nbsp;&nbsp; Date: _______________________<br/><br/>
    <span style="font-size: 10px; color: #64748b;">Disclaimer: BrandProof AI is an automated quality inspector and advisor. Final publication approval must always be verified by an authorized human reviewer.</span>
  </div>

  <div class="footer-rule">
    <div>BrandProof AI — Brand Compliance & Language Quality Audit</div>
    <div>Page 2 of 2</div>
  </div>
</body>
</html>`;

  printWindow.document.open();
  printWindow.document.write(htmlDoc);
  printWindow.document.close();
}
