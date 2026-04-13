# 📖 DardlashAI haqida batafsil

---

## 💜 Loyiha nomi: DardlashAI

**"Dardlash"** — o'zbek tilida "dard bilan gaplashish" degan ma'noni anglatadi. Bu so'z odamlar o'zlarining ichki tashvish, g'am, quvonch yoki charchoqlarini ishonchli odamga aytishini ifodalaydi.

**DardlashAI** — bu g'oya asosida yaratilgan sun'iy intellekt chat tizimi. U sizning hissiy holatingizni tushunadi va xavfsiz, iliq javoblar beradi — xuddi samimiy do'st kabi.

---

## 🎯 Maqsad

### Muammo
Hozirgi kunda ko'p odamlar stress, tashvish yoki g'amginlik hissini boshdan kechiradi, lekin har doim ham yaqin odamga gapirishga imkoniyat yoki jasorat bo'lmaydi. Professional yordam olish esa vaqt va pul talab qiladi.

### Yechim
DardlashAI — bu **7/24 ishlaydigon**, **bepul**, **xavfsiz** hissiy qo'llab-quvvatlash tizimi. U:

- ❤️ Sizning his-tuyg'ularingizni tan oladi
- 🤗 Hukm qilmasdan tinglaydi
- 💡 Bitta oddiy, amaliy maslahat beradi
- 🛡️ Hech qachon diagnoz qo'ymaydi yoki dori tavsiya qilmaydi

---

## 🧠 Qanday ishlaydi?

### 1. Foydalanuvchi xabar yozadi
Foydalanuvchi o'zining kayfiyatini tanlaydi (masalan: "anxious") va xabar yozadi (masalan: "Imtihon haqida tashvishlanayapman").

### 2. Kontekst tahlili
Tizim foydalanuvchining xabarini tahlil qiladi va mavzuni aniqlaydi:
- 💼 **Ish** — ish bosimi, deadline, boss bilan muammo
- 📚 **O'qish** — imtihon, uy vazifa, baholar
- 👥 **Munosabatlar** — do'stlar, oila, yolg'izlik
- 😴 **Uyqu** — insomnia, charchoq, dam olish
- 😶 **Umumiy** — boshqa mavzular

### 3. Javob generatsiyasi
Tizim 3 ta komponentni birlashtiradi:

| Komponent | Tavsif |
|-----------|--------|
| **Ochilish** | Hissiyotni tan oladigan iliq ibora |
| **Maslahat** | Bitta oddiy, amaliy tavsiya |
| **Davom** | Yumshoq davom ettiruvchi savol (ixtiyoriy) |

Har bir komponent uchun **5 ta variant** mavjud — shuning uchun javoblar har safar biroz farq qiladi va takrorlanmaydi.

### 4. Xavfsizlik tekshiruvi
Har bir javob xavfsizlik filtridan o'tadi:
- ❌ Diagnoz iboralari bloklanadi
- ❌ Dori-darmon maslahatlar bloklanadi
- ❌ Zararli iboralar (masalan: "shunchaki o'zingizni bosing") olib tashlanadi
- ✅ Faqat xavfsiz, ijobiy javob foydalanuvchiga yetib boradi

### 5. Suhbat xotirasi
Tizim oxirgi 10 ta suhbatni eslab qoladi. Agar foydalanuvchi bir necha marta ketma-ket "sad" yoki "anxious" hissiyotini ko'rsatsa, tizim buni sezadi va yanada hamdardlik bilan javob beradi.

---

## 🏛️ Arxitektura

```
┌──────────────────────────────────────────────────────┐
│                    FRONTEND                          │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ Xabar    │  │ Hissiyot     │  │ Chat          │  │
│  │ kiritish │  │ tanlash      │  │ ko'rsatish    │  │
│  └────┬─────┘  └──────┬───────┘  └───────▲───────┘  │
│       │               │                  │          │
│       └───────┬───────┘                  │          │
│               │                          │          │
│         POST /chat                  JSON response   │
└───────────────┼──────────────────────────┼──────────┘
                │                          │
┌───────────────▼──────────────────────────┼──────────┐
│                    BACKEND (FastAPI)                 │
│                                                      │
│  ┌─────────────────────────────────────────────┐    │
│  │              main.py (Router)                │    │
│  └──────────────────┬──────────────────────────┘    │
│                     │                                │
│        ┌────────────▼────────────┐                  │
│        │     ai/model.py         │                  │
│        │  ┌──────────────────┐   │                  │
│        │  │ Kontekst tahlili │   │                  │
│        │  └────────┬─────────┘   │                  │
│        │           │             │                  │
│        │  ┌────────▼─────────┐   │                  │
│        │  │ Javob generatsiya│   │                  │
│        │  └────────┬─────────┘   │                  │
│        │           │             │                  │
│        │  ┌────────▼─────────┐   │                  │
│        │  │ Suhbat xotirasi  │   │                  │
│        │  └──────────────────┘   │                  │
│        └────────────┬────────────┘                  │
│                     │                                │
│  ┌─────────────┐    │    ┌──────────────────┐       │
│  │ ai/prompt.py│◄───┤───►│  ai/safety.py    │       │
│  │ (Shablonlar)│    │    │  (Xavfsizlik)    │       │
│  └─────────────┘    │    └──────────────────┘       │
│                     │                                │
│              Xavfsiz javob                          │
└─────────────────────┼───────────────────────────────┘
                      │
                 Foydalanuvchiga
```

