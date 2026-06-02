"""
otp.py — EduFlow AI OTP Verification Route

Manages 6-digit OTP generation, WhatsApp dispatch via Twilio,
verification, and student session creation.
"""

import json
import random
import string
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import whatsapp_service
from app.routes.chat import create_session

router = APIRouter()
DATA_DIR = Path(__file__).parent.parent / "data"

# In-memory OTP store: { phone: { otp, expires_at, name } }
_otp_store: dict[str, dict] = {}


# ─── Models ─────────────────────────────────────────────────────────────────

class SendOTPRequest(BaseModel):
    phone: str  # 10-digit Indian mobile number
    name: str


class VerifyOTPRequest(BaseModel):
    phone: str
    otp: str


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


def _generate_otp() -> str:
    return "".join(random.choices(string.digits, k=6))


def _get_or_create_student(phone: str, name: str) -> dict:
    """Look up an existing student or create a new verified record."""
    students = _load_json("students.json")
    verified = students.get("verified_students", [])

    # Check for returning student
    for student in verified:
        if student["phone"] == phone:
            # Update name if changed
            student["name"] = name
            student["verified"] = True
            _save_json("students.json", students)
            return student

    # New student
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

    # Bump analytics total enquirers
    try:
        analytics = _load_json("analytics.json")
        analytics["total_sessions"] = analytics.get("total_sessions", 0) + 1
        analytics["total_enquirers"] = analytics.get("total_enquirers", 0) + 1
        analytics["last_updated"] = datetime.now().isoformat(timespec="seconds")
        _save_json("analytics.json", analytics)
    except Exception as e:
        print(f"[Analytics Error] {e}")

    return new_student


# ─── Routes ─────────────────────────────────────────────────────────────────

@router.post("/otp/send")
async def send_otp(req: SendOTPRequest):
    """Generate and send a 6-digit OTP via WhatsApp."""
    phone = req.phone.strip().replace(" ", "").replace("-", "")
    if not phone.isdigit() or len(phone) != 10:
        raise HTTPException(status_code=400, detail="Please provide a valid 10-digit Indian mobile number.")

    otp = _generate_otp()
    _otp_store[phone] = {
        "otp": otp,
        "name": req.name.strip(),
        "expires_at": (datetime.now() + timedelta(minutes=10)).isoformat(),
    }

    result = whatsapp_service.send_otp(phone=phone, name=req.name.strip(), otp=otp)

    return {
        "success": True,
        "message": f"OTP sent to WhatsApp number +91{phone}",
        "simulated": result.get("simulated", False),
        # ⚠️ Include OTP in response for demo/dev mode (simulated only)
        "demo_otp": otp if result.get("simulated") else None,
    }


@router.post("/otp/verify")
async def verify_otp(req: VerifyOTPRequest):
    """Verify the OTP and create an authenticated student session."""
    phone = req.phone.strip().replace(" ", "").replace("-", "")
    stored = _otp_store.get(phone)

    if not stored:
        raise HTTPException(status_code=400, detail="No OTP found for this number. Please request a new OTP.")

    if datetime.now().isoformat() > stored["expires_at"]:
        del _otp_store[phone]
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")

    if req.otp.strip() != stored["otp"]:
        raise HTTPException(status_code=400, detail="Invalid OTP. Please check and try again.")

    # OTP valid — create session
    del _otp_store[phone]
    student = _get_or_create_student(phone=phone, name=stored["name"])
    session_token = create_session(student)

    is_returning = student.get("message_count", 0) > 0

    # Contextual welcome message based on enrollment status
    welcome_msg = ""
    if student.get("enrolled"):
        course_id = student.get("enrolled_course", "")
        courses = _load_json("courses.json")
        course_obj = next((c for c in courses if c["id"] == course_id), None)
        course_name = course_obj["name"] if course_obj else "AI/ML Bootcamp"
        welcome_msg = f"Welcome back, {student['name']}! 👋 You are enrolled in our **{course_name}**. How can I assist you with your schedule or course details today? 🎓"
    elif is_returning:
        welcome_msg = f"Welcome back, {student['name']}! 👋 Great to see you again. What course details or batch schedules can I help you explore today? 🎓"
    else:
        welcome_msg = f"Welcome to EduFlow, {student['name']}! 🎓 I'm your AI Academic Advisor. Ask me anything about our premium bootcamps, fees, batch slots, or corporate internships!"

    return {
        "success": True,
        "session_token": session_token,
        "student": {
            "name": student["name"],
            "phone": student["phone"],
            "enrolled": student.get("enrolled", False),
            "course_interest": student.get("course_interest"),
            "is_returning": is_returning,
        },
        "welcomeMsg": welcome_msg,
    }
