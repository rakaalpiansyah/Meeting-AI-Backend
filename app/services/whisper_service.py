"""
Whisper Service — "Telinga" AI.
Menggunakan faster-whisper (lebih stabil di Windows, lebih cepat 4x).
Model di-load sekali saat startup agar tidak reload tiap request.

Fix: Browser mengirim WebM chunk tanpa header lengkap.
Solusi: Kumpulkan semua chunk, gabung, lalu konversi ke WAV pakai ffmpeg subprocess.
"""
from faster_whisper import WhisperModel
import tempfile
import os
import subprocess
import logging
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class WhisperService:
    _model = None

    @classmethod
    def load_model(cls):
        settings = get_settings()
        if cls._model is None:
            logger.info(f"Loading Whisper model: {settings.whisper_model_size}...")
            cls._model = WhisperModel(
                settings.whisper_model_size,
                device="cpu",
                compute_type="int8",
            )
            logger.info("Whisper model loaded successfully ✓")
        return cls._model

    @classmethod
    async def transcribe_audio_chunk(
        cls,
        audio_bytes: bytes,
        language: str = "id",
    ) -> str:
        """
        Terima bytes audio dari WebSocket (WebM/Opus).
        Konversi ke WAV dulu via ffmpeg, baru transkripsi.
        """
        model = cls._model
        if model is None:
            raise RuntimeError("Whisper model belum di-load.")

        webm_path = None
        wav_path = None

        try:
            # 1. Simpan bytes WebM ke file temp
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
                f.write(audio_bytes)
                webm_path = f.name

            # 2. Konversi WebM → WAV pakai ffmpeg
            wav_path = webm_path.replace(".webm", ".wav")
            result = subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-i", webm_path,
                    "-ar", "16000",   # Sample rate 16kHz (optimal untuk Whisper)
                    "-ac", "1",       # Mono channel
                    "-f", "wav",
                    wav_path,
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr}")
                raise RuntimeError(f"FFmpeg konversi gagal: {result.stderr[-200:]}")

            # 3. Transkripsi WAV dengan faster-whisper
            segments, info = model.transcribe(
                wav_path,
                language=language,
                task="transcribe",
                beam_size=5,
                vad_filter=True,  # Skip bagian sunyi otomatis
            )
            transcript = " ".join(seg.text.strip() for seg in segments)
            logger.debug(f"Transcribed ({info.language}): {transcript[:60]}...")
            return transcript

        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            raise

        finally:
            for path in [webm_path, wav_path]:
                if path and os.path.exists(path):
                    try:
                        os.unlink(path)
                    except Exception:
                        pass

    @classmethod
    async def transcribe_full_audio(cls, audio_bytes: bytes, language: str = "id") -> str:
        return await cls.transcribe_audio_chunk(audio_bytes, language)