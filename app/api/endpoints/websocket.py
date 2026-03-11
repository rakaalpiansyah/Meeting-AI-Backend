"""
WebSocket Endpoint — Kumpulkan SEMUA audio, proses saat stop.
WebM stream harus utuh dari awal — tidak bisa diproses per chunk.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.whisper_service import WhisperService
from app.services.supabase_service import SupabaseService
import logging
import json

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/ws/transcribe/{meeting_id}")
async def websocket_transcribe(websocket: WebSocket, meeting_id: str):
    await websocket.accept()
    logger.info(f"WebSocket connected: meeting_id={meeting_id}")

    supabase = SupabaseService()
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
                                transcript_text = await WhisperService.transcribe_audio_chunk(
                                    bytes(audio_buffer), language="id"
                                )

                                if transcript_text and transcript_text.strip():
                                    # Simpan ke DB
                                    await supabase.save_transcript_chunk(
                                        meeting_id=meeting_id,
                                        chunk_index=0,
                                        text=transcript_text,
                                    )

                                    await websocket.send_json({
                                        "type": "transcript",
                                        "chunk_index": 0,
                                        "text": transcript_text,
                                        "is_final": True,
                                    })

                                    await websocket.send_json({
                                        "type": "session_ended",
                                        "full_transcript": transcript_text,
                                        "total_chunks": 1,
                                    })
                                else:
                                    await websocket.send_json({
                                        "type": "session_ended",
                                        "full_transcript": "",
                                        "total_chunks": 0,
                                    })

                            except Exception as e:
                                logger.error(f"Transcription error: {e}")
                                await websocket.send_json({
                                    "type": "error",
                                    "message": f"Transkripsi gagal: {str(e)}",
                                })
                                await websocket.send_json({
                                    "type": "session_ended",
                                    "full_transcript": "",
                                    "total_chunks": 0,
                                })
                        else:
                            await websocket.send_json({
                                "type": "session_ended",
                                "full_transcript": "",
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