---

## 🎭 Hissiy holat strategiyalari — batafsil

### 😰 Anxious (Tashvishli)
**Strategiya:** Tinchlantirish + nafas mashqlari

Tashvish — bu jismoniy ham, ruhiy ham reaksiya. DardlashAI avval foydalanuvchining tashvishini tan oladi, keyin oddiy nafas mashqini taklif qiladi. Masalan:
> "Nafas oling — 4 son hisoblang, 4 son ushlab turing, 6 songa chiqaring. Bu tanangizga tinchlantirish signalini yuboradi."

Bundan tashqari, "grounding" mashqlari ham taklif qilinadi — masalan, atrofingizdagi 5 ta narsani ko'ring, bu fikrlaringizni hozirgi paytga qaytaradi.

### 😢 Sad (G'amgin)
**Strategiya:** Hissiy qo'llab-quvvatlash + yumshoq dalda

G'amginlik hissini bosib qo'yish o'rniga, DardlashAI uni tan oladi va qabul qiladi. Masalan:
> "G'amgin bo'lish — bu normal, va siz buni itarib yuborishingiz shart emas. Hozir biror yaqin odamingizga oddiy 'salom' yozib ko'ring — ba'zan kichik qadam katta farq qiladi."

### 😴 Tired (Charchagan)
**Strategiya:** Dam olish + bosimni kamaytirish

Charchoq — bu tana va ruhning signal berishi. DardlashAI dam olishga ruxsat beradi va bugungi kutilganlarni pasaytirish mumkinligini eslatadi. Masalan:
> "Agar iloji bo'lsa, o'zingizga dam olishga ruxsat bering — hatto 10 daqiqa ko'zingizni yumish ham yordam beradi."

### 😄 Happy (Xursand)
**Strategiya:** Ijobiy mustahkamlash

Yaxshi kayfiyatda bo'lganingizda, DardlashAI buni nishonlaydi va bu daqiqani qadrashga undaydi. Masalan:
> "Bu ajoyib! Yaxshi daqiqalarni his qilish — ularni yanada uzoqroq saqlab qolishga yordam beradi. Nimadan xursand bo'ldingiz?"

### 😊 Neutral (Neytral)
**Strategiya:** Do'stona, yengil ohang

Maxsus hissiyot bo'lmasa ham, DardlashAI do'stona suhbat boshlaydi va foydalanuvchini ichki holatini tekshirishga undaydi.

---

## 🛡️ Xavfsizlik tizimi — batafsil

### Nima uchun xavfsizlik muhim?
Hissiy qo'llab-quvvatlash tizimi noto'g'ri javob bersa, foydalanuvchiga zarar yetkazishi mumkin. Shuning uchun DardlashAI uch darajali himoya tizimiga ega:

### 1-daraja: Diagnoz bloklash
Tizim hech qachon ruhiy sog'liq haqida diagnoz qo'ymaydi:
```
❌ "Sizda depression bor"
❌ "Bu anxiety disorder belgilari"
❌ "Siz PTSD dan aziyat chekayapsiz"
```

### 2-daraja: Tibbiy maslahat bloklash
Tizim hech qachon dori-darmon yoki tibbiy jaravon tavsiya qilmaydi:
```
❌ "Antidepressant iching"
❌ "Melatonin tabletka olsangiz bo'ladi"
❌ "Dozani oshiring"
```

### 3-daraja: Zararli iboralar bloklash
Tizim hech qachon foydalanuvchining his-tuyg'ularini kamsitmaydi:
```
❌ "Shunchaki o'zingizni bosing"
❌ "Bu unchalik ham katta gap emas"
❌ "Siz haddan oshirib reaksiya qilyapsiz"
❌ "Hammada ham shunday"
```

