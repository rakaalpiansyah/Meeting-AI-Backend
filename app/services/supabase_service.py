"""
Supabase Service — Layer database.
Semua operasi CRUD ke Supabase terpusat di sini.
"""
from supabase import create_client, Client, ClientOptions
from app.core.config import get_settings
from app.schemas.meeting import ActionItem
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class SupabaseService:

    def __init__(self, access_token: str | None = None):
        settings = get_settings()
        
        # 1. Siapkan identitas user (token) jika ada
        options = ClientOptions()
        if access_token:
            options.headers.update({"Authorization": f"Bearer {access_token}"})

        # 2. Gunakan ANON_KEY (bukan service_role_key) agar RLS aktif!
        self.client: Client = create_client(
            settings.supabase_url,
            settings.supabase_anon_key, 
            options=options
        )

    async def create_meeting(self, title: str, user_id: str) -> dict:
        data = {
            "title": title,
            "user_id": user_id,
            "status": "recording",
            "created_at": datetime.utcnow().isoformat(),
        }
        response = self.client.table("meetings").insert(data).execute()
        logger.info(f"Meeting created: {response.data[0]['id']}")
        return response.data[0]

    async def save_meeting_result(
        self,
        meeting_id: str,
        full_transcript: str,
        summary: str,
        action_items: list[ActionItem],
        recommendations: list[dict] = [],
        duration_seconds: int = 0,
        diarized_transcript: str | None = None,
        speakers_detected: int | None = None,
    ) -> dict:
        items_data = [item.model_dump() for item in action_items]

        update_data = {
            "full_transcript": full_transcript,
            "summary": summary,
            "action_items": items_data,
            "recommendations": recommendations,
            "status": "completed",
            "duration_seconds": duration_seconds,
            "finished_at": datetime.utcnow().isoformat(),
        }

        # Simpan hasil diarization jika tersedia
        if diarized_transcript is not None:
            update_data["diarized_transcript"] = diarized_transcript
        if speakers_detected is not None:
            update_data["speakers_detected"] = speakers_detected

        response = (
            self.client.table("meetings")
            .update(update_data)
            .eq("id", meeting_id)
            .execute()
        )
        logger.info(f"Meeting result saved: {meeting_id}")
        return response.data[0]

    async def get_meeting_by_id(self, meeting_id: str) -> dict | None:
        response = (
            self.client.table("meetings")
            .select("*")
            .eq("id", meeting_id)
            .single()
            .execute()
        )
        return response.data

    async def get_meetings_by_user(self, user_id: str) -> list[dict]:
        response = (
            self.client.table("meetings")
            .select("id, title, summary, created_at, duration_seconds, status")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return response.data

    async def get_my_meetings(
        self,
        limit: int = 20,
        offset: int = 0,
        status_filter: str | None = None,
    ) -> tuple[list[dict], int]:
        query = (
            self.client.table("meetings")
            .select(
                "id, title, summary, created_at, duration_seconds, status",
                count="exact",
            )
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
        )

        if status_filter:
            query = query.eq("status", status_filter)

        response = query.execute()
        total = response.count or 0
        return response.data, total

    async def delete_meeting(self, meeting_id: str, user_id: str) -> bool:
        response = (
            self.client.table("meetings")
            .delete()
            .eq("id", meeting_id)
            .eq("user_id", user_id)
            .execute()
        )
        return len(response.data) > 0

    async def update_meeting(
        self,
        meeting_id: str,
        update_fields: dict,
    ) -> dict | None:
        """
        Partial update data meeting.
        Hanya field yang ada di update_fields yang diubah.
        Selalu menyertakan updated_at timestamp.

        Args:
            meeting_id: UUID meeting yang akan diupdate
            update_fields: dict berisi field yang ingin diubah,
                           mis. {"title": "...", "full_transcript": "..."}

        Returns:
            Row meeting yang sudah diupdate, atau None jika tidak ditemukan.
        """
        if not update_fields:
            # Tidak ada yang perlu diupdate, return data saat ini
            return await self.get_meeting_by_id(meeting_id)

        update_fields["updated_at"] = datetime.utcnow().isoformat()

        response = (
            self.client.table("meetings")
            .update(update_fields)
            .eq("id", meeting_id)
            .execute()
        )

        if not response.data:
            return None

        logger.info(f"Meeting updated: {meeting_id} | fields: {list(update_fields.keys())}")
        return response.data[0]

    async def save_transcript_chunk(
        self, meeting_id: str, chunk_index: int, text: str
    ) -> None:
        data = {
            "meeting_id": meeting_id,
            "chunk_index": chunk_index,
            "text": text,
            "created_at": datetime.utcnow().isoformat(),
        }
        self.client.table("transcript_chunks").insert(data).execute()

    async def upload_audio(
        self,
        file_content: bytes,
        file_path: str,
        content_type: str = "audio/wav",
    ) -> dict:
        """
        Mengunggah konten file ke storage bucket audio-uploads.
        Path file disarankan menggunakan format: 'user_id/meeting_id.wav'
        """
        try:
            # Menggunakan client yang sudah terautentikasi dengan token user
            response = self.client.storage.from_("audio-uploads").upload(
                path=file_path,
                file=file_content,
                file_options={"content-type": content_type, "upsert": "true"}
            )
            return response
        except Exception as e:
            logger.error(f"Gagal mengunggah ke storage: {str(e)}")
            raise e