"""
DardlashAI — Mental Health Text Classification Model Training

DistilBERT asosida matn klassifikatsiya modeli.
3 ta kategoriya: normal (0), stress (1), high_risk (2)

Ishlatish:
    cd d:\\DardlashAI
    python -m model.train
"""

import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, classification_report

from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    EarlyStoppingCallback,
)
from datasets import Dataset

# ═══════════════════════════════════════════════════════════════════════
# SOZLAMALAR
# ═══════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).resolve().parent.parent  # d:\DardlashAI
DATA_PATH = BASE_DIR / "data" / "mental_health.csv"
MODEL_SAVE_DIR = BASE_DIR / "model" / "saved_model"
CHECKPOINT_DIR = BASE_DIR / "model" / "checkpoints"

# Model nomi — Hugging Face dan yuklanadi
BASE_MODEL = "distilbert-base-uncased"

# Label xaritasi
LABEL2ID = {"normal": 0, "stress": 1, "high_risk": 2}
ID2LABEL = {0: "normal", 1: "stress", 2: "high_risk"}

# Training parametrlari
NUM_EPOCHS = 3
BATCH_SIZE = 8
LEARNING_RATE = 2e-5
MAX_LENGTH = 256
WARMUP_STEPS = 50
WEIGHT_DECAY = 0.01
TEST_SIZE = 0.2
RANDOM_SEED = 42


# ═══════════════════════════════════════════════════════════════════════
# 1. DATASETNI YUKLASH VA TAYYORLASH
# ═══════════════════════════════════════════════════════════════════════

def load_dataset():
    """CSV fayldan datasetni yuklash va tozalash."""
    print(f"\n📂 Dataset yuklanyapti: {DATA_PATH}")

    if not DATA_PATH.exists():
        print(f"❌ XATO: {DATA_PATH} fayli topilmadi!")
        print("   Avval data/mental_health.csv faylini yarating.")
        sys.exit(1)

    df = pd.read_csv(DATA_PATH)
    print(f"   Jami qatorlar: {len(df)}")

    # Bo'sh qatorlarni olib tashlash
    df = df.dropna(subset=["text", "label"])
    df["text"] = df["text"].astype(str).str.strip()
    df["label"] = df["label"].astype(str).str.strip().str.lower()

    # Faqat to'g'ri labellarni saqlash
    valid_labels = set(LABEL2ID.keys())
    invalid = df[~df["label"].isin(valid_labels)]
    if len(invalid) > 0:
        print(f"   ⚠️ {len(invalid)} ta noto'g'ri label topildi, olib tashlandi")
        df = df[df["label"].isin(valid_labels)]

    # Labellarni raqamga o'tkazish
    df["label"] = df["label"].map(LABEL2ID)

    print(f"   Tozalangan qatorlar: {len(df)}")
    print(f"   Label taqsimoti:")
    for label_name, label_id in LABEL2ID.items():
        count = len(df[df["label"] == label_id])
        print(f"     {label_name} ({label_id}): {count} ta")

    return df


def split_dataset(df):
    """Datasetni train va test ga bo'lish (80/20)."""
    train_df, test_df = train_test_split(
        df,
        test_size=TEST_SIZE,
        random_state=RANDOM_SEED,
        stratify=df["label"],  # Har bir sinf uchun teng taqsimot
    )

    print(f"\n📊 Dataset bo'linishi:")
    print(f"   Train: {len(train_df)} ta")
    print(f"   Test:  {len(test_df)} ta")

    return train_df, test_df


# ═══════════════════════════════════════════════════════════════════════
# 2. TOKENIZATSIYA
# ═══════════════════════════════════════════════════════════════════════

def tokenize_data(train_df, test_df):
    """DistilBERT tokenizer bilan matnlarni tokenizatsiya qilish."""
    print(f"\n🔤 Tokenizer yuklanyapti: {BASE_MODEL}")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)

    def tokenize_function(examples):
        return tokenizer(
            examples["text"],
            padding="max_length",
            truncation=True,
            max_length=MAX_LENGTH,
        )

    # Pandas DataFrame -> Hugging Face Dataset
    train_dataset = Dataset.from_pandas(train_df[["text", "label"]].reset_index(drop=True))
    test_dataset = Dataset.from_pandas(test_df[["text", "label"]].reset_index(drop=True))

    print("   Train tokenizatsiya...")
    train_dataset = train_dataset.map(tokenize_function, batched=True)

    print("   Test tokenizatsiya...")
    test_dataset = test_dataset.map(tokenize_function, batched=True)

    # PyTorch format
    train_dataset.set_format("torch", columns=["input_ids", "attention_mask", "label"])
    test_dataset.set_format("torch", columns=["input_ids", "attention_mask", "label"])

    print(f"   ✅ Tokenizatsiya tugadi")

    return tokenizer, train_dataset, test_dataset


# ═══════════════════════════════════════════════════════════════════════
# 3. MODEL YARATISH
# ═══════════════════════════════════════════════════════════════════════

