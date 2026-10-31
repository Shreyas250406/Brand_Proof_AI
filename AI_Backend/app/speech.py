"""Speech and Video Analysis Module for BrandProof AI.

Processes MP3 (audio) and MP4 (video) files by:
1. Extracting speech using FFmpeg and Groq Whisper STT (whisper-large-v3-turbo).
2. Extracting on-screen visual text second-by-second using OpenCV and PaddleOCR.
3. Applying consecutive duplicate text removal with timestamp retention.
4. Proofreading spoken and visual text using Gemini AI with brand compliance checks.
5. Providing cross-modal consistency analysis and optional Supabase persistence.
"""

import os
import re
import shutil
import tempfile
import subprocess
import logging
from typing import Optional, List, Dict, Any, Tuple
import cv2
import numpy as np

from app.core.config import settings
from app.core.exceptions import (
    MediaProcessingError,
    InvalidMediaError,
    SpeechToTextError,
    AIProviderError,
)
from app.services.ocr_service import ocr_service
from app.services.ai_provider import ai_provider_service
from app.services.supabase_service import supabase_service
from app.api.schemas import (
    MediaAnalysisResponse,
    TranscriptionAnalysis,
    VisualTextAnalysis,
    CombinedAnalysis,
    MediaAnalysisSummary,
    SpeechFinding,
    VisualFinding,
    VisualTextSegment,
    CombinedFinding,
    GrammarFinding,
)

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# FFmpeg Binary Resolution
# ------------------------------------------------------------------------------

def resolve_ffmpeg_path() -> str:
    """Finds and returns the path to a working FFmpeg executable.

    Checks:
    1. settings.FFMPEG_BINARY / environment variable FFMPEG_BINARY
    2. System PATH (shutil.which('ffmpeg'))
    3. Bundled imageio_ffmpeg binary
    """
    custom = getattr(settings, "FFMPEG_BINARY", None) or os.environ.get("FFMPEG_BINARY")
    if custom and os.path.exists(custom):
        return custom

    on_path = shutil.which("ffmpeg")
    if on_path:
        return on_path

    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.exists(exe):
            return exe
    except Exception:
        pass

    raise MediaProcessingError(
        "FFmpeg binary not found. Please install FFmpeg on your system PATH, "
        "install 'imageio-ffmpeg', or set FFMPEG_BINARY in your environment."
    )


# ------------------------------------------------------------------------------
# Media Inspection & Validation
# ------------------------------------------------------------------------------

def get_media_info(media_path: str) -> Dict[str, Any]:
    """Inspects media file duration, streams, and format using FFmpeg/OpenCV."""
    if not os.path.exists(media_path):
        raise InvalidMediaError(f"Media file not found: {media_path}")

    size_bytes = os.path.getsize(media_path)
    if size_bytes == 0:
        raise InvalidMediaError("Uploaded media file is empty (0 bytes).")

    ffmpeg_exe = resolve_ffmpeg_path()
    cmd = [ffmpeg_exe, "-hide_banner", "-i", media_path]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stderr = res.stderr or ""

    # Check for corruption / unreadable container
    if "Invalid data found when processing input" in stderr:
        raise InvalidMediaError("Uploaded media file is corrupted or not a valid MP3/MP4.")

    has_audio = "Audio:" in stderr
    has_video = "Video:" in stderr

    # Extract duration from stderr e.g. "Duration: 00:01:23.45"
    duration = 0.0
    dur_match = re.search(r"Duration:\s*(\d{2}):(\d{2}):(\d{2}(?:\.\d+)?)", stderr)
    if dur_match:
        hrs, mins, secs = dur_match.groups()
        duration = int(hrs) * 3600 + int(mins) * 60 + float(secs)
    elif has_video:
        try:
            cap = cv2.VideoCapture(media_path)
            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
            if fps > 0 and total_frames > 0:
                duration = total_frames / fps
            cap.release()
        except Exception:
            duration = 0.0

    ext = os.path.splitext(media_path)[1].lower()
    media_format = "mp4" if ext == ".mp4" or has_video else "mp3"

    return {
        "duration": duration,
        "has_audio": has_audio,
        "has_video": has_video,
        "format": media_format,
        "size_bytes": size_bytes,
    }


