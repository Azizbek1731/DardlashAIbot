"""
DardlashAI — Gemini API Client

Google Gemini API bilan ishlash uchun singleton client.
Barcha pipeline qatlamlari shu client orqali Gemini ga murojaat qiladi.

call_gemini_json() — JSON javob kutadi va dict qaytaradi
call_gemini_text() — oddiy matn javob kutadi va str qaytaradi
"""

import os
import json
import logging
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("dardlash.gemini")

# ═══════════════════════════════════════════════════════════════════════
# SOZLAMALAR
# ═══════════════════════════════════════════════════════════════════════

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# Singleton client
_client = None
_initialized = False


def _get_client():
    """Gemini clientni olish yoki yaratish (singleton)."""
    global _client, _initialized

    if _initialized:
        return _client

    _initialized = True

    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        logger.warning(
            "⚠️ GEMINI_API_KEY topilmadi! "
            ".env faylga GEMINI_API_KEY=... qo'shing. "
            "Pipeline fallback rejimida ishlaydi."
        )
        _client = None
        return None

    try:
        from google import genai
        _client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info(f"✅ Gemini client tayyor (model: {GEMINI_MODEL})")
        return _client
    except ImportError:
        logger.error(
            "google-genai kutubxonasi o'rnatilmagan! "
            "pip install google-genai"
        )
        _client = None
        return None
    except Exception as e:
        logger.error(f"Gemini client xatosi: {e}")
        _client = None
        return None


def is_available() -> bool:
    """Gemini API ishga tayyor mi?"""
    return _get_client() is not None


# ═══════════════════════════════════════════════════════════════════════
# JSON JAVOB SO'RASH
# ═══════════════════════════════════════════════════════════════════════

async def call_gemini_json(
    prompt: str,
    model: str = GEMINI_MODEL,
    max_retries: int = 1,
) -> Optional[dict]:
    """
    Gemini ga prompt yuborib, JSON javob oladi.

    Args:
        prompt: So'rov matni (JSON qaytarish kerakligini prompt ichida yozish kerak)
        model: Gemini model nomi
        max_retries: Qayta urinishlar soni

    Returns:
        dict — JSON javob, yoki None agar xatolik bo'lsa
    """
    client = _get_client()
    if not client:
        return None

    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
            )

            raw_text = response.text.strip()

            # JSON ni ajratib olish (ba'zan Gemini ```json...``` ichida qaytaradi)
            json_text = _extract_json(raw_text)

            result = json.loads(json_text)
            return result

        except json.JSONDecodeError as e:
            logger.warning(
                f"Gemini JSON parse xatosi (urinish {attempt + 1}): {e}\n"
                f"Raw javob: {raw_text[:200]}"
            )
            if attempt < max_retries:
                continue
            return None

        except Exception as e:
            logger.error(f"Gemini API xatosi (urinish {attempt + 1}): {e}")
            if attempt < max_retries:
                continue
            return None

    return None


# ═══════════════════════════════════════════════════════════════════════
# MATN JAVOB SO'RASH
# ═══════════════════════════════════════════════════════════════════════

async def call_gemini_text(
    prompt: str,
    model: str = GEMINI_MODEL,
    max_retries: int = 1,
) -> Optional[str]:
    """
    Gemini ga prompt yuborib, oddiy matn javob oladi.

    Args:
        prompt: So'rov matni
        model: Gemini model nomi
        max_retries: Qayta urinishlar soni

    Returns:
        str — matn javob, yoki None agar xatolik bo'lsa
    """
    client = _get_client()
    if not client:
        return None

    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
            )

            text = response.text.strip()

            # Agar Gemini markdown code block ichida qaytarsa — tozalash
            if text.startswith("```") and text.endswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1]).strip()

            return text

        except Exception as e:
            logger.error(f"Gemini API xatosi (urinish {attempt + 1}): {e}")
            if attempt < max_retries:
                continue
            return None

    return None


# ═══════════════════════════════════════════════════════════════════════
# YORDAMCHI
# ═══════════════════════════════════════════════════════════════════════

def _extract_json(text: str) -> str:
    """
    Gemini javobidan JSON ni ajratib oladi.
    Ba'zan Gemini ```json ... ``` yoki boshqa matn bilan o'raydi.
    """
    # ```json ... ``` ichidan
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        return text[start:end].strip()

    # ``` ... ``` ichidan
    if text.startswith("```") and text.endswith("```"):
        lines = text.split("\n")
        return "\n".join(lines[1:-1]).strip()

    # { ... } topish
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return text[first_brace:last_brace + 1]

    return text
