# 🎙️ Meeting FastAPI AI

Backend FastAPI untuk aplikasi **perekam dan analisis rapat** otomatis berbasis AI.

> Transkripsi audio via **Groq Whisper API** + Analisis cerdas via **AI LLM** + Penyimpanan via **Supabase**

## Arsitektur

```text
Frontend  ──WebSocket──▶  FastAPI  ──▶  Groq Whisper API  (Speech-to-Text)
                                   ──▶  AI LLM            (Summary + Action Items)
                                   ──▶  Supabase           (Penyimpanan & Auth)
```

## Stack Teknologi

| Komponen | Teknologi | Fungsi |
|----------|-----------|--------|
| Framework | FastAPI | Web framework async |
| Transkripsi | Groq Whisper API (`whisper-large-v3-turbo`) | Speech-to-Text via cloud |
| Analisis AI | LLM (konfigurabel) | Ringkasan, action items, rekomendasi |
| Database | Supabase (PostgreSQL) | Penyimpanan hasil rapat |
| Real-time | WebSocket | Streaming audio dari browser |
| **User Auth** | **Supabase Auth** | **Registrasi, Login, dan manajemen JWT** |
| System Auth | API Key (`X-API-Key` header) | Autentikasi client/server aplikasi |

---

## 🔐 Autentikasi

Aplikasi ini menggunakan dua lapis keamanan: **System API Key** (untuk memastikan request berasal dari aplikasi frontend yang sah) dan **User JWT** (untuk identitas pengguna).

### 1. Autentikasi Pengguna (User Auth via Supabase)
Untuk mendapatkan akses sebagai pengguna, client harus memanggil endpoint `/login` untuk mendapatkan `access_token` (JWT).

### 2. Autentikasi Sistem (REST API)
Kirim header `X-API-Key` di setiap request untuk melindungi endpoint secara global:
```bash
curl -H "X-API-Key: YOUR_API_KEY" https://your-server.com/api/v1/meetings/user/USER_ID
```

### 3. Autentikasi WebSocket
Kirim API Key sebagai query parameter saat membuka koneksi:
```text
ws://your-server.com/api/v1/ws/transcribe/{meeting_id}?=YOUR_API_KEY
```

### Response Error

| Status | Arti |
|--------|------|
| `401` | API Key tidak dikirim |
| `403` | API Key tidak valid |

---

## Setup

