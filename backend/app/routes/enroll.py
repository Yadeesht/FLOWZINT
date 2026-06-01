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

from app.services import twilio_service
from app.routes.chat import get_session_student, update_session_student

router = APIRouter()
DATA_DIR = Path(__file__).parent.parent / "data"


# ─── Models ─────────────────────────────────────────────────────────────────

class EnrollRequest(BaseModel):
    session_token: str
    batch_id: str  # e.g. "batch-ai-jun"


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
        print(f"[Save Error] {e}")


# ─── Route ──────────────────────────────────────────────────────────────────

@router.post("/enroll")
async def enroll_student(req: EnrollRequest):
    """Enroll a student in a batch and send confirmation."""
    student = get_session_student(req.session_token)
    if not student:
        raise HTTPException(status_code=404, detail="Session not found. Please verify OTP.")

    # Load batch data
    batches = _load_json("batches.json")
    batch = next((b for b in batches if b["id"] == req.batch_id), None)
    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch '{req.batch_id}' not found.")

    if batch["seats_left"] <= 0:
        raise HTTPException(status_code=400, detail="Sorry, this batch is full. Please choose another batch.")

    # Load course data
    courses = _load_json("courses.json")
    course = next((c for c in courses if c["id"] == batch["course_id"]), None)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")

    # Update batch seats
    batch["seats_left"] -= 1
    _save_json("batches.json", batches)

    # Update student record
    enrollment_data = {
        "enrolled": True,
        "enrolled_course": course["id"],
        "enrolled_batch": batch["id"],
        "enrolled_at": datetime.now().isoformat(timespec="seconds"),
        "course_interest": course["name"],
    }
    update_session_student(req.session_token, enrollment_data)

    # Persist to students.json
    students = _load_json("students.json")
    phone = student.get("phone", "")
    for s in students.get("verified_students", []):
        if s["phone"] == phone:
            s.update(enrollment_data)
            break
    _save_json("students.json", students)

    # Update analytics
    try:
        analytics = _load_json("analytics.json")
        analytics["total_enrolled"] = analytics.get("total_enrolled", 0) + 1
        total_enquirers = analytics.get("total_enquirers", 1)
        analytics["conversion_rate"] = round(
            (analytics["total_enrolled"] / max(total_enquirers, 1)) * 100, 1
        )
        analytics["last_updated"] = datetime.now().isoformat(timespec="seconds")
        _save_json("analytics.json", analytics)
    except Exception as e:
        print(f"[Analytics Error] {e}")

    # Send WhatsApp confirmation
    wa_result = twilio_service.send_enrollment_confirmation(
        phone=phone,
        name=student["name"],
        course=course,
        batch=batch,
    )

    return {
        "success": True,
        "message": f"🎉 {student['name']}, you're enrolled in {course['name']}!",
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
