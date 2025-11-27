"""
RAG Audio Parser - ORKIO v3.7.0
Parser para áudio/vídeo com Whisper API
"""

import logging
import os
import subprocess
import tempfile
from openai import OpenAI

logger = logging.getLogger(__name__)

ALLOW_AUDIO = os.getenv("ALLOW_AUDIO", "true").lower() == "true"
ALLOW_VIDEO = os.getenv("ALLOW_VIDEO", "true").lower() == "true"

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
)


def transcribe_audio(file_path: str) -> str:
    """Transcribe audio with OpenAI Whisper API"""
    if not ALLOW_AUDIO:
        raise ValueError("Audio transcription not enabled")
    
    try:
        with open(file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        
        text = transcript.text
        logger.info(f"Audio transcribed: {len(text)} chars")
        return text
    
    except Exception as e:
        logger.error(f"Audio transcription failed: {e}")
        raise ValueError(f"Audio transcription failed: {e}")


def transcribe_video(file_path: str) -> str:
    """Transcribe video by extracting audio and transcribing"""
    if not ALLOW_VIDEO:
        raise ValueError("Video transcription not enabled")
    
    try:
        # Extract audio with ffmpeg
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_audio:
            audio_path = tmp_audio.name
        
        cmd = [
            "ffmpeg",
            "-i", file_path,
            "-vn",  # No video
            "-acodec", "libmp3lame",
            "-y",  # Overwrite
            audio_path
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Transcribe audio
        text = transcribe_audio(audio_path)
        
        # Cleanup
        os.remove(audio_path)
        
        logger.info(f"Video transcribed: {len(text)} chars")
        return text
    
    except Exception as e:
        logger.error(f"Video transcription failed: {e}")
        raise ValueError(f"Video transcription failed: {e}")

