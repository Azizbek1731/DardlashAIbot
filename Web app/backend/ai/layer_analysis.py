"""
DardlashAI — Layer 1: Gemini Analysis

Foydalanuvchi matnini tahlil qilib, hissiyot, maqsad, kontekst va
jiddiylik darajasini aniqlaydi.

Chiqish: AnalysisResult (JSON)
Fallback: Kalit so'zlarga asoslangan oddiy tahlil
"""

import logging
from ai.gemini_client import call_gemini_json
from ai.schemas import AnalysisResult

logger = logging.getLogger("dardlash.layer1")

# ═══════════════════════════════════════════════════════════════════════
# GEMINI PROMPT
# ═══════════════════════════════════════════════════════════════════════

ANALYSIS_PROMPT_TEMPLATE = """Sen matn tahlil qiluvchi AI tizimsan.
Foydalanuvchining xabarini tahlil qilib, quyidagi ma'lumotlarni JSON formatida qaytar.

FOYDALANUVCHI XABARI: "{user_text}"
KAMERA HISSIYOTI: "{camera_emotion}"

RUXSAT ETILGAN QIYMATLAR:

emotion (matndan aniqlangan hissiyot):
- neutral — oddiy, hissiyotsiz
- happy — xursand, quvnoq
- sad — g'amgin, xafa
- anxious — tashvishli, bezovta
- tired — charchagan, holsiz
- overwhelmed — bosim ostida, hamma narsa haddan oshgan
- lonely — yolg'iz, tashlandiq his

intent (foydalanuvchi nima xohlayapti):
- wants_emotional_support — hissiy qo'llab-quvvatlash xohlaydi
- wants_calming — tinchlantirish xohlaydi
- wants_encouragement — dalda-ruhlantirish xohlaydi
- wants_to_vent — shunchaki gapirmoqchi, javob shart emas
- wants_small_practical_help — oddiy amaliy maslahat xohlaydi
- wants_check_in — salomlashmoqda, oddiy suhbat

context (mavzu):
- work — ish bilan bog'liq
- study — o'qish, ta'lim
- relationship — munosabatlar, oila, do'stlar
- health — sog'liq
- financial — moliya, pul
- sleep — uyqu, dam olish
- general — umumiy yoki aniq emas

severity (jiddiylik):
- low — yengil, oddiy
- moderate — o'rtacha, e'tibor kerak
- high — jiddiy, ehtiyot bo'lish kerak

QOIDALAR:
1. Kamera hissiyoti va matndagi hissiyotni solishtir. Matn ustunroq.
2. Agar matn aniq bo'lmasa — "neutral" va "general" qo'y.
3. key_themes — matndan 1-3 ta asosiy mavzuni ajratib yoz.
4. FAQAT JSON qaytar, hech qanday qo'shimcha matn yozma.

JAVOB FORMATI (faqat shu JSON):
{{
  "emotion": "...",
  "intent": "...",
  "context": "...",
  "severity": "...",
  "key_themes": ["...", "..."]
}}"""


# ═══════════════════════════════════════════════════════════════════════
# ASOSIY FUNKSIYA
# ═══════════════════════════════════════════════════════════════════════

async def analyze(user_text: str, camera_emotion: str = "neutral") -> AnalysisResult:
    """
    Layer 1: Foydalanuvchi matnini Gemini orqali tahlil qiladi.

    Args:
        user_text: Foydalanuvchi xabari
        camera_emotion: Kameradan aniqlangan hissiyot

    Returns:
        AnalysisResult — tahlil natijasi (har doim qaytaradi, xatolikda fallback)
    """
    prompt = ANALYSIS_PROMPT_TEMPLATE.format(
        user_text=user_text,
        camera_emotion=camera_emotion,
    )

    result = await call_gemini_json(prompt)

    if result:
        try:
            analysis = AnalysisResult(**result)
            logger.info(
                f"Layer 1 ✅: emotion={analysis.emotion}, "
                f"intent={analysis.intent}, context={analysis.context}, "
                f"severity={analysis.severity}"
            )
            return analysis
        except Exception as e:
            logger.warning(f"Layer 1: JSON validatsiya xatosi: {e}")

    # Fallback — kalit so'zlarga asoslangan tahlil
    logger.info("Layer 1 ⚠️: Fallback (kalit so'z tahlili)")
    return _fallback_analysis(user_text, camera_emotion)


