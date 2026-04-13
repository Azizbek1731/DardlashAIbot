"""
DardlashAI — Hissiy Qo'llab-quvvatlash Chat API (v5 — Gemini Pipeline)

Oqim:
1. Foydalanuvchi matni + kamera hissiyoti keladi
2. ML model matnni klassifikatsiya qiladi (normal / stress / high_risk)
3. 4-qatlamli Gemini Pipeline:
   → Layer 1: Analysis (emotion, intent, context, severity)
   → Layer 2: Protocol Response (draft)
   → Layer 3: Polish (natural Uzbek)
   → Layer 4: Safety Validation
4. Edge-TTS audio yaratadi
5. Hammasi frontendga qaytariladi
"""

import sys
import uuid
import logging
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional
from pathlib import Path

# Loyiha ildizini sys.path ga qo'shish (model/ papkani import qilish uchun)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.pipeline import get_pipeline
from ai.prompt import VALID_EMOTIONS, EMOTION_EMOJIS, EMOTION_LABELS_UZ
from tts import generate_audio_bytes, list_available_voices, AUDIO_DIR

# ML model import — xavfsiz tarzda (model train bo'lmagan bo'lishi mumkin)
_ml_model_available = False
_ml_predict = None

try:
    from model.inference import predict as ml_predict
    _ml_predict = ml_predict
    _ml_model_available = True
except Exception as e:
    logging.warning(f"ML model yuklanmadi (train qiling): {e}")

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("dardlash.api")

# ─── Ilova sozlamalari ────────────────────────────────────────────────────────

app = FastAPI(
    title="DardlashAI",
    description="Hissiy qo'llab-quvvatlash AI — 4-qatlamli Gemini Pipeline + ML + Edge-TTS",
    version="5.0.0",
)

# CORS — frontendga ulanishga ruxsat
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── So'rov / Javob modellari ────────────────────────────────────────────────

class ChatRequest(BaseModel):
    user_text: str = Field(..., min_length=1, max_length=2000, description="Foydalanuvchi xabari")
    emotion: str = Field(..., description="Aniqlangan hissiyot (kameradan)")

class ChatResponse(BaseModel):
    response: str
    emotion_received: str
    emotion_label: str
    emoji: str
    audio_url: Optional[str] = None
    # ML model natijalari
    risk_level: Optional[str] = None
    risk_confidence: Optional[float] = None
    ml_available: bool = False
    # Pipeline metadata
    detected_emotion: Optional[str] = None
    detected_intent: Optional[str] = None
    context: Optional[str] = None
    severity: Optional[str] = None
    strategy_used: Optional[str] = None
    safety_passed: Optional[bool] = None
    layers_completed: Optional[list[str]] = None
    fallback_used: Optional[bool] = None


# ─── WebSocket va Asosiy Chat Mantiqi ────────────────────────────────────────

# WebSocket menejeri
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

manager = ConnectionManager()