# ------------------------------------------------------------------------------
# Video-to-Audio Conversion
# ------------------------------------------------------------------------------

def convert_video_to_audio(video_path: str, output_path: Optional[str] = None) -> Optional[str]:
    """Extracts audio stream from MP4 video into an MP3 file using FFmpeg.

    Returns the path to the MP3 file, or None if the video contains no audio stream.
    Never overwrites the original uploaded file.
    """
    info = get_media_info(video_path)
    if not info["has_audio"]:
        logger.info("Video %s contains no audio stream. Skipping audio extraction.", video_path)
        return None

    ffmpeg_exe = resolve_ffmpeg_path()
    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix=".mp3", prefix="extracted_audio_")
        os.close(fd)

    cmd = [
        ffmpeg_exe,
        "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "libmp3lame",
        "-ar", "16000",
        "-ac", "1",
        "-b:a", "128k",
        output_path,
    ]

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception:
                pass
        err_msg = res.stderr or "Unknown FFmpeg error"
        if "does not contain any stream" in err_msg.lower() or "matches no streams" in err_msg.lower():
            logger.info("Video has no audio stream during extraction.")
            return None
        raise MediaProcessingError(f"Failed to extract audio from video: {err_msg}")

    return output_path


# ------------------------------------------------------------------------------
# Groq Speech-to-Text Integration
# ------------------------------------------------------------------------------

def get_groq_client():
    """Initializes and returns the official Groq client using settings.GROQ_API_KEY."""
    api_key = getattr(settings, "GROQ_API_KEY", None) or os.environ.get("GROQ_API_KEY")
    if not api_key or not api_key.strip():
        raise SpeechToTextError(
            "GROQ_API_KEY is not configured. Please set GROQ_API_KEY in your environment or .env file."
        )

    try:
        from groq import Groq
        return Groq(api_key=api_key.strip())
    except ImportError:
        raise SpeechToTextError(
            "The official 'groq' Python package is not installed. Run 'pip install groq'."
        )



def find_speech_timestamp(excerpt: str, segments: List[Dict[str, Any]]) -> str:
    """Finds the timestamp MM:SS where the speech error excerpt occurs."""
    if not excerpt or not segments:
        return "00:00"
    clean_excerpt = re.sub(r"[^\w\s]", "", excerpt.lower()).strip()
    if not clean_excerpt:
        return segments[0].get("timestamp", "00:00")
    words = clean_excerpt.split()

    # 1. Exact substring match
    for seg in segments:
        seg_clean = re.sub(r"[^\w\s]", "", seg.get("text", "").lower())
        if clean_excerpt in seg_clean:
            return seg.get("timestamp", "00:00")

    # 2. Token overlap match
    best_ts = segments[0].get("timestamp", "00:00")
    best_score = 0
    for seg in segments:
        seg_clean = re.sub(r"[^\w\s]", "", seg.get("text", "").lower())
        seg_words = set(seg_clean.split())
        score = sum(1 for w in words if w in seg_words)
        if score > best_score:
            best_score = score
            best_ts = seg.get("timestamp", "00:00")

    return best_ts


def find_visual_timestamp(excerpt: str, segments: List[Dict[str, str]]) -> str:
    """Finds the timestamp MM:SS where the visual text occurs."""
    if not excerpt or not segments:
        return "00:00"
    clean_excerpt = re.sub(r"[^\w\s]", "", excerpt.lower()).strip()
    for seg in segments:
        seg_clean = re.sub(r"[^\w\s]", "", seg.get("text", "").lower())
        if clean_excerpt in seg_clean or seg_clean in clean_excerpt:
            return seg.get("timestamp", "00:00")
    return segments[0].get("timestamp", "00:00")


