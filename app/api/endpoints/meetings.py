"""
Meeting Endpoints — REST API untuk operasi rapat.
WebSocket handles real-time audio.
REST API handles: buat rapat, finish + analisis, ambil history, hapus.
"""
from fastapi import APIRouter, HTTPException, status
from app.schemas.meeting import (
    MeetingCreateRequest,
    MeetingFinishRequest,
    MeetingResultResponse,
    MeetingListItem,
    ActionItem,
    Recommendation,
)
from app.services.ai_service import AIService
from app.services.supabase_service import SupabaseService
from datetime import datetime
import logging

router = APIRouter(prefix="/meetings", tags=["Meetings"])
logger = logging.getLogger(__name__)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_meeting(payload: MeetingCreateRequest):
    """
    Buat sesi rapat baru.
    Dipanggil FE saat user menekan tombol 'Mulai Rapat'.
    Returns meeting_id yang digunakan untuk WebSocket session.
    """
    supabase = SupabaseService()
    meeting = await supabase.create_meeting(
        title=payload.title,
        user_id=payload.user_id,
    )
    return {
        "meeting_id": meeting["id"],
        "title": meeting["title"],
        "status": meeting["status"],
        "message": "Rapat dibuat. Hubungkan WebSocket untuk mulai rekam.",
    }


@router.post("/{meeting_id}/finish", response_model=MeetingResultResponse)
async def finish_meeting(meeting_id: str, payload: MeetingFinishRequest):
    """
    Selesaikan rapat dan jalankan analisis AI.
    Dipanggil FE setelah WebSocket mengirim 'session_ended'.

    Alur:
    1. Terima transkrip lengkap dari FE
    2. Kirim ke AI untuk analisis
    3. Simpan hasil ke Supabase
    4. Return hasil ke FE
    """
    if not payload.full_transcript.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transkrip tidak boleh kosong.",
        )

    supabase = SupabaseService()
    meeting = await supabase.get_meeting_by_id(meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting {meeting_id} tidak ditemukan.",
        )

    # ── Analisis AI ─────────────────────────────────────────
    logger.info(f"Analyzing meeting {meeting_id} with AI...")
    ai = AIService()
    analysis = await ai.analyze_meeting(
        transcript=payload.full_transcript,
        meeting_title=meeting["title"],
    )

    # ── Simpan ke Supabase ──────────────────────────────────
    saved = await supabase.save_meeting_result(
        meeting_id=meeting_id,
        full_transcript=payload.full_transcript,
        summary=analysis["summary"],
        action_items=analysis["action_items"],
    )

    return MeetingResultResponse(
        meeting_id=meeting_id,
        title=meeting["title"],
        summary=analysis["summary"],
        action_items=analysis["action_items"],
        recommendations=analysis.get("recommendations", []),
        full_transcript=payload.full_transcript,
        created_at=datetime.fromisoformat(saved["created_at"]),
    )


@router.get("/user/{user_id}", response_model=list[MeetingListItem])
async def get_user_meetings(user_id: str):
    """
    Ambil semua rapat milik user — untuk halaman history.
    Diurutkan dari terbaru ke terlama.
    """
    supabase = SupabaseService()
    meetings = await supabase.get_meetings_by_user(user_id)
    return [
        MeetingListItem(
            id=m["id"],
            title=m["title"],
            summary=m.get("summary"),
            status=m.get("status"),
            created_at=datetime.fromisoformat(m["created_at"]),
            duration_seconds=m.get("duration_seconds"),
        )
        for m in meetings
    ]


@router.get("/{meeting_id}", response_model=MeetingResultResponse)
async def get_meeting_detail(meeting_id: str):
    """Ambil detail lengkap satu rapat — untuk halaman detail."""
    supabase = SupabaseService()
    meeting = await supabase.get_meeting_by_id(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting tidak ditemukan.")

    return MeetingResultResponse(
        meeting_id=meeting["id"],
        title=meeting["title"],
        summary=meeting.get("summary", ""),
        action_items=[ActionItem(**item) for item in meeting.get("action_items", [])],
        recommendations=[Recommendation(**r) for r in meeting.get("recommendations", [])],
        full_transcript=meeting.get("full_transcript", ""),
        created_at=datetime.fromisoformat(meeting["created_at"]),
    )


@router.delete("/{meeting_id}")
async def delete_meeting(meeting_id: str, user_id: str):
    """
    Hapus rapat.
    user_id dikirim sebagai query param — validasi kepemilikan di service.
    """
    supabase = SupabaseService()
    deleted = await supabase.delete_meeting(meeting_id, user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting tidak ditemukan atau Anda tidak punya akses.",
        )
    return {"message": "Meeting berhasil dihapus."}