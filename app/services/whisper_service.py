"""
Whisper Service — "Telinga" AI.
Menggunakan Groq Cloud API (whisper-large-v3-turbo) untuk speech-to-text.
Audio dikirim via HTTP ke server Groq — tidak perlu load model lokal.
Keuntungan: RAM server aman, kecepatan <1 detik, akurasi tinggi.

Mode response:
  - verbose_json (default): return segments dengan timestamps — digunakan untuk diarization
  - text: return plain text saja — digunakan untuk backward compat
"""
import httpx
import tempfile
import os
import logging
from typing import Optional
from app.core.config import get_settings

logger = logging.getLogger(__name__)

GROQ_TRANSCRIPTION_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_MODEL = "whisper-large-v3-turbo"


class WhisperService:

    @classmethod
    async def transcribe_with_timestamps(
        cls,
        audio_bytes: bytes,
        language: str = "id",
    ) -> dict:
        """
        Transkripsi audio dengan timestamps per segment.
        Menggunakan verbose_json untuk mendapat data diarization.

        Returns:
            {
                "text": str,           # Transkrip lengkap plain
                "segments": [
                    {"start": float, "end": float, "text": str, ...}
                ]
            }
        """
        settings = get_settings()
        tmp_path = None

        try:
            # 1. Simpan bytes ke file temp (Groq API butuh file upload)
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
                f.write(audio_bytes)
                tmp_path = f.name

            # 2. Kirim ke Groq Whisper API dengan verbose_json
            async with httpx.AsyncClient(timeout=120.0) as client:
                with open(tmp_path, "rb") as audio_file:
                    response = await client.post(
                        GROQ_TRANSCRIPTION_URL,
                        headers={
                            "Authorization": f"Bearer {settings.groq_api_key}",
                        },
                        files={
                            "file": ("audio.webm", audio_file, "audio/webm"),
                        },
                        data={
                            "model": GROQ_MODEL,
                            "language": language,
                            "response_format": "verbose_json",
                        },
                    )

            if response.status_code != 200:
                error_detail = response.text[:300]
                logger.error(f"Groq API error {response.status_code}: {error_detail}")
                raise RuntimeError(
                    f"Groq transcription gagal (HTTP {response.status_code}): {error_detail}"
                )

            data = response.json()
            text = data.get("text", "").strip()
            segments = data.get("segments", [])

            logger.info(
                f"Transcribed via Groq: {len(text)} chars, {len(segments)} segments."
            )
            return {"text": text, "segments": segments}

        except httpx.TimeoutException:
            logger.error("Groq API timeout — audio terlalu besar atau koneksi lambat")
            raise RuntimeError("Groq API timeout. Coba lagi nanti.")

        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            raise

        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

    @classmethod
    async def transcribe_audio_chunk(
        cls,
        audio_bytes: bytes,
        language: str = "id",
    ) -> str:
        """
        Backward-compatible method — return plain text saja.
        Internally memanggil transcribe_with_timestamps.
        """
        result = await cls.transcribe_with_timestamps(audio_bytes, language)
        return result["text"]

    @classmethod
    async def transcribe_full_audio(cls, audio_bytes: bytes, language: str = "id") -> str:
        """Alias untuk transcribe_audio_chunk — backward compat."""
        return await cls.transcribe_audio_chunk(audio_bytes, language)