def transcribe_audio_chunks(
    audio_path: str,
    chunk_duration_secs: int = 600,
    language: Optional[str] = None,
) -> Dict[str, Any]:
    """Splits large audio files into chronological chunks and merges their transcripts."""
    ffmpeg_exe = resolve_ffmpeg_path()
    info = get_media_info(audio_path)
    total_duration = info["duration"]

    client = get_groq_client()
    model = getattr(settings, "GROQ_MODEL", "whisper-large-v3-turbo")

    chunk_transcripts: List[str] = []
    detected_lang: Optional[str] = None

    temp_dir = tempfile.mkdtemp(prefix="audio_chunks_")
    try:
        start = 0
        idx = 0
        while start < total_duration:
            chunk_file = os.path.join(temp_dir, f"chunk_{idx:03d}.mp3")
            split_cmd = [
                ffmpeg_exe,
                "-y",
                "-ss", str(start),
                "-t", str(chunk_duration_secs),
                "-i", audio_path,
                "-acodec", "copy",
                chunk_file,
            ]
            res = subprocess.run(split_cmd, capture_output=True)
            if res.returncode != 0 or not os.path.exists(chunk_file) or os.path.getsize(chunk_file) == 0:
                break

            with open(chunk_file, "rb") as cf:
                chunk_resp = client.audio.transcriptions.create(
                    file=(f"chunk_{idx}.mp3", cf.read()),
                    model=model,
                    response_format="verbose_json",
                    language=language,
                    temperature=0.0,
                )

            chunk_text = getattr(chunk_resp, "text", "") or ""
            if chunk_text.strip():
                chunk_transcripts.append(chunk_text.strip())

            if not detected_lang and hasattr(chunk_resp, "language"):
                detected_lang = chunk_resp.language

            start += chunk_duration_secs
            idx += 1

        full_transcript = " ".join(chunk_transcripts).strip()
        return {
            "transcript": full_transcript,
            "language": detected_lang or language or "en",
            "duration": total_duration,
        }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def transcribe_audio(audio_path: str, language: Optional[str] = None) -> Dict[str, Any]:
    """Transcribes an MP3 audio file using Groq Whisper API (whisper-large-v3-turbo).

    Preserves original speech transcript separately from any AI-corrected versions.
    Handles large files by splitting into chronological chunks if size exceeds 24MB.
    """
    if not os.path.exists(audio_path):
        raise InvalidMediaError(f"Audio file not found for transcription: {audio_path}")

    size_bytes = os.path.getsize(audio_path)
    if size_bytes == 0:
        return {"transcript": "", "language": "en", "duration": 0.0}

    # Groq Whisper upload limit is 25MB
    if size_bytes > 24 * 1024 * 1024:
        logger.info("Audio size (%d bytes) exceeds 24MB. Splitting into chronological chunks.", size_bytes)
        return transcribe_audio_chunks(audio_path, language=language)

    client = get_groq_client()
    model = getattr(settings, "GROQ_MODEL", "whisper-large-v3-turbo")

    try:
        with open(audio_path, "rb") as af:
            file_bytes = af.read()

        transcription = client.audio.transcriptions.create(
            file=(os.path.basename(audio_path), file_bytes),
            model=model,
            response_format="verbose_json",
            language=language,
            temperature=0.0,
        )

        full_text = getattr(transcription, "text", "") or ""
        detected_lang = getattr(transcription, "language", None) or language or "en"
        duration = getattr(transcription, "duration", 0.0) or 0.0

        raw_segs = getattr(transcription, "segments", []) or []
        parsed_segs = []
        for s in raw_segs:
            s_dict = s if isinstance(s, dict) else (s.__dict__ if hasattr(s, "__dict__") else {})
            s_start = float(s_dict.get("start", 0.0) or 0.0)
            s_end = float(s_dict.get("end", 0.0) or 0.0)
            s_text = str(s_dict.get("text", "") or "").strip()
            mins, secs = divmod(int(s_start), 60)
            parsed_segs.append({
                "timestamp": f"{mins:02d}:{secs:02d}",
                "start": s_start,
                "end": s_end,
                "text": s_text,
            })

        return {
            "transcript": full_text.strip(),
            "language": str(detected_lang),
            "duration": float(duration),
            "segments": parsed_segs,
        }

    except Exception as exc:
        err_str = str(exc)
        logger.error("Groq Whisper STT API error: %s", err_str)
        if "401" in err_str or "unauthorized" in err_str.lower():
            raise SpeechToTextError(f"Groq API authentication failed: {err_str}")
        if "429" in err_str or "rate limit" in err_str.lower():
            raise SpeechToTextError(f"Groq API rate limit exceeded: {err_str}")
        raise SpeechToTextError(f"Groq transcription failed: {err_str}")


