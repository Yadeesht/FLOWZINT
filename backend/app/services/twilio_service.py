"""
twilio_service.py — EduFlow AI WhatsApp Service

Wraps the Twilio WhatsApp API. When credentials are not configured,
falls back to logging all outbound messages to analytics.json so they
still appear in the Admin Dashboard's live WhatsApp outbound log.
"""

import os
import json
import uuid
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False


def _is_configured() -> bool:
    """Check if Twilio credentials are set and non-placeholder."""
    sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    token = os.getenv("TWILIO_AUTH_TOKEN", "")
    return (
        TWILIO_AVAILABLE
        and bool(sid)
        and sid != "YOUR_TWILIO_ACCOUNT_SID"
        and bool(token)
        and token != "YOUR_TWILIO_AUTH_TOKEN"
    )


def _get_client():
    """Return a Twilio client using env credentials."""
    return TwilioClient(
        os.getenv("TWILIO_ACCOUNT_SID"),
        os.getenv("TWILIO_AUTH_TOKEN"),
    )


def _log_to_analytics(msg_type: str, to_phone: str, name: str, message: str) -> dict:
    """Log an outbound message to analytics.json WA log and return the log entry."""
    try:
        analytics_path = DATA_DIR / "analytics.json"
        with open(analytics_path, "r", encoding="utf-8") as f:
            analytics = json.load(f)

        entry = {
            "id": f"wa-{uuid.uuid4().hex[:6]}",
            "type": msg_type,
            "to": to_phone,
            "name": name,
            "message": message,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "status": "simulated",
        }

        if "wa_outbound_log" not in analytics:
            analytics["wa_outbound_log"] = []

        analytics["wa_outbound_log"].insert(0, entry)
        # Keep log at max 50 entries
        analytics["wa_outbound_log"] = analytics["wa_outbound_log"][:50]
        analytics["last_updated"] = entry["timestamp"]

        with open(analytics_path, "w", encoding="utf-8") as f:
            json.dump(analytics, f, indent=2, ensure_ascii=False)

        print(f"[WhatsApp LOG] → {to_phone} ({msg_type}): {message[:80]}...")
        return entry
    except Exception as e:
        print(f"[WhatsApp LOG Error] {e}")
        return {}


def send_otp(phone: str, name: str, otp: str) -> dict:
    """Send OTP message via WhatsApp (or log it if unconfigured)."""
    message = f"Your EduFlow OTP is *{otp}*. Valid for 10 minutes. Do not share this with anyone. 🔐"
    to = f"whatsapp:+91{phone}"
    from_ = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

    if _is_configured():
        try:
            client = _get_client()
            msg = client.messages.create(from_=from_, to=to, body=message)
            _log_to_analytics("otp", f"+91 {phone[:5]} {phone[5:]}", name, message)
            return {"success": True, "sid": msg.sid}
        except Exception as e:
            print(f"[Twilio Error - OTP] {e}")

    # Fallback: log to analytics
    entry = _log_to_analytics("otp", f"+91 {phone[:5]} {phone[5:]}", name, message)
    return {"success": True, "simulated": True, "entry": entry}


def send_abandoned_nudge(phone: str, name: str, course_interest: str, discount: int = 15) -> dict:
    """Send the abandoned enquiry recovery nudge via WhatsApp."""
    message = (
        f"Hey {name}! 👋 Still thinking about the *{course_interest}*? "
        f"🎓 Here's *{discount}% off* — valid for 30 mins only! ⚡ "
        f"Only a few seats left. Reply here or come back to the chat to lock your spot. "
        f"Use code *COMEBACK{discount}* at checkout!"
    )
    to = f"whatsapp:+91{phone}"
    from_ = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

    if _is_configured():
        try:
            client = _get_client()
            msg = client.messages.create(from_=from_, to=to, body=message)
            _log_to_analytics("abandoned_nudge", f"+91 {phone[:5]} {phone[5:]}", name, message)
            return {"success": True, "sid": msg.sid}
        except Exception as e:
            print(f"[Twilio Error - Nudge] {e}")

    entry = _log_to_analytics("abandoned_nudge", f"+91 {phone[:5]} {phone[5:]}", name, message)
    return {"success": True, "simulated": True, "entry": entry}


