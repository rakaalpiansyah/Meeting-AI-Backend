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
    diarized_transcript: Optional[str] = None


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
    created_at: datetime


class MeetingListItem(BaseModel):
    id: str
    title: str
    summary: Optional[str] = None
    status: Optional[str] = None
    created_at: datetime
    duration_seconds: Optional[int] = None


class MeetingListResponse(BaseModel):
    items: List[MeetingListItem]
    total: int
    limit: int
    offset: int
    has_more: bool


class MeetingUpdateRequest(BaseModel):
    title: Optional[str] = None
    full_transcript: Optional[str] = None
    re_analyze: bool = False


class MeetingUpdateResponse(BaseModel):
    meeting_id: str
    title: str
    full_transcript: Optional[str] = None
    summary: Optional[str] = None
    action_items: List[ActionItem] = []
    recommendations: List[Recommendation] = []
    re_analyzed: bool = False
    message: str


class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None