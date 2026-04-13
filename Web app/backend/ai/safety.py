"""
DardlashAI — Layer 4: Xavfsizlik Validatori (Enhanced)

Ikki bosqichli xavfsizlik tekshiruvi:
1. Gemini — AI orqali javobni semantik tekshirish
2. Regex — qat'iy pattern matching (har doim ishlaydi)

Chiqish: SafetyResult (JSON)
Fallback: faqat regex tekshiruv
"""

import re
import logging
from ai.gemini_client import call_gemini_json
from ai.schemas import SafetyResult

logger = logging.getLogger("dardlash.layer4")


# ═══════════════════════════════════════════════════════════════════════
# 1. GEMINI XAVFSIZLIK TEKSHIRUVI
# ═══════════════════════════════════════════════════════════════════════

SAFETY_PROMPT_TEMPLATE = """Sen hissiy qo'llab-quvvatlash tizimining xavfsizlik tekshiruvchisisisan.
Quyidagi javobni tekshir va xavfsiz ekanligini baholab JSON qaytar.

═══ TEKSHIRILADIGAN JAVOB ═══
"{response_text}"

═══ XAVFSIZLIK QOIDALARI ═══
Quyidagilarning BIRORTASI ham bo'lmasligi kerak:

1. DIAGNOZ — "sizda depressiya bor", "bu anxiety disorder", "sizda ruhiy kasallik" kabi
2. DORI TAVSIYASI — "antidepressant oling", "tabletka iching", "dori qabul qiling" kabi
3. KLINIK DA'VO — "siz albatta tuzalasiz", "bu kasallik", "shifokorga boring" kabi
4. QATTIQ TIL — "shunchaki chidang", "o'zingizni qo'lga oling", "bu katta gap emas" kabi
5. AYBLOV — "siz o'zingiz aybdorsiz", "haddan oshiryapsiz", "dramatizatsiya qilmang" kabi
6. ORTIQCHA ISHONCH — "hech qachon...", "doim...", "albatta..." kabi mutlaq da'volar

Agar biror qoida buzilsa:
- is_safe = false
- violations ga buzilish turini yoz
- corrected_text ga tuzatilgan versiyani yoz (buzilgan qismlarni olib tashla)

Agar hammasi yaxshi bo'lsa:
- is_safe = true
- violations bo'sh bo'lsin
- corrected_text ga asl matnni qo'y

FAQAT JSON qaytar:
{{
  "is_safe": true,
  "violations": [],
  "corrected_text": "..."
}}"""


async def _gemini_safety_check(response_text: str) -> SafetyResult | None:
    """Gemini orqali semantik xavfsizlik tekshiruvi."""
    prompt = SAFETY_PROMPT_TEMPLATE.format(response_text=response_text)

    result = await call_gemini_json(prompt)

    if result:
        try:
            safety = SafetyResult(**result)
            return safety
        except Exception as e:
            logger.warning(f"Layer 4 Gemini: JSON validatsiya xatosi: {e}")

    return None


# ═══════════════════════════════════════════════════════════════════════
# 2. REGEX XAVFSIZLIK TEKSHIRUVI (har doim ishlaydi)
# ═══════════════════════════════════════════════════════════════════════

# Diagnoz yoki klinik baho berish iboralari
DIAGNOSIS_PATTERNS = [
    # Ingliz tilida
    r"\byou have\b.*\b(disorder|syndrome|condition|disease|depression|anxiety disorder|ptsd|ocd|bipolar|adhd)\b",
    r"\byou('re| are) (clearly |obviously )?(depressed|mentally ill|suffering from|diagnosed)\b",
    r"\bthis (is|sounds like) (a case of|symptoms of|clinical)\b",
    r"\byou (need|should) (therapy|counseling|psychiatric|professional help)\b",
    r"\bi (think|believe) you (have|suffer|are suffering)\b",
    r"\byou('re| are) showing signs of\b",
    # O'zbek tilida
    r"\bsizda .*(kasallik|sindrom|buzilish|depressiya|ruhiy kasal)\b",
    r"\bsiz .*(depressiyada|ruhiy kasal|aziyat chek)\b",
    r"\bbu .*(belgilar|simptomlar|kasallik belgisi)\b",
    r"\bsizga .*(terapiya|psixolog|psixiatr|davolanish) kerak\b",
    r"\bmenimcha sizda\b",
    r"\bsiz.*kasal\b.*\bbo'l\b",
]

# Tibbiy maslahat iboralari
MEDICAL_ADVICE_PATTERNS = [
    # Ingliz tilida
    r"\b(take|try|use|start|consider)\b.*\b(medication|medicine|pills|antidepressant|ssri|benzodiazepine|supplement|melatonin|valerian)\b",
    r"\b(prescribe|prescription|dosage|mg)\b",
    r"\bincrease your (dose|medication)\b",
    r"\bstop taking\b",
    r"\bmedical treatment\b",
    # O'zbek tilida
    r"\b(iching|oling|ishlating|boshlang)\b.*\b(dori|tabletka|preparat|antidepressant|vitamin|qo'shimcha)\b",
    r"\b(retsept|dozaj|milligramm)\b",
    r"\b(dori|tabletka).*\b(iching|oling|qabul qiling)\b",
    r"\bdori.*tavsiya\b",
    r"\bdavolanish.*kerak\b",
]

