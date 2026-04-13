/**
 * DardlashAI — To'liq interaktiv tizim v3
 * 
 * TUZATISHLAR:
 * - Yuz hissiyoti real-time yangilanadi (past bo'sag'a, tez interval)
 * - Speech recognition: ru-RU ga o'tkazildi (uz-UZ brauzerda yo'q)
 * - TTS: turk tili ovozi (o'zbekchaga eng yaqin til)
 * - AI gapirish to'xtatish tugmasi
 */

const API_BASE = window.location.origin;
const MODEL_URL = 'https://justadudewhohacks.github.io/face-api.js/models';
const SILENCE_TIMEOUT = 2500; // 2.5s jimlik = avtomatik jo'natish (tezkor ovozli chat)

// ═══════════════════════════════════════════════════════════════════════
// HOLAT
// ═══════════════════════════════════════════════════════════════════════
let selectedEmotion = 'neutral';
let lastDisplayedEmotion = '';
let isLoading = false;
let faceApiLoaded = false;
let detectionInterval = null;
let chatSocket = null;

// Hissiyot tekislash (smooth) - oxirgi 5 ta natijani hisobga oladi
let emotionHistory = [];
const EMOTION_HISTORY_SIZE = 5;

// Ovoz holati
let recognition = null;
let isListening = false;
let accumulatedText = '';
let silenceTimer = null;
let silenceStartTime = null;
let silenceAnimFrame = null;
let lastInputMode = 'text'; // 'text' yoki 'voice'

// TTS
let isSpeaking = false;
let currentUtterance = null;

// ═══════════════════════════════════════════════════════════════════════
// HISSIYOT XARITALARI
// ═══════════════════════════════════════════════════════════════════════
const EMOTION_EMOJIS = {
    neutral: '😊', happy: '😄', sad: '😢', anxious: '😰',
    tired: '😴', angry: '😠', fearful: '😨', surprised: '😲', disgusted: '🤢',
};

const EMOTION_LABELS = {
    neutral: 'Neytral', happy: 'Xursand', sad: "G'amgin", anxious: 'Tashvishli',
    tired: 'Charchagan', angry: "G'azablangan", fearful: "Qo'rqinchli",
    surprised: 'Hayratda', disgusted: 'Norozilik',
};

// ═══════════════════════════════════════════════════════════════════════
// DOM
// ═══════════════════════════════════════════════════════════════════════
const chatArea = document.getElementById('chatArea');
const welcomeScreen = document.getElementById('welcomeScreen');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const typingIndicator = document.getElementById('typingIndicator');
const welcomeChips = document.querySelectorAll('.welcome-chip');
const resetBtn = document.getElementById('resetBtn');
const toast = document.getElementById('toast');

const cameraVideo = document.getElementById('cameraVideo');
const cameraCanvas = document.getElementById('cameraCanvas');
const cameraOverlay = document.getElementById('cameraOverlay');
const liveEmoji = document.getElementById('liveEmoji');
const emotionBadge = document.getElementById('emotionBadge');
const emotionBadgeEmoji = document.getElementById('emotionBadgeEmoji');
const emotionBadgeText = document.getElementById('emotionBadgeText');
const emotionConfidence = document.getElementById('emotionConfidence');

const micBtn = document.getElementById('micBtn');
const micIcon = document.getElementById('micIcon');
const micText = document.getElementById('micText');
const micStatus = document.getElementById('micStatus');
const speechPreview = document.getElementById('speechPreview');
const speechText = document.getElementById('speechText');
const silenceProgress = document.getElementById('silenceProgress');

const aiSpeaking = document.getElementById('aiSpeaking');
const stopSpeakBtn = document.getElementById('stopSpeakBtn');

// ═══════════════════════════════════════════════════════════════════════
// 1. KAMERA VA YUZ HISSIYOT ANIQLASH — REAL-TIME
// ═══════════════════════════════════════════════════════════════════════

