# -*- coding: utf-8 -*-
"""Telegram-бот поддержки: OpenAI, RAG (FAISS), многоязычные промпты."""
import tempfile
import logging
import os
import aiohttp
import time
import asyncio
import secrets
import io
import base64
from datetime import timedelta
from dotenv import load_dotenv
from cryptography.fernet import Fernet
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, User
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, PicklePersistence
from telegram.request import HTTPXRequest
from telegram.constants import ChatAction
from openai import AsyncOpenAI
from functools import wraps
from collections import deque
from enum import Enum
from typing import Dict, Any, Optional, Tuple, Deque, Callable, Awaitable
from pathlib import Path
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

BOT_VERSION = "2.2.0"

# ================= ENVIRONMENT VALIDATION =========================
if not os.path.exists('.env'):
    print("ОШИБКА: Файл .env не найден. Создайте его на основе .env.example.")
    exit(1)

load_dotenv()

# ================= LOGGING CONFIGURATION =========================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamStatusHandler() if hasattr(logging, "StreamStatusHandler") else logging.StreamHandler()
    ]
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# ================= CONSTANTS =========================
MAX_HISTORY_MESSAGES = 10
DEFAULT_LANG = "ru"
STREAM_EDIT_THROTTLE_SECONDS = 0.8
STREAM_CURSOR = " ▌"
FILE_DELETE_RETRIES = 3
FILE_DELETE_RETRY_DELAY = 0.2
SUMMARY_TRIGGER_COUNT = 5
SUMMARY_TIME_TRIGGER_SECONDS = 3600
CRISIS_MODE_COOLDOWN_SECONDS = 3600
USER_DATA_CLEANUP_HOURS = 24
USER_DATA_INACTIVE_DAYS = 30
# ПОВЫШЕННЫЕ ТАЙМАУТЫ ДЛЯ СТАБИЛЬНОСТИ
OPENAI_REQUEST_TIMEOUT = 90.0
FFMPEG_TIMEOUT = 45.0
FFMPEG_KILL_WAIT_TIMEOUT = 5.0
MAX_STREAM_CHUNKS = 1000
MAX_STREAM_SECONDS = 60
MAX_STREAM_TEXT_LEN = 4000
MUXLISA_AUDIO_SAMPLE_RATE = 16000
MAX_TTS_FILE_SIZE = 10 * 1024 * 1024
DEV_NOTIFICATION_DEDUP_SECONDS = 300
DEV_NOTIFICATIONS_MAX_SIZE = 10000
DEV_NOTIFICATIONS_CLEANUP_DAYS = 30

# Rate limiting
RATE_LIMIT_COUNT = 5
RATE_LIMIT_SECONDS = 60
RATE_LIMIT_COUNT_CRISIS = 25
WORD_LIMIT = 3000
AUDIO_LIMIT_SECONDS = 120

# Load environment variables with validation
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MUXLISA_API_TOKEN = os.getenv("MUXLISA_API_TOKEN")
DEVELOPER_CHAT_ID = os.getenv("DEVELOPER_CHAT_ID")
BOT_ACCESS_PASSWORD = os.getenv("BOT_ACCESS_PASSWORD")

try:
    SPEAKER_ID_RANGE = range(1, 11)
    speaker_id_from_env = int(os.getenv("MUXLISA_SPEAKER_ID", "1"))
    if speaker_id_from_env not in SPEAKER_ID_RANGE:
        raise ValueError(f"MUXLISA_SPEAKER_ID должен быть в диапазоне {SPEAKER_ID_RANGE}")
    MUXLISA_SPEAKER_ID = speaker_id_from_env
except ValueError as e:
    logger.error(f"Ошибка валидации MUXLISA_SPEAKER_ID: {e}. Используется '1'.")
    MUXLISA_SPEAKER_ID = 1

