<p align="center">
  <img src="https://img.shields.io/badge/💜-DardlashAI-8B5CF6?style=for-the-badge&labelColor=1e1e3f" alt="DardlashAI" />
</p>

<h1 align="center">DardlashAI</h1>

<p align="center">
  <strong>Emotional support AI chatbot — your safe space to share how you feel 💜</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" />
  <img src="https://img.shields.io/badge/status-MVP-blueviolet?style=flat-square" />
</p>

---

## 🧠 Nima bu?

**DardlashAI** — bu foydalanuvchilarning hissiy holatini tushunib, iliq va xavfsiz javoblar beradigan sun'iy intellekt chat tizimi. U psixolog emas, diagnoz qo'ymaydi, dori tavsiya qilmaydi — shunchaki samimiy, g'amxo'r do'st kabi gaplashadi.

> **"Dardlash"** — o'zbek tilida "dard bilan gaplashish", ya'ni ichingizda bo'lgan narsalarni kimgadir aytish ma'nosini beradi.

---

## ✨ Imkoniyatlar

| Xususiyat | Tavsif |
|-----------|--------|
| 🎭 **5 ta hissiy holat** | Neutral, Happy, Sad, Anxious, Tired — har biri uchun maxsus javob strategiyasi |
| 🧠 **Kontekstual javoblar** | Ish, o'qish, munosabatlar, uyqu haqida gapirsangiz — shuni tushunadi |
| 🛡️ **Xavfsizlik filtri** | Diagnoz, dori maslahat, zararli iboralarni avtomatik bloklaydi |
| 💬 **Suhbat xotirasi** | Oxirgi 10 ta suhbatni eslab qoladi, takroriy his-tuyg'ularni sezadi |
| 😊 **Emoji hissiyot ko'rsatkichi** | Har bir xabarda hissiy holat tegi va emoji |
| 🎨 **Premium UI** | Dark glassmorphism dizayn, animatsiyalar, responsive layout |
| ⚡ **Tez ishga tushirish** | Quick-start chiplar bilan bir bosishda suhbat boshlash |

---

## 🖼️ Skrinshot

<p align="center">
  <img src="docs/welcome_screen.png" alt="Welcome Screen" width="420" />
  <img src="docs/chat_screen.png" alt="Chat Screen" width="420" />
</p>

---

## 🏗️ Loyiha tuzilishi

```
DardlashAI/
├── 📄 README.md                ← Shu fayl
├── 📄 ABOUT.md                 ← Loyiha haqida batafsil
│
├── 🔧 backend/
│   ├── main.py                 ← FastAPI server + API endpointlar
│   ├── requirements.txt        ← Python kutubxonalar
│   └── ai/
│       ├── __init__.py
│       ├── prompt.py           ← System prompt + hissiy strategiyalar
│       ├── model.py            ← AI javob generatori + suhbat xotirasi
│       └── safety.py           ← Xavfsizlik filtri (diagnoz/dori bloklash)
│
└── 🌐 frontend/
    ├── index.html              ← Chat UI sahifasi
    ├── style.css               ← Dark theme + glassmorphism + animatsiyalar
    └── app.js                  ← Frontend logika (chat, emoji, typing indicator)
```

---

## 🚀 Ishga tushirish

### Talablar

- Python 3.10+
- pip

### O'rnatish va ishga tushirish

