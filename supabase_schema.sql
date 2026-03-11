-- ============================================================
-- Supabase Database Schema — Meeting AI
-- Jalankan di Supabase SQL Editor
-- ============================================================

-- ─── Tabel Utama: meetings ───────────────────────────────────
CREATE TABLE IF NOT EXISTS meetings (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID NOT NULL,                     -- FK ke auth.users Supabase
    title             TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'recording'  -- recording | completed | failed
                      CHECK (status IN ('recording', 'completed', 'failed')),

    -- Hasil AI
    full_transcript   TEXT,
    summary           TEXT,
    action_items      JSONB DEFAULT '[]'::jsonb,         -- Array of {task, assignee, deadline}

    -- Metadata
    duration_seconds  INTEGER DEFAULT 0,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at       TIMESTAMPTZ
);

-- ─── Tabel Pendukung: transcript_chunks ──────────────────────
-- Menyimpan setiap chunk transkripsi secara real-time
-- Berguna untuk fault tolerance jika koneksi putus di tengah rapat
CREATE TABLE IF NOT EXISTS transcript_chunks (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id   UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    chunk_index  INTEGER NOT NULL,
    text         TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Indexes ─────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_meetings_user_id    ON meetings(user_id);
CREATE INDEX IF NOT EXISTS idx_meetings_created_at ON meetings(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chunks_meeting_id   ON transcript_chunks(meeting_id);

-- ─── Row Level Security (RLS) ────────────────────────────────
-- Aktifkan RLS agar user hanya bisa akses data miliknya sendiri
ALTER TABLE meetings          ENABLE ROW LEVEL SECURITY;
ALTER TABLE transcript_chunks ENABLE ROW LEVEL SECURITY;

-- Policy: User hanya bisa SELECT, INSERT, UPDATE, DELETE data miliknya
CREATE POLICY "Users can manage own meetings"
    ON meetings FOR ALL
    USING (auth.uid() = user_id);

CREATE POLICY "Users can manage own transcript chunks"
    ON transcript_chunks FOR ALL
    USING (
        meeting_id IN (
            SELECT id FROM meetings WHERE user_id = auth.uid()
        )
    );

-- ─── Catatan Struktur JSON action_items ───────────────────────
-- Contoh isi kolom action_items (JSONB):
-- [
--   {
--     "task": "Buat mockup halaman login",
--     "assignee": "Budi",
--     "deadline": "Jumat, 5 Juli 2024"
--   },
--   {
--     "task": "Review proposal budget Q3",
--     "assignee": null,
--     "deadline": null
--   }
-- ]