GPT_MODEL_TO_USE = os.getenv("GPT_MODEL", "gpt-4o")
GPT_MODEL_CLASSIFIER = os.getenv("GPT_MODEL_CLASSIFIER", "gpt-4o-mini")
GPT_MODEL_SUMMARIZER = os.getenv("GPT_MODEL_SUMMARIZER", "gpt-4o")
MAX_MUXLISA_TTS_LEN = int(os.getenv("MAX_MUXLISA_TTS_LEN", "510"))
MIN_CRISIS_LEN_PREFILTER = int(os.getenv("MIN_CRISIS_LEN_PREFILTER", "15"))
# ================= RAG INITIALIZATION =========================
vector_db = None
try:
    if os.path.exists("faiss_index"):
        embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")
        vector_db = FAISS.load_local("faiss_index", embeddings_model, allow_dangerous_deserialization=True)
        logger.info("RAG: index loaded (faiss_index).")
    else:
        logger.warning("RAG: faiss_index missing; retrieval disabled.")
except Exception as e:
    logger.error("RAG initialization failed: %s", e)
    
# ================= ENCRYPTION HELPERS =========================
def get_cipher(password: str) -> Fernet:
    """Генерирует детерминированный ключ на основе пароля бота."""
    key = base64.urlsafe_b64encode(password.ljust(32)[:32].encode())
    return Fernet(key)

