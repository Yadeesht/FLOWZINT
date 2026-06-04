<div align="center">

<h1>
  <img src="https://img.shields.io/badge/EduFlow_AI-Support_Bot-6C63FF?style=for-the-badge&logo=openai&logoColor=white" alt="EduFlow AI" />
</h1>

<p><strong>An intelligent AI-powered student support & enrollment assistant for coaching institutes.</strong><br/>
Built on Azure OpenAI · FastAPI · Next.js · WhatsApp Integration</p>

<p>
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi&logoColor=white"/>
  <img src="https://img.shields.io/badge/Next.js-14-000000?style=flat-square&logo=nextdotjs&logoColor=white"/>
  <img src="https://img.shields.io/badge/Azure_OpenAI-GPT--4o-0078D4?style=flat-square&logo=microsoftazure&logoColor=white"/>
  <img src="https://img.shields.io/badge/Deployed_on-Azure_VM-0089D6?style=flat-square&logo=microsoftazure&logoColor=white"/>
</p>

</div>

<br/>

<div align="center">
<table width="80%" style="border: 2px solid #6C63FF; border-radius: 12px; background: #0d1117;">
<tr>
<td align="center" width="50%" style="padding: 20px;">

### 🌐 Live Application

## **[→ http://98.70.51.30](http://98.70.51.30)**

*Click to open the live deployed app*

</td>
<td align="center" width="50%" style="padding: 20px; border-left: 2px solid #6C63FF;">

### 📖 API Documentation

## **[→ http://98.70.51.30/docs](http://98.70.51.30/docs)**

*Interactive Swagger UI for all endpoints*

</td>
</tr>
</table>
</div>

<br/>

---

## 📋 Table of Contents

