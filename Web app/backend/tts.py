"""
DardlashAI — Edge-TTS Moduli (Bepul, kalitsiz)

O'zbek tilida matnni ovozga aylantiradi.
edge-tts kutubxonasidan foydalanadi (Microsoft Edge neural voices).

Azure kaliti kerak EMAS — bepul ishlaydi.

Ishlatish:
    from tts import generate_audio_bytes
    audio = await generate_audio_bytes("Salom, bugun qanday kayfiyatingiz?")
"""

import re
import io
import logging
import edge_tts

logger = logging.getLogger("dardlash.tts")

# ═══════════════════════════════════════════════════════════════════════
# SOZLAMALAR
# ═══════════════════════════════════════════════════════════════════════

VOICE = "uz-UZ-MadinaNeural"

# Tezlik: "+20%" = tezroq (7 sek → ~3 sek), "+0%" = oddiy, "-10%" = sekin
RATE = "+20%"
PITCH = "+0Hz"
VOLUME = "+0%"


# ═══════════════════════════════════════════════════════════════════════
# RAQAMLARNI SO'ZGA AYLANTIRISH
# ═══════════════════════════════════════════════════════════════════════

_ONES = {
    0: "nol", 1: "bir", 2: "ikki", 3: "uch", 4: "to'rt",
    5: "besh", 6: "olti", 7: "yetti", 8: "sakkiz", 9: "to'qqiz",
}
_TEENS = {
    10: "o'n", 11: "o'n bir", 12: "o'n ikki", 13: "o'n uch",
    14: "o'n to'rt", 15: "o'n besh", 16: "o'n olti", 17: "o'n yetti",
    18: "o'n sakkiz", 19: "o'n to'qqiz",
}
_TENS = {
    2: "yigirma", 3: "o'ttiz", 4: "qirq", 5: "ellik",
    6: "oltmish", 7: "yetmish", 8: "sakson", 9: "to'qson",
}


def _number_to_uzbek(n: int) -> str:
    """Butun sonni o'zbek so'zlariga aylantiradi."""
    if n < 0:
        return "minus " + _number_to_uzbek(-n)
    if n < 10:
        return _ONES[n]
    if n < 20:
        return _TEENS[n]
    if n < 100:
        tens, ones = divmod(n, 10)
        return _TENS[tens] + (" " + _ONES[ones] if ones else "")
    if n < 1000:
        h, r = divmod(n, 100)
        return (_ONES[h] + " yuz") + (" " + _number_to_uzbek(r) if r else "")
    if n < 1_000_000:
        t, r = divmod(n, 1000)
        prefix = "ming" if t == 1 else _number_to_uzbek(t) + " ming"
        return prefix + (" " + _number_to_uzbek(r) if r else "")
    return str(n)


def _convert_numbers(text: str) -> str:
    """Matndagi raqamlarni o'zbek so'zlariga aylantiradi."""
    def _decimal(m):
        dec_words = " ".join(_ONES[int(d)] for d in m.group(2))
        return _number_to_uzbek(int(m.group(1))) + " butun " + dec_words
    text = re.sub(r'(\d+)\.(\d+)', _decimal, text)

    def _integer(m):
        s = m.group(0)
        return s if len(s) >= 7 else _number_to_uzbek(int(s))
    text = re.sub(r'\d+', _integer, text)
    return text


# ═══════════════════════════════════════════════════════════════════════
# MATNNI TOZALASH
# ═══════════════════════════════════════════════════════════════════════

_ABBREVIATIONS = {
    "va h.k.": "va hokazo", "h.k.": "hokazo",
    "va b.": "va boshqalar", "mas.": "masalan",
    "t.r.": "to'g'ri", "q.q.": "qo'llab-quvvatlash",
    "m-chi": "menchi", "shu j.": "shu jumladan",
    "sh.j.": "shu jumladan",
}


def _clean_text(text: str) -> str:
    """Matnni TTS uchun tozalaydi."""
    if not text:
        return ""

    # Emojilarni olib tashlash
    text = re.sub(
        r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF'
        r'\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF'
        r'\U00002702-\U000027B0\U000024C2-\U0001F251'
        r'\U0000200d\U0000fe0f\U00002764\U0001FA70-\U0001FAFF]+',
        '', text
    )

    # Qavslar va maxsus belgilar
    text = re.sub(r'\([^)]*\)', '', text)
    text = re.sub(r'\[[^\]]*\]', '', text)
    text = re.sub(r'[*#_~`|<>@&^\\]', '', text)
    text = re.sub(r'https?://\S+', '', text)

    # Qisqartmalarni yoyish
    for short, full in sorted(_ABBREVIATIONS.items(), key=lambda x: -len(x[0])):
        text = text.replace(short, full)

    # Raqamlarni so'zlarga
    text = _convert_numbers(text)

    # Takroriy belgilar
    text = re.sub(r'\.{2,}', '.', text)
    text = re.sub(r'!{2,}', '!', text)
    text = re.sub(r'\?{2,}', '?', text)
    text = re.sub(r'—', ', ', text)
    text = re.sub(r'-{2,}', ', ', text)

    # Bo'shliqlarni tozalash
    text = re.sub(r'\s+', ' ', text).strip()

    return text


