"""
Meeting Endpoints — REST API untuk operasi rapat.
WebSocket handles real-time audio.
REST API handles: buat rapat, finish + analisis, edit, ambil history, hapus.
"""
from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List
from app.schemas.meeting import (
    MeetingCreateRequest,
    MeetingFinishRequest,
    MeetingUpdateRequest,
    MeetingUpdateResponse,
    MeetingResultResponse,
    MeetingListItem,
    MeetingListResponse,
    MeetingUpdateRequest,
    MeetingUpdateResponse,
    ActionItem,
    Recommendation,
)
from app.services.ai_service import AIService
from app.services.supabase_service import SupabaseService
from app.core.auth import verify_api_key
from datetime import datetime
import logging

router = APIRouter(prefix="/meetings", tags=["Meetings"], dependencies=[Depends(verify_api_key)])
logger = logging.getLogger(__name__)

# Skema untuk mengekstrak Bearer Token dari Header
token_auth_scheme = HTTPBearer()

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_meeting(
    payload: MeetingCreateRequest,
    token: HTTPAuthorizationCredentials = Depends(token_auth_scheme)
):
    """
    Buat sesi rapat baru.
    Dipanggil FE saat user menekan tombol 'Mulai Rapat'.
    Returns meeting_id yang digunakan untuk WebSocket session.
    """
    supabase = SupabaseService(access_token=token.credentials)
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
async def finish_meeting(
    meeting_id: str,
    payload: MeetingFinishRequest,
    token: HTTPAuthorizationCredentials = Depends(token_auth_scheme)
):
    """
    Selesaikan rapat dan jalankan analisis AI.
    Dipanggil FE setelah WebSocket mengirim 'session_ended'.

    Alur:
    1. Terima transkrip lengkap dari FE (raw + diarized jika tersedia)
    2. Gunakan diarized_transcript untuk AI (konteks speaker lebih baik)
    3. Kirim ke AI untuk analisis
    4. Simpan hasil ke Supabase
    5. Return hasil ke FE
    """
    if not payload.full_transcript.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transkrip tidak boleh kosong.",
        )

    supabase = SupabaseService(access_token=token.credentials)
    meeting = await supabase.get_meeting_by_id(meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting {meeting_id} tidak ditemukan.",
        )

    # ── Tentukan transkrip untuk AI ───────────────────────────
    # Gunakan diarized_transcript jika FE mengirimnya (lebih baik untuk AI)
    # Fallback ke full_transcript jika tidak ada
    transcript_for_ai = (
        payload.diarized_transcript
        if payload.diarized_transcript and payload.diarized_transcript.strip()
        else payload.full_transcript
    )

    has_diarization = bool(
        payload.diarized_transcript and payload.diarized_transcript.strip()
    )
    if has_diarization:
        logger.info(f"Meeting {meeting_id}: menggunakan diarized_transcript untuk AI.")
    else:
        logger.info(f"Meeting {meeting_id}: diarized_transcript tidak tersedia, pakai plain transcript.")

    # ── Analisis AI ───────────────────────────────────────────
    logger.info(f"Analyzing meeting {meeting_id} with AI...")
    ai = AIService()
    analysis = await ai.analyze_meeting(
        transcript=transcript_for_ai,
        meeting_title=meeting["title"],
    )

    # ── Simpan ke Supabase ────────────────────────────────────
    saved = await supabase.save_meeting_result(
        meeting_id=meeting_id,
        full_transcript=payload.full_transcript,
        summary=analysis["summary"],
        action_items=analysis["action_items"],
        recommendations=analysis.get("recommendations", []),
        diarized_transcript=payload.diarized_transcript,
    )

    return MeetingResultResponse(
        meeting_id=meeting_id,
        title=meeting["title"],
        summary=analysis["summary"],
        action_items=analysis["action_items"],
        recommendations=analysis.get("recommendations", []),
        full_transcript=payload.full_transcript,
        diarized_transcript=payload.diarized_transcript,
        created_at=datetime.fromisoformat(saved["created_at"]),
    )


@router.get("/", response_model=MeetingListResponse)
async def get_my_meetings(
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    token: HTTPAuthorizationCredentials = Depends(token_auth_scheme),
):
    """
    Ambil daftar meeting milik user yang sedang login.
    Mendukung pagination (limit/offset) dan filter status.
    """
    allowed_status = {"recording", "completed", "failed"}
    if status_filter and status_filter not in allowed_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filter status tidak valid. Gunakan: recording | completed | failed.",
        )

    supabase = SupabaseService(access_token=token.credentials)
    meetings, total = await supabase.get_my_meetings(
        limit=limit,
        offset=offset,
        status_filter=status_filter,
    )

    items = [
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

    return MeetingListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + len(items)) < total,
    )


@router.get("/user/{user_id}", response_model=List[MeetingListItem])
async def get_user_meetings(
    user_id: str,
    token: HTTPAuthorizationCredentials = Depends(token_auth_scheme)
):
    """
    Ambil semua rapat milik user — untuk halaman history.
    Diurutkan dari terbaru ke terlama.
    """
    supabase = SupabaseService(access_token=token.credentials)
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
async def get_meeting_detail(
    meeting_id: str,
    token: HTTPAuthorizationCredentials = Depends(token_auth_scheme)
):
    """Ambil detail lengkap satu rapat — untuk halaman detail."""
    supabase = SupabaseService(access_token=token.credentials)
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


