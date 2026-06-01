"""
inactive.py — EduFlow AI Abandoned Enquiry Recovery Route

THE KILLER FEATURE. When the frontend inactivity timer fires, this
endpoint sends a personalised WhatsApp nudge with a discount offer
and urgency timer to recover the abandoned enquiry.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import twilio_service

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
    Called by the frontend inactivity timer after 3 minutes (or 30s demo mode).
    """
    phone = req.phone.strip().replace(" ", "").replace("-", "")
    if not phone.isdigit() or len(phone) != 10:
        raise HTTPException(status_code=400, detail="Invalid phone number format.")

    if not req.course_interest:
        raise HTTPException(status_code=400, detail="Course interest is required for the nudge.")

    result = twilio_service.send_abandoned_nudge(
        phone=phone,
        name=req.name,
        course_interest=req.course_interest,
        discount=req.discount,
    )

    return {
        "success": result.get("success", False),
        "message": f"Abandoned enquiry nudge sent to {req.name} (+91{phone})",
        "course_interest": req.course_interest,
        "discount": req.discount,
        "simulated": result.get("simulated", False),
    }
