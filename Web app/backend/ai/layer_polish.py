"""
DardlashAI — Layer 3: Gemini Final Polish

Qoralama javobni tabiiy o'zbek tiliga jilolaydi (polish qiladi).
Noqulay iboralarni tuzatadi, ohangni yumshoqlashtiradi, 3-5 jumla
chegarasini saqlaydi.

Chiqish: str (faqat matn, JSON emas)
Fallback: qoralama javobni o'zini qaytarish
"""

import logging
from ai.gemini_client import call_gemini_text
from ai.schemas import AnalysisResult

logger = logging.getLogger("dardlash.layer3")

# ═══════════════════════════════════════════════════════════════════════
# GEMINI PROMPT
# ═══════════════════════════════════════════════════════════════════════

POLISH_PROMPT_TEMPLATE = """Sen o'zbek tilida yozilgan matnni jilolashga (polish) ixtisoslashgan tilshunos AI san.

Quyidagi qoralama javobni tabiiy, iliq va ravon o'zbek tiliga o'girib ber.

═══ QORALAMA JAVOB ═══
{draft_response}

═══ KONTEKST ═══
Hissiyot: {emotion}
Maqsad: {intent}

═══ QOIDALAR ═══
1. Ohang: ILIQ, samimiy, do'stona — yaqin do'st kabi
2. Uzunlik: 3-5 jumla. Agar qisqa bo'lsa — qisqa qolsin. Agar uzun bo'lsa — qisqartir
3. Til: sof o'zbek, lotin yozuvi, oddiy so'zlar
4. Noqulay jumlalarni tabiiy qilib yoz, robotdek eshitilmasin
5. Ma'noni o'zgartirma, faqat shaklini yaxshila
6. Yangi ma'lumot qo'shma, faqat mavjud matnni jilola
7. Birinchi jumla — hissiyotni tan olish bo'lsin
8. Oxirgi jumla — yumshoq savol yoki dalda bo'lsin

═══ TAQIQLAR ═══
❌ Diagnoz, dori, klinik iboralar qo'shma
❌ "Siz albatta..." yoki "siz hech qachon..." kabi kuchli da'volar qo'shma
❌ JSON qaytarma — FAQAT matn

FAQAT jilolangan matnni qaytar. Boshqa hech narsa yozma — tushuntirish, izoh, sarlavha bo'lmasin."""


# ═══════════════════════════════════════════════════════════════════════
# ASOSIY FUNKSIYA
# ═══════════════════════════════════════════════════════════════════════

async def polish(draft_response: str, analysis: AnalysisResult) -> str:
    """
    Layer 3: Qoralama javobni tabiiy o'zbek tiliga jilolaydi.

    Args:
        draft_response: Layer 2 dan kelgan qoralama javob
        analysis: Layer 1 tahlil natijasi (kontekst uchun)

    Returns:
        str — jilolangan matn (fallback: qoralama javobning o'zi)
    """
    if not draft_response:
        return ""

    prompt = POLISH_PROMPT_TEMPLATE.format(
        draft_response=draft_response,
        emotion=analysis.emotion,
        intent=analysis.intent,
    )

    polished = await call_gemini_text(prompt)

    if polished and len(polished) > 10:
        logger.info(
            f"Layer 3 ✅: Jilolandi "
            f"({len(draft_response)} → {len(polished)} belgi)"
        )
        return polished

    # Fallback — qoralama javobning o'zi
    logger.info("Layer 3 ⚠️: Fallback (qoralama javob)")
    return draft_response
