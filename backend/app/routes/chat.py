"""
chat.py — EduFlow AI Chat Route

Handles multi-turn conversational AI with:
- Per-session message history
- Azure OpenAI (or local fallback) response generation
- Sentiment detection and classification
- Analytics logging (session count, sentiment breakdown)
- Hot-lead scoring update on every turn
"""

import json
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.azure_openai import chat_with_llm

router = APIRouter()
DATA_DIR = Path(__file__).parent.parent / "data"

# In-memory session store: { session_token: { history, student_data } }
_sessions: dict[str, dict] = {}


# ─── Request / Response Models ───────────────────────────────────────────────

class ChatRequest(BaseModel):
    session_token: str
    message: str


class ChatResponse(BaseModel):
    response: str
    sentiment: str
    session_token: str
    student_name: str
    message_count: int


# ─── Helpers ────────────────────────────────────────────────────────────────

def _load_json(filename: str) -> dict | list:
    try:
        with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_json(filename: str, data: dict | list):
    try:
        with open(DATA_DIR / filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Save Error] {filename}: {e}")


def _update_student_record(phone: str, updates: dict):
    """Update a student's persistent record in students.json."""
    students = _load_json("students.json")
    for student in students.get("verified_students", []):
        if student["phone"] == phone:
            student.update(updates)
            break
    _save_json("students.json", students)


def _increment_analytics_sentiment(sentiment: str):
    """Bump the analytics sentiment counter."""
    try:
        analytics = _load_json("analytics.json")
        breakdown = analytics.get("sentiment_breakdown", {})
        breakdown[sentiment] = breakdown.get(sentiment, 0) + 1
        analytics["sentiment_breakdown"] = breakdown
        analytics["last_updated"] = datetime.now().isoformat(timespec="seconds")
        _save_json("analytics.json", analytics)
    except Exception as e:
        print(f"[Analytics Error] {e}")


def _detect_course_interest(message: str) -> str | None:
    """Detect if the message mentions a specific course and return its name."""
    courses = _load_json("courses.json")
    msg_lower = message.lower()
    for course in courses:
        if any(tag.lower() in msg_lower for tag in course["tags"]):
            return course["name"]
        if course["short_name"].lower() in msg_lower:
            return course["name"]
    return None