def send_enrollment_confirmation(phone: str, name: str, course: dict, batch: dict) -> dict:
    """Send enrollment confirmation with batch details via WhatsApp."""
    message = (
        f"🎉 Congratulations {name}! You're officially enrolled in *{course['name']}*!\n\n"
        f"📅 *Batch:* {batch['id']}\n"
        f"🗓️ *Starts:* {batch['start_date']}\n"
        f"⏰ *Time:* {batch['time']} | {batch['days']}\n"
        f"👨‍🏫 *Instructor:* {batch['instructor']}\n"
        f"🖥️ *Mode:* {batch['mode'].title()}\n"
        f"🔗 *Joining Link:* {batch['joining_link']}\n\n"
        f"Welcome to the EduFlow family! See you on {batch['start_date']}. 🚀"
    )
    to = f"whatsapp:+91{phone}"
    from_ = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

    if _is_configured():
        try:
            client = _get_client()
            msg = client.messages.create(from_=from_, to=to, body=message)
            _log_to_analytics("enrollment_confirmation", f"+91 {phone[:5]} {phone[5:]}", name, message)
            return {"success": True, "sid": msg.sid}
        except Exception as e:
            print(f"[Twilio Error - Enrollment] {e}")

    entry = _log_to_analytics("enrollment_confirmation", f"+91 {phone[:5]} {phone[5:]}", name, message)
    return {"success": True, "simulated": True, "entry": entry}


def send_reminder(phone: str, name: str, reminder_type: str, course_name: str, details: str = "") -> dict:
    """Send a scheduled reminder (exam, fee, class) via WhatsApp."""
    templates = {
        "exam": f"📚 Hi {name}! Heads up — you have an *exam/quiz tomorrow* for *{course_name}*. {details} All the best! 💪",
        "fee": f"💳 Hi {name}! Friendly reminder — your fee instalment for *{course_name}* is *due in 2 days*. {details} Pay via the student portal to avoid any interruption.",
        "class": f"📅 Hi {name}! Your *{course_name}* class is *tomorrow*. {details} Don't forget to review the pre-class material! 🎓",
        "reschedule": f"⚠️ Hi {name}! Important update — your *{course_name}* class has been *rescheduled*. {details} Sorry for the inconvenience!",
    }
    message = templates.get(reminder_type, f"Hi {name}! EduFlow reminder: {details}")
    to = f"whatsapp:+91{phone}"
    from_ = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

    if _is_configured():
        try:
            client = _get_client()
            msg = client.messages.create(from_=from_, to=to, body=message)
            _log_to_analytics("reminder", f"+91 {phone[:5]} {phone[5:]}", name, message)
            return {"success": True, "sid": msg.sid}
        except Exception as e:
            print(f"[Twilio Error - Reminder] {e}")

    entry = _log_to_analytics("reminder", f"+91 {phone[:5]} {phone[5:]}", name, message)
    return {"success": True, "simulated": True, "entry": entry}


def send_review_request(phone: str, name: str, course_name: str) -> dict:
    """Send a post-course review request via WhatsApp."""
    message = (
        f"Hi {name}! 🌟 Congratulations on completing *{course_name}*!\n\n"
        f"Your journey means the world to us. We'd love to hear your feedback — "
        f"it takes just 2 minutes and helps future students make better decisions.\n\n"
        f"Click here to leave your review: https://eduflow.ai/review?phone={phone}\n\n"
        f"Thank you for being part of the EduFlow family! 🎓"
    )
    to = f"whatsapp:+91{phone}"
    from_ = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

    if _is_configured():
        try:
            client = _get_client()
            msg = client.messages.create(from_=from_, to=to, body=message)
            _log_to_analytics("review_request", f"+91 {phone[:5]} {phone[5:]}", name, message)
            return {"success": True, "sid": msg.sid}
        except Exception as e:
            print(f"[Twilio Error - Review Request] {e}")

    entry = _log_to_analytics("review_request", f"+91 {phone[:5]} {phone[5:]}", name, message)
    return {"success": True, "simulated": True, "entry": entry}
