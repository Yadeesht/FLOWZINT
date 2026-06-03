"""
scheduler.py — EduFlow AI Background Scheduler

Uses APScheduler to run proactive reminder jobs. In demo mode, sends
mock WhatsApp reminders to pre-seeded enrolled students to demonstrate
the scheduled reminder feature during the judge walkthrough.
"""

import json
import logging
from pathlib import Path
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.services import whatsapp_service

logger = logging.getLogger(__name__)
DATA_DIR = Path(__file__).parent.parent / "data"

scheduler = AsyncIOScheduler()


def _load_json(filename: str) -> list | dict:
    try:
        with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


async def _send_demo_reminders():
    """
    Demo scheduler job — fires every 10 minutes and sends simulated
    reminders to enrolled students. This demonstrates APScheduler
    integration in the Admin Dashboard's WhatsApp outbound log.
    """
    try:
        students_data = _load_json("students.json")
        enrolled = [
            s for s in students_data.get("verified_students", [])
            if s.get("enrolled") and s.get("enrolled_course")
        ]

        if not enrolled:
            logger.info("[Scheduler] No enrolled students to remind.")
            return

        # Cycle through reminder types for demo
        reminder_types = ["class", "exam", "fee"]
        hour = datetime.now().hour
        reminder_type = reminder_types[hour % len(reminder_types)]

        for student in enrolled[:3]:  # Max 3 per run for demo
            course_name = student.get("enrolled_course", "your course").replace("-", " ").title()
            details_map = {
                "class": "Topic: Advanced Concepts — Reviewing pre-class notes recommended!",
                "exam": "Topics covered: Modules 1-4. Open-book quiz.",
                "fee": "Amount: ₹4,500 EMI instalment. Pay at https://eduflow.ai/pay",
            }
            whatsapp_service.send_reminder(
                phone=student["phone"],
                name=student["name"],
                reminder_type=reminder_type,
                course_name=course_name,
                details=details_map.get(reminder_type, ""),
            )

        logger.info(f"[Scheduler] Sent {reminder_type} reminders to {len(enrolled)} students")

    except Exception as e:
        logger.error(f"[Scheduler Error] {e}")


async def _update_hot_leads():
    """
    Periodically compute and store hot leads in analytics.json.
    Hot leads = unenrolled students actively engaging (message_count >= 1),
    scored dynamically by engagement and urgency needs (confused/frustrated).
    """
    try:
        students_data = _load_json("students.json")
        verified = students_data.get("verified_students", [])

        hot_leads = []
        for s in verified:
            if s.get("enrolled"):
                continue
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

            hot_leads.append({
                "name": s["name"],
                "phone": s["phone"],
                "course_interest": s.get("course_interest", "Unknown"),
                "message_count": msg_count,
                "sentiment": last_sentiment,
                "score": min(100, score),
                "last_active": s.get("last_active", ""),
            })

        hot_leads.sort(key=lambda x: x["score"], reverse=True)

        analytics_path = DATA_DIR / "analytics.json"
        with open(analytics_path, "r", encoding="utf-8") as f:
            analytics = json.load(f)

        analytics["hot_leads"] = hot_leads[:10]
        analytics["last_updated"] = datetime.now().isoformat(timespec="seconds")

        with open(analytics_path, "w", encoding="utf-8") as f:
            json.dump(analytics, f, indent=2, ensure_ascii=False)

        logger.info(f"[Scheduler] Updated hot leads: {len(hot_leads)} leads scored")

    except Exception as e:
        logger.error(f"[Hot Leads Scheduler Error] {e}")


def start_scheduler():
    """Register and start all background jobs."""
    if scheduler.running:
        return

    # Demo reminders — every 10 minutes
    scheduler.add_job(
        _send_demo_reminders,
        trigger=IntervalTrigger(minutes=10),
        id="demo_reminders",
        name="Demo WhatsApp Reminders",
        replace_existing=True,
        misfire_grace_time=60,
    )

    # Hot leads scoring — every 5 minutes
    scheduler.add_job(
        _update_hot_leads,
        trigger=IntervalTrigger(minutes=5),
        id="hot_leads",
        name="Hot Leads Scorer",
        replace_existing=True,
        misfire_grace_time=30,
    )

    scheduler.start()
    logger.info("[Scheduler] APScheduler started with demo reminders & hot leads jobs")


def stop_scheduler():
    """Gracefully stop the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[Scheduler] APScheduler stopped")
