"""
Konfigurasi sentral aplikasi.
Semua env variable dibaca dari sini — satu sumber kebenaran.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List, Optional


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────
    app_name: str = "FastAPI Vcols"
    app_version: str = "1.0.0"
    debug: bool = False
    api_keys: str = ""  # comma-separated, API keys untuk autentikasi client

    # ── AI ───────────────────────────────────────────────────
    gemini_api_key: str
    groq_api_key: str  # Groq Cloud API key untuk Whisper STT
    hf_token: Optional[str] = None  # Hugging Face token — opsional, untuk pyannote di masa depan

    # ── Supabase ─────────────────────────────────────────────
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str

    # ── CORS ─────────────────────────────────────────────────
    frontend_url: str = "http://localhost:5173"
    allowed_origins: str = ""  # comma-separated, isi saat production

    def get_api_keys(self) -> List[str]:
        """Parse comma-separated API keys dari env."""
        if not self.api_keys:
            return []
        return [k.strip() for k in self.api_keys.split(",") if k.strip()]

    def get_allowed_origins(self) -> List[str]:
        """
        Gabungkan semua allowed origins.
        Localhost selalu diizinkan untuk development.
        """
        origins = [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:5500",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:5500",
            self.frontend_url,
        ]
        # Tambah origins dari env jika ada (comma-separated)
        if self.allowed_origins:
            extras = [o.strip() for o in self.allowed_origins.split(",") if o.strip()]
            origins.extend(extras)
        # Buang duplikat
        return list(set(origins))

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