# ═══════════════════════════════════════════════════════════════════════
# ASOSIY FUNKSIYA — async, bytes qaytaradi
# ═══════════════════════════════════════════════════════════════════════

async def generate_audio_bytes(
    text: str,
    voice: str = VOICE,
    rate: str = RATE,
    pitch: str = PITCH,
    volume: str = VOLUME,
) -> bytes:
    """
    Matnni ovozga aylantiradi — bir yo'la, ravon, tez.
    Diskka hech narsa saqlamaydi, bytes qaytaradi.

    Returns:
        MP3 audio bytes. Xatolikda b"" qaytaradi.
    """
    try:
        clean = _clean_text(text)
        if not clean:
            return b""

        logger.info(f"TTS: Matn uzunligi={len(clean)} belgi, ovoz={voice}, tezlik={rate}")

        buffer = io.BytesIO()

        communicate = edge_tts.Communicate(
            text=clean,
            voice=voice,
            rate=rate,
            pitch=pitch,
            volume=volume,
        )

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buffer.write(chunk["data"])

        result = buffer.getvalue()
        logger.info(f"TTS: Audio tayyor, hajmi={len(result)} bytes")
        return result

    except Exception as e:
        logger.error(f"TTS xatolik: {e}")
        return b""


# ═══════════════════════════════════════════════════════════════════════
# ESKI API UCHUN MOSLIK (main.py generate_audio() chaqiradi)
# ═══════════════════════════════════════════════════════════════════════

# Bu funksiyalar main.py bilan moslik uchun qoldirilgan.
# main.py da: from tts import generate_audio, list_available_voices, AUDIO_DIR

import asyncio
import uuid
from pathlib import Path

AUDIO_DIR = Path(__file__).resolve().parent / "static" / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

MAX_AUDIO_FILES = 50


def generate_audio(text: str, voice: str = VOICE) -> str | None:
    """
    Eski API uchun moslik — main.py shu funksiyani chaqiradi.
    Audio bytes yaratib, diskka saqlaydi va URL qaytaradi.
    """
    try:
        # async funksiyani sync kontekstda chaqirish
        audio_bytes = asyncio.run(generate_audio_bytes(text, voice=voice))

        if not audio_bytes:
            return None

        # Diskka saqlash
        file_id = uuid.uuid4().hex[:12]
        filename = f"response_{file_id}.mp3"
        filepath = AUDIO_DIR / filename
        filepath.write_bytes(audio_bytes)

        logger.info(f"Audio saqlandi: {filepath}")
        _cleanup_old_files()

        return f"/audio/{filename}"

    except RuntimeError:
        # Agar event loop allaqachon ishlayotgan bo'lsa
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(
                asyncio.run,
                generate_audio_bytes(text, voice=voice),
            )
            audio_bytes = future.result(timeout=30)

        if not audio_bytes:
            return None

        file_id = uuid.uuid4().hex[:12]
        filename = f"response_{file_id}.mp3"
        filepath = AUDIO_DIR / filename
        filepath.write_bytes(audio_bytes)

        logger.info(f"Audio saqlandi: {filepath}")
        _cleanup_old_files()

        return f"/audio/{filename}"

    except Exception as e:
        logger.error(f"TTS generate_audio xatolik: {e}")
        return None


def list_available_voices() -> list:
    """Edge-TTS ovozlari ro'yxati."""
    return [
        {"name": "uz-UZ-MadinaNeural", "locale": "uz-UZ", "gender": "Female"},
        {"name": "uz-UZ-SardorNeural", "locale": "uz-UZ", "gender": "Male"},
    ]


def _cleanup_old_files():
    """Eski audio fayllarni o'chirish."""
    import os
    try:
        files = sorted(AUDIO_DIR.glob("response_*.mp3"), key=os.path.getmtime)
        if len(files) > MAX_AUDIO_FILES:
            for f in files[:len(files) - MAX_AUDIO_FILES]:
                f.unlink(missing_ok=True)
    except Exception:
        pass
