"""
Health Check Endpoint.
Digunakan untuk monitoring dan deployment checks (Docker, K8s, dll).
"""
from fastapi import APIRouter
from app.core.config import get_settings
from app.services.whisper_service import WhisperService

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Cek status server dan model AI."""
    settings = get_settings()
    whisper_loaded = WhisperService._model is not None

    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "services": {
            "whisper": "loaded" if whisper_loaded else "not_loaded",
            "gemini": "configured" if settings.gemini_api_key else "missing_api_key",
            "supabase": "configured" if settings.supabase_url else "missing_url",
        },
    }