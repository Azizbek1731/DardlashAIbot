"""
DardlashAI — Layer 2: Custom Supportive Protocol Model

Tahlil natijasiga qarab, maxsus protokol asosida qo'llab-quvvatlovchi
javob yaratadi. Bu tizimning "ruhiy" yadrosiga — har bir hissiyot uchun
aniq strategiya, ohang va tuzilma belgilangan.

Chiqish: ProtocolResult (JSON)
Fallback: Shablon javoblar (EMOTION_STRATEGIES dan)
"""

import random
import logging
from ai.gemini_client import call_gemini_json
from ai.schemas import AnalysisResult, ProtocolResult, ResponseComponents
from ai.prompt import EMOTION_STRATEGIES

logger = logging.getLogger("dardlash.layer2")

# ═══════════════════════════════════════════════════════════════════════
# GEMINI PROMPT — MAXSUS PROTOKOL
# ═══════════════════════════════════════════════════════════════════════

PROTOCOL_PROMPT_TEMPLATE = """Sen hissiy qo'llab-quvvatlash protokoli bo'yicha ixtisoslashgan AI modelsan.
Sening vazifang — foydalanuvchining hissiy holatiga mos, xavfsiz va iliq javob yaratish.

═══ FOYDALANUVCHI MA'LUMOTLARI ═══
Xabar: "{user_text}"
Aniqlangan hissiyot: {emotion}
Maqsad: {intent}
Kontekst: {context}
Jiddiylik: {severity}
Asosiy mavzular: {key_themes}

═══ JAVOB PROTOKOLI ═══

TUZILMA (aynan shu tartibda):
1. ACKNOWLEDGMENT — Foydalanuvchining hissiyotini tan ol (1 jumla)
2. VALIDATION — Bu hisni his qilish normal ekanini tastiqla (1 jumla)
3. SUGGESTION — Bitta kichik, amaliy maslahat ber (1 jumla)
4. FOLLOW_UP — Yumshoq davom ettiruvchi savol (1 jumla, ixtiyoriy)

UMUMIY: 3-5 jumla. Qisqa va ta'sirli.

HISSIYOT STRATEGIYALARI:
- neutral → do'stona, yengil ohang, ochiq savol
- happy → ijobiy mustahkamlash, quvonchni qadrash
- sad → hamdardlik, yumshoq dalda, sabr
- anxious → tinchlantirish, nafas mashqlari, xavfsizlik hissi
- tired → dam olishga ruxsat, bosimni kamaytirish
- overwhelmed → yuklarni soddalash, bitta qadam
- lonely → aloqa hissi, siz yolg'iz emasingizni bildirish

INTENT STRATEGIYALARI:
- wants_emotional_support → hissiy dalda va hamdardlik
- wants_calming → nafas mashqlari, tinchlantiruvchi gaplar
- wants_encouragement → kuch berish, ijobiy tomonga e'tibor
- wants_to_vent → faol tinglash, hukm qilmaslik
- wants_small_practical_help → aniq, oddiy amaliy maslahat
- wants_check_in → yengil muloqot, ochiq savol

═══ QATIY TAQIQLAR ═══
❌ HECH QACHON diagnoz qo'yma ("sizda depressiya bor" kabi)
❌ HECH QACHON dori-darmon tavsiya qilma
❌ HECH QACHON klinik da'vo qilma
❌ HECH QACHON qattiq yoki ayblovchi til ishlat
❌ HECH QACHON haddan ortiq ishonch bildir ("siz albatta tuzalasiz")
✅ DOIMO iliq, qisqa va hukm qilmaydigan bo'l
✅ FAQAT o'zbek tilida (lotin yozuvi) javob ber

═══ TIL TALABLARI ═══
- Sof o'zbek tilida yoz (lotin yozuvi)
- Oddiy, tushunarli so'zlar ishlat
- Do'stona ohang — yaqin do'st kabi
- Robot kabi emas, insoniy bo'l

═══ JAVOB FORMATI ═══
FAQAT quyidagi JSON qaytar, boshqa hech narsa yozma:
{{
  "draft_response": "To'liq javob matni shu yerda",
  "strategy_used": "ishlatilgan strategiya nomi",
  "tone": "warm_supportive",
  "components": {{
    "acknowledgment": "Hissiyotni tan olish jumla",
    "validation": "Tasdiqlash jumla",
    "suggestion": "Amaliy maslahat jumla",
    "follow_up": "Davom savol (yoki bo'sh)"
  }}
}}"""


# ═══════════════════════════════════════════════════════════════════════
# ASOSIY FUNKSIYA
# ═══════════════════════════════════════════════════════════════════════

async def generate_protocol_response(
    user_text: str,
    analysis: AnalysisResult,
) -> ProtocolResult:
    """
    Layer 2: Tahlil natijasiga qarab protokol javob yaratadi.

    Args:
        user_text: Foydalanuvchi xabari
        analysis: Layer 1 tahlil natijasi

    Returns:
        ProtocolResult — protokol javob (har doim qaytaradi, xatolikda fallback)
    """
    prompt = PROTOCOL_PROMPT_TEMPLATE.format(
        user_text=user_text,
        emotion=analysis.emotion,
        intent=analysis.intent,
        context=analysis.context,
        severity=analysis.severity,
        key_themes=", ".join(analysis.key_themes) if analysis.key_themes else "umumiy",
    )

    result = await call_gemini_json(prompt)

    if result:
        try:
            # components ni alohida parse qilish
            components_data = result.get("components", {})
            components = ResponseComponents(**components_data)

            protocol = ProtocolResult(
                draft_response=result.get("draft_response", ""),
                strategy_used=result.get("strategy_used", ""),
                tone=result.get("tone", "warm_supportive"),
                components=components,
            )

            if protocol.draft_response:
                logger.info(
                    f"Layer 2 ✅: strategy={protocol.strategy_used}, "
                    f"tone={protocol.tone}, "
                    f"length={len(protocol.draft_response)} chars"
                )
                return protocol

        except Exception as e:
            logger.warning(f"Layer 2: JSON validatsiya xatosi: {e}")

    # Fallback — shablon javoblar
    logger.info("Layer 2 ⚠️: Fallback (shablon javob)")
    return _fallback_protocol(user_text, analysis)


# ═══════════════════════════════════════════════════════════════════════
# FALLBACK: SHABLON JAVOBLAR
# ═══════════════════════════════════════════════════════════════════════

def _fallback_protocol(user_text: str, analysis: AnalysisResult) -> ProtocolResult:
    """Gemini ishlamasa — mavjud shablonlardan javob yaratish."""

    # Hissiyotni mavjud strategiyalarga moslashtirish
    emotion_map = {
        "neutral": "neutral", "happy": "happy", "sad": "sad",
        "anxious": "anxious", "tired": "tired",
        "overwhelmed": "tired", "lonely": "sad",
    }
    mapped_emotion = emotion_map.get(analysis.emotion, "neutral")

    strategy = EMOTION_STRATEGIES.get(mapped_emotion, EMOTION_STRATEGIES["neutral"])

    opener = random.choice(strategy["openers"])
    suggestion = random.choice(strategy["suggestions"])
    follow_up = random.choice(strategy["follow_ups"])

    parts = [opener, suggestion]
    if follow_up:
        parts.append(follow_up)

    draft = " ".join(parts)

    return ProtocolResult(
        draft_response=draft,
        strategy_used=strategy.get("strategy", "fallback"),
        tone="warm_supportive",
        components=ResponseComponents(
            acknowledgment=opener,
            validation="",
            suggestion=suggestion,
            follow_up=follow_up,
        ),
    )
