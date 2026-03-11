"""
AI Analysis Service.
Menggunakan Groq sebagai LLM provider (gratis, cepat, tanpa kartu kredit).
Daftar API key di: https://console.groq.com/keys
"""
from openai import OpenAI
import json
import logging
import re
from app.core.config import get_settings
from app.schemas.meeting import ActionItem

logger = logging.getLogger(__name__)


class AIService:

    def __init__(self):
        settings = get_settings()
        self.client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=settings.gemini_api_key,
        )
        self.model_name = "llama-3.3-70b-versatile"

    async def analyze_meeting(self, transcript: str, meeting_title: str) -> dict:
        prompt = self._build_prompt(transcript, meeting_title)
        try:
            logger.info(f"Sending transcript to AI ({len(transcript)} chars)...")
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=3000,
            )
            raw_text = response.choices[0].message.content
            logger.debug(f"AI raw response: {raw_text[:200]}...")
            result = self._parse_response(raw_text)
            logger.info("AI analysis completed ✓")
            return result
        except Exception as e:
            logger.error(f"AI API error: {e}")
            return {
                "summary": f"[AI tidak tersedia: {str(e)[:150]}] Transkrip berhasil disimpan.",
                "action_items": [],
                "recommendations": [],
            }

    def _detect_language(self, transcript: str) -> str:
        """
        Deteksi bahasa transkrip secara sederhana.
        Cek kata-kata umum bahasa Indonesia.
        """
        id_words = ["yang", "dan", "ini", "itu", "dengan", "untuk", "tidak",
                    "ada", "saya", "kami", "kita", "mereka", "akan", "sudah",
                    "bisa", "juga", "tapi", "kalau", "karena", "dari", "ke",
                    "di", "ya", "nah", "nih", "gitu", "dong", "sih"]
        words = transcript.lower().split()
        id_count = sum(1 for w in words if w in id_words)
        ratio = id_count / max(len(words), 1)
        return "Indonesian" if ratio > 0.05 else "English"

    def _build_prompt(self, transcript: str, meeting_title: str) -> str:
        lang = self._detect_language(transcript)
        lang_instruction = (
            "BAHASA INDONESIA. Seluruh output WAJIB dalam Bahasa Indonesia."
            if lang == "Indonesian"
            else "English. All output MUST be in English."
        )

        return f"""You are a senior business consultant and expert meeting analyst with 20+ years of experience.

CRITICAL LANGUAGE RULE: The transcript is in {lang}. You MUST write ALL output — summary, action items, recommendations, every single word — in {lang_instruction}. Do NOT use any other language. This is mandatory.

Meeting Title: "{meeting_title}"

YOUR TASKS:

1. EXECUTIVE SUMMARY: Tulis ringkasan eksekutif yang tajam dan profesional dalam 4-6 kalimat. Bahas: topik utama, keputusan penting, hasil rapat, dan isu yang belum selesai.

2. ACTION ITEMS: Ekstrak semua tugas konkret, komitmen, atau tindak lanjut yang disebutkan. Spesifik.

3. STRATEGIC RECOMMENDATIONS: Berikan 3-5 rekomendasi strategis berdasarkan diskusi. Harus insightful, praktis, dan melampaui apa yang eksplisit dibahas — identifikasi gap, risiko, peluang, atau perbaikan yang mungkin terlewat peserta.

OUTPUT FORMAT — balas HANYA dengan JSON valid ini, tanpa teks lain, tanpa markdown, tanpa backtick:
{{
  "summary": "ringkasan eksekutif di sini...",
  "action_items": [
    {{
      "task": "deskripsi tugas spesifik",
      "assignee": "nama orang atau null",
      "deadline": "tanggal/waktu atau null"
    }}
  ],
  "recommendations": [
    {{
      "title": "Judul rekomendasi singkat",
      "detail": "Penjelasan detail rekomendasi, mengapa penting, dan cara implementasinya.",
      "priority": "high/medium/low"
    }}
  ]
}}

TRANSKRIP RAPAT:
---
{transcript}
---

INGAT: Semua teks dalam JSON harus dalam {lang}. Balas HANYA dengan JSON."""

    def _parse_response(self, raw_text: str) -> dict:
        clean = raw_text.strip()
        clean = re.sub(r"```json\s*", "", clean)
        clean = re.sub(r"```\s*", "", clean)
        clean = clean.strip()

        try:
            data = json.loads(clean)
        except json.JSONDecodeError:
            json_match = re.search(r"\{.*\}", clean, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = {"summary": clean, "action_items": [], "recommendations": []}

        action_items = [
            ActionItem(
                task=item.get("task", ""),
                assignee=item.get("assignee") or None,
                deadline=item.get("deadline") or None,
            )
            for item in data.get("action_items", [])
        ]

        recommendations = [
            {
                "title": r.get("title", ""),
                "detail": r.get("detail", ""),
                "priority": r.get("priority", "medium"),
            }
            for r in data.get("recommendations", [])
            if isinstance(r, dict)
        ]

        return {
            "summary": data.get("summary", ""),
            "action_items": action_items,
            "recommendations": recommendations,
        }