### 1. Prasyarat
- Python 3.11+
- API Key dari [Groq Console](https://console.groq.com) (gratis)
- Akun dan Project di [Supabase](https://supabase.com)

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
```

Buat file `.env` dari `.env.example` dan isi variabel berikut:

| Variable | Wajib | Deskripsi |
|----------|-------|-----------|
| `API_KEYS` | ✅ | API keys untuk client (comma-separated) |
| `GEMINI_API_KEY` | ✅ | API key dari Google AI Studio |
| `GROQ_API_KEY` | ✅ | API key dari Groq Console |
| `SUPABASE_URL` | ✅ | Project URL Supabase |
| `SUPABASE_ANON_KEY` | ✅ | Anon key Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ | Service role key Supabase (Akses admin backend) |
| `FRONTEND_URL` | ❌ | URL frontend untuk CORS (default: `http://localhost:5173`) |
| `ALLOWED_ORIGINS` | ❌ | Origin tambahan, comma-separated |

### 4. Setup Database Supabase
1. Buka Supabase dashboard → SQL Editor
2. Copy-paste seluruh isi file `supabase_schema.sql`
3. Klik **Run**
4. *(Opsional)* Matikan "Confirm Email" di menu **Authentication > Providers > Email** untuk mempermudah testing lokal.

### 5. Jalankan Server

```bash
# Development (auto-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```
---

## API Endpoints

> 📖 Swagger UI tersedia di: `http://localhost:8000/docs`

### Auth (Supabase)
| Method | URL | Deskripsi |
|--------|-----|-----------|
| `POST` | `/api/v1/auth/signup` | Registrasi user baru |
| `POST` | `/api/v1/auth/login` | Login user, mengembalikan `access_token` (JWT) |

### Health Check (tanpa auth)
| Method | URL | Deskripsi |
|--------|-----|-----------|
| `GET` | `/health` | Status server & semua service |

### Meetings (perlu `X-API-Key`)
| Method | URL | Deskripsi |
|--------|-----|-----------|
| `POST` | `/api/v1/meetings/` | Buat sesi rapat baru |
| `POST` | `/api/v1/meetings/{id}/finish` | Selesaikan rapat + analisis AI |
| `GET` | `/api/v1/meetings/user/{user_id}` | Daftar rapat milik user |
| `GET` | `/api/v1/meetings/{id}` | Detail lengkap satu rapat |
| `DELETE` | `/api/v1/meetings/{id}?user_id=xxx` | Hapus rapat |

### WebSocket (perlu `api_key` query param)

```
ws://localhost:8000/api/v1/ws/transcribe/{meeting_id}?api_key=YOUR_API_KEY
```

**Kirim dari Frontend:**

| Tipe | Data | Deskripsi |
|------|------|-----------|
| Binary | `bytes` | Audio chunk (WebM/Opus) |
| Text | `{"type": "ping"}` | Keepalive |
| Text | `{"type": "stop"}` | Akhiri rekaman & mulai transkripsi |

**Terima di Frontend:**

| Tipe | Data | Deskripsi |
|------|------|-----------|
| `audio_received` | `{"buffer_kb": 123.4}` | Konfirmasi audio diterima |
| `processing` | `{"message": "..."}` | Sedang memproses audio |
| `transcript` | `{"text": "...", "is_final": true}` | Hasil transkripsi |
| `session_ended` | `{"full_transcript": "..."}` | Sesi selesai |
| `error` | `{"message": "..."}` | Error |

---

## Contoh Penggunaan (Frontend)

### 0. Registrasi & Login (Baru)

```javascript
// 1. Sign Up
const signupRes = await fetch("[https://your-server.com/api/v1/auth/signup](https://your-server.com/api/v1/auth/signup)", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email: "user@domain.com", password: "password123" })
});
const signupData = await signupRes.json();

// 2. Login
const loginRes = await fetch("[https://your-server.com/api/v1/auth/login](https://your-server.com/api/v1/auth/login)", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email: "user@domain.com", password: "password123" })
});
const { access_token, user_id } = await loginRes.json();
// Simpan access_token dan user_id di localStorage / state
```

### 1. Buat Meeting
```javascript
const res = await fetch("[https://your-server.com/api/v1/meetings/](https://your-server.com/api/v1/meetings/)", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "X-API-Key": "YOUR_API_KEY",
    "Authorization": `Bearer ${access_token}` // Opsional: jika endpoint butuh verifikasi JWT
  },
  body: JSON.stringify({
    title: "Weekly Standup",
    user_id: user_id // Didapat dari response login
  })
});
const { meeting_id } = await res.json();
```

### 2. Rekam Audio via WebSocket
```javascript
const ws = new WebSocket(
  `wss://[your-server.com/api/v1/ws/transcribe/$](https://your-server.com/api/v1/ws/transcribe/$){meetingId}?api_key=YOUR_API_KEY`
);

// Kirim audio chunks dari MediaRecorder
mediaRecorder.ondataavailable = (e) => {
  if (e.data.size > 0) ws.send(e.data);
};

// Stop & transkripsi
ws.send(JSON.stringify({ type: "stop" }));

// Terima hasil
ws.onmessage = (e) => {
  const msg = JSON.parse(e.data);
  if (msg.type === "transcript") console.log("Transkrip:", msg.text);
  if (msg.type === "session_ended") console.log("Selesai:", msg.full_transcript);
};
```

### 3. Analisis AI
```javascript
const res = await fetch(`[https://your-server.com/api/v1/meetings/$](https://your-server.com/api/v1/meetings/$){meetingId}/finish`, {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "X-API-Key": "YOUR_API_KEY"
  },
  body: JSON.stringify({
    meeting_id: meetingId,
    full_transcript: fullTranscript
  })
});
const analysis = await res.json();
```

---

## Struktur Folder

```text
meeting-ai-backend/
├── app/
│   ├── main.py                    # Entry point FastAPI
│   ├── core/
│   │   ├── config.py              # Konfigurasi & env variables
│   │   └── auth.py                # API Key authentication
│   ├── api/
│   │   └── endpoints/
│   │       ├── auth.py            # 🔐 Endpoint Supabase Signup & Login
│   │       ├── meetings.py        # REST endpoints rapat
│   │       ├── websocket.py       # WebSocket streaming audio
│   │       └── health.py          # Health check
│   ├── schemas/
│   │   └── meeting.py             # Pydantic request/response models
│   └── services/
│       ├── whisper_service.py     # Groq Whisper API (speech-to-text)
│       ├── ai_service.py          # AI LLM (analisis rapat)
│       └── supabase_service.py    # Database operations
├── meeting-ai-tester.html         # HTML tester untuk testing manual
├── supabase_schema.sql            # SQL schema untuk Supabase
├── requirements.txt
├── nixpacks.toml                  # Deploy config Railway
├── railway.json                   # Railway settings
├── .env.example
└── README.md
```

---

## Response Schemas

### MeetingResultResponse

```json
{
  "meeting_id": "uuid",
  "title": "Weekly Sync Tim Produk",
  "summary": "Ringkasan rapat dari AI...",
  "action_items": [
    {
      "task": "Buat mockup halaman dashboard",
      "assignee": "Raka",
      "deadline": "2026-03-15"
    }
  ],
  "recommendations": [
    {
      "title": "Prioritaskan fitur login",
      "detail": "Berdasarkan diskusi, fitur login harus selesai minggu ini...",
      "priority": "high"
    }
  ],
  "full_transcript": "Teks transkripsi lengkap...",
  "created_at": "2026-03-11T20:00:00"
}
```

---

## Deploy ke Railway

1. Push ke GitHub
2. Hubungkan repo ke [Railway](https://railway.app)
3. Tambahkan **environment variables** di Railway dashboard:
   - `API_KEYS`
   - `GEMINI_API_KEY`
   - `GROQ_API_KEY`
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `FRONTEND_URL` (URL frontend production)
   - `ALLOWED_ORIGINS` (URL frontend, comma-separated)
4. Deploy otomatis! 🚀
