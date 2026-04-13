"""
DardlashAI — Model Inference Moduli

Saqlangan modelni yuklaydi va bashorat qiladi.
3 ta kategoriya: normal, stress, high_risk

Ishlatish:
    from model.inference import predict
    result = predict("I feel so stressed about everything")
    print(result)
    # {'label': 'stress', 'confidence': 0.91, 'response': '...'}

Yoki to'g'ridan-to'g'ri terminalda test:
    cd d:\\DardlashAI
    python -m model.inference
"""

import torch
import json
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# ═══════════════════════════════════════════════════════════════════════
# SOZLAMALAR
# ═══════════════════════════════════════════════════════════════════════

MODEL_DIR = Path(__file__).resolve().parent / "saved_model"
MAX_LENGTH = 256

# Label xaritalari
ID2LABEL = {0: "normal", 1: "stress", 2: "high_risk"}
LABEL2ID = {"normal": 0, "stress": 1, "high_risk": 2}

# ═══════════════════════════════════════════════════════════════════════
# XAVFSIZ JAVOBLAR
# ═══════════════════════════════════════════════════════════════════════

RESPONSES = {
    "normal": (
        "Sizni tinglayapman. Yana nima aytmoqchi bo'lsangiz — men shu yerdaman. 😊"
    ),
    "stress": (
        "Ko'rinib turibdiki, hozir sizga og'ir. Siz yolg'iz emassiz — "
        "va bu hislarni boshdan kechirayotganingiz tabiiy. "
        "Bir nafas oling va o'zingizga vaqt bering. 💛"
    ),
    "high_risk": (
        "⚠️ Sizning xavfsizligingiz eng muhim narsa. "
        "Iltimos, hozir ishonchli odamingizga yoki mutaxassisga murojaat qiling. "
        "Siz yolg'iz emassiz va yordam mavjud.\n\n"
        "📞 Ishonch telefoni: 1199 (O'zbekiston)\n"
        "📞 Yordamchi xizmat: +998 71 233-36-14"
    ),
}

# ═══════════════════════════════════════════════════════════════════════
# MODEL YUKLASH (SINGLETON — FAQAT BIR MARTA YUKLANADI)
# ═══════════════════════════════════════════════════════════════════════

_model = None
_tokenizer = None


def _load_model():
    """Modelni xotiraga yuklash. Faqat birinchi marta chaqirilganda ishlaydi."""
    global _model, _tokenizer

    if _model is not None:
        return  # Allaqachon yuklangan

    if not MODEL_DIR.exists():
        raise FileNotFoundError(
            f"Model topilmadi: {MODEL_DIR}\n"
            f"Avval modelni train qiling:\n"
            f"  cd d:\\DardlashAI\n"
            f"  python -m model.train"
        )

    print(f"🧠 Model yuklanmoqda: {MODEL_DIR}")

    _tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR))
    _model = AutoModelForSequenceClassification.from_pretrained(str(MODEL_DIR))
    _model.eval()  # Inference rejimiga o'tkazish

    # Label xaritasini yuklash (agar mavjud bo'lsa)
    config_path = MODEL_DIR / "label_config.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            global ID2LABEL, LABEL2ID
            ID2LABEL = {int(k): v for k, v in config["id2label"].items()}
            LABEL2ID = config["label2id"]

    print(f"   ✅ Model yuklandi!")


# ═══════════════════════════════════════════════════════════════════════
# BASHORAT
# ═══════════════════════════════════════════════════════════════════════

def predict(text: str) -> dict:
    """
    Matnni klassifikatsiya qiladi va xavfsiz javob qaytaradi.

    Args:
        text: Foydalanuvchi xabari

    Returns:
        dict: {
            "label": "stress",
            "confidence": 0.91,
            "response": "qo'llab-quvvatlovchi matn"
        }
    """
    # Model yuklash (agar yuklanmagan bo'lsa)
    _load_model()

    # Matnni tozalash
    text = text.strip()
    if not text:
        return {
            "label": "normal",
            "confidence": 1.0,
            "response": RESPONSES["normal"],
        }

    # Tokenizatsiya
    inputs = _tokenizer(
        text,
        padding="max_length",
        truncation=True,
        max_length=MAX_LENGTH,
        return_tensors="pt",
    )

    # Bashorat (gradient hisoblash kerak emas)
    with torch.no_grad():
        outputs = _model(**inputs)
        logits = outputs.logits

    # Softmax bilan ehtimolliklar
    probs = torch.softmax(logits, dim=-1)
    confidence, predicted_class = torch.max(probs, dim=-1)

    label_id = predicted_class.item()
    label = ID2LABEL.get(label_id, "normal")
    conf = round(confidence.item(), 4)

    # Barcha sinf ehtimolliklari
    all_probs = {
        ID2LABEL[i]: round(probs[0][i].item(), 4)
        for i in range(len(ID2LABEL))
    }

    return {
        "label": label,
        "confidence": conf,
        "response": RESPONSES.get(label, RESPONSES["normal"]),
        "probabilities": all_probs,
    }


# ═══════════════════════════════════════════════════════════════════════
# INTERACTIVE TEST
# ═══════════════════════════════════════════════════════════════════════

def interactive_test():
    """Terminalda interaktiv test."""
    print("=" * 60)
    print("  DardlashAI — Model Inference Test")
    print("  Chiqish uchun: 'exit' yoki 'q' yozing")
    print("=" * 60)

    # Test namunalari
    test_texts = [
        "I had a great day at work today",
        "I feel so stressed about my exams",
        "I don't want to live anymore",
        "Bugun oddiy kun bo'ldi",
        "Hamma narsadan bezildim bosim katta",
        "Hayotimda hech qanday ma'no yo'q",
    ]

    print("\n📋 Avtomatik test namunalari:")
    print("-" * 60)

    for text in test_texts:
        result = predict(text)
        emoji = {"normal": "🟢", "stress": "🟡", "high_risk": "🔴"}
        print(f"\n  Matn:     {text}")
        print(f"  Natija:   {emoji.get(result['label'], '⚪')} {result['label']} ({result['confidence']:.1%})")
        print(f"  Barcha:   {result['probabilities']}")

    print(f"\n{'=' * 60}")
    print("📝 Endi o'zingiz yozing:\n")

    while True:
        try:
            text = input("Siz: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not text or text.lower() in ("exit", "q", "quit", "chiqish"):
            print("\n👋 Xayr!")
            break

        result = predict(text)
        emoji = {"normal": "🟢", "stress": "🟡", "high_risk": "🔴"}
        print(f"\n  {emoji.get(result['label'], '⚪')} {result['label']} ({result['confidence']:.1%})")
        print(f"  📊 {result['probabilities']}")
        print(f"  💬 {result['response']}\n")


if __name__ == "__main__":
    interactive_test()
