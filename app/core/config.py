"""
Konfigurasi sentral aplikasi.
Semua env variable dibaca dari sini — satu sumber kebenaran.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────
    app_name: str = "Meeting AI Backend"
    app_version: str = "1.0.0"
    debug: bool = False
    secret_key: str = "changeme"

    # ── AI ───────────────────────────────────────────────────
    gemini_api_key: str
    whisper_model_size: str = "base"  # tiny/base/small/medium/large

    # ── Supabase ─────────────────────────────────────────────
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str

    # ── CORS ─────────────────────────────────────────────────
    frontend_url: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Cached settings — hanya dibaca sekali dari disk.
    Gunakan dependency injection FastAPI untuk akses di endpoint.
    """
    return Settings()
