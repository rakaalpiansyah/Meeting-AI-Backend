"""
WebSocket Endpoint — Kumpulkan SEMUA audio, proses saat stop.
WebM stream harus utuh dari awal — tidak bisa diproses per chunk.

Alur yang diperbarui (dengan Speaker Diarization):
  1. Terima audio stream dari FE via WebSocket
  2. Saat stop: kirim audio ke Groq Whisper (verbose_json) → dapat text + segments
  3. Jalankan DiarizationService → assign speaker label ke setiap segment
  4. Format transkrip berlabel: "[Speaker 1]: teks... [Speaker 2]: teks..."
  5. Return ke FE: transcript biasa DAN diarized_transcript
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.services.whisper_service import WhisperService
from app.services.diarization_service import DiarizationService
from app.services.supabase_service import SupabaseService
from app.core.config import get_settings
import logging
import json

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/ws/transcribe/{meeting_id}")
async def websocket_transcribe(
    websocket: WebSocket,
    meeting_id: str,
    api_key: str = Query(..., alias="api_key"),
):
    # ── Verifikasi API Key ──
    settings = get_settings()
    valid_keys = settings.get_api_keys()
    if api_key not in valid_keys:
        await websocket.close(code=4003, reason="API key tidak valid.")
        return

    await websocket.accept()
    logger.info(f"WebSocket connected: meeting_id={meeting_id}")

    supabase = SupabaseService(use_service_role=True)
    audio_buffer = bytearray()  # Kumpulkan SEMUA audio — jangan pernah di-clear sampai stop

    try:
        while True:
            message = await websocket.receive()

            # ── Terima audio chunk ────────────────────────────
            if "bytes" in message and message["bytes"]:
                audio_bytes = message["bytes"]
                audio_buffer.extend(audio_bytes)
                logger.debug(f"Buffer total: {len(audio_buffer)/1024:.1f} KB")

                # Kirim notifikasi ke FE bahwa audio diterima
                await websocket.send_json({
                    "type": "audio_received",
                    "buffer_kb": round(len(audio_buffer) / 1024, 1),
                })

            # ── Kontrol sinyal ────────────────────────────────
            elif "text" in message and message["text"]:
                try:
                    control = json.loads(message["text"])
                    msg_type = control.get("type")

                    if msg_type == "ping":
                        await websocket.send_json({"type": "pong"})

                    elif msg_type == "stop":
                        # Proses SEMUA audio sekaligus saat stop
                        if len(audio_buffer) > 10000:
                            logger.info(f"Processing full audio: {len(audio_buffer)/1024:.1f} KB")

                            await websocket.send_json({
                                "type": "processing",
                                "message": "Memproses audio dengan Whisper...",
                            })

                            try:
                                # ── Step 1: Transkripsi dengan timestamps ──────────
                                whisper_result = await WhisperService.transcribe_with_timestamps(
                                    bytes(audio_buffer), language="id"
                                )
                                transcript_text = whisper_result.get("text", "")
                                segments = whisper_result.get("segments", [])

                                if transcript_text and transcript_text.strip():
                                    # ── Step 2: Speaker Diarization ───────────────
                                    await websocket.send_json({
                                        "type": "processing",
                                        "message": "Mendeteksi speaker...",
                                    })

                                    diarized_segments = DiarizationService.diarize(segments)
                                    diarized_transcript = DiarizationService.format_labeled_transcript(
                                        diarized_segments
                                    )
                                    speakers_detected = DiarizationService.count_speakers(
                                        diarized_segments
                                    )

                                    logger.info(
                                        f"Diarization: {speakers_detected} speaker terdeteksi."
                                    )

                                    # ── Step 3: Simpan transkrip ke DB ────────────
                                    try:
                                        await supabase.save_transcript_chunk(
                                            meeting_id=meeting_id,
                                            chunk_index=0,
                                            text=transcript_text,
                                        )
                                    except Exception as db_err:
                                        logger.warning(f"Gagal menyimpan chunk ke DB (mungkin meeting sudah dihapus): {db_err}")

                                    # ── Step 4: Kirim hasil ke FE ─────────────────
                                    await websocket.send_json({
                                        "type": "transcript",
                                        "chunk_index": 0,
                                        "text": transcript_text,
                                        "is_final": True,
                                    })

                                    await websocket.send_json({
                                        "type": "session_ended",
                                        "full_transcript": transcript_text,
                                        "diarized_transcript": diarized_transcript,
                                        "speakers_detected": speakers_detected,
                                        "total_chunks": 1,
                                    })
                                else:
                                    empty_msg = "Tidak ada suara yang terdeteksi selama rekaman."
                                    await websocket.send_json({
                                        "type": "session_ended",
                                        "full_transcript": empty_msg,
                                        "diarized_transcript": f"[Sistem]: {empty_msg}",
                                        "speakers_detected": 0,
                                        "total_chunks": 0,
                                    })

                            except Exception as e:
                                logger.error(f"Transcription/diarization error: {e}")
                                await websocket.send_json({
                                    "type": "error",
                                    "message": f"Pemrosesan audio gagal: {str(e)}",
                                })
                                await websocket.send_json({
                                    "type": "session_ended",
                                    "full_transcript": "Gagal memproses audio, tidak ada teks yang dihasilkan.",
                                    "diarized_transcript": "[Sistem]: Gagal memproses audio.",
                                    "speakers_detected": 0,
                                    "total_chunks": 0,
                                })
                        else:
                            empty_msg = "Tidak ada suara yang terdeteksi selama rekaman."
                            await websocket.send_json({
                                "type": "session_ended",
                                "full_transcript": empty_msg,
                                "diarized_transcript": f"[Sistem]: {empty_msg}",
                                "speakers_detected": 0,
                                "total_chunks": 0,
                            })
                        break

                except json.JSONDecodeError:
                    pass

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: meeting_id={meeting_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass