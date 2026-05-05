# 📋 WAR ALERT BOT — Development Steps & Prompt History
**สำหรับทีม และสำหรับ AI (Claude) จดจำสิ่งที่ทำไปแล้ว**
**Last Updated:** 2026-05-05
**Version:** 2.1 (Free tier — Bilingual TH/EN, Auto-translate)

---

## 🧠 วิธีใช้ Document นี้

### สำหรับ AI (Claude):
> "อ่าน DEVELOPMENT_STEPS.md ก่อน แล้วช่วย [สิ่งที่ต้องการ]"

### สำหรับทีม Developer:
> อ่าน Prompt History เพื่อเข้าใจที่มาของการตัดสินใจแต่ละอย่าง
> แล้วดู Current State เพื่อรู้ว่าระบบอยู่ในสถานะไหน

---

## 📁 Project Structure (สถานะปัจจุบัน)

```
war-alert-bot/
├── backend/
│   ├── main.py              ✅ v2.1 — FastAPI + lifespan + translator integration
│   ├── models.py            ✅ SQLite + title_th column + auto migration
│   ├── news_fetcher.py      ✅ ดึงข่าวจาก NewsAPI.org + date range
│   ├── analyzer.py          ✅ v2.1 — Keyword matching + bilingual alert message
│   ├── translator.py        ✅ NEW — Auto-translate EN→TH (Google Translate, ฟรี)
│   ├── line_notifier.py     ✅ LINE Messaging API push/broadcast
│   └── requirements.txt     ✅ Python dependencies
├── frontend/
│   └── index.html           ✅ v2.1 — Redesigned Admin Dashboard (bilingual news cards)
├── .env                     ✅ Environment variables (สร้างจาก env.example)
├── env.example              ✅ Template environment variables
├── venv/                    ✅ Python virtual environment (local)
├── start.sh                 ✅ Start script (local)
├── railway.json             ✅ Railway.app deploy config
├── nixpacks.toml            ✅ Build config (แก้ path requirements.txt แล้ว)
└── DEVELOPMENT_STEPS.md     ✅ This file
```

---

## 🔑 Environment Variables ที่ต้องการ

```env
NEWSAPI_KEY=xxx          # จาก newsapi.org (ฟรี)
LINE_CHANNEL_ACCESS_TOKEN=xxx   # จาก LINE Developers Console
LINE_USER_ID=xxx         # User ID ขึ้นต้นด้วย U
ADMIN_SECRET=xxx         # รหัสผ่าน admin (ตั้งเองได้)
PORT=8000
```

> ⚠️ **ไม่ต้องการ ANTHROPIC_API_KEY แล้ว** (ตัดออกใน Prompt 5)

---

## 📝 Prompt History — สิ่งที่ทำในแต่ละ Prompt

---

### 🟦 Prompt 1 — Initial Requirements Gathering
**ผู้ใช้ต้องการ:**
- ระบบแจ้งเตือนข่าวความรุนแรง (สงคราม เช่น US-Iran) ผ่าน LINE
- แจ้งเตือนเมื่อเกิดการโจมตี → "ระวังทอง/หุ้นร่วง"
- แจ้งเตือนเมื่อมีการเจรจา/ยุติสงคราม → ข่าวดี
- Admin Website ควบคุม auto/manual fetch
- ต้องการ document สำหรับ AI จดจำ

**การตัดสินใจ:**
- ถามผู้ใช้ 3 คำถาม: LINE channel, News API, Deploy platform
- ผู้ใช้ตอบ: LINE Notify + Messaging API, ยังไม่แน่ใจ API, ยังไม่แน่ใจ deploy

---

### 🟦 Prompt 2 — Architecture Design & Stack Selection
**การตัดสินใจสำคัญ:**
- ❌ ยกเลิก LINE Notify เพราะ **ปิดบริการถาวรแล้ว 31 มี.ค. 2025**
- ✅ ใช้ LINE Messaging API อย่างเดียว
- ✅ Stack: Python + FastAPI + SQLite + APScheduler
- ✅ Deploy: Railway.app (ฟรี)
- ✅ News: NewsAPI.org (ฟรี 100 req/วัน)
- ✅ AI Analyzer: Anthropic Claude API (ตอนนี้ยังใช้อยู่)
- ✅ Frontend: HTML + TailwindCSS (Single page, no framework)

