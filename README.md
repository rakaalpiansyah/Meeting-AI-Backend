# 🎙️ Meeting AI — FastAPI Backend

> **Backend layanan AI** untuk perekaman, transkripsi otomatis, deteksi speaker, dan analisis rapat berbasis kecerdasan buatan.

🚀 **Live Production:** [https://meeting-ai-backend-production-b61e.up.railway.app/docs](https://meeting-ai-backend-production-b61e.up.railway.app/docs)

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=flat-square&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![Groq](https://img.shields.io/badge/Groq-Whisper%20API-f97316?style=flat-square)](https://console.groq.com)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E?style=flat-square&logo=supabase)](https://supabase.com)

---

## ✨ Fitur Utama

| Fitur                          | Deskripsi                                                   |
| ------------------------------ | ----------------------------------------------------------- |
| 🎤 **Real-time Transcription** | Streaming audio via WebSocket → Groq Whisper API            |
| 👥 **Speaker Diarization**     | Deteksi otomatis siapa berbicara — tanpa model ML lokal     |
| 🧠 **AI Meeting Analysis**     | Summary, action items, dan rekomendasi strategis via LLM    |
| 💾 **Persistent Storage**      | Semua hasil rapat disimpan di Supabase (PostgreSQL)         |
| 🔐 **Dual Auth Layer**         | API Key (sistem) + Supabase Auth (pengguna)                 |
| ⚡ **Async & Fast**            | Dibangun di atas FastAPI + `async/await` — siap skala besar |

---

## 🏛️ Arsitektur

```
┌─────────────┐        WebSocket         ┌──────────────────────────────────────────┐
│   Frontend  │ ──────────────────────▶  │             FastAPI Backend              │
│  (Browser)  │ ◀──────────────────────  │                                          │
└─────────────┘    JSON / Binary         │  ┌─────────────┐  ┌────────────────────┐ │
                                         │  │   Whisper   │  │  Diarization       │ │
                                         │  │  Service    │  │  Service           │ │
                                         │  │ (Groq API)  │  │ (Pause Clustering) │ │
                                         │  └──────┬──────┘  └────────┬───────────┘ │
                                         │         │                  │             │
                                         │  ┌──────▼──────────────────▼───────────┐ │
                                         │  │           AI Service (LLM)          │ │
                                         │  │  Summary + Action Items + Rekom.    │ │
                                         │  └──────────────────┬──────────────────┘ │
                                         │                     │                    │
                                         │  ┌──────────────────▼──────────────────┐ │
                                         │  │        Supabase Service             │ │
                                         │  │    PostgreSQL + Row Level Security  │ │
                                         │  └─────────────────────────────────────┘ │
                                         └──────────────────────────────────────────┘
```

---

## 🔧 Stack Teknologi

| Layer                   | Teknologi                                   | Keterangan                                          |
| ----------------------- | ------------------------------------------- | --------------------------------------------------- |
| **Framework**           | FastAPI                                     | Async web framework Python                          |
| **Transcription**       | Groq Whisper API (`whisper-large-v3-turbo`) | Speech-to-text via cloud, tanpa GPU lokal           |
| **Speaker Diarization** | Pure Python (pause-based clustering)        | Deteksi speaker dari timestamps Groq `verbose_json` |
| **AI Analysis**         | LLM via Groq (Llama 3.3 70B)                | Summary, action items, rekomendasi strategis        |
| **Database**            | Supabase (PostgreSQL)                       | Penyimpanan hasil rapat & transcript                |
| **Real-time**           | WebSocket                                   | Streaming audio dari browser ke backend             |
| **User Auth**           | Supabase Auth                               | JWT-based user authentication                       |
| **System Auth**         | API Key (`X-API-Key` header)                | Autentikasi client aplikasi                         |

---

## 👥 Speaker Diarization

Fitur diarization mendeteksi **siapa yang berbicara** dalam rapat secara otomatis, mengubah transkrip biasa menjadi transkrip berlabel speaker.

**Sebelum diarization:**

```
oke jadi hari ini kita bahas roadmap Q3 betul saya sudah siapkan slide-nya bagus kita mulai dari fitur login
```

**Setelah diarization:**

```
[Speaker 1]: Oke jadi hari ini kita bahas roadmap Q3
[Speaker 2]: Betul, saya sudah siapkan slide-nya.
[Speaker 1]: Bagus, kita mulai dari fitur login.
```

### Cara Kerja

```
Audio WebM
    │
    ▼
Groq Whisper (verbose_json)
    │
    ├── text: "transkrip plain"
    └── segments: [{start, end, text}, ...]
                │
                ▼
    DiarizationService.diarize()
         Gap Analysis (>1.2 detik = ganti speaker)
                │
                ▼
    [{..., speaker: "Speaker 1"}, ...]
                │
                ▼
    "[Speaker 1]: teks...\n[Speaker 2]: teks..."
```

### Keunggulan Pendekatan

| Aspek                     | `pyannote.audio`            | Pendekatan Ini                           |
| ------------------------- | --------------------------- | ---------------------------------------- |
| Install size              | ~3 GB (torch + model)       | 0 MB (built-in)                          |
| Dependencies baru         | torch, torchaudio, pyannote | Tidak ada                                |
| Cold start                | ~30 detik                   | Instan                                   |
| Akurasi                   | Tinggi (ML-based)           | Baik (rule-based, optimal untuk meeting) |
| Cocok untuk Railway/Cloud | ❌ Sulit                    | ✅ Ya                                    |

---

## 🚀 Setup Lokal

### Prasyarat

- Python **3.11+**
- Akun & API Key [Groq Console](https://console.groq.com) _(gratis)_
- Akun & Project [Supabase](https://supabase.com)

### 1. Clone & Install

```bash
git clone https://github.com/rakaalpiansyah/Meeting-AI-Backend.git
cd UAS-BE-AI

# Buat virtual environment
python -m venv venv
source venv/bin/activate      # Linux/Mac
venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Konfigurasi Environment

```bash
cp .env.example .env
```

Edit file `.env` dan isi variabel berikut:

| Variable                    | Wajib | Deskripsi                                                  |
| --------------------------- | ----- | ---------------------------------------------------------- |
| `API_KEYS`                  | ✅    | API keys untuk client (comma-separated)                    |
| `GEMINI_API_KEY`            | ✅    | API key Groq (untuk LLM analysis)                          |
| `GROQ_API_KEY`              | ✅    | API key Groq (untuk Whisper STT)                           |
| `SUPABASE_URL`              | ✅    | Project URL Supabase                                       |
| `SUPABASE_ANON_KEY`         | ✅    | Anon key Supabase                                          |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅    | Service role key (akses admin backend)                     |
| `FRONTEND_URL`              | ❌    | URL frontend untuk CORS (default: `http://localhost:5173`) |
| `ALLOWED_ORIGINS`           | ❌    | Origin tambahan, comma-separated                           |
| `HF_TOKEN`                  | ❌    | Hugging Face token — opsional, untuk upgrade ke pyannote   |

### 3. Jalankan Server

```bash
# Development (dengan auto-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Swagger UI tersedia di: **[http://localhost:8000/docs](http://localhost:8000/docs)**

---

## 📡 API Reference

### Authentication

| Method | Endpoint              | Auth | Deskripsi                          |
| ------ | --------------------- | ---- | ---------------------------------- |
| `POST` | `/api/v1/auth/signup` | —    | Registrasi user baru               |
| `POST` | `/api/v1/auth/login`  | —    | Login, return `access_token` (JWT) |

### Health

| Method | Endpoint  | Auth | Deskripsi                     |
| ------ | --------- | ---- | ----------------------------- |
| `GET`  | `/health` | —    | Status server & semua service |

### Meetings

| Method   | Endpoint                            | Auth        | Deskripsi                                             |
| -------- | ----------------------------------- | ----------- | ----------------------------------------------------- |
| `POST`   | `/api/v1/meetings/`                 | `X-API-Key` | Buat sesi rapat baru                                  |
| `POST`   | `/api/v1/meetings/{id}/finish`      | `X-API-Key` | Selesaikan rapat + analisis AI                        |
| `PATCH`  | `/api/v1/meetings/{id}`             | `X-API-Key` | Edit judul dan/atau transkrip (+ re-analyze opsional) |
| `GET`    | `/api/v1/meetings/user/{user_id}`   | `X-API-Key` | Daftar rapat milik user                               |
| `GET`    | `/api/v1/meetings/{id}`             | `X-API-Key` | Detail lengkap satu rapat                             |
| `DELETE` | `/api/v1/meetings/{id}?user_id=xxx` | `X-API-Key` | Hapus rapat                                           |

### WebSocket

```
ws://localhost:8000/api/v1/ws/transcribe/{meeting_id}?api_key=YOUR_API_KEY
```

**Pesan dari Frontend → Backend:**

| Type   | Payload            | Deskripsi                                       |
| ------ | ------------------ | ----------------------------------------------- |
| Binary | `bytes`            | Audio chunk (WebM/Opus)                         |
| Text   | `{"type": "ping"}` | Keepalive                                       |
| Text   | `{"type": "stop"}` | Akhiri rekaman, mulai transkripsi & diarization |

**Pesan dari Backend → Frontend:**

| Type             | Payload                             | Deskripsi                        |
| ---------------- | ----------------------------------- | -------------------------------- |
| `audio_received` | `{"buffer_kb": 123.4}`              | Konfirmasi audio diterima        |
| `processing`     | `{"message": "..."}`                | Status pemrosesan                |
| `transcript`     | `{"text": "...", "is_final": true}` | Hasil transkripsi                |
| `session_ended`  | Lihat di bawah                      | Sesi selesai + hasil diarization |
| `error`          | `{"message": "..."}`                | Pesan error                      |

**Payload `session_ended` (lengkap):**

```json
{
  "type": "session_ended",
  "full_transcript": "teks transkrip plain...",
  "diarized_transcript": "[Speaker 1]: teks...\n[Speaker 2]: teks...",
  "speakers_detected": 2,
  "total_chunks": 1
}
```

---

## 📦 Response Schemas

### `MeetingResultResponse`

```json
{
  "meeting_id": "uuid-rapat",
  "title": "Weekly Sync Tim Produk",
  "summary": "Ringkasan eksekutif dari AI...",
  "action_items": [
    {
      "task": "Buat mockup halaman dashboard",
      "assignee": "Raka",
      "deadline": "2026-04-20"
    }
  ],
  "recommendations": [
    {
      "title": "Prioritaskan fitur login",
      "detail": "Fitur login harus selesai minggu ini sebagai fondasi...",
      "priority": "high"
    }
  ],
  "full_transcript": "Teks transkripsi plain...",
  "diarized_transcript": "[Speaker 1]: Oke hari ini kita bahas...\n[Speaker 2]: Setuju, saya sudah siapkan...",
  "speakers_detected": 2,
  "created_at": "2026-04-17T08:00:00Z"
}
```

---

## 🔐 Autentikasi

Sistem menggunakan **dua lapis autentikasi**:

### Layer 1 — System Auth (API Key)

Semua endpoint REST (kecuali `/health` dan `/auth/*`) mengharuskan header `X-API-Key`:

```bash
curl -H "X-API-Key: YOUR_API_KEY" \
     https://your-server.com/api/v1/meetings/user/USER_ID
```

WebSocket menggunakan query param:

```
wss://your-server.com/api/v1/ws/transcribe/{meeting_id}?api_key=YOUR_API_KEY
```

| HTTP Status | Arti                      |
| ----------- | ------------------------- |
| `401`       | `X-API-Key` tidak dikirim |
| `403`       | `X-API-Key` tidak valid   |

### Layer 2 — User Auth (Supabase JWT)

```javascript
// Signup
await fetch("/api/v1/auth/signup", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email: "user@domain.com", password: "password123" }),
});

// Login
const { access_token, user_id } = await fetch("/api/v1/auth/login", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email: "user@domain.com", password: "password123" }),
}).then((r) => r.json());
```

---

## 💻 Contoh Integrasi Frontend

### Alur Lengkap (dengan Diarization)

```javascript
// 1. Buat meeting
const { meeting_id } = await fetch("/api/v1/meetings/", {
  method: "POST",
  headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
  body: JSON.stringify({ title: "Weekly Standup", user_id: userId }),
}).then((r) => r.json());

// 2. Buka WebSocket & stream audio
const ws = new WebSocket(
  `wss://your-server.com/api/v1/ws/transcribe/${meeting_id}?api_key=${API_KEY}`,
);

mediaRecorder.ondataavailable = (e) => {
  if (e.data.size > 0) ws.send(e.data); // Kirim binary audio
};

// 3. Stop & terima hasil
ws.send(JSON.stringify({ type: "stop" }));

ws.onmessage = (e) => {
  const msg = JSON.parse(e.data);
  if (msg.type === "session_ended") {
    console.log("Transkrip biasa:", msg.full_transcript);
    console.log("Berlabel speaker:", msg.diarized_transcript);
    // "[Speaker 1]: teks...\n[Speaker 2]: teks..."
    console.log("Jumlah speaker:", msg.speakers_detected);
  }
};

// 4. Analisis AI (kirim kedua transkrip)
const analysis = await fetch(`/api/v1/meetings/${meeting_id}/finish`, {
  method: "POST",
  headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
  body: JSON.stringify({
    meeting_id,
    full_transcript: plainTranscript,
    diarized_transcript: diarizedTranscript, // opsional, tingkatkan akurasi AI
  }),
}).then((r) => r.json());

console.log("Summary:", analysis.summary);
console.log("Action Items:", analysis.action_items);
console.log("Rekomendasi:", analysis.recommendations);
```

---

## 🗂️ Struktur Folder

```
Meeting-Ai-Backend/
├── app/
│   ├── main.py                      # Entry point FastAPI + CORS + lifespan
│   ├── core/
│   │   ├── config.py                # Settings & env variables (pydantic-settings)
│   │   └── auth.py                  # API Key dependency injection
│   ├── api/
│   │   └── endpoints/
│   │       ├── auth.py              # Supabase Signup & Login
│   │       ├── meetings.py          # REST CRUD rapat + finish + AI analysis
│   │       ├── websocket.py         # WebSocket streaming + transcription + diarization
│   │       └── health.py            # Health check endpoint
│   ├── schemas/
│   │   └── meeting.py               # Pydantic request/response models
│   └── services/
│       ├── whisper_service.py       # Groq Whisper API (verbose_json + timestamps)
│       ├── diarization_service.py   # 👥 Speaker diarization (pause-based clustering)
│       ├── ai_service.py            # LLM analysis (Groq Llama 3.3)
│       └── supabase_service.py      # Database CRUD operations
├── index.html                       # HTML tester interaktif (buka di browser)
├── supabase_schema.sql              # SQL schema + migration scripts
├── requirements.txt                 # Python dependencies
├── nixpacks.toml                    # Deploy config Railway
├── railway.json                     # Railway service settings
├── runtime.txt                      # Python version pin
├── .env.example                     # Template environment variables
└── README.md
```

---

## 🧪 Testing

### Menggunakan HTML Tester

Jalankan backend dan HTML tester secara lokal dengan flow berikut agar stabil (terutama untuk WebSocket, akses mic, dan CORS).

#### 1) Jalankan Backend API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Pastikan backend aktif di `http://localhost:8000`.

#### 2) Jalankan HTML Tester via Static Server (Recommended)

```bash
py -m http.server 5500
```

Lalu buka:

`http://localhost:5500/index.html`

> Catatan: Menjalankan via static server lebih direkomendasikan dibanding buka file langsung (`file://`) karena lebih konsisten untuk request API, WebSocket, dan permission browser.

#### 3) Konfigurasi di Halaman Tester

1. Set **Backend URL** ke `http://localhost:8000`
2. Masukkan **API Key** yang sesuai dengan `.env`
3. Tab **Health** → klik _Run Health Check_ untuk verifikasi koneksi
4. Tab **Record** → Buat meeting → Rekam audio → Lihat hasil diarization di tab "Berlabel Speaker"
5. Klik **Analisis AI** → lihat summary + action items + rekomendasi

#### 4) Opsi Cepat (Tanpa Static Server)

`index.html` tetap bisa dibuka langsung di browser, tetapi jika muncul kendala permission atau koneksi, gunakan metode static server pada langkah (2).

### Menggunakan Swagger UI

Buka **[http://localhost:8000/docs](http://localhost:8000/docs)** untuk interactive API documentation.

### Menggunakan cURL

```bash
# Health check
curl http://localhost:8000/health

# Buat meeting
curl -X POST http://localhost:8000/api/v1/meetings/ \
  -H "Content-Type: application/json" \
  -H "X-API-Key: vcols-key-12345" \
  -d '{"title": "Test Rapat", "user_id": "00000000-0000-0000-0000-000000000001"}'

# Finish meeting dengan diarization
curl -X POST http://localhost:8000/api/v1/meetings/{id}/finish \
  -H "Content-Type: application/json" \
  -H "X-API-Key: vcols-key-12345" \
  -d '{
    "meeting_id": "{id}",
    "full_transcript": "teks transkrip di sini",
    "diarized_transcript": "[Speaker 1]: teks...\n[Speaker 2]: teks..."
  }'
```

---

## 🚂 Deploy ke Railway

1. **Push** repository ke GitHub
2. **Connect** repo ke [Railway](https://railway.app)
3. Tambahkan **Environment Variables** di Railway dashboard:

| Variable                    | Keterangan                              |
| --------------------------- | --------------------------------------- |
| `API_KEYS`                  | API keys client (comma-separated)       |
| `GEMINI_API_KEY`            | Groq API key untuk LLM                  |
| `GROQ_API_KEY`              | Groq API key untuk Whisper STT          |
| `SUPABASE_URL`              | URL project Supabase                    |
| `SUPABASE_ANON_KEY`         | Anon key Supabase                       |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key Supabase               |
| `FRONTEND_URL`              | URL frontend production                 |
| `ALLOWED_ORIGINS`           | Tambahan CORS origins (comma-separated) |

4. Railway akan otomatis build & deploy menggunakan `nixpacks.toml` 🚀

---

## ⚠️ Troubleshooting

| Masalah                                   | Solusi                                                                           |
| ----------------------------------------- | -------------------------------------------------------------------------------- |
| `422 Unprocessable Entity` pada `/finish` | Pastikan `meeting_id` dan `full_transcript` tidak kosong                         |
| WebSocket error `4003`                    | API Key salah atau tidak dikirim sebagai query param                             |
| Groq API `401`                            | Cek `GROQ_API_KEY` di `.env`                                                     |
| Transkrip tidak ada speaker label         | Audio terlalu pendek (<5 detik) atau tidak ada jeda antar pembicara              |
| `Column not found` error di Supabase      | Jalankan migration SQL untuk kolom `diarized_transcript` dan `speakers_detected` |
| CORS error dari frontend                  | Tambahkan URL frontend ke `ALLOWED_ORIGINS` di `.env`                            |

---

## 📄 License

MIT License — Free to use for educational and commercial purposes.
