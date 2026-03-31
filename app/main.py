"""
Entry Point — Meeting AI Backend
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.endpoints import meetings, websocket, health, auth

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting Meeting AI Backend...")
    logger.info("✅ Backend siap menerima request (Groq Whisper API mode).")
    yield
    logger.info("⛔ Shutting down Meeting AI Backend...")


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
## Meeting AI Vcols
Backend untuk aplikasi perekam dan analisis rapat otomatis berbasis AI.

### Fitur:
- 🎙️ **Real-time transcription** via WebSocket + Groq Whisper API
- 🧠 **Meeting analysis** via AI LLM (summary + action items + rekomendasi strategis)
- 💾 **Persistent storage** via Supabase
- 🔐 **API Key auth** — semua endpoint (kecuali `/health`) dilindungi `X-API-Key`

### Cara Pakai:
1. `POST /api/v1/meetings/` — buat sesi rapat baru, dapat `meeting_id`
2. `WS /api/v1/ws/transcribe/{meeting_id}?api_key=KEY` — stream audio real-time
3. `POST /api/v1/meetings/{id}/finish` — kirim transkrip, dapatkan analisis AI
4. `GET /api/v1/meetings/user/{user_id}` — ambil history rapat per user
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────
allowed_origins = settings.get_allowed_origins()
logger.info(f"CORS allowed origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(meetings.router, prefix="/api/v1")
app.include_router(websocket.router, prefix="/api/v1")

# Router Auth dari Supabase
app.include_router(auth.router, prefix="/api/v1/auth")


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs",
    }