PROMPT_REPOSITORY: Dict[str, Dict[str, Any]] = {
    "ru": {
        "welcome_and_disclaimer": (
            "Рад приветствовать Вас! ✨ Я — Ваш ИИ-помощник.\n\n"
            "Вы можете писать мне текстом или отправлять **голосовые сообщения**. "
            "Чтобы я начал озвучивать свои ответы, введите команду /voice.\n\n"
            "⚠️ Я не заменяю врача. Если Вам нужна экстренная помощь — обратитесь к специалисту."
        ),
        "base_system_prompt": (
            "ГЛАВНОЕ ПРАВИЛО: Говорите кратко, тепло и строго на 'Вы'. Избегайте нумерованных списков. "
            "Пишите связным текстом (не более 2 абзацев). Если хотите что-то посоветовать, используйте фразы "
            "'Мне кажется...' или 'А что если...'. Если пользователь прощается или говорит 'спасибо', "
            "просто пожелайте удачи и НЕ ЗАДАВАЙТЕ встречных вопросов."
        ),
        "few_shot_examples": (
            "\nПРИМЕР:\nПользователь: 'Мне плохо'\n"
            "Ассистент: 'Звучит так, будто Вы сейчас в густом тумане. На что похожа эта тяжесть?'"
        ),
        "password_correct": (
            "✅ Пароль верный, благодарю! Я готов Вас выслушать.\n\n"
            "❓ Вы хотите просто выговориться или нам стоит поискать решение конкретной проблемы?"
        ),        
        "password_prompt": "Для доступа к функциям бота, пожалуйста, введите пароль:",
        "password_incorrect": "❌ Неверный пароль. Попробуйте еще раз.",
        "change_language_button": "🌐 Сменить язык",
        "cancel_language_button": "⬅️ Назад",
        "analyze_prompt": "Понял Вас. Пожалуйста, опишите ситуацию максимально подробно.",
        "crisis_classifier_prompt": "Проанализируй текст на суицидальный риск (0, 1, 2). Текст: \"{user_text}\"",
        "crisis_deescalation_prompt": "Вы в режиме экстренной поддержки. Будьте очень теплы. Спросите о безопасности.",
        "conversation_summarizer_prompt": "Суммируй суть проблемы. Если есть зацикливание, добавь [LOOP_DETECTED].\nИстория:\n{history_text}",
        "checkin_message": "Здравствуйте! Хотел узнать, как Вы? Я рядом, если нужно поговорить.",
        "pre_crisis_keywords": ["помоги", "плохо", "больно", "умереть", "суицид", "убить", "конец"],
        "error_gpt": "Извините, произошла ошибка ожидания. Я увеличил время ожидания, попробуйте еще раз.",
        "error_limit_rate": "Слишком много запросов. Повторите через {remaining} с.",
        "error_stt_fail_empathetic": "Не удалось распознать речь. Напишите, пожалуйста, текстом.",
        "voice_mode_on": "🎙 Голосовые ответы ВКЛЮЧЕНЫ.",
        "voice_mode_off": "🔕 Голосовые ответы ВЫКЛЮЧЕНЫ.",
    },
    "uz": {
        "welcome_and_disclaimer": (
            "Xush kelibsiz! ✨ Men Sizning yordamchingizman.\n\n"
            "Men bilan matn yoki **ovozli xabarlar** orqali muloqot qilishingiz mumkin. "
            "Javoblarimni eshitish uchun /voice buyrug'ini bering.\n\n"
            "⚠️ Men shifokor emasman. Agar yordam zarur bo'lsa, mutaxassisga murojaat qiling."
        ),
        "base_system_prompt": (
            "ASOSIY QOIDA: Har doim xushmuomalalik bilan 'Siz' deb murojaat qiling (senlash qat'iyan man etiladi). "
            "Maksimal qisqa javob bering (2 abzasdan oshmasin). Maslahatlarni ro'yxat (1, 2, 3...) qilib berish TAQIQLANADI. "
            "Faqat bog'lamali matn bilan yozing. Agar foydalanuvchi 'rahmat' desa yoki suhbat tugaganini bildirsa, "
            "shunchaki xayrlashing va ortiqcha savol bermang."
        ),
        "few_shot_examples": (
            "\nNAMUNA:\nFoydalanuvchi: 'Menga juda yomon'\n"
            "Assistent: 'Hozir qalbingizda og'irlik borligini eshityapman. Bu og'irlik ko'proq nimaga o'xshaydi?'"
        ),
        "password_correct": (
            "✅ Parol to'g'ri, rahmat! Men Sizni tinglashga tayyorman.\n\n"
            "❓ Siz shunchaki dardlashib yengil tortmoqchimisiz yoki muammoni hal qilishda yordam kerakmi?"
        ),        
        "password_prompt": "Bot funksiyalaridan foydalanish uchun parolni kiriting:",
        "password_incorrect": "❌ Noto'g'ri parol. Qaytadan urinib ko'ring.",
        "change_language_button": "🌐 Tilni o'zgartirish",
        "cancel_language_button": "⬅️ Orqaga",
        "analyze_prompt": "Tushundim. Vaziyatni batafsil tasvirlab bering.",
        "crisis_classifier_prompt": "Suitsidal xavfni tahlil qiling (0, 1, 2). Matn: \"{user_text}\"",
        "crisis_deescalation_prompt": "Siz favqulodda yordam rejimidasiz. Juda muloyim bo'ling. Xavfsizlik haqida so'rang.",
        "conversation_summarizer_prompt": "Suhbatni tahlil qiling. Takrorlansa [LOOP_DETECTED] qo'shing.\nSuhbat:\n{history_text}",
        "checkin_message": "Salom! Ahvolingiz qandayligini bilmoqchi edim. Agar kerak bo'lsam, men shu yerdaman.",
        "pre_crisis_keywords": ["yordam", "yomon", "og'riq", "o'lish", "suitsid", "o'ldirish", "nafratlanaman"],
        "error_gpt": "Kechirasiz, javob olishda xatolik yuz berdi. Qayta urinib ko'ring.",
        "error_limit_rate": "Juda ko'p so'rov. {remaining} soniyadan keyin qayta urinib ko'ring.",
        "error_stt_fail_empathetic": "Nutqni tanib bo'lmadi. Iltimos, matn yuboring.",
        "voice_mode_on": "🎙 Ovozli javoblar YOQILDI.",
        "voice_mode_off": "🔕 Ovozli javoblar O'CHIRILDI.",
    },
    "en": {
        "welcome_and_disclaimer": (
            "Welcome! ✨ I am your AI companion.\n\n"
            "You can communicate with me via text or **voice messages**. "
            "To hear my responses, use the /voice command.\n\n"
            "⚠️ I am not a doctor. If you need emergency help, please contact a professional."
        ),
        "base_system_prompt": (
            "MAIN RULE: Speak concisely, warmly, and respectfully. Avoid numbered lists. "
            "Write in connected text (no more than 2 paragraphs). If you want to suggest something, use phrases "
            "like 'I feel...' or 'What if...'. If the user says 'thank you' or 'goodbye', "
            "simply wish them well and DO NOT ask follow-up questions."
        ),
        "few_shot_examples": (
            "\nEXAMPLE:\nUser: 'I feel bad'\n"
            "Assistant: 'It sounds like you are in a thick fog right now. What does this heaviness feel like?'"
        ),
        "password_correct": (
            "✅ Password correct, thank you! I am ready to listen.\n\n"
            "❓ Do you want to just vent or should we look for a solution to a specific problem?"
        ),        
        "password_prompt": "Please enter the password to access the bot functions:",
        "password_incorrect": "❌ Incorrect password. Please try again.",
        "change_language_button": "🌐 Change language",
        "cancel_language_button": "⬅️ Back",
        "analyze_prompt": "Understood. Please describe the situation in detail.",
        "crisis_classifier_prompt": "Analyze text for suicide risk (0, 1, 2). Text: \"{user_text}\"",
        "crisis_deescalation_prompt": "You are in emergency support mode. Be very warm. Ask about safety.",
        "conversation_summarizer_prompt": "Summarize the core issue. If there is looping, add [LOOP_DETECTED].\nHistory:\n{history_text}",
        "checkin_message": "Hello! Just wanted to check in. I'm here if you need to talk.",
        "pre_crisis_keywords": ["help", "bad", "hurt", "die", "suicide", "kill", "end"],
        "error_gpt": "Sorry, a timeout error occurred. I have increased the wait time, please try again.",
        "error_limit_rate": "Too many requests. Try again in {remaining} seconds.",
        "error_stt_fail_empathetic": "Could not transcribe the voice. Please send a text message.",
        "voice_mode_on": "🎙 Voice responses ENABLED.",
        "voice_mode_off": "🔕 Voice responses DISABLED.",
    }
}

