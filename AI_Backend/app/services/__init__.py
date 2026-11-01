"""Services package for BrandProof AI."""

from app.services.ai_provider import ai_provider_service, AIProviderService
from app.services.grammar_analyzer import grammar_analyzer_service, GrammarAnalyzerService
from app.services.ocr_service import ocr_service, OCRService
from app.services.report_generator import report_generator_service, ReportGeneratorService
from app.services.storage_service import storage_service, StorageService
from app.services.supabase_service import supabase_service, SupabaseService
from app.services.text_processor import text_processor_service, TextProcessorService
from app.services.claim_verification.evidence_evaluator import (
    claim_evidence_evaluator,
    ClaimEvidenceEvaluator,
)

__all__ = [
    "ai_provider_service",
    "AIProviderService",
    "grammar_analyzer_service",
    "GrammarAnalyzerService",
    "ocr_service",
    "OCRService",
    "report_generator_service",
    "ReportGeneratorService",
    "storage_service",
    "StorageService",
    "supabase_service",
    "SupabaseService",
    "text_processor_service",
    "TextProcessorService",
    "claim_evidence_evaluator",
    "ClaimEvidenceEvaluator",
]