async function initCamera() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: { width: 480, height: 360, facingMode: 'user' }
        });
        cameraVideo.srcObject = stream;

        showToast('Yuz aniqlash modeli yuklanmoqda...');
        await Promise.all([
            faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL),
            faceapi.nets.faceExpressionNet.loadFromUri(MODEL_URL),
        ]);
        faceApiLoaded = true;
        cameraOverlay.classList.add('hidden');
        showToast('Kamera tayyor! 📷');

        cameraVideo.addEventListener('playing', () => {
            startFaceDetection();
        }, { once: true });

    } catch (err) {
        console.error('Kamera xatosi:', err);
        cameraOverlay.innerHTML = `
            <div class="camera-loading">
                <span style="font-size:2rem">📷</span>
                <span>Kameraga ulanib bo'lmadi</span>
            </div>`;
    }
}

function startFaceDetection() {
    const displaySize = {
        width: cameraVideo.videoWidth,
        height: cameraVideo.videoHeight,
    };
    faceapi.matchDimensions(cameraCanvas, displaySize);

    // HAR 250ms DA — tezroq aniqlash
    detectionInterval = setInterval(async () => {
        try {
            const detections = await faceapi
                .detectAllFaces(cameraVideo, new faceapi.TinyFaceDetectorOptions({
                    inputSize: 320,    // Kattaroq = aniqroq
                    scoreThreshold: 0.4,
                }))
                .withFaceExpressions();

            const ctx = cameraCanvas.getContext('2d');
            ctx.clearRect(0, 0, cameraCanvas.width, cameraCanvas.height);

            if (detections.length > 0) {
                const detection = detections[0];
                const resized = faceapi.resizeResults([detection], displaySize)[0];

                // YUZ ATROFIDA KVADRAT
                drawFaceBox(ctx, resized);

                // HISSIYOT — barcha skorlarni ko'rish
                const allEmotions = detection.expressions;
                const sorted = Object.entries(allEmotions)
                    .sort((a, b) => b[1] - a[1]);

                const topEmotion = sorted[0][0];
                const topScore = sorted[0][1];

                // Hissiyot tarixiga qo'shish (smoothing)
                emotionHistory.push(topEmotion);
                if (emotionHistory.length > EMOTION_HISTORY_SIZE) {
                    emotionHistory.shift();
                }

                // Eng ko'p takrorlangan hissiyotni aniqlash
                const smoothed = getMostFrequent(emotionHistory);

                // UI YANGILASH — DOIM, har safar
                updateLiveEmotion(smoothed, topScore, sorted);

            } else {
                // Yuz topilmadi
                emotionBadgeText.textContent = 'Yuz topilmadi';
                emotionConfidence.textContent = '';
            }
        } catch (err) {
            // Xatolikni o'tkazib yuborish
        }
    }, 250);
}

function getMostFrequent(arr) {
    const counts = {};
    arr.forEach(item => { counts[item] = (counts[item] || 0) + 1; });
    return Object.entries(counts).sort((a, b) => b[1] - a[1])[0][0];
}

function drawFaceBox(ctx, resized) {
    const box = resized.detection.box;
    const x = box.x, y = box.y, w = box.width, h = box.height;

    // Burchak chiziqlari — yashil neon
    const cornerLen = Math.min(w, h) * 0.22;

    ctx.lineWidth = 3;
    ctx.strokeStyle = '#a855f7';
    ctx.shadowColor = '#a855f7';
    ctx.shadowBlur = 15;
    ctx.lineCap = 'round';

    ctx.beginPath();
    // Chap yuqori
    ctx.moveTo(x, y + cornerLen); ctx.lineTo(x, y); ctx.lineTo(x + cornerLen, y);
    // O'ng yuqori
    ctx.moveTo(x + w - cornerLen, y); ctx.lineTo(x + w, y); ctx.lineTo(x + w, y + cornerLen);
    // O'ng pastki
    ctx.moveTo(x + w, y + h - cornerLen); ctx.lineTo(x + w, y + h); ctx.lineTo(x + w - cornerLen, y + h);
    // Chap pastki
    ctx.moveTo(x + cornerLen, y + h); ctx.lineTo(x, y + h); ctx.lineTo(x, y + h - cornerLen);
    ctx.stroke();

    // Nozik punkt ramka
    ctx.shadowBlur = 0;
    ctx.strokeStyle = 'rgba(168, 85, 247, 0.25)';
    ctx.lineWidth = 1;
    ctx.setLineDash([5, 5]);
    ctx.strokeRect(x, y, w, h);
    ctx.setLineDash([]);
}

let emotionStableTimer = null;
let lastProactiveTime = 0;
const EMOTION_STABLE_DURATION = 3000; // 3 soniya barqaror
const PROACTIVE_COOLDOWN = 30000; // Har 30 sekundda

