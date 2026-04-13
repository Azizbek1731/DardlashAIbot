"""
AI Javob Modeli — qo'llab-quvvatlovchi javoblar yaratadi.

Har bir hissiyot uchun turli ochilish, maslahat va davom savollari
bilan ishlaydi. Kontekstni tushunadi (ish, o'qish, munosabat va h.k.)
va suhbat xotirasini saqlaydi.

To'liq o'zbek tilida.
"""

import random
from typing import Optional
from ai.prompt import EMOTION_STRATEGIES, VALID_EMOTIONS
from ai.safety import ensure_safe_output


class EmotionalSupportModel:
    """Foydalanuvchi matni va hissiyotiga asoslangan xavfsiz, qo'llab-quvvatlovchi javoblar yaratadi."""

    def __init__(self):
        # Oddiy suhbat xotirasi — oxirgi N ta suhbatni saqlaydi
        self.memory: list[dict] = []
        self.max_memory = 10

    def generate_response(
        self,
        user_text: str,
        emotion: str,
        conversation_id: Optional[str] = None,
    ) -> str:
        """
        Qo'llab-quvvatlovchi javob yaratadi.

        Args:
            user_text: Foydalanuvchi xabari
            emotion: Aniqlangan hissiyot (VALID_EMOTIONS ichida bo'lishi kerak)
            conversation_id: Ixtiyoriy sessiya ID

        Returns:
            Xavfsiz, qo'llab-quvvatlovchi javob matni
        """
        # Hissiyotni normalizatsiya qilish
        emotion = emotion.lower().strip()
        if emotion not in VALID_EMOTIONS:
            emotion = "neutral"

        strategy = EMOTION_STRATEGIES[emotion]

        # Xilma-xillik uchun tasodifiy komponentlar tanlash
        opener = random.choice(strategy["openers"])
        suggestion = random.choice(strategy["suggestions"])
        follow_up = random.choice(strategy["follow_ups"])

        # Kontekstga asoslangan javob qurish
        response_parts = []

        # Foydalanuvchi aytgan narsalardan kontekst ajratib olish
        contextual = self._extract_context(user_text, emotion)
        if contextual:
            response_parts.append(contextual)
        else:
            response_parts.append(opener)

        # Amaliy maslahat qo'shish
        response_parts.append(suggestion)

        # Davom ettiruvchi savol qo'shish (agar bo'lsa)
        if follow_up:
            response_parts.append(follow_up)

        response = " ".join(response_parts)

        # Xavfsizlik filtridan o'tkazish
        response = ensure_safe_output(response)

        # Xotiraga saqlash
        self._store_memory(user_text, emotion, response)

        return response

    def _extract_context(self, user_text: str, emotion: str) -> Optional[str]:
        """
        Foydalanuvchi matnidan kontekst ajratib olishga harakat qiladi,
        shunda javob shaxsiylashtirilgan va shablonli bo'lmaydi.
        """
        text_lower = user_text.lower()

        # Ishga oid stress
        if any(w in text_lower for w in ["ish", "job", "boss", "rahbar", "direktor", "ofis", "office",
                                          "deadline", "loyiha", "project", "yig'ilish", "meeting",
                                          "hamkasb", "ishxona", "maosh"]):
            if emotion in ("anxious", "fearful"):
                return "Ish bosimi ba'zan juda kuchli bo'ladi va bundan bezovta bo'lish tabiiy."
            elif emotion in ("tired",):
                return "Ish haqiqatan charchatadi va o'zingizga dam berish juda muhim."
            elif emotion in ("sad",):
                return "Ish bilan bog'liq qiyinchiliklar og'ir tushadi. His-tuyg'ularingiz to'liq o'rinli."
            elif emotion in ("angry",):
                return "Ishda g'azablantiruvchi holatlar bo'ladi. Bu hisni his qilishga haqqingiz bor."

        # Munosabatlarga oid
        if any(w in text_lower for w in ["do'st", "oila", "ota", "ona", "aka", "uka", "opa", "singil",
                                          "turmush", "sevgi", "yolg'iz", "yolg'izlik", "partner",
                                          "friend", "family", "lonely", "alone", "er", "xotin"]):
            if emotion in ("sad",):
                return "Munosabatlar chuqur his-tuyg'ularni uyg'otadi. Bu haqda his qilayotganlaringiz mutlaqo tabiiy."
            elif emotion in ("anxious", "fearful"):
                return "Yaqin odamlar haqida tashvishlanish — bu ularni qanchalik qadrashingizning belgisi."
            elif emotion in ("angry",):
                return "Yaqin odamlar bilan muammo bo'lganda g'azab his qilish — bu tabiiy."

        # Uyqu bilan bog'liq
        if any(w in text_lower for w in ["uxla", "uyqu", "insomnia", "uxlay olma", "tong",
                                          "tun", "charchagan", "sleep", "exhausted", "toliq"]):
            return "Yetarli dam olmaslik hamma narsaga ta'sir qiladi. O'zingizga yumshoq bo'ling."

        # O'qish/ta'lim bilan bog'liq
        if any(w in text_lower for w in ["o'qi", "maktab", "universitet", "imtihon", "test",
                                          "uy vazifa", "baho", "talaba", "stipendiya",
                                          "school", "exam", "study", "college", "kurs"]):
            if emotion in ("anxious", "fearful"):
                return "O'qish bosimi katta bo'lishi mumkin, lekin esda tuting — bir qadam, bir qadam."
            elif emotion in ("tired",):
                return "O'qish ko'p kuch oladi. Dam olib, yangilanib qaytishda hech qanday ayb yo'q."
            elif emotion in ("sad",):
                return "O'qishdagi qiyinchiliklar kayfiyatga ta'sir qiladi. Siz yolg'iz emassiz bu yo'lda."

        # Pul va moliyaviy muammolar
        if any(w in text_lower for w in ["pul", "moliya", "qarz", "maosh", "ish haqi",
                                          "money", "financial", "debt", "payment", "to'lov"]):
            return "Moliyaviy tashvishlar juda og'ir bo'lishi mumkin. Bu haqda gapirishning o'zi allaqachon qadamdir."

        # Sog'liq
        if any(w in text_lower for w in ["kasal", "og'ri", "bosh", "kasalxona", "vrach",
                                          "dard", "sog'liq", "sick", "pain", "health"]):
            return "Sog'liq bilan bog'liq tashvishlar juda qiyin. O'zingizga g'amxo'rlik qilayotganingiz yaxshi."

        # Tiqilib qolish hissi
        if any(w in text_lower for w in ["tiqil", "yo'l yo'q", "bilma", "tushunma",
                                          "umidsiz", "ma'nosiz", "stuck", "lost",
                                          "confused", "hopeless", "nimaga", "nega"]):
            return "Tiqilib qolish hissi eng og'ir joylardan biri, lekin bu siz doim shu yerda qolasiz degani emas."

        # Suhbat xotirasidan kontekst tekshirish
        if self.memory:
            last = self.memory[-1]
            if last["emotion"] == emotion and emotion in ("sad", "anxious", "fearful", "angry"):
                return "Ko'ryapmanki, hali ham shu hisni boshdan kechirayapsiz. Men hali ham siz bilan birgaman."

        return None

    def _store_memory(self, user_text: str, emotion: str, response: str):
        """Suhbatni oddiy xotiraga saqlash."""
        self.memory.append({
            "user_text": user_text,
            "emotion": emotion,
            "response": response,
        })
        # Maksimal xotira hajmini saqlash
        if len(self.memory) > self.max_memory:
            self.memory = self.memory[-self.max_memory:]

    def get_conversation_summary(self) -> dict:
        """Suhbat xulosa qaytarish."""
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


# Singleton nusxa
_model_instance: Optional[EmotionalSupportModel] = None


def get_model() -> EmotionalSupportModel:
    """Model singletonini olish yoki yaratish."""
    global _model_instance
    if _model_instance is None:
        _model_instance = EmotionalSupportModel()
    return _model_instance