# ═══════════════════════════════════════════════════════════════════════
# FALLBACK: KALIT SO'Z TAHLILI
# ═══════════════════════════════════════════════════════════════════════

# Hissiyot kalit so'zlari
_EMOTION_KEYWORDS = {
    "sad": ["g'amgin", "xafa", "yig'la", "qayg'u", "og'ri", "yo'qot",
            "sad", "unhappy", "cry", "miss", "pain", "hurt"],
    "anxious": ["tashvish", "bezovta", "qo'rq", "xavotir", "stress",
                "anxious", "worried", "nervous", "panic", "fear"],
    "tired": ["charch", "toliq", "uxla", "holsiz", "kuch yo'q",
              "tired", "exhausted", "sleep", "fatigue", "energy"],
    "happy": ["xursand", "baxtli", "yaxshi", "ajoyib", "zo'r",
              "happy", "great", "wonderful", "excited", "joy"],
    "overwhelmed": ["bosim", "ko'p", "haddan", "bari", "uldur",
                    "overwhelm", "too much", "pressure", "drowning"],
    "lonely": ["yolg'iz", "tashlan", "hech kim", "tanho",
               "lonely", "alone", "isolated", "nobody"],
}

# Kontekst kalit so'zlari
_CONTEXT_KEYWORDS = {
    "work": ["ish", "job", "boss", "rahbar", "ofis", "loyiha", "maosh", "hamkasb"],
    "study": ["o'qi", "maktab", "universitet", "imtihon", "test", "talaba", "kurs"],
    "relationship": ["do'st", "oila", "ota", "ona", "sevgi", "yolg'iz", "er", "xotin"],
    "health": ["kasal", "og'ri", "dard", "sog'liq", "vrach", "kasalxona"],
    "financial": ["pul", "moliya", "qarz", "maosh", "to'lov"],
    "sleep": ["uxla", "uyqu", "tun", "tong", "insomnia"],
}


def _fallback_analysis(user_text: str, camera_emotion: str) -> AnalysisResult:
    """Gemini ishlamasa — kalit so'z tahlili."""
    text_lower = user_text.lower()

    # Hissiyot aniqlash
    emotion = "neutral"
    for emo, keywords in _EMOTION_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            emotion = emo
            break

    # Agar matndan aniqlanmasa — kamera hissiyotidan olish
    if emotion == "neutral" and camera_emotion != "neutral":
        # Kamera hissiyotlarini pipeline hissiyotlariga map qilish
        camera_map = {
            "happy": "happy", "sad": "sad", "angry": "anxious",
            "fearful": "anxious", "disgusted": "overwhelmed",
            "surprised": "neutral",
        }
        emotion = camera_map.get(camera_emotion, "neutral")

    # Kontekst aniqlash
    context = "general"
    for ctx, keywords in _CONTEXT_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            context = ctx
            break

    # Intent aniqlash
    intent = "wants_emotional_support"
    if emotion in ("anxious",):
        intent = "wants_calming"
    elif emotion in ("sad", "lonely"):
        intent = "wants_emotional_support"
    elif emotion in ("happy",):
        intent = "wants_check_in"
    elif emotion in ("tired", "overwhelmed"):
        intent = "wants_small_practical_help"

    # Jiddiylik
    severity = "low"
    high_risk_words = ["o'lim", "o'ldir", "umidsiz", "ma'nosiz", "hayot", "suicide", "die", "hopeless"]
    if any(w in text_lower for w in high_risk_words):
        severity = "high"
    elif emotion in ("overwhelmed", "lonely") or len(user_text) > 100:
        severity = "moderate"

    return AnalysisResult(
        emotion=emotion,
        intent=intent,
        context=context,
        severity=severity,
        key_themes=[context] if context != "general" else [],
    )