def create_model():
    """DistilBERT klassifikatsiya modelini yaratish."""
    print(f"\n🧠 Model yuklanyapti: {BASE_MODEL}")

    model = AutoModelForSequenceClassification.from_pretrained(
        BASE_MODEL,
        num_labels=3,
        id2label=ID2LABEL,
        label2id=LABEL2ID,
    )

    # Parametrlar sonini ko'rsatish
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"   Jami parametrlar:     {total_params:,}")
    print(f"   O'qitiladigan:        {trainable_params:,}")

    return model


# ═══════════════════════════════════════════════════════════════════════
# 4. METRIKALAR
# ═══════════════════════════════════════════════════════════════════════

def compute_metrics(eval_pred):
    """Training jarayonida accuracy, precision, recall, f1 hisoblash."""
    predictions, labels = eval_pred
    preds = np.argmax(predictions, axis=-1)

    accuracy = accuracy_score(labels, preds)
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, preds, average="weighted"
    )

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


# ═══════════════════════════════════════════════════════════════════════
# 5. TRAINING (ASOSIY JARAYON)
# ═══════════════════════════════════════════════════════════════════════

def train():
    """To'liq training jarayoni."""
    print("=" * 60)
    print("  DardlashAI — Model Training")
    print("  DistilBERT Text Classification")
    print("=" * 60)

    # 1. Dataset yuklash
    df = load_dataset()

    # 2. Train/Test split
    train_df, test_df = split_dataset(df)

    # 3. Tokenizatsiya
    tokenizer, train_dataset, test_dataset = tokenize_data(train_df, test_df)

    # 4. Model yaratish
    model = create_model()

    # 5. Training sozlamalari
    print(f"\n⚙️ Training sozlamalari:")
    print(f"   Epochs:         {NUM_EPOCHS}")
    print(f"   Batch size:     {BATCH_SIZE}")
    print(f"   Learning rate:  {LEARNING_RATE}")
    print(f"   Max length:     {MAX_LENGTH}")
    print(f"   Warmup steps:   {WARMUP_STEPS}")

    training_args = TrainingArguments(
        output_dir=str(CHECKPOINT_DIR),
        num_train_epochs=NUM_EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        per_device_eval_batch_size=BATCH_SIZE,
        learning_rate=LEARNING_RATE,
        warmup_steps=WARMUP_STEPS,
        weight_decay=WEIGHT_DECAY,
        eval_strategy="epoch",
        save_strategy="epoch",
        logging_strategy="steps",
        logging_steps=10,
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        greater_is_better=True,
        save_total_limit=2,
        fp16=False,  # GPU bo'lmasa False
        report_to="none",  # wandb/tensorboard ishlatmaymiz
        seed=RANDOM_SEED,
    )

    # 6. Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=test_dataset,
        compute_metrics=compute_metrics,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
    )

    # 7. TRAINING BOSHLASH
    print(f"\n🚀 Training boshlandi...")
    print("-" * 60)

    train_result = trainer.train()

    print("-" * 60)
    print(f"\n✅ Training tugadi!")
    print(f"   Training loss:  {train_result.training_loss:.4f}")
    print(f"   Training vaqti: {train_result.metrics.get('train_runtime', 0):.1f} soniya")

    # 8. TEST NATIJLARI
    print(f"\n📈 Test natijalari:")
    eval_results = trainer.evaluate()
    for key, value in eval_results.items():
        if isinstance(value, float):
            print(f"   {key}: {value:.4f}")

    # 9. Batafsil classification report
    print(f"\n📋 Batafsil hisobot:")
    predictions = trainer.predict(test_dataset)
    preds = np.argmax(predictions.predictions, axis=-1)
    labels = predictions.label_ids

    report = classification_report(
        labels, preds,
        target_names=list(LABEL2ID.keys()),
        digits=4,
    )
    print(report)

    # 10. MODELNI SAQLASH
    print(f"\n💾 Model saqlanmoqda: {MODEL_SAVE_DIR}")
    MODEL_SAVE_DIR.mkdir(parents=True, exist_ok=True)

    trainer.save_model(str(MODEL_SAVE_DIR))
    tokenizer.save_pretrained(str(MODEL_SAVE_DIR))

    # Label xaritasini ham saqlash
    import json
    config_path = MODEL_SAVE_DIR / "label_config.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump({
            "label2id": LABEL2ID,
            "id2label": ID2LABEL,
        }, f, ensure_ascii=False, indent=2)

    print(f"   ✅ Model saqlandi!")
    print(f"   📁 Papka: {MODEL_SAVE_DIR}")
    print(f"\n{'=' * 60}")
    print(f"  Tayyor! Endi inference.py orqali test qilishingiz mumkin.")
    print(f"  python -m model.inference")
    print(f"{'=' * 60}\n")


# ═══════════════════════════════════════════════════════════════════════
# BOSHLASH
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    train()
