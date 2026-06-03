"""
main.py — EduFlow AI FastAPI Application

Entry point for the backend. Configures:
- CORS for Next.js frontend
- All API routes
- APScheduler background jobs on startup
- Analytics endpoint
- Health check
"""

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from app.routes import chat, otp, enroll, inactive, review, admin_copilot
from app.services.scheduler import start_scheduler, stop_scheduler

DATA_DIR = Path(__file__).parent / "data"


# ─── Lifespan ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start scheduler on boot, stop gracefully on shutdown."""
    start_scheduler()
    print("✅ EduFlow AI backend started — APScheduler running")
    yield
    stop_scheduler()
    print("🛑 EduFlow AI backend shutting down")


# ─── App ─────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="EduFlow AI API",
    description="Proactive AI-powered support and sales bot for coaching institutes",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow Next.js dev server and Vercel production
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        frontend_url,
        "https://*.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Routes ──────────────────────────────────────────────────────────────────

app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(otp.router, prefix="/api", tags=["otp"])
app.include_router(enroll.router, prefix="/api", tags=["enrollment"])
app.include_router(inactive.router, prefix="/api", tags=["inactivity"])
app.include_router(review.router, prefix="/api", tags=["reviews"])
app.include_router(admin_copilot.router, prefix="/api", tags=["admin-copilot"])


# ─── Core Endpoints ──────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "name": "EduFlow AI API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/api/analytics")
async def get_analytics():
    """Return full analytics data for the Admin Dashboard."""
    try:
        with open(DATA_DIR / "analytics.json", "r", encoding="utf-8") as f:
            analytics = json.load(f)
        return analytics
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/students")
async def get_students():
    """Return student pipeline data for the Admin Dashboard."""
    try:
        with open(DATA_DIR / "students.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        verified = data.get("verified_students", [])

        enrolled = [s for s in verified if s.get("enrolled")]
        investigated = [s for s in verified if not s.get("enrolled")]

        # Hot leads: unenrolled students who are actively engaging (message_count >= 1)
        # Prioritized by engagement level and immediate sentiment needs (confused/frustrated need immediate attention)
        hot_leads = []
        for s in investigated:
            msg_count = s.get("message_count", 0)
            if msg_count < 1:
                continue

            sentiments = s.get("sentiment_history", [])
            last_sentiment = sentiments[-1] if sentiments else "neutral"

            # Base score from message count engagement
            score = min(50, msg_count * 10)

            # Sentiment-based priority bump
            if last_sentiment == "confused":
                score += 40
            elif last_sentiment == "frustrated":
                score += 50
            elif last_sentiment == "positive":
                score += 30
            else:  # neutral
                score += 20

            hot_leads.append({**s, "score": min(100, score)})

        hot_leads.sort(key=lambda x: x["score"], reverse=True)

        return {
            "enrolled": enrolled,
            "investigated": investigated,
            "hot_leads": hot_leads[:10],
            "totals": {
                "enrolled": len(enrolled),
                "investigated": len(investigated),
                "hot_leads": len(hot_leads),
            },
        }
    except Exception as e:
        return {"error": str(e), "enrolled": [], "investigated": [], "hot_leads": []}


@app.get("/api/courses")
async def get_courses():
    """Return all courses data."""
    try:
        with open(DATA_DIR / "courses.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/batches")
async def get_batches():
    """Return all batch data."""
    try:
        with open(DATA_DIR / "batches.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}