# ─── Routes ─────────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Process a student's chat message and return the AI response.
    """
    token = req.session_token
    if token not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found. Please verify OTP first.")

    session = _sessions[token]
    student = session["student"]
    history = session["history"]

    # Detect course interest update
    detected_course = _detect_course_interest(req.message)
    if detected_course and not student.get("course_interest"):
        student["course_interest"] = detected_course

    # Get AI response
    response, sentiment = chat_with_llm(req.message, history, student)

    # Track frustrated count
    if sentiment == "frustrated":
        student["frustrated_count"] = student.get("frustrated_count", 0) + 1

    # Auto-escalation trigger (3+ frustrated messages)
    if student.get("frustrated_count", 0) >= 3:
        response += (
            "\n\n⚠️ I can see this hasn't been resolved to your satisfaction. "
            "I've flagged your case for our support manager — you'll hear back within 2 hours. "
            "I'm really sorry for the trouble, and we'll make this right!"
        )
        student["frustrated_count"] = 0  # Reset after escalation

    # Update history (keep last 20 messages to prevent token overflow)
    history.append({"role": "user", "content": req.message})
    history.append({"role": "assistant", "content": response})
    if len(history) > 20:
        history = history[-20:]
    session["history"] = history

    # Update session data
    student["message_count"] = student.get("message_count", 0) + 1
    student["last_active"] = datetime.now().isoformat(timespec="seconds")
    if detected_course:
        student["course_interest"] = detected_course
    sentiment_history = student.get("sentiment_history", [])
    sentiment_history.append(sentiment)
    student["sentiment_history"] = sentiment_history[-10:]  # Keep last 10
    session["student"] = student

    # Persist updates to students.json
    if student.get("phone"):
        _update_student_record(student["phone"], {
            "message_count": student["message_count"],
            "last_active": student["last_active"],
            "course_interest": student.get("course_interest"),
            "sentiment_history": student["sentiment_history"],
            "frustrated_count": student.get("frustrated_count", 0),
        })

    # Update analytics
    _increment_analytics_sentiment(sentiment)

    return ChatResponse(
        response=response,
        sentiment=sentiment,
        session_token=token,
        student_name=student.get("name", "Student"),
        message_count=student["message_count"],
    )


@router.get("/chat/session/{token}")
async def get_session(token: str):
    """Get current session info (used by frontend to restore state)."""
    if token not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    session = _sessions[token]
    return {
        "student": session["student"],
        "message_count": session["student"].get("message_count", 0),
        "history_length": len(session["history"]),
    }


# ─── Exposed session store (for use by otp.py) ──────────────────────────────
def create_session(student: dict) -> str:
    """Create a new session for a verified student. Returns session token."""
    token = str(uuid.uuid4())
    _sessions[token] = {
        "student": student.copy(),
        "history": [],
    }
    return token


def get_session_student(token: str) -> dict | None:
    """Retrieve student data from an active session."""
    if token in _sessions:
        return _sessions[token]["student"]
    return None


def update_session_student(token: str, updates: dict):
    """Update student data in an active session."""
    if token in _sessions:
        _sessions[token]["student"].update(updates)


# === WhatsApp Webhook Integration ===

def _get_or_create_student_by_phone(phone: str, name: str = "WhatsApp Student") -> dict:
    """Look up an existing student by phone or create a new verified record."""
    students = _load_json("students.json")
    verified = students.get("verified_students", [])

    for s in verified:
        if s["phone"] == phone:
            return s

    new_student = {
        "phone": phone,
        "name": name,
        "verified": True,
        "course_interest": None,
        "enrolled": False,
        "enrolled_course": None,
        "enrolled_batch": None,
        "enrolled_at": None,
        "message_count": 0,
        "sentiment_history": [],
        "last_active": datetime.now().isoformat(timespec="seconds"),
        "frustrated_count": 0,
    }
    verified.append(new_student)
    students["verified_students"] = verified
    _save_json("students.json", students)
    return new_student


from fastapi import Form, Response
import os

@router.post("/whatsapp/incoming")
async def incoming_whatsapp(
    From: str = Form(...),
    Body: str = Form(...),
    ProfileName: str = Form("WhatsApp Student"),
):
    """
    Handle incoming WhatsApp messages from Sandbox.
    Routes the incoming text message to the core AI chatbot.
    """
    # Clean standard WhatsApp sender prefix (e.g., "whatsapp:+917010599822")
    phone = From.replace("whatsapp:", "").replace("+91", "").strip()
    if len(phone) > 10:
        phone = phone[-10:]

    # 1. Look for an active session matching this phone number
    session_token = None
    session = None
    for token, sess in _sessions.items():
        if sess.get("student", {}).get("phone") == phone:
            session_token = token
            session = sess
            break

    # 2. If no active session, look up/register student and open a new session
    if not session:
        student = _get_or_create_student_by_phone(phone, ProfileName)
        session_token = create_session(student)
        session = _sessions[session_token]

    student = session["student"]
    history = session["history"]

    # 3. Detect interest updates from incoming text
    detected_course = _detect_course_interest(Body)
    if detected_course and not student.get("course_interest"):
        student["course_interest"] = detected_course

    # 4. Generate AI response using student context and chat history
    response, sentiment = chat_with_llm(Body, history, student)

    # 5. Handle sentiment tracking and support escalation
    if sentiment == "frustrated":
        student["frustrated_count"] = student.get("frustrated_count", 0) + 1

    if student.get("frustrated_count", 0) >= 3:
        response += (
            "\n\n⚠️ I can see this hasn't been resolved to your satisfaction. "
            "I've flagged your case for our support manager — you'll hear back within 2 hours."
        )
        student["frustrated_count"] = 0

    # 6. Update conversational session history
    history.append({"role": "user", "content": Body})
    history.append({"role": "assistant", "content": response})
    if len(history) > 20:
        history = history[-20:]
    session["history"] = history

    # 7. Update student details
    student["message_count"] = student.get("message_count", 0) + 1
    student["last_active"] = datetime.now().isoformat(timespec="seconds")
    if detected_course:
        student["course_interest"] = detected_course
    sentiment_history = student.get("sentiment_history", [])
    sentiment_history.append(sentiment)
    student["sentiment_history"] = sentiment_history[-10:]
    session["student"] = student

    # 8. Save persistent updates
    _update_student_record(phone, {
        "message_count": student["message_count"],
        "last_active": student["last_active"],
        "course_interest": student.get("course_interest"),
        "sentiment_history": student["sentiment_history"],
        "frustrated_count": student.get("frustrated_count", 0),
    })

    # 9. Update live analytics dashboard
    _increment_analytics_sentiment(sentiment)

    # 10. Dispatch response back to user via WhatsApp (or fallback log)
    from app.services import whatsapp_service

    # Log it immediately to analytics
    whatsapp_service._log_to_analytics("bot_reply", f"+91 {phone[:5]} {phone[5:]}", student["name"], response)

    if whatsapp_service._is_configured():
        whatsapp_service._send_via_node_bot(phone, response, student["name"], "bot_reply")

    # Return standard TwiML XML payload to complete the transaction
    twiml_payload = """<?xml version="1.0" encoding="UTF-8"?>
<Response></Response>"""
    return Response(content=twiml_payload, media_type="application/xml")
