"""Comprehensive unit test suite for app.speech module.

Verifies all 15 required scenarios:
1. MP3 transcription
2. MP4-to-MP3 conversion
3. Video without an audio stream
4. Second-by-second frame extraction
5. PaddleOCR text extraction
6. Consecutive duplicate text removal
7. Text reappearing after an intervening different segment
8. Empty OCR frames
9. Gemini speech analysis
10. Gemini visual text analysis
11. Combined speech and visual analysis
12. Missing Groq API key
13. Groq API failure
14. Invalid or corrupted media files
15. Temporary file cleanup
"""

import os
import tempfile
import subprocess
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import numpy as np

import app.speech as sp
from app.core.exceptions import (
    InvalidMediaError,
    SpeechToTextError,
)


@pytest.fixture
def ffmpeg_bin():
    return sp.resolve_ffmpeg_path()


@pytest.fixture
def sample_mp3(tmp_path, ffmpeg_bin):
    """Generates a small 1-second silent MP3 test file."""
    path = str(tmp_path / "test_audio.mp3")
    cmd = [
        ffmpeg_bin, "-y",
        "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
        "-t", "1",
        "-acodec", "libmp3lame",
        path,
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return path


@pytest.fixture
def sample_mp4_with_audio(tmp_path, ffmpeg_bin):
    """Generates a 2-second test MP4 video with an audio stream."""
    path = str(tmp_path / "test_video_with_audio.mp4")
    cmd = [
        ffmpeg_bin, "-y",
        "-f", "lavfi", "-i", "testsrc=duration=2:size=160x120:rate=10",
        "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
        "-t", "2",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        path,
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return path


@pytest.fixture
def sample_mp4_no_audio(tmp_path, ffmpeg_bin):
    """Generates a 2-second test MP4 video without an audio stream."""
    path = str(tmp_path / "test_silent_video.mp4")
    cmd = [
        ffmpeg_bin, "-y",
        "-f", "lavfi", "-i", "testsrc=duration=2:size=160x120:rate=10",
        "-t", "2",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        path,
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return path


# ------------------------------------------------------------------------------
# 1. MP3 Transcription
# ------------------------------------------------------------------------------

def test_1_mp3_transcription(sample_mp3):
    mock_transcription = MagicMock()
    mock_transcription.text = "Welcome to BrandProof AI speech analysis."
    mock_transcription.language = "en"
    mock_transcription.duration = 1.0

    mock_client = MagicMock()
    mock_client.audio.transcriptions.create.return_value = mock_transcription

    with patch("app.speech.get_groq_client", return_value=mock_client):
        result = sp.transcribe_audio(sample_mp3)

    assert result["transcript"] == "Welcome to BrandProof AI speech analysis."
    assert result["language"] == "en"
    assert result["duration"] == 1.0
    mock_client.audio.transcriptions.create.assert_called_once()


# ------------------------------------------------------------------------------
# 2. MP4-to-MP3 Conversion
# ------------------------------------------------------------------------------

def test_2_mp4_to_mp3_conversion(sample_mp4_with_audio):
    output_mp3 = sp.convert_video_to_audio(sample_mp4_with_audio)
    try:
        assert output_mp3 is not None
        assert os.path.exists(output_mp3)
        assert os.path.getsize(output_mp3) > 0
        info = sp.get_media_info(output_mp3)
        assert info["has_audio"] is True
    finally:
        if output_mp3 and os.path.exists(output_mp3):
            os.remove(output_mp3)


# ------------------------------------------------------------------------------
# 3. Video Without an Audio Stream
# ------------------------------------------------------------------------------

def test_3_video_without_audio_stream(sample_mp4_no_audio):
    output_mp3 = sp.convert_video_to_audio(sample_mp4_no_audio)
    assert output_mp3 is None, "Expected None for video without audio stream"


# ------------------------------------------------------------------------------
# 4. Second-by-Second Frame Extraction
# ------------------------------------------------------------------------------

def test_4_second_by_second_frame_extraction(sample_mp4_with_audio):
    frames = sp.extract_video_frames(sample_mp4_with_audio)
    assert len(frames) >= 2, "Expected at least 2 frames for 2-second video"
    # Check timestamps format MM:SS
    assert frames[0][0] == "00:00"
    assert frames[1][0] == "00:01"
    # Check frame is a numpy image array
    assert isinstance(frames[0][1], np.ndarray)
    assert len(frames[0][1].shape) == 3


# ------------------------------------------------------------------------------
# 5. PaddleOCR Text Extraction
# ------------------------------------------------------------------------------

def test_5_paddleocr_text_extraction():
    dummy_frame = np.zeros((100, 200, 3), dtype=np.uint8)

    with patch.object(sp.ocr_service, "extract_text_from_bytes", return_value=("BrandProof AI Platform", MagicMock())) as mock_ocr:
        text = sp.extract_text_from_frame(dummy_frame)
        assert text == "BrandProof AI Platform"
        mock_ocr.assert_called_once()


# ------------------------------------------------------------------------------
# 6. Consecutive Duplicate Text Removal
# ------------------------------------------------------------------------------

def test_6_consecutive_duplicate_text_removal():
    raw_segments = [
        {"timestamp": "00:00", "text": "Welcome to BrandProof AI"},
        {"timestamp": "00:01", "text": "Welcome to BrandProof AI"},
        {"timestamp": "00:02", "text": "  Welcome to   BrandProof AI  "},  # Whitespace duplicate
        {"timestamp": "00:03", "text": "AI-powered content platform"},
        {"timestamp": "00:04", "text": "AI-powered content platform"},
        {"timestamp": "00:05", "text": "Our mission is quality"},
    ]

    deduped = sp.deduplicate_ocr_segments(raw_segments)
    assert len(deduped) == 3
    assert deduped[0] == {"timestamp": "00:00", "text": "Welcome to BrandProof AI"}
    assert deduped[1] == {"timestamp": "00:03", "text": "AI-powered content platform"}
    assert deduped[2] == {"timestamp": "00:05", "text": "Our mission is quality"}


# ------------------------------------------------------------------------------
# 7. Text Reappearing After an Intervening Different Segment
# ------------------------------------------------------------------------------

def test_7_text_reappearing_after_intervening_segment():
    raw_segments = [
        {"timestamp": "00:00", "text": "BrandProof AI"},
        {"timestamp": "00:01", "text": "BrandProof AI"},
        {"timestamp": "00:02", "text": "Different Slogan"},
        {"timestamp": "00:03", "text": "BrandProof AI"},  # Reappears after intervening segment
        {"timestamp": "00:04", "text": "BrandProof AI"},
    ]

    deduped = sp.deduplicate_ocr_segments(raw_segments)
    assert len(deduped) == 3
    assert deduped[0] == {"timestamp": "00:00", "text": "BrandProof AI"}
    assert deduped[1] == {"timestamp": "00:02", "text": "Different Slogan"}
    assert deduped[2] == {"timestamp": "00:03", "text": "BrandProof AI"}


# ------------------------------------------------------------------------------
# 8. Empty OCR Frames
# ------------------------------------------------------------------------------

def test_8_empty_ocr_frames():
    raw_segments = [
        {"timestamp": "00:00", "text": ""},
        {"timestamp": "00:01", "text": "   "},
        {"timestamp": "00:02", "text": "Valid Header"},
        {"timestamp": "00:03", "text": ""},
    ]

    deduped = sp.deduplicate_ocr_segments(raw_segments)
    assert len(deduped) == 1
    assert deduped[0] == {"timestamp": "00:02", "text": "Valid Header"}


# ------------------------------------------------------------------------------
# 9. Gemini Speech Analysis
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_9_gemini_speech_analysis():
    mock_ai_output = {
        "transcription": {
            "original_text": "We is launching our new product.",
            "corrected_text": "We are launching our new product.",
            "findings": [
                {
                    "original_excerpt": "We is",
                    "suggested_correction": "We are",
                    "category": "grammar",
                    "explanation": "Subject-verb agreement error.",
                    "severity": "major",
                }
            ],
        },
        "visual_text": {"findings": []},
        "combined_analysis": {"findings": [], "recommendations": []},
        "summary": {"total_issues": 1, "grammar_issues": 1},
    }

    with patch.object(sp.ai_provider_service, "generate_structured_json", new_callable=AsyncMock, return_value=mock_ai_output):
        result = await sp.analyze_transcript("We is launching our new product.")

    trans = result.get("transcription", {})
    assert trans["corrected_text"] == "We are launching our new product."
    assert len(trans["findings"]) == 1
    assert trans["findings"][0]["original_excerpt"] == "We is"


# ------------------------------------------------------------------------------
# 10. Gemini Visual Text Analysis
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_10_gemini_visual_text_analysis():
    visual_segments = [
        {"timestamp": "00:03", "text": "AI powered content platform"}
    ]

    mock_ai_output = {
        "transcription": {"original_text": "", "corrected_text": "", "findings": []},
        "visual_text": {
            "findings": [
                {
                    "timestamp": "00:03",
                    "original_text": "AI powered content platform",
                    "suggested_text": "AI-powered content platform",
                    "category": "punctuation",
                    "explanation": "A hyphen improves the compound modifier.",
                    "severity": "minor",
                }
            ]
        },
        "combined_analysis": {"findings": [], "recommendations": []},
        "summary": {"total_issues": 1, "punctuation_issues": 1},
    }

    with patch.object(sp.ai_provider_service, "generate_structured_json", new_callable=AsyncMock, return_value=mock_ai_output):
        result = await sp.analyze_visual_text(visual_segments)

    visual = result.get("visual_text", {})
    assert len(visual["findings"]) == 1
    assert visual["findings"][0]["timestamp"] == "00:03"
    assert visual["findings"][0]["suggested_text"] == "AI-powered content platform"


# ------------------------------------------------------------------------------
# 11. Combined Speech and Visual Analysis
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_11_combined_speech_and_visual_analysis():
    visual_segments = [{"timestamp": "00:04", "text": "Price: $49/mo"}]
    transcript = "Get started today for only thirty-nine dollars a month."

    mock_ai_output = {
        "transcription": {"original_text": transcript, "corrected_text": transcript, "findings": []},
        "visual_text": {"findings": []},
        "combined_analysis": {
            "findings": [
                {
                    "topic": "Pricing Discrepancy",
                    "visual_text": "Price: $49/mo",
                    "spoken_text": "thirty-nine dollars a month",
                    "contradiction_type": "contradiction",
                    "explanation": "The on-screen graphic displays $49/mo while the audio says thirty-nine dollars.",
                    "severity": "critical",
                }
            ],
            "recommendations": ["Ensure on-screen graphics match verbal pricing claims."],
        },
        "summary": {"total_issues": 1, "brand_issues": 1},
    }

    with patch.object(sp.ai_provider_service, "generate_structured_json", new_callable=AsyncMock, return_value=mock_ai_output):
        result = await sp.analyze_combined_content(transcript, visual_segments)

    comb = result.get("combined_analysis", {})
    assert len(comb["findings"]) == 1
    assert comb["findings"][0]["contradiction_type"] == "contradiction"
    assert "Pricing" in comb["findings"][0]["topic"]
    assert len(comb["recommendations"]) == 1


# ------------------------------------------------------------------------------
# 12. Missing Groq API Key
# ------------------------------------------------------------------------------

def test_12_missing_groq_api_key(sample_mp3):
    with patch.object(sp.settings, "GROQ_API_KEY", None), patch.dict(os.environ, {"GROQ_API_KEY": ""}):
        with pytest.raises(SpeechToTextError) as exc_info:
            sp.transcribe_audio(sample_mp3)
        assert "GROQ_API_KEY is not configured" in str(exc_info.value)


# ------------------------------------------------------------------------------
# 13. Groq API Failure
# ------------------------------------------------------------------------------

def test_13_groq_api_failure(sample_mp3):
    mock_client = MagicMock()
    mock_client.audio.transcriptions.create.side_effect = Exception("Rate limit reached (429)")

    with patch("app.speech.get_groq_client", return_value=mock_client):
        with pytest.raises(SpeechToTextError) as exc_info:
            sp.transcribe_audio(sample_mp3)
        assert "rate limit" in str(exc_info.value).lower()


# ------------------------------------------------------------------------------
# 14. Invalid or Corrupted Media Files
# ------------------------------------------------------------------------------

def test_14_invalid_or_corrupted_media_files(tmp_path):
    corrupted = str(tmp_path / "corrupted.mp4")
    with open(corrupted, "wb") as f:
        f.write(b"NOT_A_REAL_VIDEO_HEADER_DATA_GARBAGE")

    with pytest.raises(InvalidMediaError):
        sp.get_media_info(corrupted)

    empty_file = str(tmp_path / "empty.mp3")
    with open(empty_file, "wb") as f:
        pass

    with pytest.raises(InvalidMediaError):
        sp.get_media_info(empty_file)


# ------------------------------------------------------------------------------
# 15. Temporary File Cleanup
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_15_temporary_file_cleanup(sample_mp4_with_audio):
    created_temps = []

    original_mkstemp = tempfile.mkstemp

    def track_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        created_temps.append(path)
        return fd, path

    with patch("tempfile.mkstemp", side_effect=track_mkstemp):
        with patch.object(sp, "transcribe_audio", return_value={"transcript": "Hello", "language": "en", "duration": 2.0}):
            with patch.object(sp, "extract_unique_video_text", return_value=[{"timestamp": "00:00", "text": "Hello"}]):
                with patch.object(sp, "analyze_media_ai", new_callable=AsyncMock, return_value={
                    "transcription": {"original_text": "Hello", "corrected_text": "Hello", "findings": []},
                    "visual_text": {"findings": []},
                    "combined_analysis": {"findings": [], "recommendations": []},
                    "summary": {"total_issues": 0},
                }):
                    await sp.analyze_media(
                        file_path=sample_mp4_with_audio,
                        save_history=False,
                    )

    # Verify all temporary files tracked during execution have been cleaned up
    for temp_path in created_temps:
        assert not os.path.exists(temp_path), f"Temporary file was not cleaned up: {temp_path}"
