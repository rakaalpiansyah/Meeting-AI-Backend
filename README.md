# 🎙️ Meeting AI Backend

Backend FastAPI untuk aplikasi perekam dan analisis rapat otomatis berbasis AI.

## Arsitektur

```
React FE  ──WebSocket──▶  FastAPI  ──▶  Whisper  (Transkripsi real-time)
                                   ──▶  Gemini   (Summary + Action Items)
                                   ──▶  Supabase (Penyimpanan)
```

## Stack Teknologi

| Komponen | Teknologi | Fungsi |
|----------|-----------|--------|
| Framework | FastAPI | Web framework async |
| AI Transkripsi | Whisper (OpenAI) | Speech-to-Text |
| AI Analisis | Gemini 1.5 Flash | Ringkasan & Action Items |
| Database | Supabase (PostgreSQL) | Penyimpanan hasil rapat |
| Real-time | WebSocket | Streaming audio dari browser |

---

## Setup

### 1. Prasyarat

- Python 3.11+
- `ffmpeg` terinstall di sistem (wajib untuk Whisper)

```bash
# MacOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows
# Download dari https://ffmpeg.org/download.html
```

### 2. Clone & Install

```bash
git clone <repo-url>
cd meeting-ai-backend

# Buat virtual environment
python -m venv venv
source venv/bin/activate      # Linux/Mac
# atau: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Konfigurasi Environment

```bash
cp .env.example .env
# Edit .env dan isi semua variable yang diperlukan
```

Variabel wajib diisi:
- `GEMINI_API_KEY` → Dapatkan di [Google AI Studio](https://aistudio.google.com/app/apikey)
- `SUPABASE_URL` → Project URL di dashboard Supabase
- `SUPABASE_ANON_KEY` → Anon key Supabase
- `SUPABASE_SERVICE_ROLE_KEY` → Service role key Supabase

### 4. Setup Database Supabase

1. Buka Supabase dashboard → SQL Editor
2. Copy-paste seluruh isi file `supabase_schema.sql`
3. Klik "Run"

### 5. Jalankan Server

```bash
# Development (auto-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

> ⚠️ Gunakan `--workers 1` karena Whisper model di-load ke memori — multi-worker akan duplikasi model dan boros RAM.

---

## API Endpoints

### REST

| Method | URL | Deskripsi |
|--------|-----|-----------|
| `GET` | `/health` | Status server & model AI |
| `POST` | `/api/v1/meetings/` | Buat sesi rapat baru |
| `POST` | `/api/v1/meetings/{id}/finish` | Selesaikan + analisis dengan Gemini |
| `GET` | `/api/v1/meetings/user/{user_id}` | Daftar rapat milik user |
| `GET` | `/api/v1/meetings/{id}` | Detail satu rapat |
| `DELETE` | `/api/v1/meetings/{id}` | Hapus rapat |

### WebSocket

```
ws://localhost:8000/api/v1/ws/transcribe/{meeting_id}
```

**Kirim dari FE:**
- `bytes` → Audio chunk (binary)
- `{"type": "ping"}` → Keepalive
- `{"type": "stop"}` → Akhiri sesi

**Terima di FE:**
- `{"type": "transcript", "chunk_index": 0, "text": "..."}` → Hasil transkripsi
- `{"type": "pong"}` → Respons ping
- `{"type": "session_ended", "full_transcript": "..."}` → Rapat selesai
- `{"type": "error", "message": "..."}` → Error

---

## Swagger UI

Buka di browser setelah server jalan:
```
http://localhost:8000/docs
```

---

## Struktur Folder

```
meeting-ai-backend/
├── app/
│   ├── main.py                    # Entry point FastAPI
│   ├── core/
│   │   └── config.py              # Konfigurasi & env variables
│   ├── api/
│   │   └── endpoints/
│   │       ├── meetings.py        # REST endpoints rapat
│   │       ├── websocket.py       # WebSocket streaming audio
│   │       └── health.py          # Health check
│   ├── schemas/
│   │   └── meeting.py             # Pydantic request/response models
│   └── services/
│       ├── whisper_service.py     # Whisper speech-to-text
│       ├── gemini_service.py      # Gemini summarization
│       └── supabase_service.py    # Database operations
├── supabase_schema.sql            # SQL schema untuk Supabase
├── requirements.txt
├── .env.example
└── README.md
```

---

## Pilihan Ukuran Model Whisper

| Model | VRAM | Kecepatan | Akurasi | Rekomendasi |
|-------|------|-----------|---------|-------------|
| `tiny` | ~1 GB | ⚡⚡⚡⚡ | ⭐⭐ | Testing lokal |
| `base` | ~1 GB | ⚡⚡⚡ | ⭐⭐⭐ | **Default (direkomendasikan)** |
| `small` | ~2 GB | ⚡⚡ | ⭐⭐⭐⭐ | Jika RAM cukup |
| `medium` | ~5 GB | ⚡ | ⭐⭐⭐⭐⭐ | Server production |

Ganti via `.env`: `WHISPER_MODEL_SIZE=small`
# Rest-API-TTS-Summary