function triggerProactiveEmotion(emotion) {
    // Agar dastur band bo'lsa yoki neytral his bo'lsa teginmaymiz
    if (isSpeaking || isListening || isLoading) return;
    if (emotion === 'neutral') return;

    const now = Date.now();
    if (now - lastProactiveTime < PROACTIVE_COOLDOWN) return;
    lastProactiveTime = now;
    
    if (chatSocket && chatSocket.readyState === WebSocket.OPEN) {
        console.log(`Proaktiv so'rov yuborilmoqda: ${emotion}`);
        isLoading = true;
        showTyping(true);
        // maxsus trigger uzatish
        chatSocket.send(JSON.stringify({ 
            user_text: "[PROACTIVE_EMOTION_TRIGGER]", 
            emotion: emotion 
        }));
    }
}

function updateLiveEmotion(emotion, score, allScores) {
    const emoji = EMOTION_EMOJIS[emotion] || '😊';
    const label = EMOTION_LABELS[emotion] || emotion;
    const pct = Math.round(score * 100);

    // Badge — DOIM yangilanadi
    emotionBadgeEmoji.textContent = emoji;
    emotionBadgeText.textContent = label;
    emotionConfidence.textContent = pct + '%';

    // Katta emoji — hissiyot O'ZGARGANDA animatsiya
    if (emotion !== lastDisplayedEmotion) {
        liveEmoji.textContent = emoji;
        // Animatsiyani qayta boshlash
        liveEmoji.style.animation = 'none';
        liveEmoji.offsetHeight; // reflow
        liveEmoji.style.animation = 'emojiPop 0.5s ease-out';
        lastDisplayedEmotion = emotion;

        console.log(`Hissiyot o'zgardi: ${emotion} (${pct}%)`);

        // Hissiyot o'zgarganda niyat taymerini qayta boshlash
        if (emotionStableTimer) clearTimeout(emotionStableTimer);
        emotionStableTimer = setTimeout(() => {
            triggerProactiveEmotion(emotion);
        }, EMOTION_STABLE_DURATION);
    }

    // Chat uchun tanlov
    selectedEmotion = emotion;
}

// ═══════════════════════════════════════════════════════════════════════
// 2. OVOZLI KIRITISH — SPEECH-TO-TEXT
// ═══════════════════════════════════════════════════════════════════════

function initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
        showToast('Brauzeringiz ovoz aniqlashni qo\'llab-quvvatlamaydi. Chrome ishlating.');
        micBtn.style.opacity = '0.5';
        micBtn.style.pointerEvents = 'none';
        return;
    }

    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    
    // MUHIM: uz-UZ Chrome da yo'q!
    // Variantlar: 'ru-RU' (ruscha), 'tr-TR' (turkcha — o'zbekchaga yaqin)
    // Yoki brauzer tilini ishlatish
    recognition.lang = 'ru-RU';

    recognition.onresult = (event) => {
        let currentText = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
                accumulatedText += transcript + ' ';
            } else {
                currentText = transcript;
            }
        }

        // Ekranda ko'rsatish
        const display = accumulatedText + currentText;
        if (display.trim()) {
            speechText.innerHTML = escapeHtml(accumulatedText) + 
                (currentText ? `<span class="interim">${escapeHtml(currentText)}</span>` : '');
        } else {
            speechText.innerHTML = '<span class="interim">Tinglanmoqda...</span>';
        }

        // Jimlik taymerini qayta boshlash — gap eshitildi
        resetSilenceTimer();
    };

    recognition.onerror = (event) => {
        console.log('Speech xato:', event.error);
        
        if (event.error === 'not-allowed') {
            showToast('Mikrofonga ruxsat bering (brauzer sozlamalaridan)');
            stopListening();
        } else if (event.error === 'no-speech') {
            // Gapirish yo'q — normal holat
        } else if (event.error === 'network') {
            showToast('Internet aloqasini tekshiring');
        }
    };

    recognition.onend = () => {
        if (isListening) {
            // Avtomatik qayta boshlash
            try { recognition.start(); } catch (e) {}
        }
    };
}

