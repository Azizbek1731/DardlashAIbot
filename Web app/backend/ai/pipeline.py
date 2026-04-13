"""
DardlashAI — Pipeline Orchestrator

4 qatlamli hissiy qo'llab-quvvatlash pipeline:

  User Input
    → Layer 1: Gemini Analysis (emotion, intent, context, severity)
    → Layer 2: Protocol Model (draft response)
    → Layer 3: Gemini Polish (natural Uzbek text)
    → Layer 4: Safety Validator (final check)
    → Final Response

Har bir qatlam mustaqil fallback ga ega.
Agar BARCHA qatlamlar ishlamasa — hardcoded xavfsiz javob qaytariladi.
"""

import logging
from typing import Optional

from ai.schemas import AnalysisResult, ProtocolResult, SafetyResult, PipelineResult
from ai.layer_analysis import analyze
from ai.layer_protocol import generate_protocol_response
from ai.layer_polish import polish
from ai.safety import validate_safety

logger = logging.getLogger("dardlash.pipeline")

# Oxirgi chora — agar HAMMA narsa ishlamasa
ULTIMATE_FALLBACK = (
    "Sizni tinglayapman va bo'lishganingiz uchun rahmat. "
    "Gaplashmoqchi bo'lsangiz, men doim shu yerdaman. 💛"
)


class EmotionalSupportPipeline:
    """
    4 qatlamli hissiy qo'llab-quvvatlash pipeline.

    Har bir qatlam:
    1. Gemini orqali ishga tushadi
    2. Xatolik bo'lsa — o'z fallbacki ishlaydi
    3. Natijani keyingi qatlamga uzatadi

    Ishlatish:
        pipeline = EmotionalSupportPipeline()
        result = await pipeline.process("Bugun juda charchadim", "tired")
    """

    def __init__(self):
        # Suhbat xotirasi — oxirgi N ta suhbat
        self.memory: list[dict] = []
        self.max_memory = 15

    async def process(
        self,
        user_text: str,
        camera_emotion: str = "neutral",
        risk_level: Optional[str] = None,
    ) -> PipelineResult:
        """
        To'liq pipeline ni ishga tushiradi.

        Args:
            user_text: Foydalanuvchi xabari
            camera_emotion: Kameradan aniqlangan hissiyot
            risk_level: ML model dan kelgan xavf darajasi (ixtiyoriy)

        Returns:
            PipelineResult — to'liq natija
        """
        layers_completed = []
        fallback_used = False

        logger.info(f"{'═' * 60}")
        logger.info(f"Pipeline START | matn: \"{user_text[:60]}...\"")
        logger.info(f"{'═' * 60}")

        try:
            # ═══════════════════════════════════════════════════════
            # LAYER 1: ANALYSIS
            # ═══════════════════════════════════════════════════════
            logger.info("📊 Layer 1: Analysis...")
            analysis = await analyze(user_text, camera_emotion)
            layers_completed.append("analysis")

            # ML model xavf darajasini pipeline ga moslashtirish
            if risk_level == "high_risk":
                analysis.severity = "high"
                if analysis.emotion in ("neutral", "happy"):
                    analysis.emotion = "sad"
            elif risk_level == "stress" and analysis.severity == "low":
                analysis.severity = "moderate"

            # ═══════════════════════════════════════════════════════
            # LAYER 2: PROTOCOL RESPONSE
            # ═══════════════════════════════════════════════════════
            logger.info("📝 Layer 2: Protocol Response...")
            protocol = await generate_protocol_response(user_text, analysis)
            layers_completed.append("protocol")

            draft = protocol.draft_response
            if not draft:
                draft = ULTIMATE_FALLBACK
                fallback_used = True

            # ═══════════════════════════════════════════════════════
            # LAYER 3: POLISH
            # ═══════════════════════════════════════════════════════
            logger.info("✨ Layer 3: Polish...")
            polished = await polish(draft, analysis)
            layers_completed.append("polish")

            if not polished:
                polished = draft

            # ═══════════════════════════════════════════════════════
            # LAYER 4: SAFETY VALIDATION
            # ═══════════════════════════════════════════════════════
            logger.info("🛡️ Layer 4: Safety...")
            safety = await validate_safety(polished)
            layers_completed.append("safety")

            final_text = safety.corrected_text if safety.corrected_text else polished

            # high_risk uchun xavfsizlik xabari qo'shish
            if risk_level == "high_risk" or analysis.severity == "high":
                final_text += (
                    "\n\n⚠️ Sizning xavfsizligingiz eng muhim narsa. "
                    "Iltimos, ishonchli odamingizga yoki mutaxassisga murojaat qiling. "
                    "Siz yolg'iz emassiz va yordam mavjud. "
                    "📞 Ishonch telefoni: 1199"
                )

            # Xotiraga saqlash
            self._store_memory(user_text, analysis, final_text)

            logger.info(f"{'═' * 60}")
            logger.info(
                f"Pipeline DONE ✅ | layers={layers_completed} | "
                f"fallback={fallback_used} | safe={safety.is_safe}"
            )
            logger.info(f"{'═' * 60}")

            return PipelineResult(
                final_response=final_text,
                detected_emotion=analysis.emotion,
                detected_intent=analysis.intent,
                context=analysis.context,
                severity=analysis.severity,
                strategy_used=protocol.strategy_used,
                tone=protocol.tone,
                safety_passed=safety.is_safe,
                safety_violations=safety.violations,
                layers_completed=layers_completed,
                fallback_used=fallback_used,
            )

        except Exception as e:
            logger.error(f"Pipeline CRITICAL ERROR: {e}", exc_info=True)

            return PipelineResult(
                final_response=ULTIMATE_FALLBACK,
                detected_emotion="neutral",
                detected_intent="wants_emotional_support",
                context="general",
                severity="low",
                strategy_used="fallback",
                tone="warm_supportive",
                safety_passed=True,
                safety_violations=[],
                layers_completed=layers_completed,
                fallback_used=True,
            )

    # ═══════════════════════════════════════════════════════════════════════
    # SUHBAT XOTIRASI
    # ═══════════════════════════════════════════════════════════════════════

    def _store_memory(
        self,
        user_text: str,
        analysis: AnalysisResult,
        response: str,
    ):
        """Suhbatni xotiraga saqlash."""
        self.memory.append({
            "user_text": user_text,
            "emotion": analysis.emotion,
            "intent": analysis.intent,
            "response": response,
        })
        if len(self.memory) > self.max_memory:
            self.memory = self.memory[-self.max_memory:]

    def get_conversation_summary(self) -> dict:
        """Suhbat xulosasi."""
        if not self.memory:
            return {"turns": 0, "emotions": [], "summary": "Hali suhbat boshlanmagan."}

        emotions = [m["emotion"] for m in self.memory]
        return {
            "turns": len(self.memory),
            "emotions": emotions,
            "dominant_emotion": max(set(emotions), key=emotions.count),
            "summary": f"{len(self.memory)} ta xabar almashilgan suhbat.",
        }

    def clear_memory(self):
        """Suhbat xotirasini tozalash."""
        self.memory = []


# ═══════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════

_pipeline_instance: Optional[EmotionalSupportPipeline] = None


def get_pipeline() -> EmotionalSupportPipeline:
    """Pipeline singletonini olish yoki yaratish."""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = EmotionalSupportPipeline()
    return _pipeline_instance