```bash
# 1. Repositoryni klonlash
git clone https://github.com/your-username/DardlashAI.git
cd DardlashAI

# 2. Kutubxonalarni o'rnatish
cd backend
pip install -r requirements.txt

# 3. Serverni ishga tushirish
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Brauzerni oching: **http://localhost:8000** 🎉

---

## 📡 API Endpointlar

| Endpoint | Method | Tavsif |
|----------|--------|--------|
| `/chat` | `POST` | Asosiy chat — `user_text` + `emotion` qabul qiladi |
| `/emotions` | `GET` | Barcha hissiyotlar ro'yxati + emoji |
| `/conversation` | `GET` | Suhbat xulosa |
| `/reset` | `POST` | Suhbat xotirasini tozalash |
| `/health` | `GET` | Server holati tekshirish |
| `/` | `GET` | Frontend sahifasi |

### Chat endpoint misoli

**Request:**
```json
POST /chat
{
  "user_text": "Imtihon haqida juda tashvishlanayapman",
  "emotion": "anxious"
}
```

**Response:**
```json
{
  "response": "Academic pressure can feel enormous, but remember — one step at a time gets you there. Try breathing in for 4 counts, holding for 4, and exhaling for 6. What's the one thing weighing on you the most right now?",
  "emotion_received": "anxious",
  "emoji": "😰"
}
```

---

## 🛡️ Xavfsizlik tizimi

DardlashAI **hech qachon** quyidagilarni qilmaydi:

| ❌ Bloklangan | Misol |
|--------------|-------|
| Diagnoz qo'yish | "Sizda anxiety disorder bor" |
| Dori-darmon tavsiyasi | "Antidepressant iching" |
| Zararli iboralar | "Shunchaki o'zingizni bosing", "Bu unchalik ham muhim emas" |
| Kuchli da'volar | "Siz doim shunday bo'lasiz" |

Xavfsizlik filtri har bir javobni regex-based pattern matching bilan tekshiradi va xavfli jumlalarni o'chiradi.

---

## 🎭 Hissiy holat strategiyasi

| Hissiyot | Strategiya | Misol |
|----------|-----------|-------|
| 😰 **Anxious** | Tinchlantirish + nafas mashqlari | "Nafas oling — 4 son hisoblang, 4 son ushlab turing..." |
| 😢 **Sad** | Hissiy qo'llab-quvvatlash + yumshoq dalda | "Sizning his-tuyg'ularingiz muhim, va buni bo'lishganingiz uchun rahmat." |
| 😴 **Tired** | Dam olish + bosimni kamaytirish | "Bugun kutilganlarni pastlatish ham yaxshi. Kam qilish — bu normal." |
| 😄 **Happy** | Ijobiy mustahkamlash | "Bu ajoyib! Yaxshi daqiqalarni his qilish — ularni uzoqroq saqlab qoladi." |
| 😊 **Neutral** | Do'stona, yengil ohang | "Salom! Bugun sizga qanday yordam bera olaman?" |

---

## 🛠️ Texnologiyalar

| Texnologiya | Maqsad |
|-------------|--------|
| **FastAPI** | Backend API framework |
| **Uvicorn** | ASGI server |
| **Pydantic** | Ma'lumotlarni validatsiya qilish |
| **Vanilla JS** | Frontend logika |
| **CSS3** | Glassmorphism + animatsiyalar |
| **HTML5** | Semantik tuzilish |

---

## 🤝 Hissa qo'shish

1. Fork qiling
2. Yangi branch yarating (`git checkout -b feature/yangi-xususiyat`)
3. O'zgarishlarni commit qiling (`git commit -m 'Yangi xususiyat qo'shildi'`)
4. Push qiling (`git push origin feature/yangi-xususiyat`)
5. Pull Request oching

---

## 📋 Kelajak rejalari

- [ ] 🌐 O'zbek tilida javob berish qo'llab-quvvatlash
- [ ] 🤖 Haqiqiy LLM integratsiyasi (OpenAI / Ollama)
- [ ] 📊 Hissiy holat tarixi grafigi
- [ ] 🔐 Foydalanuvchi autentifikatsiyasi
- [ ] 📱 Mobile-optimized PWA
- [ ] 🗣️ Ovozli kiritish qo'llab-quvvatlash

---

## ⚠️ Muhim eslatma

> DardlashAI **psixolog yoki vrach emas**. Bu tizim faqat umumiy hissiy qo'llab-quvvatlash uchun mo'ljallangan. Jiddiy ruhiy sog'liq muammolari uchun **malakali mutaxassisga** murojaat qiling.

---

## 📄 Litsenziya

MIT License — batafsil [LICENSE](LICENSE) faylida.

---

<p align="center">
  <strong>💜 Dardlash — chunki har bir his-tuyg'u muhim.</strong>
</p>