function startListening() {
    if (!recognition) {
        showToast('Ovoz aniqlash mavjud emas. Chrome brauzerini ishlating.');
        return;
    }
    if (isSpeaking) {
        showToast('AI gapirishi tugashini kuting yoki to\'xtating');
        return;
    }

    isListening = true;
    accumulatedText = '';

    micBtn.classList.add('recording');
    micIcon.textContent = '⏹';
    micText.textContent = "To'xtatish";
    micStatus.style.display = 'flex';
    speechPreview.style.display = 'block';
    speechText.innerHTML = '<span class="interim">Tinglanmoqda...</span>';
    silenceProgress.style.width = '0%';

    try {
        recognition.start();
        showToast('Gapiring — men tinglayapman 🎤');
    } catch (e) {
        console.error('Recognition start xato:', e);
    }
}

function stopListening() {
    isListening = false;
    clearSilenceTimer();

    try { recognition?.stop(); } catch (e) {}

    micBtn.classList.remove('recording');
    micIcon.textContent = '🎤';
    micText.textContent = 'Gapirish boshlash';
    micStatus.style.display = 'none';
}

// ─── 7 soniya jimlik taymeri ────────────────────────────────────────────
function resetSilenceTimer() {
    clearSilenceTimer();
    silenceStartTime = Date.now();
    updateSilenceBar();

    silenceTimer = setTimeout(() => {
        autoSendSpeech();
    }, SILENCE_TIMEOUT);
}

function updateSilenceBar() {
    if (!silenceStartTime) return;
    const elapsed = Date.now() - silenceStartTime;
    const pct = Math.min((elapsed / SILENCE_TIMEOUT) * 100, 100);
    silenceProgress.style.width = pct + '%';
    if (pct < 100) {
        silenceAnimFrame = requestAnimationFrame(updateSilenceBar);
    }
}

function clearSilenceTimer() {
    if (silenceTimer) { clearTimeout(silenceTimer); silenceTimer = null; }
    if (silenceAnimFrame) { cancelAnimationFrame(silenceAnimFrame); silenceAnimFrame = null; }
    silenceStartTime = null;
    silenceProgress.style.width = '0%';
}

function autoSendSpeech() {
    const text = accumulatedText.trim();
    if (text) {
        lastInputMode = 'voice'; // Avtomatik uzatilganda ovozli rejim tasdiqlanadi
        stopListening();
        userInput.value = text;
        speechPreview.style.display = 'none';
        sendMessage();
    } else {
        // Bo'sh — qayta boshlash
        if (isListening) resetSilenceTimer();
    }
}

micBtn.addEventListener('click', () => {
    if (isListening) {
        lastInputMode = 'text'; // Ovozni qo'lda o'chirsa, uzluksiz rejim to'xtatiladi
        const text = accumulatedText.trim();
        stopListening();
        if (text) {
            userInput.value = text;
            speechPreview.style.display = 'none';
            sendMessage();
        } else {
            speechPreview.style.display = 'none';
        }
    } else {
        lastInputMode = 'voice'; // Mikrofonni bosish uzluksiz rejimni boshlaydi
        startListening();
    }
});

// ═══════════════════════════════════════════════════════════════════════
// 3. TEXT-TO-SPEECH — AZURE AUDIO PLAYER
// ═══════════════════════════════════════════════════════════════════════

let currentAudio = null;

/**
 * AI javobini ijro etish.
 * Agar audio_url bo'lsa — Azure WAV faylni ijro etadi.
 * Agar yo'q bo'lsa — brauzer TTS ga fallback.
 */
function speakResponse(audioUrl, text, emotion) {
    // Oldingi audioni to'xtatish
    stopSpeaking();

    if (audioUrl) {
        // AZURE AUDIO — WAV faylni ijro etish
        playAzureAudio(audioUrl);
    } else {
        // FALLBACK — brauzer TTS
        playBrowserTTS(text, emotion);
    }
}

function playAzureAudio(url) {
    currentAudio = new Audio(url);

    currentAudio.addEventListener('play', () => {
        isSpeaking = true;
        aiSpeaking.style.display = 'flex';
    });

    currentAudio.addEventListener('ended', () => {
        finishSpeaking();
    });

    currentAudio.addEventListener('error', (e) => {
        console.error('Audio ijro xatosi:', e);
        finishSpeaking();
    });

    currentAudio.play().catch(err => {
        console.error('Audio play xatosi:', err);
        finishSpeaking();
    });
}