class ConversationState(Enum):
    AWAITING_PASSWORD = "AWAITING_PASSWORD_STATE"
    AWAITING_INTENT = "AWAITING_INTENT_STATE"
    AUTHORIZED = "AUTHORIZED_STATE"
    CRISIS_MODE_ACTIVE = "CRISIS_MODE_ACTIVE_STATE"

# ================= HELPER FUNCTIONS =========================

def get_prompt(lang: str, key: str, default_lang: str = DEFAULT_LANG) -> str:
    try:
        value = PROMPT_REPOSITORY[lang][key]
        return value[0] if isinstance(value, list) else value
    except KeyError:
        try:
            return PROMPT_REPOSITORY[default_lang][key]
        except KeyError:
            return "Error: Missing prompt."

async def _handle_seamless_memory_save(update: Update, context: ContextTypes.DEFAULT_TYPE, summary: str):
    """Шифрует и отправляет зашифрованную память в чат пользователя."""
    if not summary or not BOT_ACCESS_PASSWORD:
        return

    try:
        cipher = get_cipher(BOT_ACCESS_PASSWORD)
        encrypted_data = cipher.encrypt(summary.encode())
        
        file_stream = io.BytesIO(encrypted_data)
        file_stream.name = f"memory_{update.effective_user.id}.bin"

        old_mid = context.user_data.get('memory_message_id')
        if old_mid:
            try: await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=old_mid)
            except: pass

        msg = await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=file_stream,
            caption="🔒 System Memory File (Do not delete / Не удалять)",
            disable_notification=True
        )
        context.user_data['memory_message_id'] = msg.message_id
        logger.info(f"Seamless memory saved for user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Error in seamless memory save: {e}")