# ------------------------------------------------------------------------------
# Video OCR Pipeline — Second-by-Second Frame Extraction & Deduplication
# ------------------------------------------------------------------------------

def extract_video_frames(video_path: str) -> List[Tuple[str, np.ndarray]]:
    """Extracts exactly one frame per second from a video file using OpenCV.

    Timestamp is formatted as MM:SS (e.g. 00:00, 00:01, 00:02).
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise InvalidMediaError(f"Could not open video file with OpenCV: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 25.0

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_secs = total_frames / fps if fps > 0 else 0
    total_seconds = int(duration_secs)

    frames: List[Tuple[str, np.ndarray]] = []
    try:
        for sec in range(total_seconds + 1):
            frame_idx = int(round(sec * fps))
            if frame_idx >= total_frames and total_frames > 0:
                break

            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret or frame is None:
                continue

            mins = sec // 60
            secs = sec % 60
            timestamp = f"{mins:02d}:{secs:02d}"
            frames.append((timestamp, frame))
    finally:
        cap.release()

    return frames


def extract_text_from_frame(frame: np.ndarray) -> str:
    """Passes an extracted video frame to the existing PaddleOCR service."""
    success, encoded_img = cv2.imencode(".png", frame)
    if not success:
        return ""

    try:
        text, _ = ocr_service.extract_text_from_bytes(
            encoded_img.tobytes(),
            content_type="image/png",
            filename="video_frame.png",
        )
        return text.strip()
    except Exception as exc:
        logger.debug("Frame OCR extraction notice: %s", exc)
        return ""


def normalize_ocr_text(text: str) -> str:
    """Normalizes whitespace and casing for robust deduplication."""
    if not text:
        return ""
    return " ".join(text.strip().split())


def deduplicate_ocr_segments(raw_segments: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Removes consecutive duplicate text segments while preserving timestamps.

    Rules:
    - If current extracted text is identical to the previous non-empty extracted text
      (ignoring whitespace differences), do not append it.
    - If current text differs, append it with its timestamp.
    - Ignore frames where no text is detected.
    - Do NOT remove text that reappears after an intervening different segment.
    """
    unique_segments: List[Dict[str, str]] = []
    last_normalized: Optional[str] = None

    for item in raw_segments:
        raw_text = item.get("text", "")
        norm = normalize_ocr_text(raw_text)
        if not norm:
            continue  # Ignore empty frames

        if last_normalized is None or norm.lower() != last_normalized.lower():
            unique_segments.append({
                "timestamp": item.get("timestamp", "00:00"),
                "text": raw_text.strip(),
            })
            last_normalized = norm

    return unique_segments


def extract_unique_video_text(video_path: str) -> List[Dict[str, str]]:
    """Performs full video OCR pipeline: extracts 1 frame/sec, runs PaddleOCR,

    and removes consecutive duplicates with timestamp retention.
    """
    frames = extract_video_frames(video_path)
    raw_segments: List[Dict[str, str]] = []

    for timestamp, frame in frames:
        text = extract_text_from_frame(frame)
        if text:
            raw_segments.append({"timestamp": timestamp, "text": text})

    return deduplicate_ocr_segments(raw_segments)


# ------------------------------------------------------------------------------
# Gemini AI Analysis (Speech, Visual, and Cross-Modal Combined)
# ------------------------------------------------------------------------------