function playBrowserTTS(text, emotion) {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();

    const cleanText = text.replace(/[😊😄😢😰😴😠😨😲🤢💛💜🤗✨]/g, '')
        .replace(/\s+/g, ' ').trim();
    if (!cleanText) return;

    const utterance = new SpeechSynthesisUtterance(cleanText);

    // Turk/rus/ingliz ovoz tanlash
    const voices = window.speechSynthesis.getVoices();
    const voice = voices.find(v => v.lang.startsWith('tr'))
        || voices.find(v => v.lang.startsWith('ru'))
        || voices.find(v => v.lang.startsWith('en'))
        || voices[0];

    if (voice) {
        utterance.voice = voice;
        utterance.lang = voice.lang;
    }

    utterance.rate = 0.9;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;

    utterance.onstart = () => {
        isSpeaking = true;
        aiSpeaking.style.display = 'flex';
    };

    utterance.onend = () => finishSpeaking();
    utterance.onerror = () => finishSpeaking();

    window.speechSynthesis.speak(utterance);
}

function finishSpeaking() {
    isSpeaking = false;
    currentAudio = null;
    aiSpeaking.style.display = 'none';

    // Gapirish tugagach — faqat ovozli chat rejimida bo'lsa qayta tinglash
    setTimeout(() => {
        if (!isListening && !isSpeaking && lastInputMode === 'voice') {
            startListening(); // Xuddi telefon qo'ng'irog'idek yana tinglash
        }
    }, 600); // 0.6 soniyadan so'ng darhol ochiladi, juda silliq (seamless) ulanish
}

function stopSpeaking() {
    // Azure audio to'xtatish
    if (currentAudio) {
        currentAudio.pause();
        currentAudio.currentTime = 0;
        currentAudio = null;
    }
    // Browser TTS to'xtatish
    if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
    }
    isSpeaking = false;
    aiSpeaking.style.display = 'none';
}

// To'xtatish tugmasi
if (stopSpeakBtn) {
    stopSpeakBtn.addEventListener('click', () => {
        stopSpeaking();
        showToast('AI to\'xtatildi');
    });
}

// ═══════════════════════════════════════════════════════════════════════
// 4. XABAR YUBORISH
// ═══════════════════════════════════════════════════════════════════════

function sendMessage() {
    const text = userInput.value.trim();
    if (!text || isLoading) return;

    // Agar WebSocket ulanmagan bo'lsa
    if (!chatSocket || chatSocket.readyState !== WebSocket.OPEN) {
        showToast('Server bilan aloqa uzilgan. Qayta ulanmoqda...');
        initWebSocket();
        return;
    }

    // Agar AI gapirayotgan bo'lsa — to'xtatish
    if (isSpeaking) stopSpeaking();

    isLoading = true;
    sendBtn.disabled = true;

    if (welcomeScreen) welcomeScreen.style.display = 'none';

    addMessage(text, 'user', selectedEmotion);
    userInput.value = '';
    autoResizeInput();
    showTyping(true);

    // Xabarni WebSocket orqali yuborish
    chatSocket.send(JSON.stringify({ user_text: text, emotion: selectedEmotion }));
}

// ═══════════════════════════════════════════════════════════════════════
// 5. YORDAMCHI FUNKSIYALAR
// ═══════════════════════════════════════════════════════════════════════

function addMessage(text, sender, emotion, emoji, riskLevel = null, riskConfidence = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;

    const avatarEmoji = sender === 'user' ? (EMOTION_EMOJIS[emotion] || '😊') : '💜';
    const emotionLabel = EMOTION_LABELS[emotion] || emotion;
    
    let extraTags = '';
    
    // Foydalanuvchi hissiyoti
    if (sender === 'user') {
        extraTags += `<div class="message-emotion-tag">${EMOTION_EMOJIS[emotion] || '😊'} ${emotionLabel}</div>`;
    }
    
    // AI uchun ML model Risk darajasini ko'rsatish
    if (sender === 'ai' && riskLevel) {
        let riskColor = '#4ade80'; // normal (yashil)
        let riskLabel = 'Normal holat';
        let riskEmoji = '🟢';
        
        if (riskLevel === 'stress') {
            riskColor = '#facc15'; // stress (sariq)
            riskLabel = 'Stress aniqlandi';
            riskEmoji = '🟡';
        } else if (riskLevel === 'high_risk') {
            riskColor = '#f87171'; // high_risk (qizil)
            riskLabel = 'Yuqori xavf';
            riskEmoji = '🔴';
        }
        
        const confText = riskConfidence ? ` (${Math.round(riskConfidence * 100)}%)` : '';
        extraTags += `<div class="message-emotion-tag" style="background: rgba(0,0,0,0.5); border-color: ${riskColor}; color: ${riskColor};">
            ${riskEmoji} ML: ${riskLabel}${confText}
        </div>`;
    }

    messageDiv.innerHTML = `
        <div class="message-avatar">${avatarEmoji}</div>
        <div class="message-bubble">
            ${escapeHtml(text)}
            <div style="display: flex; gap: 8px; margin-top: 5px;">
                ${extraTags}
            </div>
        </div>
    `;
    chatArea.appendChild(messageDiv);
    scrollToBottom();
}