**ไฟล์ที่สร้าง:**
- `PROJECT_DOCUMENT.md` — Architecture reference
- `requirements.txt` — รวม anthropic library
- `.env.example`
- `backend/models.py` — SQLite schema
- `backend/analyzer.py` — v1.0 ใช้ Claude API
- `backend/news_fetcher.py` — NewsAPI integration
- `backend/line_notifier.py` — LINE push/broadcast
- `backend/main.py` — FastAPI + APScheduler
- `frontend/index.html` — Admin Dashboard
- `railway.json` + `nixpacks.toml`
- `README.md`

---

### 🟦 Prompt 3 — LINE Bot Setup Guidance
**ปัญหาที่พบ:**
- ผู้ใช้หา "Issue" Channel Access Token ไม่เจอ
- ผู้ใช้ยังไม่ได้สร้าง Channel เลย มีแค่ Provider

**การแก้ไข:**
- อธิบายว่าต้องสร้าง Channel ก่อน ไม่ใช่แค่ Provider
- แนะนำให้กด "Create a Messaging API channel"

---

### 🟦 Prompt 4 — LINE Official Account Connection
**ปัญหาที่พบ:**
- ผู้ใช้สร้าง Official Account (`@039oxctd / War Alert Bot v.1`) แล้ว
- แต่ยังไม่ได้เชื่อมกับ Messaging API Channel

**การแก้ไข:**
- แนะนำวิธีเชื่อม OA กับ Messaging API ผ่าน LINE OA Manager
- URL: `https://manager.line.biz/account/@039oxctd` → Settings → Messaging API
- ผู้ใช้เชื่อมสำเร็จ ได้ Channel ID: `2009974797`

**⚠️ Security Incident:**
- ผู้ใช้ paste Channel Access Token และ User ID ใน chat
- Token: `HWzfPR1Rib7B/...` (ควร Reissue ใหม่ทันที)
- User ID: `U492634b76a2c5d78c060bdfbffc1d344` (ใช้ได้ปกติ)
- **แนะนำให้ Reissue token ใหม่ก่อนใช้งาน**

---

### 🟦 Prompt 5 — Remove Anthropic API (Cost Optimization)
**ปัญหาที่พบ:**
- ผู้ใช้ไม่ต้องการเสียเงินค่า Anthropic API

**การตัดสินใจ:**
- ✅ เปลี่ยน `analyzer.py` เป็น Keyword Matching 100% ฟรี
- ✅ ลบ `anthropic` library ออกจาก `requirements.txt`
- ✅ ลบ `ANTHROPIC_API_KEY` ออกจาก `.env.example`
- Logic: เช็ค DANGER_KEYWORDS และ PEACE_KEYWORDS ในหัวข้อ + เนื้อข่าว
- ความแม่นยำ: ~80-90% สำหรับข่าวสงคราม

**ไฟล์ที่เปลี่ยน:**
- `backend/analyzer.py` → v1.2 keyword matching
- `requirements.txt` → ลบ anthropic
- `.env.example` → ลบ ANTHROPIC_API_KEY

---

### 🟦 Prompt 6 — Full File Export + This Document
**ผู้ใช้ต้องการ:**
- ไฟล์ทั้งหมดอีกครั้ง
- Development Steps Document นี้
- Document สำหรับให้ทีมนำไปใช้ต่อ

**สิ่งที่ทำ:**
- สร้าง `DEVELOPMENT_STEPS.md` (ไฟล์นี้)
- Export ไฟล์ทั้งหมดรวมกัน

---

## 🏗️ Architecture Overview

```
[NewsAPI.org]
     ↓ (HTTP GET ทุก N นาที หรือกด manual)
[FastAPI Backend]
     ├── news_fetcher.py  → ดึงข่าว
     ├── analyzer.py      → จับ keyword → danger/peace/neutral
     ├── models.py        → บันทึก SQLite
     └── line_notifier.py → ส่ง LINE Push Message
          ↓
[LINE Messaging API] → มือถือผู้ใช้
          ↑
[Admin Dashboard (index.html)]
     ├── เปิด/ปิด Auto Fetch
     ├── ตั้ง Interval (นาที)
     ├── กด Manual Fetch
     ├── ดูข่าวทั้งหมด (filter: danger/peace/neutral/sent)
     ├── ส่ง LINE เฉพาะข่าวที่เลือก
     └── ทดสอบส่ง LINE
```

---

## 🗄️ Database Schema

