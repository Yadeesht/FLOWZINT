"""
inactive.py — EduFlow AI Abandoned Enquiry Recovery Route

THE KILLER FEATURE. When the frontend inactivity timer fires, this
endpoint sends a personalised WhatsApp nudge with a discount offer
and urgency timer to recover the abandoned enquiry.
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.routes import chat
from app.services import whatsapp_service, azure_openai

router = APIRouter()


# ─── Models ─────────────────────────────────────────────────────────────────

class NudgeRequest(BaseModel):
    phone: str
    name: str
    course_interest: str
    discount: int = 15
    session_token: str | None = None


# ─── Route ──────────────────────────────────────────────────────────────────

@router.post("/inactive")
async def trigger_abandoned_nudge(req: NudgeRequest):
    """
    Trigger an abandoned enquiry WhatsApp nudge.
    Called by the frontend inactivity timer or manual admin action.
    """
    phone = req.phone.strip().replace(" ", "").replace("-", "")
    if not phone.isdigit() or len(phone) != 10:
        raise HTTPException(status_code=400, detail="Invalid phone number format.")

    if not req.course_interest:
        raise HTTPException(status_code=400, detail="Course interest is required for the nudge.")

    # 1. Retrieve student session/persistent record and conversation history
    student = None
    history = []
    token = req.session_token

    if token:
        student = chat.get_session_student(token)
        history = chat.get_session_history(token) or []

    # Fallback to lookup by phone in active sessions
    if not student:
        token, student, history = chat.get_session_by_phone(phone)
        if not history:
            history = []

    # Fallback to persistent storage
    if not student:
        student = chat.get_persistent_student(phone)

    # Fallback to default constructed dict if student is not found anywhere
    if not student:
        student = {
            "phone": phone,
            "name": req.name,
            "course_interest": req.course_interest,
            "enrolled": False,
            "nudge_count": 0,
            "sentiment_history": [],
            "last_active": None,
            "frustrated_count": 0
        }

    # Ensure sentiment_history and nudge_count exist in the student object
    if "sentiment_history" not in student:
        student["sentiment_history"] = []
    if "nudge_count" not in student:
        student["nudge_count"] = 0

    # 2. Check if student is already enrolled
    if student.get("enrolled"):
        return {
            "success": False,
            "reason": "already_enrolled",
            "message": f"Student {student.get('name', req.name)} is already enrolled. No nudge sent.",
        }

    # 3. Enforce the nudge count limit (only for automated inactivity timers)
    nudge_count = student.get("nudge_count", 0)
    if req.session_token and nudge_count >= 2:
        return {
            "success": False,
            "reason": "nudge_limit_exceeded",
            "message": f"Nudge limit (2) reached for this session. No nudge sent.",
        }

    # 4. Use AI / Sentiment Analyzer to decide if nudge is needed and customize the message
    should_nudge, custom_message = azure_openai.generate_nudge_with_llm(student, history)

    # For manual admin dashboard nudges, we always override should_nudge to True if LLM decides not to nudge
    if not req.session_token:
        should_nudge = True
        if not custom_message:
            _, custom_message = azure_openai._local_nudge_fallback(student, history)

    if not should_nudge:
        return {
            "success": False,
            "reason": "ai_skipped",
            "message": "AI determined a nudge is not appropriate or needed at this time.",
        }

    # 5. Dispatch the nudge message
    result = whatsapp_service.send_abandoned_nudge(
        phone=phone,
        name=student.get("name", req.name),
        course_interest=student.get("course_interest", req.course_interest),
        discount=req.discount,
        custom_message=custom_message,
    )

    # 6. Update tracking details persistently and in active session
    new_nudge_count = nudge_count + 1
    updates = {
        "nudge_count": new_nudge_count,
        "last_nudge_time": datetime.now().isoformat(timespec="seconds")
    }

    if token:
        chat.update_session_student(token, updates)
    
    chat.update_student_record(phone, updates)

    return {
        "success": result.get("success", False),
        "message": f"Abandoned enquiry nudge sent to {student.get('name', req.name)} (+91{phone})",
        "custom_message": custom_message,
        "nudge_count": new_nudge_count,
        "simulated": result.get("simulated", False),
    }
