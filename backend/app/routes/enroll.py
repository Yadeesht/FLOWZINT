"""
enroll.py — EduFlow AI Enrollment Route

Processes student enrollment:
- Updates batch seat availability
- Updates student record in students.json
- Sends WhatsApp enrollment confirmation via Twilio
- Updates analytics conversion metrics
"""

import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.routes.chat import get_session_student
from app.services.enrollment import enroll_student_in_batch

router = APIRouter()
DATA_DIR = Path(__file__).parent.parent / "data"


# ─── Models ─────────────────────────────────────────────────────────────────

class EnrollRequest(BaseModel):
    session_token: str
    batch_id: str  # e.g. "batch-ai-jun"


# ─── Route ──────────────────────────────────────────────────────────────────

@router.post("/enroll")
async def enroll_student(req: EnrollRequest):
    """Enroll a student in a batch and send confirmation."""
    student = get_session_student(req.session_token)
    if not student:
        raise HTTPException(status_code=404, detail="Session not found. Please verify OTP.")

    res = enroll_student_in_batch(
        phone=student.get("phone", ""),
        batch_id=req.batch_id,
        student_session_dict=student
    )

    if not res["success"]:
        raise HTTPException(status_code=400, detail=res.get("error", "Enrollment failed."))

    course = res["course"]
    batch = res["batch"]
    wa_result = res["wa_result"]

    return {
        "success": True,
        "message": f"🎉 {res['student_name']}, you're enrolled in {course['name']}!",
        "course": {
            "id": course["id"],
            "name": course["name"],
            "fee": course["fee"],
        },
        "batch": {
            "id": batch["id"],
            "start_date": batch["start_date"],
            "time": batch["time"],
            "days": batch["days"],
            "instructor": batch["instructor"],
            "joining_link": batch["joining_link"],
            "seats_left": batch["seats_left"],
        },
        "whatsapp_sent": wa_result.get("success", False),
        "whatsapp_simulated": wa_result.get("simulated", False),
    }