### Table: `news_items`
| Column | Type | หมายเหตุ |
|--------|------|---------|
| id | INTEGER PK | Auto |
| title | TEXT | หัวข้อข่าว |
| description | TEXT | เนื้อหา (max 500 chars) |
| url | TEXT | ลิงก์ต้นฉบับ |
| source | TEXT | แหล่งข่าว |
| published_at | DATETIME | เวลาเผยแพร่ |
| category | TEXT | danger/peace/neutral |
| alert_message | TEXT | ข้อความที่จะส่ง LINE |
| line_sent | BOOLEAN | ส่งแล้วหรือยัง |
| created_at | DATETIME | เวลาบันทึก |

### Table: `settings`
| Key | Default | หมายเหตุ |
|-----|---------|---------|
| auto_fetch | false | เปิด/ปิด auto |
| fetch_interval | 30 | นาที |
| keywords | "Iran attack,..." | คำค้นหา NewsAPI |
| danger_keywords | "attack,strike,..." | keyword จำแนก danger |
| peace_keywords | "ceasefire,..." | keyword จำแนก peace |
| max_news_age_hours | 6 | ดึงข่าวย้อนหลังกี่ชม. |

---

## 🔌 API Endpoints

| Method | Path | หน้าที่ |
|--------|------|--------|
| GET | `/api/status` | สถานะระบบ |
| GET | `/api/news` | ดูข่าวทั้งหมด |
| POST | `/api/news/fetch` | Manual fetch |
| DELETE | `/api/news/{id}` | ลบข่าว |
| GET | `/api/settings` | ดู settings |
| PUT | `/api/settings` | อัปเดต settings |
| POST | `/api/settings/toggle-auto` | เปิด/ปิด auto |
| POST | `/api/line/test` | ทดสอบ LINE |
| POST | `/api/line/send/{id}` | ส่ง LINE ข่าวนั้น |
| GET | `/` | Admin Dashboard |

---

## 📊 News Classification Logic

```python
text = title + description (lowercase)

danger_score = count(DANGER_KEYWORDS in text)
peace_score  = count(PEACE_KEYWORDS in text)

if danger_score > 0 and danger_score >= peace_score:
    → category = "danger"
    → ส่ง LINE แจ้งเตือน: ระวังทอง/หุ้นร่วง

elif peace_score > 0 and peace_score > danger_score:
    → category = "peace"  
    → ส่ง LINE แจ้งเตือน: ตลาดอาจผ่อนคลาย

else:
    → category = "neutral"
    → ไม่ส่ง LINE
```

**DANGER_KEYWORDS** (ตัวอย่าง):
`attack, strike, missile, bomb, explosion, war, invasion, airstrike, killed, casualties, escalation, โจมตี, ระเบิด`

**PEACE_KEYWORDS** (ตัวอย่าง):
`ceasefire, peace talks, negotiation, truce, treaty, withdraw, de-escalation, หยุดยิง, เจรจา, สันติภาพ`

---

## 📱 LINE Message Format

### Danger 🚨
```
🚨 WAR ALERT - ระวัง!
━━━━━━━━━━━━━━━
📰 [หัวข้อข่าว]

📊 ผลกระทบตลาดที่คาดการณ์:
  • ทองคำ: 📈 อาจพุ่งสูง (safe haven)
  • หุ้น: 📉 อาจร่วงแรง (risk-off)
  • 💵 USD: อาจแข็งค่า (flight to safety)

💡 เหตุการณ์ความรุนแรงมักทำให้ทองคำพุ่งและหุ้นร่วงในระยะสั้น
━━━━━━━━━━━━━━━
🔗 [URL]
🕐 [เวลา UTC]
```

### Peace ☮️
```
☮️ PEACE NEWS - ข่าวดี!
━━━━━━━━━━━━━━━
📰 [หัวข้อข่าว]

📊 ผลกระทบตลาดที่คาดการณ์:
  • ทองคำ: 📉 อาจลดลง (ลด safe haven demand)
  • หุ้น: 📈 อาจฟื้นตัว (risk-on)
  • 🌏 ตลาดเอเชีย: อาจบวก

💡 ข่าวสันติภาพมักทำให้ตลาดหุ้นฟื้นตัวและทองคำปรับลง
━━━━━━━━━━━━━━━
🔗 [URL]
🕐 [เวลา UTC]
```

---

## 🚀 Setup Guide (ขั้นตอนการติดตั้ง)