welcomeChips.forEach(chip => {
    chip.addEventListener('click', () => {
        selectedEmotion = chip.dataset.emotion;
        userInput.value = chip.dataset.text;
        sendMessage();
    });
});

sendBtn.addEventListener('click', () => { lastInputMode = 'text'; sendMessage(); });
userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { 
        e.preventDefault(); 
        lastInputMode = 'text'; // Text kiritilganda uzluksiz ovozli chat to'xtatiladi
        sendMessage(); 
    }
});

function autoResizeInput() {
    userInput.style.height = 'auto';
    userInput.style.height = Math.min(userInput.scrollHeight, 100) + 'px';
}
userInput.addEventListener('input', autoResizeInput);

function showTyping(v) { typingIndicator.classList.toggle('visible', v); scrollToBottom(); }

resetBtn.addEventListener('click', async () => {
    try { await fetch(`${API_BASE}/reset`, { method: 'POST' }); } catch (e) {}
    if (isSpeaking) stopSpeaking();
    chatArea.innerHTML = '';
    chatArea.appendChild(welcomeScreen);
    welcomeScreen.style.display = '';
    showToast('Suhbat tozalandi ✨');
});

function escapeHtml(t) { const d = document.createElement('div'); d.textContent = t; return d.innerHTML; }
function scrollToBottom() { requestAnimationFrame(() => { chatArea.scrollTop = chatArea.scrollHeight; }); }
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
function showToast(msg, dur = 3000) {
    toast.textContent = msg;
    toast.classList.add('visible');
    setTimeout(() => toast.classList.remove('visible'), dur);
}

// ═══════════════════════════════════════════════════════════════════════
// WEBSOCKET ULANISH
// ═══════════════════════════════════════════════════════════════════════
function initWebSocket() {
    if (chatSocket && chatSocket.readyState === WebSocket.OPEN) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/chat`;

    chatSocket = new WebSocket(wsUrl);

    chatSocket.onopen = () => {
        console.log('WebSocket ulandi!');
    };

    chatSocket.onmessage = async (event) => {
        try {
            const data = JSON.parse(event.data);
            
            await sleep(200); // Kichik tabiiy kechikish
            showTyping(false);
            
            // AI javobini qo'shish
            addMessage(data.response, 'ai', data.emotion_received, data.emoji, data.risk_level, data.risk_confidence);
            
            // Audio ijrosi
            speakResponse(data.audio_url, data.response, data.emotion_received);
            
        } catch (err) {
            console.error('WebSocket JSON xato:', err);
            showTyping(false);
        } finally {
            isLoading = false;
            sendBtn.disabled = false;
        }
    };

    chatSocket.onclose = () => {
        console.log('WebSocket uzildi, qayta ulanmoqda...');
        // Uzilib qolsa xatolik holatini tozalash
        if (isLoading) {
            showTyping(false);
            isLoading = false;
            sendBtn.disabled = false;
            showToast('Aloqa uzildi. Yana urinib ko\'ring.');
        }
        setTimeout(initWebSocket, 3000);
    };

    chatSocket.onerror = (err) => {
        console.error('WebSocket xatosi:', err);
    };
}

// ═══════════════════════════════════════════════════════════════════════
// BOSHLASH
// ═══════════════════════════════════════════════════════════════════════
window.addEventListener('DOMContentLoaded', async () => {
    initWebSocket();
    await initCamera();
    initSpeechRecognition();
});