| Section | What's Inside |
|---|---|
| [✨ Features](#-features) | Core capabilities of EduFlow AI |
| [🏗️ Architecture](#️-architecture) | How the system is built & connected |
| [🚀 Deployment](#-deployment) | How it runs on the Azure VM |
| [⚙️ Setup & Configuration](#️-setup--configuration) | Steps to run it yourself |
| [📡 API Reference](#-api-reference) | Key backend routes |
| [📝 A Note](#-a-note) | Final thoughts |

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 🤖 Conversational AI Chat
The core of EduFlow AI is a streaming-capable chat engine powered by **Azure OpenAI (GPT-4o)**. Students ask questions in plain language and get structured, friendly answers about courses, fees, batch timings, and FAQs — all sourced from live JSON data files loaded at runtime. No hardcoded answers.

</td>
<td width="50%">

### 📝 In-Chat Enrollment
Students can **enroll directly inside the chat** without visiting another page. When a student confirms they want to join a batch, the AI calls the `enroll_in_batch` tool which writes their record, updates the JSON data store, and sends a confirmation — all in one conversation turn.

</td>
</tr>
<tr>
<td width="50%">

### 💬 WhatsApp Notifications
After enrollment or when a student asks for details to be sent, the AI uses the `send_whatsapp_message` tool to dispatch a real WhatsApp message via **pywhatkit** to the student's registered phone number. The chat clearly confirms when a message has been sent.

</td>
<td width="50%">

### 📊 Real-Time Sentiment Analysis
Every AI response is appended with a `SENTIMENT:` tag (`positive | neutral | frustrated | confused`). The frontend strips this tag and uses it internally. If the system detects 2+ frustrated signals, the AI proactively offers to escalate to a human coordinator.

</td>
</tr>
<tr>
<td width="50%">

### 🛡️ OTP Phone Verification
Before a student can chat, they verify their phone number via a **6-digit OTP**. This ensures all chat sessions are tied to real, verified users — preventing anonymous spam and anchoring the enrollment data to confirmed phone numbers.

</td>
<td width="50%">

### 🧑‍💼 Admin Copilot Dashboard
A full **admin panel** (password-protected) gives coordinators a real-time view of all active chats, enrollment analytics, inactive student nudges, and a built-in AI copilot that can answer internal queries about student data.

</td>
</tr>
</table>

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     NGINX (Port 80)                     │
│         Reverse Proxy · Routes /api/* to backend        │
└──────────────────┬──────────────────┬───────────────────┘
                   │                  │
       ┌───────────▼──────┐  ┌────────▼────────────┐
       │  Next.js Frontend│  │  FastAPI Backend     │
       │  (Port 3000)     │  │  (Port 8000)         │
       │                  │  │                      │
       │  ChatWindow.jsx  │  │  /api/chat           │
       │  OTPScreen.jsx   │  │  /api/otp            │
       │  AdminDashboard  │  │  /api/enroll         │
       │  MessageBubble   │  │  /api/admin-copilot  │
       └──────────────────┘  │  /api/inactive       │
                             └────────┬─────────────┘
                                      │
                    ┌─────────────────┼──────────────────┐
                    │                 │                   │
          ┌─────────▼──────┐ ┌───────▼──────┐ ┌────────▼──────┐
          │  Azure OpenAI  │ │ JSON Data    │ │  WhatsApp     │
          │  GPT-4o API    │ │ Store        │ │  Bot (3001)   │
          │  (with local   │ │ courses.json │ │  pywhatkit    │
          │  fallback)     │ │ batches.json │ │               │
          └────────────────┘ └──────────────┘ └───────────────┘
```

The backend is a **FastAPI** app served by **Uvicorn**, managed by **PM2** for process persistence and auto-restart. All three processes (backend, frontend, whatsapp-bot) are declared in `ecosystem.config.js` and managed as a single unit.

---

## 🚀 Deployment

The application is deployed on a **Microsoft Azure VM** running Ubuntu, accessible at:

> **[http://98.70.51.30](http://98.70.51.30)**

### Process Management (PM2)

All three services are managed by PM2:

```bash
# Start all services
pm2 start ecosystem.config.js

# Check running processes
pm2 status

# View logs for a specific service
pm2 logs flowzint-backend
pm2 logs flowzint-frontend
pm2 logs flowzint-whatsapp-bot

# Restart everything (e.g. after a git pull)
pm2 restart all
```

### Pulling Updates to the VM

```bash
git pull                          # fetch latest from origin/main
pm2 restart all                   # apply changes to running processes
```

---

## ⚙️ Setup & Configuration

### Prerequisites
- Python 3.11+
- Node.js 18+
- An Azure OpenAI resource with a GPT-4o (or GPT-3.5) deployment

### 1. Clone & Configure Environment

```bash
git clone https://github.com/Yadeesht/FLOWZINT.git
cd FLOWZINT/backend
cp .env.example .env
```

Edit `.env` and fill in your credentials:

```env
AZURE_OPENAI_API_KEY=your_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_API_VERSION=2024-02-15-preview
WHATSAPP_PHONE=9876543210     # optional, for real WhatsApp messages
FRONTEND_URL=http://localhost:3000
```

> **Note:** If no Azure credentials are provided, the backend automatically falls back to a local keyword-based semantic matcher — the app stays fully functional in demo mode.

### 2. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev                      # development
npm run build && npm run start   # production
```

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/chat` | Send a student message, receive AI response + sentiment |
| `POST` | `/api/otp/send` | Send OTP to a student's phone |
| `POST` | `/api/otp/verify` | Verify submitted OTP |
| `POST` | `/api/enroll` | Enroll a student into a batch |
| `GET` | `/api/admin/chats` | Fetch all active chat sessions (admin) |
| `POST` | `/api/admin-copilot` | Admin-facing AI copilot query |
| `GET` | `/docs` | Auto-generated Swagger UI |

---

## 📝 A Note

EduFlow AI was built as a production-grade demonstration of how conversational AI can replace static FAQ pages and manual enrollment processes for educational institutes. The system is intentionally designed to degrade gracefully — if the Azure API is down or unconfigured, a local semantic engine steps in so the student experience is never broken.

---

<div align="center">
  <sub>Built with ❤️ · Deployed on Azure · Powered by GPT-4o</sub>
</div>