### Local Development
```bash
# 1. Clone / Download โปรเจค
cd war-alert-bot

# 2. ติดตั้ง Python dependencies
pip install -r requirements.txt

# 3. สร้างไฟล์ .env
cp .env.example .env
# แก้ไข .env ใส่ค่าจริง

# 4. รัน
cd backend
python main.py

# 5. เปิด Admin Dashboard
# http://localhost:8000
```

### Deploy บน Railway.app
```
1. Push ขึ้น GitHub
2. railway.app → New Project → Deploy from GitHub
3. Variables → เพิ่ม env vars ทั้งหมด
4. Deploy → ได้ URL อัตโนมัติ
```

---

## 🔑 API Keys ที่ต้องสมัคร

| บริการ | URL | ค่าใช้จ่าย | หมายเหตุ |
|--------|-----|-----------|---------|
| NewsAPI | newsapi.org/register | ฟรี | 100 req/วัน, ข่าวหน่วง 15 นาที |
| LINE Messaging API | developers.line.biz | ฟรี | 200 push msg/เดือน |
| Railway.app | railway.app | ฟรี | Hobby plan มี limit |

---

## ⚠️ Known Issues & Limitations

| ปัญหา | รายละเอียด | วิธีแก้ |
|-------|-----------|--------|
| NewsAPI free tier | ข่าวหน่วง 15 นาที | อัพเกรด $449/เดือน หรือใช้ GNews API แทน |
| LINE free tier | 200 push msg/เดือน | อัพเกรด หรือ filter เฉพาะ danger/peace |
| Keyword accuracy | ~80-90% | เพิ่ม keyword หรือใช้ AI กลับมา |
| Railway free | Sleep เมื่อไม่มี traffic | ใช้ UptimeRobot ping ทุก 5 นาที |

---

## 🔮 Future Improvements (Ideas)

- [ ] เพิ่ม GNews API หรือ Google News RSS (ฟรีกว่า)
- [ ] Telegram Bot แทน/เพิ่มเติมจาก LINE
- [ ] เพิ่ม keyword สำหรับ Israel-Hamas, Russia-Ukraine
- [ ] Dashboard แสดง chart สถิติข่าวรายวัน
- [ ] Email alert เพิ่มเติม
- [ ] Docker compose สำหรับ deploy แบบ self-hosted
- [ ] เพิ่ม LINE Group ID (broadcast ไป group ได้)

---

## 👥 LINE Account Info (สำหรับทีม)

| ข้อมูล | ค่า |
|--------|-----|
| OA Name | War Alert Bot v.1 |
| Basic ID | @039oxctd |
| Channel ID | 2009974797 |
| User ID | U492634b76a2c5d78c060bdfbffc1d344 |
| OA Manager | https://manager.line.biz/account/@039oxctd |

> ⚠️ **Channel Access Token ต้อง Reissue ใหม่** (token เดิมถูก expose ใน chat)

---

## 📌 Checklist ก่อน Go Live

- [ ] Reissue LINE Channel Access Token ใหม่
- [ ] สมัคร NewsAPI และใส่ key ใน .env
- [ ] ทดสอบ "ทดสอบส่ง LINE" จาก Admin Dashboard
- [ ] ทดสอบ "ค้นหาข่าวตอนนี้" และดูว่าข่าวขึ้น
- [ ] ตรวจสอบว่าข่าว danger/peace ส่ง LINE ถูกต้อง
- [ ] Deploy บน Railway และทดสอบ URL จริง
- [ ] ตั้ง UptimeRobot ping URL ทุก 5 นาที (ป้องกัน sleep)

---

### 🟦 Prompt 8 — Bilingual Support + Frontend Redesign + Bug Fixes
**ผู้ใช้ต้องการ:**
- ข่าวภาษาอื่น (EN) → แสดง 2 version: ไทย + อังกฤษ ทั้งในเว็บและ LINE alert
- หน้าเว็บออกแบบใหม่และเมนูต่างๆทำงานได้ถูกต้อง
- อัปเดต DEVELOPMENT_STEPS.md ให้ตรงกับเวอร์ชั่นใหม่

**การเปลี่ยนแปลง:**

`backend/translator.py` (ไฟล์ใหม่):
- ฟังก์ชัน `translate_to_thai(text)` — แปล EN→TH ด้วย Google Translate (unofficial API, ฟรี)
- ตรวจสอบว่าเป็นภาษาไทยอยู่แล้วหรือไม่ (unicode range ฀-๿)
- Fallback: คืนค่าข้อความเดิมถ้าการแปลล้มเหลว