async def process_chat_logic(user_text: str, emotion_raw: str) -> dict:
    """Asosiy chat mantiqi (HTTP guruh va WebSocket uchun umumiy)."""
    emotion = emotion_raw.lower().strip()
    if emotion not in VALID_EMOTIONS:
        emotion = "neutral"

    user_text = user_text.strip()

    # QADAM 1: ML model
    risk_level = None
    risk_confidence = None
    if _ml_model_available and _ml_predict:
        try:
            ml_result = _ml_predict(user_text)
            risk_level = ml_result.get("label", None)
            risk_confidence = ml_result.get("confidence", None)
        except Exception as e:
            logger.error(f"ML model xatosi: {e}")

    # QADAM 2: 4-qatlamli Gemini Pipeline
    pipeline = get_pipeline()
    pipeline_result = await pipeline.process(
        user_text=user_text,
        camera_emotion=emotion,
        risk_level=risk_level,
    )

    response_text = pipeline_result.final_response

    # QADAM 3: Edge-TTS
    audio_url = None
    try:
        audio_bytes = await generate_audio_bytes(response_text)
        if audio_bytes:
            file_id = uuid.uuid4().hex[:12]
            filename = f"response_{file_id}.mp3"
            filepath = AUDIO_DIR / filename
            filepath.write_bytes(audio_bytes)
            audio_url = f"/audio/{filename}"
    except Exception as e:
        logger.error(f"TTS xatolik: {e}")

    # Pipeline hissiyotiga mos emojini tanlash
    pipeline_emotion = pipeline_result.detected_emotion
    emoji_map = {
        "neutral": "😊", "happy": "😄", "sad": "😢",
        "anxious": "😰", "tired": "😴", "overwhelmed": "😵",
        "lonely": "🥺",
    }
    emoji = emoji_map.get(pipeline_emotion, EMOTION_EMOJIS.get(emotion, "😊"))
    emotion_label = EMOTION_LABELS_UZ.get(emotion, emotion)

    return {
        "response": response_text,
        "emotion_received": emotion,
        "emotion_label": emotion_label,
        "emoji": emoji,
        "audio_url": audio_url,
        "risk_level": risk_level,
        "risk_confidence": risk_confidence,
        "ml_available": _ml_model_available,
        "detected_emotion": pipeline_result.detected_emotion,
        "detected_intent": pipeline_result.detected_intent,
        "context": pipeline_result.context,
        "severity": pipeline_result.severity,
        "strategy_used": pipeline_result.strategy_used,
        "safety_passed": pipeline_result.safety_passed,
        "layers_completed": pipeline_result.layers_completed,
        "fallback_used": pipeline_result.fallback_used,
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Eski HTTP endpoint — asosiy mantiqni chaqiradi."""
    result_dict = await process_chat_logic(request.user_text, request.emotion)
    return ChatResponse(**result_dict)


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    Yangi WebSocket endpoint.
    Frontenddan JSON kutadi: {"user_text": "...", "emotion": "..."}
    Xuddi shu ChatResponse strukturasi JSON formatida qaytariladi.
    """
    await manager.connect(websocket)
    logger.info("WebSocket: Yangi klent ulandi.")
    try:
        while True:
            # 1. Klijentdan xabar kutish
            data = await websocket.receive_json()
            user_text = data.get("user_text", "")
            emotion = data.get("emotion", "neutral")

            if not user_text.strip():
                continue

            if user_text == "[PROACTIVE_EMOTION_TRIGGER]":
                emo_label = EMOTION_LABELS_UZ.get(emotion, emotion).lower()
                user_text = f"Mening yuzimda {emo_label} sezilyapti. Iltimos, mendan yumshoqlik bilan 'tinchlikmi, nima bo'ldi?' deb hol-ahvol so'rang."
                logger.info(f"WebSocket: Proактив hissiyot trigeri: {emotion}")
            else:
                logger.info(f"WebSocket: Xabar keldi -> matn: {user_text[:20]}..., hissiyot: {emotion}")

            # 2. Jariyonni ishga tushirish
            result_dict = await process_chat_logic(user_text, emotion)

            # 3. Natijani qaytarish
            await websocket.send_json(result_dict)
            logger.info("WebSocket: Javob yuborildi.")

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket: Klient uzildi.")
    except Exception as e:
        logger.error(f"WebSocket Xatolik: {e}")
        manager.disconnect(websocket)


# ─── ML model predict endpoint ──────────────────────────────────────────────

class PredictRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)

class PredictResponse(BaseModel):
    label: str
    confidence: float
    response: str
    probabilities: Optional[dict] = None

@app.post("/predict", response_model=PredictResponse)
async def predict_endpoint(request: PredictRequest):
    """ML model orqali matnni klassifikatsiya qilish."""
    if not _ml_model_available or not _ml_predict:
        raise HTTPException(
            status_code=503,
            detail=(
                "ML model yuklanmagan. Avval modelni train qiling:\n"
                "  cd d:\\DardlashAI\n"
                "  python -m model.train"
            ),
        )

    result = _ml_predict(request.text)
    return PredictResponse(**result)


# ─── Qo'shimcha endpointlar ──────────────────────────────────────────────────

@app.get("/conversation")
async def get_conversation():
    """Joriy suhbat xulosasini olish."""
    pipeline = get_pipeline()
    return pipeline.get_conversation_summary()


@app.post("/reset")
async def reset_conversation():
    """Suhbat xotirasini tozalash."""
    pipeline = get_pipeline()
    pipeline.clear_memory()
    return {"message": "Suhbat xotirasi tozalandi."}


@app.get("/emotions")
async def list_emotions():
    """Barcha hissiyotlar ro'yxati."""
    return {
        "emotions": [
            {
                "name": e,
                "label": EMOTION_LABELS_UZ.get(e, e),
                "emoji": EMOTION_EMOJIS.get(e, "😊"),
            }
            for e in VALID_EMOTIONS
        ]
    }


@app.get("/tts/voices")
async def get_tts_voices():
    """TTS ovozlari."""
    voices = list_available_voices()
    return {"voices": voices}


@app.get("/health")
async def health_check():
    from ai.gemini_client import is_available as gemini_available
    return {
        "status": "healthy",
        "service": "DardlashAI",
        "version": "5.0.0",
        "pipeline": "4-layer-gemini",
        "gemini_api": "connected" if gemini_available() else "not_configured",
        "ml_model": "loaded" if _ml_model_available else "not_available",
        "tts": "edge-tts",
    }


# ─── Static va Frontend xizmat ko'rsatish ─────────────────────────────────────

BACKEND_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BACKEND_DIR.parent / "frontend"

# Audio papkani mount qilish (TTS fayllar uchun)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/audio", StaticFiles(directory=str(AUDIO_DIR)), name="audio")

# Frontend mount qilish
if FRONTEND_DIR.is_dir():
    @app.get("/")
    async def serve_frontend():
        return FileResponse(str(FRONTEND_DIR / "index.html"))

    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