MEDIA_ANALYSIS_SYSTEM_PROMPT = """You are BrandProof AI's Senior Multimedia Quality Assurance and Brand Compliance Engine.
You review marketing videos and audio to guarantee linguistic perfection, visual on-screen consistency, and brand alignment.

You analyze two inputs:
Input A: Speech Transcript (words spoken in audio).
Input B: Visual Text Segments (second-by-second on-screen text with timestamps).

Your evaluation covers:
1. Speech Analysis:
   - Identify grammar, spelling, punctuation, clarity, awkward phrasing, repetition, and brand voice issues.
   - Provide original excerpt, suggested correction, category, explanation, and severity.
   - Provide a full, beautifully corrected transcript.

2. Visual Text Analysis:
   - Proofread each on-screen text segment while retaining its exact timestamp.
   - Flag grammar, spelling, punctuation, capitalization, and brand name inconsistencies.

3. Combined Cross-Modal Analysis:
   - Detect contradictions or inconsistencies between what is spoken and what is displayed on-screen.
   - Check product name consistency, pricing/claim discrepancies, and missing visual copy.
   - Provide clear, actionable brand recommendations.

Return ONLY a valid JSON object matching the requested schema. No markdown fences, no conversational prose."""


async def analyze_media_ai(
    transcript: str,
    visual_segments: List[Dict[str, str]],
    media_type: str,
    context: Optional[Dict[str, Any]] = None,
    speech_segments: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Reuses the existing Gemini AI provider service to perform speech,

    visual, and combined proofreading in a single structured API call.
    """
    ctx = context or {}
    language = ctx.get("language") or "English"
    content_type = ctx.get("content_type") or "Marketing Media"
    target_audience = ctx.get("target_audience") or "General Audience"
    instructions = ctx.get("instructions") or "Ensure professional brand tone and accuracy."
    brand_context = ctx.get("brand_context") or "Preserve official product and company names."

    user_prompt = f"""CONTEXT & GUIDELINES:
- Media Type: {media_type.upper()}
- Target Language: {language}
- Content Type: {content_type}
- Target Audience: {target_audience}
- Instructions: {instructions}
- Brand Guidelines & Rules: {brand_context}

INPUT A - SPEECH TRANSCRIPT:
\"\"\"
{transcript or "(No audio/speech detected)"}
\"\"\"

INPUT B - VISUAL ON-SCREEN TEXT SEGMENTS (WITH TIMESTAMPS):
{visual_segments if visual_segments else "(No on-screen visual text detected)"}

RESPONSE FORMAT:
Return a JSON object with this exact structure:
{{
  "transcription": {{
    "original_text": "{transcript or ''}",
    "corrected_text": "Corrected speech transcript with grammar and spelling fixed",
    "findings": [
      {{
        "original_excerpt": "error phrase from speech",
        "suggested_correction": "corrected phrase",
        "category": "grammar|spelling|punctuation|brand_voice|clarity",
        "explanation": "Why this correction is needed",
        "severity": "critical|major|minor"
      }}
    ]
  }},
  "visual_text": {{
    "findings": [
      {{
        "timestamp": "MM:SS",
        "original_text": "text as displayed",
        "suggested_text": "suggested improvement",
        "category": "grammar|spelling|punctuation|brand_voice|clarity",
        "explanation": "Why this correction is needed",
        "severity": "critical|major|minor"
      }}
    ]
  }},
  "combined_analysis": {{
    "findings": [
      {{
        "topic": "Subject of discrepancy",
        "visual_text": "What appears on screen",
        "spoken_text": "What was spoken",
        "contradiction_type": "contradiction|inconsistency|missing_information|brand_misalignment",
        "explanation": "Detailed explanation of the issue",
        "severity": "critical|major|minor"
      }}
    ],
    "recommendations": [
      "Actionable recommendation for video/audio editors"
    ]
  }},
  "summary": {{
    "total_issues": 0,
    "grammar_issues": 0,
    "spelling_issues": 0,
    "punctuation_issues": 0,
    "brand_issues": 0,
    "clarity_issues": 0
  }}
}}"""

    raw_resp = await ai_provider_service.generate_structured_json(
        system_prompt=MEDIA_ANALYSIS_SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )

    if not isinstance(raw_resp, dict):
        raise AIProviderError("Gemini returned non-dictionary response for media analysis.")

    return raw_resp


# ------------------------------------------------------------------------------
# Modular Analysis Functions
# ------------------------------------------------------------------------------

async def analyze_transcript(transcript: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Analyzes a speech transcript independently using Gemini."""
    return await analyze_media_ai(transcript=transcript, visual_segments=[], media_type="audio", context=context)


async def analyze_visual_text(visual_segments: List[Dict[str, str]], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Analyzes visual text segments independently using Gemini."""
    return await analyze_media_ai(transcript="", visual_segments=visual_segments, media_type="video", context=context)


async def analyze_combined_content(
    transcript: str,
    visual_segments: List[Dict[str, str]],
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Performs joint speech-visual alignment analysis using Gemini."""
    return await analyze_media_ai(transcript=transcript, visual_segments=visual_segments, media_type="video", context=context)


# ------------------------------------------------------------------------------
# High-Level Media Analysis Pipeline
# ------------------------------------------------------------------------------

async def analyze_media(
    file_bytes: Optional[bytes] = None,
    file_path: Optional[str] = None,
    filename: Optional[str] = None,
    content_type: Optional[str] = None,
    target_audience: Optional[str] = None,
    instructions: Optional[str] = None,
    brand_context: Optional[str] = None,
    language: Optional[str] = "English",
    user_id: Optional[str] = None,
    save_history: bool = True,
) -> MediaAnalysisResponse:
    """Executes the complete media analysis pipeline for MP3 or MP4 uploads.

    1. Determines whether input is audio (MP3) or video (MP4).
    2. Runs Groq Whisper STT on audio stream.
    3. Runs second-by-second frame extraction + PaddleOCR + deduplication for video.
    4. Proofreads speech, visual text, and cross-modal consistency with Gemini.
    5. Optionally persists results to Supabase public.media_analysis.
    6. Automatically cleans up all temporary assets.
    """
    temp_dir = tempfile.mkdtemp(prefix="brandproof_media_")
    cleanup_paths: List[str] = []

    try:
        # Resolve target media file on disk
        if file_bytes is not None:
            clean_fn = filename or "uploaded_media"
            target_path = os.path.join(temp_dir, clean_fn)
            with open(target_path, "wb") as f:
                f.write(file_bytes)
            cleanup_paths.append(target_path)
        elif file_path and os.path.exists(file_path):
            target_path = file_path
        else:
            raise InvalidMediaError("Neither valid file_bytes nor file_path was provided.")

        info = get_media_info(target_path)
        media_type = "video" if (info["has_video"] or target_path.lower().endswith(".mp4")) else "audio"
        duration = info["duration"]

        context = {
            "content_type": content_type,
            "target_audience": target_audience,
            "instructions": instructions,
            "brand_context": brand_context,
            "language": language,
        }

        transcript_text = ""
        transcription_lang = language or "en"
        speech_segments: List[Dict[str, Any]] = []
        visual_segments: List[Dict[str, str]] = []

        if media_type == "audio":
            # MP3 Pipeline: MP3 -> Groq STT
            stt_result = transcribe_audio(target_path, language=language)
            transcript_text = stt_result["transcript"]
            transcription_lang = stt_result.get("language") or transcription_lang
            speech_segments = stt_result.get("segments", [])
            if not duration:
                duration = stt_result.get("duration", 0.0)

        else:
            # MP4 Pipeline:
            # Step A: Extract audio -> MP3 -> Groq STT (if audio stream present)
            extracted_mp3 = convert_video_to_audio(target_path)
            if extracted_mp3:
                cleanup_paths.append(extracted_mp3)
                try:
                    stt_result = transcribe_audio(extracted_mp3, language=language)
                    transcript_text = stt_result["transcript"]
                    transcription_lang = stt_result.get("language") or transcription_lang
                    speech_segments = stt_result.get("segments", [])
                except Exception as stt_err:
                    logger.warning("Groq audio transcription notice for video %s: %s", target_path, stt_err)

            # Step B: Second-by-Second Frame Extraction + PaddleOCR + Consecutive Deduplication
            visual_segments = extract_unique_video_text(target_path)

        # Step C: Gemini AI Proofreading (Speech + Visual + Combined)
        ai_data = await analyze_media_ai(
            transcript=transcript_text,
            visual_segments=visual_segments,
            media_type=media_type,
            context=context,
            speech_segments=speech_segments,
        )

        # Parse & Validate Speech Findings
        transcription_raw = ai_data.get("transcription", {})
        speech_findings: List[SpeechFinding] = []
        for idx, sf in enumerate(transcription_raw.get("findings", []), start=1):
            if isinstance(sf, dict):
                orig_ex = str(sf.get("original_excerpt", "")).strip()
                sf_ts = sf.get("timestamp")
                if not sf_ts or sf_ts == "00:00":
                    sf_ts = find_speech_timestamp(orig_ex, speech_segments)
                speech_findings.append(SpeechFinding(
                    id=f"sp-{idx}",
                    timestamp=sf_ts or "00:00",
                    original_excerpt=orig_ex,
                    suggested_correction=str(sf.get("suggested_correction", "")).strip(),
                    category=str(sf.get("category", "grammar")),
                    explanation=str(sf.get("explanation", "")).strip(),
                    severity=str(sf.get("severity", "medium")),
                ))

        transcription_obj = TranscriptionAnalysis(
            original_text=transcript_text or transcription_raw.get("original_text", ""),
            corrected_text=transcription_raw.get("corrected_text", transcript_text),
            language=transcription_lang,
            findings=speech_findings,
        )

        # Parse & Validate Visual Findings with Timestamps
        visual_raw = ai_data.get("visual_text", {})
        visual_findings: List[VisualFinding] = []
        for idx, vf in enumerate(visual_raw.get("findings", []), start=1):
            if isinstance(vf, dict):
                orig_vt = str(vf.get("original_text", "")).strip()
                vf_ts = vf.get("timestamp")
                if not vf_ts or vf_ts == "00:00":
                    vf_ts = find_visual_timestamp(orig_vt, visual_segments)
                visual_findings.append(VisualFinding(
                    timestamp=vf_ts or "00:00",
                    original_text=orig_vt,
                    suggested_text=str(vf.get("suggested_text", "")).strip(),
                    category=str(vf.get("category", "clarity")),
                    explanation=str(vf.get("explanation", "")).strip(),
                    severity=str(vf.get("severity", "medium")),
                ))

        visual_segments_obj = [
            VisualTextSegment(timestamp=s["timestamp"], text=s["text"])
            for s in visual_segments
        ]

        visual_text_obj = VisualTextAnalysis(
            segments=visual_segments_obj,
            findings=visual_findings,
        )

        # Parse & Validate Combined Findings & Recommendations
        combined_raw = ai_data.get("combined_analysis", {})
        combined_findings: List[CombinedFinding] = []
        for cf in combined_raw.get("findings", []):
            if isinstance(cf, dict):
                combined_findings.append(CombinedFinding(
                    topic=cf.get("topic"),
                    visual_text=cf.get("visual_text"),
                    spoken_text=cf.get("spoken_text"),
                    contradiction_type=cf.get("contradiction_type"),
                    explanation=str(cf.get("explanation", "")),
                    severity=str(cf.get("severity", "medium")),
                ))

        recommendations = [
            str(r) for r in combined_raw.get("recommendations", []) if r
        ]

        combined_obj = CombinedAnalysis(
            findings=combined_findings,
            recommendations=recommendations,
        )

        # Construct Unified Text-Compatible Findings with exact Timestamps
        unified_findings: List[GrammarFinding] = []
        for sf in speech_findings:
            unified_findings.append(GrammarFinding(
                id=sf.id or f"sp-{len(unified_findings) + 1}",
                category=sf.category,
                severity=sf.severity,
                original_text=sf.original_excerpt,
                suggestion=sf.suggested_correction,
                explanation=sf.explanation,
                timestamp=sf.timestamp,
                media_type="speech",
                confidence=0.95,
            ))

        for vf in visual_findings:
            unified_findings.append(GrammarFinding(
                id=f"vis-{len(unified_findings) + 1}",
                category=vf.category,
                severity=vf.severity,
                original_text=vf.original_text,
                suggestion=vf.suggested_text,
                explanation=vf.explanation,
                timestamp=vf.timestamp,
                media_type="visual",
                confidence=0.90,
            ))

        for cf in combined_findings:
            unified_findings.append(GrammarFinding(
                id=f"comb-{len(unified_findings) + 1}",
                category="consistency",
                severity=cf.severity,
                original_text=f"Spoken: '{cf.spoken_text or ''}' vs Visual: '{cf.visual_text or ''}'",
                suggestion="Align spoken and visual messaging for brand clarity",
                explanation=cf.explanation,
                timestamp="00:00",
                media_type="combined",
                confidence=0.88,
            ))

        # Determine Root original_text and corrected_text
        if transcript_text:
            root_orig_text = transcript_text
            root_corr_text = transcription_obj.corrected_text or transcript_text
        elif visual_segments:
            root_orig_text = "\n".join(f"[{s['timestamp']}] {s['text']}" for s in visual_segments)
            root_corr_text = root_orig_text
        else:
            root_orig_text = "No speech or visible text detected in media."
            root_corr_text = root_orig_text

        # Summary Metrics Calculation
        summary_raw = ai_data.get("summary", {})
        total_issues = len(unified_findings)

        grammar_issues = sum(1 for f in unified_findings if "grammar" in f.category.lower())
        spelling_issues = sum(1 for f in unified_findings if "spell" in f.category.lower())
        punctuation_issues = sum(1 for f in unified_findings if "punct" in f.category.lower())
        brand_issues = sum(1 for f in unified_findings if "brand" in f.category.lower()) + len(combined_findings)
        clarity_issues = sum(1 for f in unified_findings if "clarity" in f.category.lower() or "style" in f.category.lower())

        summary_obj = MediaAnalysisSummary(
            total_issues=total_issues,
            grammar_issues=grammar_issues,
            spelling_issues=spelling_issues,
            punctuation_issues=punctuation_issues,
            brand_issues=brand_issues,
            clarity_issues=clarity_issues,
        )

        response = MediaAnalysisResponse(
            status="success",
            media_type=media_type,
            duration=round(duration, 2),
            original_text=root_orig_text,
            corrected_text=root_corr_text,
            findings=unified_findings,
            transcription=transcription_obj,
            visual_text=visual_text_obj,
            combined_analysis=combined_obj,
            summary=summary_obj,
        )

        # Optional Supabase Persistence
        if save_history and supabase_service.is_configured():
            try:
                record = supabase_service.save_media_analysis(
                    media_type=media_type,
                    duration_seconds=duration,
                    original_filename=filename or os.path.basename(target_path),
                    transcription=transcription_obj.model_dump(),
                    visual_text=visual_text_obj.model_dump(),
                    combined_analysis=combined_obj.model_dump(),
                    summary=summary_obj.model_dump(),
                    user_id=user_id,
                )
                response.id = record.get("id")
                response.created_at = str(record.get("created_at", ""))

                # Also sync into analysis_history for dashboard metrics and history page
                if user_id:
                    try:
                        supabase_service.save_analysis_history(
                            user_id=user_id,
                            input_type="text",
                            original_text=f"[{media_type.upper()} Audit: {filename or 'media'}]\n" + root_orig_text[:2000],
                            corrected_text=root_corr_text[:2000],
                            findings=[f.model_dump() for f in unified_findings],
                            summary=f"{media_type.title()} analysis: {len(unified_findings)} issues identified.",
                            model_name=getattr(settings, "EFFECTIVE_MODEL", "Gemini 3.5 Flash"),
                        )
                    except Exception as hist_err:
                        logger.warning("Could not sync media to analysis_history: %s", hist_err)

            except Exception as db_exc:
                logger.warning("Could not persist media analysis to Supabase: %s", db_exc)

        return response

    finally:
        # Guarantee cleanup of all temporary disk files
        for p in cleanup_paths:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass
        shutil.rmtree(temp_dir, ignore_errors=True)
