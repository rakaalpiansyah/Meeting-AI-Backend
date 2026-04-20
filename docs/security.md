# Security & Row-Level Security (RLS) Documentation

Dokumen ini menjelaskan lapisan keamanan data pada arsitektur database Supabase untuk proyek **MeetMind**.

## Konsep Dasar
Kami menggunakan **Row-Level Security (RLS)** bawaan PostgreSQL via Supabase untuk memastikan isolasi data secara ketat (Multi-tenant architecture). Setiap baris data dalam sistem terikat pada pengguna tertentu melalui kolom `user_id`.

Meskipun *frontend* atau pihak eksternal berhasil mengakses API database secara langsung, mereka tidak akan bisa melihat atau memodifikasi data milik pengguna lain.

## Status RLS per Tabel
RLS saat ini **DIAKTIFKAN (ENABLED)** pada tabel-tabel berikut:
- `meetings`
- `transcripts`
- `summaries`
- `action_items`

## Aturan Akses (Policies)
Setiap tabel yang disebutkan di atas memiliki empat (4) *policy* dasar yang mengikat fungsi CRUD (Create, Read, Update, Delete) ke fungsi `auth.uid()` milik Supabase.

| Operasi | Tipe Policy | Definisi SQL / Logika Kondisi |
|---------|-------------|-------------------------------|
| **READ** | `SELECT` | `USING (auth.uid() = user_id)` |
| **CREATE** | `INSERT` | `WITH CHECK (auth.uid() = user_id)` |
| **UPDATE** | `UPDATE` | `USING (auth.uid() = user_id)` |
| **DELETE** | `DELETE` | `USING (auth.uid() = user_id)` |

**Penjelasan:**
- Operasi hanya diizinkan jika *User ID* dari JWT pengguna yang sedang *login* (`auth.uid()`) cocok (sama persis) dengan nilai yang ada di kolom `user_id` pada baris data tersebut.

## Bypass RLS (Backend Access)
Untuk kebutuhan operasional *backend* FastAPI (seperti menyimpan hasil transkripsi dari *Groq Whisper* atau hasil analisis *AI LLM*), *backend* menggunakan **Supabase Service Role Key** (`SUPABASE_SERVICE_ROLE_KEY`). 

Key ini beroperasi pada level admin (`postgres` role) yang secara default **mem-bypass seluruh aturan RLS**. Hal ini memastikan *pipeline* asinkron atau proses otomatis di *backend* tidak diblokir oleh sistem keamanan *client-side*.

## Cara Pengujian (Testing)
Validasi RLS dapat dilakukan dengan skenario berikut:
1. Buat **User A** dan **User B** via endpoint registrasi.
2. Masukkan data meeting menggunakan *access token* **User A**.
3. Coba lakukan *request* GET/UPDATE ke data tersebut menggunakan *access token* **User B**.
4. **Hasil yang Diharapkan:** *Request* User B akan mengembalikan *array* kosong (jika GET) atau gagal mengubah (jika UPDATE), memastikan tidak ada kebocoran antar pengguna (*data leak*).