"""
Entry Point — Meeting AI Backend
Inisialisasi FastAPI, CORS, router, dan startup events di sini.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.endpoints import meetings, websocket, health
from app.services.whisper_service import WhisperService

# ─── Logging Setup ────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─── Lifespan (Startup & Shutdown) ───────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Kode di sini jalan SATU KALI saat server start.
    Load Whisper model di startup agar request pertama tidak lambat.
    """
    logger.info("🚀 Starting Meeting AI Backend...")
    
    # Load Whisper model ke memori (bisa makan waktu 10-30 detik)
    WhisperService.load_model()
    
    logger.info("✅ Backend siap menerima request.")
    
    yield  # ← Server berjalan di sini
    
    logger.info("⛔ Shutting down Meeting AI Backend...")


# ─── FastAPI App ──────────────────────────────────────────────
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    ## Meeting AI Backend
    
    Backend untuk aplikasi perekam dan analisis rapat otomatis.
    
    ### Fitur:
    - 🎙️ **Real-time transcription** via WebSocket + Whisper AI
    - 🧠 **Meeting analysis** via Gemini 1.5 Flash (summary + action items)  
    - 💾 **Persistent storage** via Supabase
    """,
    docs_url="/docs",          # Swagger UI
    redoc_url="/redoc",        # ReDoc UI
    lifespan=lifespan,
)


# ─── CORS Middleware ──────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:3000",   # React dev server
        "http://localhost:5173",   # Vite dev server
        "null",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Routers ─────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(meetings.router, prefix="/api/v1")
app.include_router(websocket.router, prefix="/api/v1")


# ─── Root ─────────────────────────────────────────────────────
@app.get("/", tags=["Root"])
async def root():
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs",
    }