async def _handle_seamless_memory_restore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Восстанавливает память из зашифрованного файла в чате."""
    mid = context.user_data.get('memory_message_id')
    if not mid or not BOT_ACCESS_PASSWORD:
        return

    try:
        msg = await context.bot.get_messages(chat_id=update.effective_chat.id, message_ids=mid)
        if not msg.document: return
        
        file = await msg.document.get_file()
        encrypted_content = await file.download_as_bytearray()
        
        cipher = get_cipher(BOT_ACCESS_PASSWORD)
        decrypted_summary = cipher.decrypt(bytes(encrypted_content)).decode()
        
        context.user_data['conversation_summary'] = decrypted_summary
        logger.info(f"Seamless memory restored for user {update.effective_user.id}")
    except Exception as e:
        logger.warning(f"Could not restore seamless memory: {e}")

def authorized_only(func: Callable[..., Awaitable[None]]) -> Callable[..., Awaitable[None]]:
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs) -> None:
        if not BOT_ACCESS_PASSWORD:
            return await func(update, context, *args, **kwargs)
        if context.user_data.get('auth_state') == ConversationState.AUTHORIZED.value:
            return await func(update, context, *args, **kwargs)
        else:
            user_lang = context.user_data.get('language', DEFAULT_LANG)
            await update.message.reply_text(get_prompt(user_lang, 'password_prompt'))
            context.user_data['current_state'] = ConversationState.AWAITING_PASSWORD.value
            return
    return wrapped

async def _robust_remove_file(filepath: str, logger_instance: logging.Logger) -> None:
    if not filepath: return
    try:
        abs_path = Path(filepath).resolve()
        if abs_path.exists():
            for i in range(FILE_DELETE_RETRIES):
                try:
                    os.remove(abs_path)
                    return
                except:
                    await asyncio.sleep(FILE_DELETE_RETRY_DELAY * (i + 1))
    except Exception: pass

def get_system_prompt_combined(
    user_lang: str,
    conversation_summary: Optional[str] = None,
    implicit_crisis: bool = False,
    is_stuck: bool = False,
    knowledge_context: str = "",
) -> str:
    base_prompt = get_prompt(user_lang, 'base_system_prompt')
    few_shot = get_prompt(user_lang, 'few_shot_examples')
    
    lang_directive = {
        "ru": "Всегда отвечай полностью на русском языке.",
        "uz": (
            "Muhim: javobingizni to'liq o'zbek tilida yozing (lotin yoki kirill — foydalanuvchi qanday yozgan bo'lsa). "
            "Quyidagi qo'shimcha matnlar ruscha bo'lishi mumkin; ularni o'zbek tiliga moslab qisqa va tabiiy tarzda yetkazing. "
            "Hech qachon 'faqat rus tilida javob bera olaman' demang — siz o'zbek tilida javob berishingiz kerak."
        ),
        "en": "Always reply entirely in English.",
    }.get(user_lang, f"Always reply in the user's UI language (code: {user_lang}).")

    full_prompt = f"{base_prompt}\n\n{few_shot}\n\n{lang_directive}"

    if knowledge_context:
        rag_intro = {
            "ru": "**ИСПОЛЬЗУЙ ЭТИ НАУЧНЫЕ ДАННЫЕ ДЛЯ СОВЕТА:**",
            "uz": "**QUYidagi ma'lumotlardan foydalan (boshqa tilda bo'lsa ham, javobni o'zbek tilida bering):**",
            "en": "**USE THE FOLLOWING REFERENCE (adapt to English in your reply if the source is not English):**",
        }.get(user_lang, "**REFERENCE:**")
        full_prompt += f"\n\n{rag_intro}\n{knowledge_context}"
    if is_stuck:
        loop_note = {
            "ru": "\n\n🚨 [LOOP_DETECTED]: Пользователь застрял. Смени тактику, перестань просто валидировать.",
            "uz": "\n\n🚨 [LOOP_DETECTED]: Foydalanuvchi aylanib qoldi. Uslubni o'zgartiring, faqat tasdiqlashdan to'xtang.",
            "en": "\n\n🚨 [LOOP_DETECTED]: The user is stuck. Change approach; stop only validating.",
        }.get(user_lang, "")
        full_prompt += loop_note
    if conversation_summary:
        ctx_title = {
            "ru": "**Контекст прошлых бесед:**",
            "uz": "**Oldingi suhbatlar konteksti:**",
            "en": "**Context from earlier conversations:**",
        }.get(user_lang, "**Context:**")
        full_prompt += f"\n\n{ctx_title}\n{conversation_summary}"
    if implicit_crisis:
        crisis_note = {
            "ru": "\n\n**Состояние:** Пользователь уязвим. Будь особо эмпатичен.",
            "uz": "\n\n**Holat:** Foydalanuvchi zaif. Juda ham empatik bo'ling.",
            "en": "\n\n**State:** The user is vulnerable. Be especially empathetic.",
        }.get(user_lang, "")
        full_prompt += crisis_note
    return full_prompt

async def _notify_developer(context: ContextTypes.DEFAULT_TYPE, user: User, user_lang: str, crisis_type: str = "запросе") -> None:
    if not DEVELOPER_CHAT_ID: return
    try:
        alert = f"⚠️ КРИЗИС: {user.full_name} (@{user.username}, ID: {user.id}), Lang: {user_lang}. Тип: {crisis_type}."
        await context.bot.send_message(chat_id=DEVELOPER_CHAT_ID, text=alert)
    except Exception: pass

def _normalize_apostrophes(text: str) -> str:
    if not text:
        return ""
    for ch in ("\u2019", "\u2018", "\u02bc", "\u02bb", "`"):
        text = text.replace(ch, "'")
    return text


def _language_from_keyboard_label(text: str) -> str:
    """Надёжно определяет язык по подписи кнопки (Telegram может слать разные апострофы)."""
    t = _normalize_apostrophes(text or "")
    if "zbek" in t.lower():
        return "uz"
    if "Русский" in t:
        return "ru"
    if "English" in t:
        return "en"
    return DEFAULT_LANG

async def get_crisis_level(user_text: str, user_lang: str) -> int:
    if not user_text or len(user_text.strip()) < MIN_CRISIS_LEN_PREFILTER: return 0
    try:
        prompt = get_prompt(user_lang, 'crisis_classifier_prompt').format(user_text=user_text)
        response = await openai_client.chat.completions.create(
            model=GPT_MODEL_CLASSIFIER,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2,
            timeout=OPENAI_REQUEST_TIMEOUT
        )
        res = response.choices[0].message.content.strip()
        if "2" in res: return 2
        if "1" in res: return 1
        return 0
    except Exception: return 0

async def update_conversation_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    current_history = context.user_data.get('conversation_history', deque())
    if len(current_history) < 4: return
    
    history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in list(current_history)])
    user_lang = context.user_data.get('language', DEFAULT_LANG)

    try:
        prompt = get_prompt(user_lang, 'conversation_summarizer_prompt').format(history_text=history_text)
        response = await openai_client.chat.completions.create(
            model=GPT_MODEL_SUMMARIZER,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            timeout=OPENAI_REQUEST_TIMEOUT
        )
        summary = response.choices[0].message.content.strip()
        
        context.user_data['loop_detected'] = "[LOOP_DETECTED]" in summary
        summary = summary.replace("[LOOP_DETECTED]", "").strip()

        context.user_data['conversation_summary'] = summary
        context.user_data['last_summary_time'] = time.time()
        
        await _handle_seamless_memory_save(update, context, summary)
    except Exception: logger.exception("Summary logic error")

async def _ensure_session(context: ContextTypes.DEFAULT_TYPE) -> Optional[aiohttp.ClientSession]:
    session = context.bot_data.get('http_session')
    if not session or session.closed:
        session = aiohttp.ClientSession()
        context.bot_data['http_session'] = session
    return session

# ================= CORE HANDLERS =========================

async def _process_and_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str, crisis_level: int = 0) -> None:
    user_lang = context.user_data.get('language', DEFAULT_LANG)
    history = context.user_data.setdefault('conversation_history', deque(maxlen=MAX_HISTORY_MESSAGES * 2))
    history.append({"role": "user", "content": user_text})

    knowledge_context = ""
    if vector_db:
        try:
            docs = vector_db.similarity_search(user_text, k=2)
            knowledge_context = "\n".join([d.page_content for d in docs])
        except Exception as e:
            logger.error(f"Ошибка поиска в базе знаний: {e}")

    system_content = get_system_prompt_combined(
        user_lang,
        context.user_data.get('conversation_summary'),
        implicit_crisis=(crisis_level == 1),
        is_stuck=context.user_data.get('loop_detected', False),
        knowledge_context=knowledge_context,
    )

    messages = [{"role": "system", "content": system_content}] + list(history)
    
    full_response, placeholder_id = await _handle_gpt_streaming(update, context, messages)
    if full_response:
        history.append({"role": "assistant", "content": full_response})
        if context.user_data.get('voice_response_enabled'):
            asyncio.create_task(_handle_voice_response(update, context, full_response, placeholder_id))
        
        if len(history) % SUMMARY_TRIGGER_COUNT == 0:
            await update_conversation_summary(update, context)

async def _handle_gpt_streaming(update: Update, context: ContextTypes.DEFAULT_TYPE, messages: list) -> Tuple[Optional[str], Optional[int]]:
    full_text = ""
    msg = None
    last_edit = 0.0
    user_lang = context.user_data.get('language', DEFAULT_LANG)
    try:
        stream = await openai_client.chat.completions.create(
            model=GPT_MODEL_TO_USE, 
            messages=messages, 
            stream=True, 
            timeout=OPENAI_REQUEST_TIMEOUT
        )
        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if not content: continue
            full_text += content
            if not msg: msg = await update.message.reply_text("...")
            
            now = time.time()
            if now - last_edit > STREAM_EDIT_THROTTLE_SECONDS:
                try: 
                    await msg.edit_text(full_text + STREAM_CURSOR)
                    last_edit = now
                except: pass
        
        if msg: await msg.edit_text(full_text)
        return full_text, msg.message_id if msg else None
    except Exception as e:
        logger.error(f"Streaming Error: {e}")
        err_msg = get_prompt(user_lang, 'error_gpt')
        if msg: await msg.edit_text(err_msg)
        else: await update.message.reply_text(err_msg)
        return None, None

@authorized_only
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice = update.message.voice
    user_lang = context.user_data.get('language', DEFAULT_LANG)
    session = await _ensure_session(context)
    
    await update.message.reply_chat_action(ChatAction.TYPING)
    temp_path, wav_path, text = None, None, ""

    try:
        file_info = await voice.get_file()
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
            await file_info.download_to_drive(f.name)
            temp_path = f.name

        if user_lang == "uz" and MUXLISA_API_TOKEN:
            wav_path = temp_path.replace(".ogg", ".wav")
            ffmpeg_cmd = ["ffmpeg", "-i", temp_path, "-acodec", "pcm_s16le", "-ar", str(MUXLISA_AUDIO_SAMPLE_RATE), "-ac", "1", "-y", wav_path]
            proc = await asyncio.create_subprocess_exec(*ffmpeg_cmd)
            try: await asyncio.wait_for(proc.communicate(), timeout=FFMPEG_TIMEOUT)
            except: proc.kill(); raise
            
            form = aiohttp.FormData()
            form.add_field('token', MUXLISA_API_TOKEN)
            with open(wav_path, 'rb') as audio:
                form.add_field('audio', audio, filename='audio.wav')
                async with session.post("https://api.muxlisa.uz/v1/api/services/stt/", data=form, timeout=60) as resp:
                    data = await resp.json()
                    text = data.get('message', {}).get('result', {}).get('text', "")
        else:
            with open(temp_path, "rb") as audio:
                res = await openai_client.audio.transcriptions.create(model="whisper-1", file=audio, response_format="text")
                text = str(res)

        if not text.strip():
            await update.message.reply_text(get_prompt(user_lang, 'error_stt_fail_empathetic'))
            return

        await _route_message_to_handler(update, context, text)
    finally:
        await _robust_remove_file(temp_path, logger)
        await _robust_remove_file(wav_path, logger)

async def _handle_voice_response(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, msg_id: int):
    lang = context.user_data.get('language', DEFAULT_LANG)
    try:
        if lang == "uz" and MUXLISA_API_TOKEN:
            session = await _ensure_session(context)
            form = aiohttp.FormData()
            form.add_field('token', MUXLISA_API_TOKEN)
            form.add_field('text', text[:MAX_MUXLISA_TTS_LEN])
            form.add_field('speaker_id', str(MUXLISA_SPEAKER_ID))
            async with session.post("https://api.muxlisa.uz/v1/api/services/tts/", data=form, timeout=45) as resp:
                content = await resp.read()
                with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
                    f.write(content)
                    with open(f.name, 'rb') as v: await update.message.reply_voice(v)
                os.remove(f.name)
        else:
            res = await openai_client.audio.speech.create(model="tts-1", voice="nova", input=text[:4000], timeout=60)
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                await res.write_to_file(f.name)
                with open(f.name, 'rb') as v: await update.message.reply_voice(v)
            os.remove(f.name)
    except: logger.exception("Voice generation failed")

# ================= ROUTING & AUTH =========================

async def text_input_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    state = context.user_data.get('current_state')

    if state == ConversationState.AWAITING_PASSWORD.value:
        await process_password(update, context, user_text)
        return
    
    if state == ConversationState.AWAITING_INTENT.value:
        await _handle_intent_classification(update, context, user_text)
        return

    await _route_message_to_handler(update, context, user_text)

async def _handle_intent_classification(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str):
    user_lang = context.user_data.get('language', DEFAULT_LANG)
    prompt = f"Classify user intent (VENTING or SOLVING) based on: '{user_text}'. Reply with one word only."
    try:
        res = await openai_client.chat.completions.create(model=GPT_MODEL_CLASSIFIER, messages=[{"role":"user", "content":prompt}], max_tokens=5, timeout=10)
        intent = res.choices[0].message.content.strip().upper()
    except: intent = "VENTING"

    context.user_data['auth_state'] = ConversationState.AUTHORIZED.value
    context.user_data.pop('current_state', None)
    
    if "SOLVING" in intent:
        history = context.user_data.setdefault('conversation_history', deque(maxlen=MAX_HISTORY_MESSAGES * 2))
        history.append({"role": "user", "content": "[USER CHOSE: PROBLEM SOLVING MODE]"})
        await update.message.reply_text(get_prompt(user_lang, 'analyze_prompt'))
    else:
        await _route_message_to_handler(update, context, user_text)

async def process_password(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    user_lang = context.user_data.get('language', DEFAULT_LANG)
    if secrets.compare_digest(text.strip().encode(), BOT_ACCESS_PASSWORD.encode()):
        
        await _handle_seamless_memory_restore(update, context)
        
        context.user_data['current_state'] = ConversationState.AWAITING_INTENT.value
        await update.message.reply_text(get_prompt(user_lang, 'password_correct'))
    else:
        await update.message.reply_text(get_prompt(user_lang, 'password_incorrect'))

async def _route_message_to_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str):
    user_lang = context.user_data.get('language', DEFAULT_LANG)
    if 'crisis_lock' not in context.user_data: context.user_data['crisis_lock'] = asyncio.Lock()
    
    async with context.user_data['crisis_lock']:
        lvl = await get_crisis_level(user_text, user_lang)
        if lvl == 2 and not context.user_data.get('crisis_mode'):
            context.user_data['crisis_mode'] = True
            await _notify_developer(context, update.effective_user, user_lang, "Suicide Level 2")
    
    await _process_and_reply(update, context, user_text, crisis_level=lvl)

# ================= JOB QUEUE TASKS =========================

async def cleanup_inactive_users(context: ContextTypes.DEFAULT_TYPE):
    now = time.time()
    inactive_threshold = USER_DATA_INACTIVE_DAYS * 24 * 3600
    app_user_data = context.application.user_data
    to_remove = [uid for uid, data in app_user_data.items() if (now - data.get('last_seen', 0)) > inactive_threshold]
    for uid in to_remove: await context.application.drop_user_data(uid)
    logger.info(f"Cleanup finished. Removed {len(to_remove)} users.")

async def health_check_job(context: ContextTypes.DEFAULT_TYPE):
    try:
        await openai_client.models.list()
        logger.info("Health Check: OpenAI OK")
    except Exception as e:
        logger.error(f"Health Check Failed: {e}")

# ================= APP START =========================

openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

def main():
    persistence = PicklePersistence(filepath="bot_data.pkl")
    req_settings = HTTPXRequest(connect_timeout=30.0, read_timeout=60.0)
    
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).persistence(persistence).request(req_settings).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        MessageHandler(
            filters.Regex(r"^(🇺🇿\s*O.zbek|🇷🇺\s*Русский|🇬🇧\s*English)$"),
            set_language,
        )
    )
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_input_router))
    
    if application.job_queue:
        application.job_queue.run_repeating(cleanup_inactive_users, interval=timedelta(hours=USER_DATA_CLEANUP_HOURS), first=10)
        application.job_queue.run_repeating(health_check_job, interval=timedelta(minutes=15), first=30)

    logger.info("Bot v%s — polling (OpenAI timeout 90s, HTTPX 60s).", BOT_VERSION)
    application.run_polling()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data['crisis_lock'] = asyncio.Lock()
    kb = [[KeyboardButton("🇺🇿 O'zbek")], [KeyboardButton("🇷🇺 Русский")], [KeyboardButton("🇬🇧 English")]]
    await update.message.reply_text("Select language / Выберите язык:", reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True))

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = _language_from_keyboard_label(update.message.text)
    context.user_data['language'] = lang
    await update.message.reply_text(get_prompt(lang, 'welcome_and_disclaimer'), reply_markup=ReplyKeyboardRemove())
    await update.message.reply_text(get_prompt(lang, 'password_prompt'))
    context.user_data['current_state'] = ConversationState.AWAITING_PASSWORD.value

if __name__ == "__main__":
    main()