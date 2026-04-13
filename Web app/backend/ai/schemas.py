"""
DardlashAI — Pipeline JSON Schemalar

Har bir pipeline qatlami uchun Pydantic modellari.
Gemini JSON javoblarini validatsiya qilish va tiplash uchun ishlatiladi.
"""

from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


# ═══════════════════════════════════════════════════════════════════════
# RUXSAT ETILGAN QIYMATLAR (Enums)
# ═══════════════════════════════════════════════════════════════════════

class Emotion(str, Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANXIOUS = "anxious"
    TIRED = "tired"
    OVERWHELMED = "overwhelmed"
    LONELY = "lonely"


class Intent(str, Enum):
    WANTS_EMOTIONAL_SUPPORT = "wants_emotional_support"
    WANTS_CALMING = "wants_calming"
    WANTS_ENCOURAGEMENT = "wants_encouragement"
    WANTS_TO_VENT = "wants_to_vent"
    WANTS_SMALL_PRACTICAL_HELP = "wants_small_practical_help"
    WANTS_CHECK_IN = "wants_check_in"


class Severity(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class Context(str, Enum):
    WORK = "work"
    STUDY = "study"
    RELATIONSHIP = "relationship"
    HEALTH = "health"
    FINANCIAL = "financial"
    SLEEP = "sleep"
    GENERAL = "general"


class Tone(str, Enum):
    WARM_SUPPORTIVE = "warm_supportive"
    GENTLE_CALMING = "gentle_calming"
    ENCOURAGING = "encouraging"
    EMPATHETIC = "empathetic"
    LIGHT_FRIENDLY = "light_friendly"


# ═══════════════════════════════════════════════════════════════════════
# LAYER 1: ANALYSIS RESULT (Gemini → JSON)
# ═══════════════════════════════════════════════════════════════════════

class AnalysisResult(BaseModel):
    """Layer 1 chiqishi: foydalanuvchi matnini tahlil qilish natijasi."""

    emotion: str = Field(
        default="neutral",
        description="Aniqlangan hissiyot: neutral, happy, sad, anxious, tired, overwhelmed, lonely"
    )
    intent: str = Field(
        default="wants_emotional_support",
        description="Foydalanuvchining maqsadi"
    )
    context: str = Field(
        default="general",
        description="Mavzu konteksti: work, study, relationship, health, financial, sleep, general"
    )
    severity: str = Field(
        default="low",
        description="Jiddiylik darajasi: low, moderate, high"
    )
    key_themes: list[str] = Field(
        default_factory=list,
        description="Asosiy mavzular ro'yxati"
    )


# ═══════════════════════════════════════════════════════════════════════
# LAYER 2: PROTOCOL RESULT (Custom Model → JSON)
# ═══════════════════════════════════════════════════════════════════════

class ResponseComponents(BaseModel):
    """Javob tarkibiy qismlari."""
    acknowledgment: str = Field(default="", description="Hissiyotni tan olish")
    validation: str = Field(default="", description="Hissiyotni tasdiqlash")
    suggestion: str = Field(default="", description="Amaliy maslahat")
    follow_up: str = Field(default="", description="Davom ettiruvchi savol")


class ProtocolResult(BaseModel):
    """Layer 2 chiqishi: protokol asosida yaratilgan javob."""

    draft_response: str = Field(
        default="",
        description="Qoralama javob matni"
    )
    strategy_used: str = Field(
        default="",
        description="Ishlatilgan strategiya nomi"
    )
    tone: str = Field(
        default="warm_supportive",
        description="Javob ohangi"
    )
    components: ResponseComponents = Field(
        default_factory=ResponseComponents,
        description="Javob tarkibiy qismlari"
    )


# ═══════════════════════════════════════════════════════════════════════
# LAYER 4: SAFETY RESULT (Validator → JSON)
# ═══════════════════════════════════════════════════════════════════════

class SafetyResult(BaseModel):
    """Layer 4 chiqishi: xavfsizlik tekshiruvi natijasi."""

    is_safe: bool = Field(
        default=True,
        description="Javob xavfsizmi?"
    )
    violations: list[str] = Field(
        default_factory=list,
        description="Topilgan buzilishlar ro'yxati"
    )
    corrected_text: str = Field(
        default="",
        description="Tuzatilgan matn (agar xavfsiz bo'lmasa)"
    )


# ═══════════════════════════════════════════════════════════════════════
# PIPELINE UMUMIY NATIJA
# ═══════════════════════════════════════════════════════════════════════

class PipelineResult(BaseModel):
    """Pipeline to'liq natijasi — frontendga qaytariladi."""

    # Asosiy javob
    final_response: str = Field(
        description="Yakuniy xavfsiz javob matni"
    )

    # Hissiyot ma'lumotlari
    detected_emotion: str = Field(default="neutral")
    detected_intent: str = Field(default="wants_emotional_support")
    context: str = Field(default="general")
    severity: str = Field(default="low")

    # Pipeline metadata
    strategy_used: str = Field(default="")
    tone: str = Field(default="warm_supportive")
    safety_passed: bool = Field(default=True)
    safety_violations: list[str] = Field(default_factory=list)

    # Qaysi qatlamlar ishladi
    layers_completed: list[str] = Field(default_factory=list)
    fallback_used: bool = Field(default=False)
