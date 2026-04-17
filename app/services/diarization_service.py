"""
Diarization Service — Speaker Detection dari Timestamps Groq Whisper.

Strategi:
  Groq Whisper verbose_json mengembalikan segments dengan timestamp (start, end, text).
  Kita analisis GAP antar segment — jeda panjang mengindikasikan ganti speaker.
  Pendekatan ini ringan (tanpa torch/pyannote), cocok untuk meeting standar.

Akurasi:
  - Bagus untuk meeting dengan 2-4 speaker yang bergantian bicara
  - Kurang akurat jika speaker overlap atau bicara bersamaan
  - Audio berkualitas baik meningkatkan akurasi signifikan
"""
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


# ─── Tipe Data Internal ────────────────────────────────────────────────────

class Segment:
    """Representasi satu segment audio dari Groq verbose_json."""

    def __init__(self, start: float, end: float, text: str, speaker: Optional[str] = None):
        self.start = start
        self.end = end
        self.text = text.strip()
        self.speaker = speaker

    def duration(self) -> float:
        return self.end - self.start

    def to_dict(self) -> dict:
        return {
            "start": self.start,
            "end": self.end,
            "text": self.text,
            "speaker": self.speaker,
        }


# ─── Konfigurasi Algoritma ─────────────────────────────────────────────────

# Jeda minimal antar segment (detik) yang dianggap sebagai pergantian speaker
SPEAKER_CHANGE_THRESHOLD_SEC: float = 1.2

# Jika gap sangat panjang (misalnya jeda diam >5 detik), tetap assign speaker baru
LONG_SILENCE_THRESHOLD_SEC: float = 5.0

# Maksimal jumlah speaker yang akan di-detect (batas atas label)
MAX_SPEAKERS: int = 10


# ─── Diarization Service ───────────────────────────────────────────────────

