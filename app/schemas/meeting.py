"""
Pydantic Schemas — kontrak data antara FE dan BE.
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ─── Request Schemas ──────────────────────────────────────────

class MeetingCreateRequest(BaseModel):
    title: str
    user_id: str

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Weekly Sync Tim Produk",
                "user_id": "uuid-user-di-sini",
            }
        }


class MeetingFinishRequest(BaseModel):
    meeting_id: str
    full_transcript: str
    diarized_transcript: Optional[str] = None  # Transkrip berlabel speaker (dari diarization)


# ─── Response Schemas ─────────────────────────────────────────

class TranscriptChunkResponse(BaseModel):
    chunk_index: int
    text: str
    is_final: bool = False


class ActionItem(BaseModel):
    task: str
    assignee: Optional[str] = None
    deadline: Optional[str] = None


class Recommendation(BaseModel):
    title: str
    detail: str
    priority: str = "medium"  # high / medium / low


class MeetingResultResponse(BaseModel):
    meeting_id: str
    title: str
    summary: str
    action_items: List[ActionItem]
    recommendations: List[Recommendation] = []
    full_transcript: str
    diarized_transcript: Optional[str] = None  # Transkrip dengan label speaker
    speakers_detected: Optional[int] = None    # Jumlah speaker yang terdeteksi
    created_at: datetime


class MeetingUpdateRequest(BaseModel):
    """
    Request schema untuk PATCH /meetings/{id} — edit rapat.
    Semua field opsional, hanya field yang dikirim yang diupdate (partial update).
    """
    title: Optional[str] = None             # Ganti judul rapat
    full_transcript: Optional[str] = None   # Koreksi transkrip manual
    re_analyze: bool = False                # True → jalankan ulang AI analisis setelah update

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Weekly Sync Tim Produk — Updated",
                "full_transcript": "Teks transkrip yang sudah dikoreksi manual...",
                "re_analyze": True,
            }
        }


class MeetingUpdateResponse(BaseModel):
    """Response schema untuk PATCH /meetings/{id}."""
    meeting_id: str
    title: str
    full_transcript: Optional[str] = None
    summary: Optional[str] = None
    action_items: List[ActionItem] = []
    recommendations: List[Recommendation] = []
    re_analyzed: bool = False
    message: str


class MeetingListItem(BaseModel):
    id: str
    title: str
    summary: Optional[str] = None
    status: Optional[str] = None
    created_at: datetime
    duration_seconds: Optional[int] = None


class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None