"""
Supabase Service — Layer database.
Semua operasi CRUD ke Supabase terpusat di sini.
"""
from supabase import create_client, Client
from app.core.config import get_settings
from app.schemas.meeting import ActionItem
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class SupabaseService:

    def __init__(self):
        settings = get_settings()
        self.client: Client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key,
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
        recommendations: list[dict] = [],  # ← tambah parameter ini
        duration_seconds: int = 0,
    ) -> dict:
        items_data = [item.model_dump() for item in action_items]

        update_data = {
            "full_transcript": full_transcript,
            "summary": summary,
            "action_items": items_data,
            "recommendations": recommendations,  # ← simpan ke DB
            "status": "completed",
            "duration_seconds": duration_seconds,
            "finished_at": datetime.utcnow().isoformat(),
        }

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

    async def delete_meeting(self, meeting_id: str, user_id: str) -> bool:
        response = (
            self.client.table("meetings")
            .delete()
            .eq("id", meeting_id)
            .eq("user_id", user_id)
            .execute()
        )
        return len(response.data) > 0

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