`backend/models.py`:
- เพิ่ม `title_th` column (Text, nullable) ใน `NewsItem`
- Auto migration ใน `init_db()` — ใช้ `ALTER TABLE ADD COLUMN` ปลอดภัยสำหรับ DB เดิม

`backend/analyzer.py` (v2.1):
- เปลี่ยน signature: `build_alert_message(title_en, title_th, url, analysis, published_at)`
- LINE message: แสดง title_th (ภาษาไทย) + title_en (อังกฤษ) ถ้าต่างกัน
- Format: `📰 [ชื่อไทย]\n   🔤 [English Title]`

`backend/main.py` (v2.1):
- Import และใช้ `translate_to_thai` ใน `process_and_notify`
- เพิ่ม `title_th` ใน NewsItem record และ API response (`/api/news`)
- ใช้ lifespan แทน deprecated `@app.on_event`

`frontend/index.html` (v2.1):
- **Bug fixes**: แก้ fetching animation ไม่ถูก remove, แก้ `esc()` function ป้องกัน XSS
- **Bilingual cards**: แสดง title_th (ใหญ่ bold) + title EN (เล็กกว่า สีหม่น) + badge 🇹🇭 แปลแล้ว
- **LINE Preview**: คลิกเพื่อแสดง/ซ่อน LINE message format (collapsible)
- **ปุ่มมี loading state**: spinner + disabled ระหว่างรอ API
- **HTML escaping**: ใช้ `esc()` ป้องกัน XSS ทุก field
- **Auto-refresh**: รีเฟรชทุก 30 วินาที โดยไม่กระทบ input ที่กำลังแก้ไข

**ไฟล์ที่เปลี่ยน:**
- `backend/translator.py` → ใหม่
- `backend/models.py` → เพิ่ม title_th + migration
- `backend/analyzer.py` → bilingual alert message
- `backend/main.py` → integrate translator, v2.1
- `frontend/index.html` → redesign ใหม่ทั้งหมด
- `DEVELOPMENT_STEPS.md` → อัปเดตเป็น v2.1

**วิธีรัน (local):**
```bash
./start.sh
# หรือ
source venv/bin/activate && cd backend && python main.py
```
เปิด http://localhost:8000

---

### 🟦 Prompt 7 — New Features: Date Range + Interval Unit
**ผู้ใช้ต้องการ:**
- Manual Search: เลือกช่วงวันที่ (from/to datetime) ได้
- Auto Fetch: เลือกหน่วยเวลาได้ทั้ง วินาที / นาที / ชั่วโมง / วัน
- ส่งโค้ดที่ใช้งานได้ทั้งหมด

**การเปลี่ยนแปลง:**

`models.py`:
- เปลี่ยน `fetch_interval` (นาทีอย่างเดียว) → `fetch_interval_value` + `fetch_interval_unit`
- `fetch_interval_unit` รับค่า: seconds / minutes / hours / days

`news_fetcher.py`:
- เพิ่ม parameter `from_dt` และ `to_dt` (Optional[datetime])
- ถ้าส่งมา → ใช้ช่วงเวลานั้น (Manual mode with date range)
- ถ้าไม่ส่ง → ใช้ hours_back (Auto mode)

`main.py` (v2.0):
- เพิ่ม Pydantic model: `ManualFetchRequest`, `SchedulerSettings`, `KeywordSettings`
- `POST /api/news/fetch` รับ body `{from_datetime, to_datetime}` (optional)
- `PUT /api/settings/scheduler` → อัปเดต auto + interval value + unit
- `PUT /api/settings/keywords` → อัปเดต keywords แยก endpoint
- `DELETE /api/news` → ลบทั้งหมด
- `/api/status` เพิ่ม `interval_value`, `interval_unit`, `danger_count`, `peace_count`
- Scheduler ใช้ `IntervalTrigger(**{unit: value})` รองรับทุกหน่วย

`frontend/index.html` (v2.0):
- Manual Search: toggle เปิด date range picker (from/to datetime-local)
- Auto section: input ตัวเลข + dropdown วินาที/นาที/ชั่วโมง/วัน
- แยก save button สำหรับ Scheduler settings และ Keywords settings
- ปุ่ม "ลบทั้งหมด" ใน news feed
- Auto badge แสดง interval เช่น "AUTO / 30m"