@router.patch("/{meeting_id}", response_model=MeetingUpdateResponse)
async def update_meeting(
    meeting_id: str,
    payload: MeetingUpdateRequest,
    token: HTTPAuthorizationCredentials = Depends(token_auth_scheme)
):
    """
    Edit data rapat — partial update (judul dan/atau transkrip).

    Alur:
    1. Validasi meeting ada di DB
    2. Build update_fields hanya dari field yang dikirim (tidak None)
    3. Simpan perubahan ke Supabase
    4. Jika re_analyze=True DAN ada transkrip (baru atau existing), jalankan ulang AI
    5. Return data terbaru

    Field yang bisa diedit:
    - title: ganti judul rapat
    - full_transcript: koreksi hasil transkripsi secara manual
    - re_analyze: set True untuk re-generate summary + action items + rekomendasi
    """
    supabase = SupabaseService(access_token=token.credentials)
    meeting = await supabase.get_meeting_by_id(meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meeting {meeting_id} tidak ditemukan.",
        )

    # ── Build partial update dict ────────────────────────────────
    update_fields: dict = {}
    if payload.title is not None:
        if not payload.title.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Judul rapat tidak boleh kosong.",
            )
        update_fields["title"] = payload.title.strip()

    if payload.full_transcript is not None:
        if not payload.full_transcript.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transkrip tidak boleh kosong.",
            )
        update_fields["full_transcript"] = payload.full_transcript.strip()

    # ── Simpan perubahan ke DB ───────────────────────────────────
    updated = await supabase.update_meeting(meeting_id, update_fields)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gagal mengupdate meeting — tidak ditemukan.",
        )

    re_analyzed = False
    analysis: dict = {}

    # ── Re-analyze AI jika diminta ───────────────────────────────
    if payload.re_analyze:
        # Gunakan transkrip baru jika ada, fallback ke yang sudah tersimpan
        transcript_for_ai = (
            update_fields.get("full_transcript")
            or meeting.get("full_transcript", "")
        )
        meeting_title = update_fields.get("title") or meeting.get("title", "")

        if transcript_for_ai.strip():
            logger.info(f"Re-analyzing meeting {meeting_id} after edit...")
            ai = AIService()
            analysis = await ai.analyze_meeting(
                transcript=transcript_for_ai,
                meeting_title=meeting_title,
            )
            # Simpan hasil AI yang baru ke DB
            ai_fields = {
                "summary": analysis["summary"],
                "action_items": [item.model_dump() for item in analysis["action_items"]],
                "recommendations": analysis.get("recommendations", []),
            }
            await supabase.update_meeting(meeting_id, ai_fields)
            re_analyzed = True
            logger.info(f"Re-analysis done for meeting {meeting_id} ✓")
        else:
            logger.warning(f"re_analyze=True tapi tidak ada transkrip untuk meeting {meeting_id}.")

    # ── Ambil data final setelah semua update ────────────────────
    final = await supabase.get_meeting_by_id(meeting_id)

    return MeetingUpdateResponse(
        meeting_id=meeting_id,
        title=final.get("title", ""),
        full_transcript=final.get("full_transcript"),
        summary=final.get("summary"),
        action_items=[
            ActionItem(**item) for item in final.get("action_items") or []
        ],
        recommendations=[
            Recommendation(**r) for r in final.get("recommendations") or []
            if isinstance(r, dict)
        ],
        re_analyzed=re_analyzed,
        message=(
            f"Meeting diperbarui{'+ AI re-analyzed' if re_analyzed else ''}. "
            f"Field diubah: {', '.join(update_fields.keys()) or 'tidak ada'}."
        ),
    )


@router.delete("/{meeting_id}")
async def delete_meeting(
    meeting_id: str, 
    user_id: str,
    token: HTTPAuthorizationCredentials = Depends(token_auth_scheme)
):
    """
    Hapus rapat.
    user_id dikirim sebagai query param — validasi kepemilikan di service.
    """
    supabase = SupabaseService(access_token=token.credentials)
    deleted = await supabase.delete_meeting(meeting_id, user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting tidak ditemukan atau Anda tidak punya akses.",
        )
    return {"message": "Meeting berhasil dihapus."}


@router.post("/{meeting_id}/upload")
async def upload_meeting_audio(
    meeting_id: str,
    file: UploadFile = File(...),
    token: HTTPAuthorizationCredentials = Depends(token_auth_scheme)
):
    """
    Endpoint untuk mengunggah file rekaman audio.
    Lokasi penyimpanan: audio-uploads/{user_id}/{meeting_id}.wav
    """
    supabase = SupabaseService(access_token=token.credentials)
    
    # Validasi keberadaan meeting dan ambil user_id
    meeting = await supabase.get_meeting_by_id(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting tidak ditemukan atau akses ditolak.")
    
    user_id = meeting["user_id"]
    file_content = await file.read()
    if not file_content:
        raise HTTPException(status_code=400, detail="File audio kosong.")
    
    # Tentukan path penyimpanan
    file_ext = file.filename.split(".")[-1] if "." in file.filename else "wav"
    storage_path = f"{user_id}/{meeting_id}.{file_ext}"
    
    try:
        await supabase.upload_audio(
            file_content,
            storage_path,
            content_type=file.content_type or "application/octet-stream",
        )
    except Exception as e:
        logger.exception(f"Upload ke storage gagal: {str(e)}")
        raise HTTPException(status_code=500, detail="Gagal upload ke storage.")

    # Simpan path audio ke record meeting; jika gagal, upload tetap dianggap berhasil.
    try:
        await supabase.update_meeting(meeting_id, {"audio_path": storage_path})
        return {
            "status": "success",
            "storage_path": storage_path,
            "message": "Rekaman berhasil diunggah ke storage."
        }
    except Exception as e:
        logger.exception(f"Upload sukses tapi update audio_path gagal: {str(e)}")
        return {
            "status": "partial_success",
            "storage_path": storage_path,
            "message": "Audio berhasil diunggah, tapi metadata audio_path di database gagal diperbarui."
        }