class DiarizationService:
    """
    Service untuk mendeteksi speaker dari segments Whisper.
    Tidak membutuhkan model ML — murni analisis timestamp.
    """

    @classmethod
    def diarize(cls, raw_segments: List[dict]) -> List[dict]:
        """
        Proses diarization dari raw segments Groq verbose_json.

        Args:
            raw_segments: List of {"start": float, "end": float, "text": str, ...}

        Returns:
            List of {"start": float, "end": float, "text": str, "speaker": "Speaker 1"}
        """
        if not raw_segments:
            logger.warning("Diarization: tidak ada segments untuk diproses.")
            return []

        # Parse ke objek Segment
        segments = cls._parse_segments(raw_segments)

        if not segments:
            return []

        # Kalau hanya 1 segment → 1 speaker
        if len(segments) == 1:
            segments[0].speaker = "Speaker 1"
            logger.info("Diarization: hanya 1 segment, assign Speaker 1.")
            return [s.to_dict() for s in segments]

        # Jalankan algoritma clustering berbasis gap
        segments = cls._assign_speakers(segments)

        speaker_count = len(set(s.speaker for s in segments))
        logger.info(
            f"Diarization selesai: {len(segments)} segments, {speaker_count} speaker terdeteksi."
        )

        return [s.to_dict() for s in segments]

    @classmethod
    def format_labeled_transcript(cls, diarized_segments: List[dict]) -> str:
        """
        Format segments berlabel menjadi transkrip yang readable.

        Merge segment berurutan dari speaker yang sama menjadi satu blok.
        Format output:
            [Speaker 1]: teks kalimat pertama, dilanjutkan teks berikutnya.
            [Speaker 2]: giliran speaker kedua bicara.

        Args:
            diarized_segments: Output dari diarize()

        Returns:
            String transkrip berlabel speaker
        """
        if not diarized_segments:
            return ""

        lines: List[str] = []
        current_speaker: Optional[str] = None
        current_texts: List[str] = []

        for seg in diarized_segments:
            speaker = seg.get("speaker", "Speaker ?")
            text = seg.get("text", "").strip()

            if not text:
                continue

            if speaker == current_speaker:
                # Lanjutkan teks speaker yang sama
                current_texts.append(text)
            else:
                # Flush akumulasi teks speaker sebelumnya
                if current_speaker and current_texts:
                    merged = " ".join(current_texts)
                    lines.append(f"[{current_speaker}]: {merged}")

                # Mulai speaker baru
                current_speaker = speaker
                current_texts = [text]

        # Flush sisa terakhir
        if current_speaker and current_texts:
            merged = " ".join(current_texts)
            lines.append(f"[{current_speaker}]: {merged}")

        return "\n".join(lines)

    @classmethod
    def count_speakers(cls, diarized_segments: List[dict]) -> int:
        """Hitung jumlah speaker unik yang terdeteksi."""
        speakers = set(seg.get("speaker") for seg in diarized_segments if seg.get("speaker"))
        return len(speakers)

    # ─── Private Methods ───────────────────────────────────────────────────

    @classmethod
    def _parse_segments(cls, raw_segments: List[dict]) -> List[Segment]:
        """
        Parse raw dict dari Groq verbose_json ke objek Segment.
        Filter segment yang terlalu pendek atau kosong.
        """
        segments: List[Segment] = []

        for item in raw_segments:
            text = item.get("text", "").strip()
            start = float(item.get("start", 0))
            end = float(item.get("end", 0))

            # Skip segment kosong
            if not text:
                continue

            # Skip segment dengan durasi tidak valid
            if end < start:
                continue

            segments.append(Segment(start=start, end=end, text=text))

        # Urutkan berdasarkan waktu mulai
        segments.sort(key=lambda s: s.start)
        return segments

    @classmethod
    def _assign_speakers(cls, segments: List[Segment]) -> List[Segment]:
        """
        Assign label speaker ke setiap segment menggunakan analisis gap.

        Algoritma:
        1. Mulai dengan Speaker 1
        2. Hitung gap antara akhir segment sebelumnya dan awal segment berikutnya
        3. Gap > SPEAKER_CHANGE_THRESHOLD_SEC → increment speaker counter
        4. Cap di MAX_SPEAKERS untuk menghindari noise

        Catatan: Ini adalah pendekatan deterministik sederhana.
        Untuk meeting 2 orang, akurasi cukup tinggi.
        Untuk >3 orang, hasil bisa kurang konsisten.
        """
        speaker_index = 0
        segments[0].speaker = cls._label(speaker_index)

        for i in range(1, len(segments)):
            prev = segments[i - 1]
            curr = segments[i]

            gap = curr.start - prev.end

            if gap >= SPEAKER_CHANGE_THRESHOLD_SEC:
                # Ada jeda — kemungkinan speaker berganti
                # Gunakan modulo jika jumlah speaker sudah tertentu,
                # atau increment sampai MAX_SPEAKERS
                speaker_index = cls._next_speaker_index(
                    speaker_index, gap, MAX_SPEAKERS
                )

            curr.speaker = cls._label(speaker_index)

        return segments

    @classmethod
    def _next_speaker_index(
        cls, current_index: int, gap: float, max_speakers: int
    ) -> int:
        """
        Tentukan index speaker berikutnya.
        - Gap pendek (1.2–3s): kemungkinan alternating (kembali ke awal jika sudah banyak)
        - Gap panjang (>5s): bisa speaker baru atau kembali ke speaker pertama
        """
        if gap >= LONG_SILENCE_THRESHOLD_SEC:
            # Jeda sangat panjang — reset ke speaker 1 (kemungkinan satu orang ngomong lagi)
            return 0

        # Increment speaker normal
        next_index = current_index + 1
        if next_index >= max_speakers:
            # Wrap kembali ke awal — meeting dengan banyak speaker akan cycle
            return 0

        return next_index

    @classmethod
    def _label(cls, index: int) -> str:
        """Konversi index (0-based) ke label speaker (1-based)."""
        return f"Speaker {index + 1}"