# Zararli iboralar
HARMFUL_PATTERNS = [
    # Ingliz tilida
    r"\byou (will|are going to) (never|always)\b",
    r"\beveryone feels this way\b",
    r"\bjust (get over it|snap out|stop feeling|man up|toughen up)\b",
    r"\bit('s| is) (all in your head|nothing|not a big deal|not that bad)\b",
    r"\byou('re| are) (overreacting|being dramatic|too sensitive)\b",
    r"\bthere('s| is) nothing wrong with you\b",
    # O'zbek tilida
    r"\bsiz (hech qachon|doim)\b",
    r"\bhamma ham shunday\b",
    r"\bshunchaki .*(o'zingizni bosing|qo'ying|unutib yuboring|chida)\b",
    r"\bbu .*(hech narsa|katta gap emas|unchalik emas|muhim emas)\b",
    r"\bsiz .*(haddan oshir|dramati|sezgir)\b",
    r"\bsizda hech qanday muammo yo'q\b",
    r"\bo'zingizni qo'lga oling\b",
]

ALL_BLOCKED_PATTERNS = DIAGNOSIS_PATTERNS + MEDICAL_ADVICE_PATTERNS + HARMFUL_PATTERNS

# Umumiy xavfsiz javob (agar hammasi bloklanib qolsa)
SAFE_FALLBACK_RESPONSE = (
    "Sizni tinglayapman va bo'lishganingiz uchun rahmat. "
    "Gaplashmoqchi bo'lsangiz, men doim shu yerdaman. 💛"
)


def _regex_safety_check(response: str) -> SafetyResult:
    """Regex orqali xavfsizlik tekshiruvi — har doim ishlaydi."""
    lower_response = response.lower()
    violations = []

    for pattern in DIAGNOSIS_PATTERNS:
        if re.search(pattern, lower_response):
            violations.append("diagnoz")
            break

    for pattern in MEDICAL_ADVICE_PATTERNS:
        if re.search(pattern, lower_response):
            violations.append("tibbiy_maslahat")
            break

    for pattern in HARMFUL_PATTERNS:
        if re.search(pattern, lower_response):
            violations.append("zararli_ibora")
            break

    if violations:
        cleaned = _sanitize_response(response)
        return SafetyResult(
            is_safe=False,
            violations=violations,
            corrected_text=cleaned,
        )

    return SafetyResult(
        is_safe=True,
        violations=[],
        corrected_text=response,
    )


def _sanitize_response(response: str) -> str:
    """Javobdan xavfli jumlalarni olib tashlaydi."""
    sentences = re.split(r'(?<=[.!?])\s+', response)
    safe_sentences = []

    for sentence in sentences:
        lower_s = sentence.lower()
        is_blocked = False
        for pattern in ALL_BLOCKED_PATTERNS:
            if re.search(pattern, lower_s):
                is_blocked = True
                break
        if not is_blocked:
            safe_sentences.append(sentence)

    if not safe_sentences:
        return SAFE_FALLBACK_RESPONSE

    return " ".join(safe_sentences)


# ═══════════════════════════════════════════════════════════════════════
# 3. BIRLASHTIRILGAN XAVFSIZLIK TEKSHIRUVI (ASOSIY FUNKSIYA)
# ═══════════════════════════════════════════════════════════════════════

async def validate_safety(response_text: str) -> SafetyResult:
    """
    Layer 4: Ikki bosqichli xavfsizlik tekshiruvi.

    1-bosqich: Gemini semantik tekshiruv (agar mavjud bo'lsa)
    2-bosqich: Regex qat'iy tekshiruv (HAR DOIM ishlaydi)

    Args:
        response_text: Tekshiriladigan javob matni

    Returns:
        SafetyResult — xavfsizlik natijasi (har doim qaytaradi)
    """
    if not response_text:
        return SafetyResult(
            is_safe=True,
            violations=[],
            corrected_text=SAFE_FALLBACK_RESPONSE,
        )

    current_text = response_text
    all_violations = []

    # ── 1-bosqich: Gemini tekshiruv ──
    gemini_result = await _gemini_safety_check(current_text)
    if gemini_result:
        if not gemini_result.is_safe:
            all_violations.extend(gemini_result.violations)
            current_text = gemini_result.corrected_text or current_text
            logger.warning(f"Layer 4 Gemini: Buzilishlar topildi: {gemini_result.violations}")
        else:
            logger.info("Layer 4 Gemini ✅: Xavfsiz")

    # ── 2-bosqich: Regex tekshiruv (har doim) ──
    regex_result = _regex_safety_check(current_text)
    if not regex_result.is_safe:
        all_violations.extend(regex_result.violations)
        current_text = regex_result.corrected_text
        logger.warning(f"Layer 4 Regex: Qo'shimcha buzilishlar: {regex_result.violations}")
    else:
        logger.info("Layer 4 Regex ✅: Xavfsiz")

    # Yakuniy natija
    is_safe = len(all_violations) == 0

    result = SafetyResult(
        is_safe=is_safe,
        violations=list(set(all_violations)),  # dublikatlarni olib tashlash
        corrected_text=current_text,
    )

    if is_safe:
        logger.info("Layer 4 ✅: Javob xavfsiz")
    else:
        logger.warning(f"Layer 4 ⚠️: {len(all_violations)} ta buzilish tuzatildi")

    return result


# ═══════════════════════════════════════════════════════════════════════
# ESKI API UCHUN MOSLIK
# ═══════════════════════════════════════════════════════════════════════

def check_response_safety(response: str) -> dict:
    """Eski API uchun moslik — sync versiya."""
    result = _regex_safety_check(response)
    return {
        "is_safe": result.is_safe,
        "violations": result.violations,
        "cleaned_response": result.corrected_text,
    }


def ensure_safe_output(response: str) -> str:
    """Eski API uchun moslik — sync versiya."""
    result = _regex_safety_check(response)
    return result.corrected_text