### Qanday ishlaydi?
Har bir javob **regex pattern matching** orqali tekshiriladi. Agar xavfli ibora topilsa:
1. Faqat xavfli **jumla** o'chiriladi (butun javob emas)
2. Agar butun javob xavfli bo'lsa — umumiy iliq javob bilan almashtiriladi:
   > "Men sizni tinglayapman va siz buni bo'lishganingizni qadrlayman. Gaplashmoqchi bo'lsangiz, men shu yerdaman. 💛"

---

## 🎨 Dizayn falsafasi

DardlashAI interfeysi ataylab **tinch, xavfsiz va iliq** muhitni yaratish uchun ishlab chiqilgan:

- **Qorong'u tema** — ko'zlarni toliqtirmaydi, yoqimli muhit yaratadi
- **Binafsha/pushti ranglar** — tinchlik va ishonch hissi uyg'otadi
- **Glassmorphism** — zamonaviy, premium ko'rinish
- **Yumshoq animatsiyalar** — tizim "tirik" va "g'amxo'r" his qilinadi
- **Katta, oson o'qiladigan matn** — stress paytida kichik matnni o'qish qiyin
- **Emoji hissiyot tegi** — foydalanuvchi o'z hissiyotini vizual ko'radi

---

## 👨‍💻 Kim uchun?

| Auditoriya | Foydalanish holati |
|------------|-------------------|
| 🎓 **Talabalar** | Imtihon stressi, o'quv bosimi, yolg'izlik |
| 💼 **Ishchilar** | Ish charchoqi, deadline bosimi, burnout |
| 🏠 **Har kim** | Kunlik stress, kayfiyat tushkunligi, dam olish kerak |
| 💻 **Dasturchilar** | Hackathon loyihalar uchun namuna, o'rganish uchun |

---

## ⚖️ Axloqiy tamoyillar

1. **Zarar yetkazmaslik** — tizim hech qachon foydalanuvchiga zarar yetkazadigan maslahat bermaydi
2. **Shaffoflik** — tizim ochiqchasiga aytadi: "Men psixolog emasman"
3. **Hurmat** — har bir his-tuyg'u muhim va hukm qilinmaydi
4. **Maxfiylik** — suhbat ma'lumotlari faqat serverni qayta ishga tushirguncha saqlanadi, hech qayerga yuborilmaydi
5. **Cheklovlarni bilish** — jiddiy holatlar uchun professional yordamga yo'naltiradi

---

## 🔮 Kelajak ko'rinishi

DardlashAI hozircha MVP bosqichida, lekin kelajakda quyidagi imkoniyatlar rejalashtirilgan:

### Qisqa muddatli (1-3 oy)
- 🌐 O'zbek tilida to'liq javob berish
- 🤖 Ollama yoki OpenAI orqali haqiqiy LLM integratsiyasi
- 📊 Hissiy holat tarixi grafigi (kunlik/haftalik)

### O'rta muddatli (3-6 oy)
- 🔐 Foydalanuvchi ro'yxatdan o'tishi va shaxsiy profil
- 📱 Progressive Web App (PWA) — telefonda o'rnatish
- 🗣️ Ovozli kiritish (speech-to-text)
- 🌍 Ko'p tilli qo'llab-quvvatlash

### Uzoq muddatli (6-12 oy)
- 📈 Hissiy holat bashorat qilish (ML model)
- 🧘 Meditatsiya va nafas mashqlari integratsiyasi
- 👨‍⚕️ Professional yordamga ulanish (telehealth integratsiya)
- 📋 Kundalik (journaling) funksiyasi

---

## 📊 Texnik xarakteristikalar

| Xarakteristika | Qiymat |
|---------------|--------|
| Backend framework | FastAPI 0.115.6 |
| Server | Uvicorn 0.34.0 |
| Data validation | Pydantic 2.10.4 |
| Frontend | Vanilla HTML5 + CSS3 + JavaScript |
| AI model | Template-based (LLM-ready architecture) |
| Javob vaqti | < 100ms (template), ~1-2s (UI delay for natural feel) |
| Hissiyot turlari | 5 (neutral, happy, sad, anxious, tired) |
| Javob variantlari | 5 opener × 5 suggestion × 5 follow-up = 125 kombinatsiya per emotion |
| Xavfsizlik filtrlari | 15+ regex pattern (3 kategoriya) |
| Suhbat xotirasi | Oxirgi 10 ta suhbat |

---

## 📝 Litsenziya

MIT License — erkin foydalanish, o'zgartirish va tarqatish mumkin.

---

<p align="center">
  <strong>💜 DardlashAI — chunki har bir his-tuyg'u muhim, va siz yolg'iz emassiz.</strong>
</p>
