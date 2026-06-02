"""
whatsapp_service.py — EduFlow AI WhatsApp Service via Node.js whatsapp-web.js Bot

Routes outbound messages by making HTTP POST calls to the Node.js bot (running on port 3001).
Uses background threads to prevent blocking FastAPI request threads.
"""

import os
import json
import uuid
import threading
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def _is_configured() -> bool:
    """Check if the test phone number is configured in .env."""
    phone = os.getenv("WHATSAPP_PHONE", "").strip()
    return bool(phone) and phone != "YOUR_WHATSAPP_PHONE"


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
            "status": "delivered" if _is_configured() else "simulated",
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


def _send_via_node_bot(phone: str, message: str, name: str, msg_type: str):
    """Forward outbound message payload to the Node.js whatsapp-web.js gateway in a background thread."""
    if not _is_configured():
        print("[WhatsApp Service] Not configured. Falling back to simulation.")
        return

    # Use the phone number configured in .env as recipient
    target_phone = os.getenv("WHATSAPP_PHONE", phone).strip()

    def worker():
        try:
            bot_url = os.getenv("WHATSAPP_BOT_URL", "http://localhost:3001/send")
            payload = json.dumps({
                "phone": target_phone,
                "message": message
            }).encode("utf-8")

            req = urllib.request.Request(
                bot_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            print(f"[WhatsApp Service] Forwarding message to Node Gateway ({bot_url}) for {target_phone}...")
            with urllib.request.urlopen(req, timeout=12) as response:
                res_body = json.loads(response.read().decode("utf-8"))
                print(f"[WhatsApp Service Response] {res_body}")
        except Exception as e:
            print(f"[WhatsApp Service Error] Failed to send via Node Gateway: {e}")

    # Launch thread
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()


def send_otp(phone: str, name: str, otp: str) -> dict:
    """Send OTP message via WhatsApp Node bot gateway."""
    message = f"Your EduFlow OTP is *{otp}*. Valid for 10 minutes. Do not share this with anyone. 🔐"
    
    # Log it immediately to analytics
    to_display = f"+91 {phone[:5]} {phone[5:]}"
    entry = _log_to_analytics("otp", to_display, name, message)

    if _is_configured():
        _send_via_node_bot(phone, message, name, "otp")
        return {"success": True, "simulated": False}

    return {"success": True, "simulated": True, "entry": entry}



def send_abandoned_nudge(phone: str, name: str, course_interest: str, discount: int = 15, custom_message: str | None = None) -> dict:
    """Send the abandoned enquiry recovery nudge via WhatsApp Node bot gateway."""
    if custom_message:
        message = custom_message
    else:
        message = (
            f"Hey {name}! 👋 Still thinking about the *{course_interest}*? "
            f"🎓 Here's *{discount}% off* — valid for 30 mins only! ⚡ "
            f"Only a few seats left. Reply here or come back to the chat to lock your spot. "
            f"Use code *COMEBACK{discount}* at checkout!"
        )
    
    to_display = f"+91 {phone[:5]} {phone[5:]}"
    entry = _log_to_analytics("abandoned_nudge", to_display, name, message)

    if _is_configured():
        _send_via_node_bot(phone, message, name, "abandoned_nudge")
        return {"success": True, "simulated": False}

    return {"success": True, "simulated": True, "entry": entry}


def send_enrollment_confirmation(phone: str, name: str, course: dict, batch: dict) -> dict:
    """Send enrollment confirmation with batch details via WhatsApp Node bot gateway."""
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
    
    to_display = f"+91 {phone[:5]} {phone[5:]}"
    entry = _log_to_analytics("enrollment_confirmation", to_display, name, message)

    if _is_configured():
        _send_via_node_bot(phone, message, name, "enrollment_confirmation")
        return {"success": True, "simulated": False}

    return {"success": True, "simulated": True, "entry": entry}


def send_reminder(phone: str, name: str, reminder_type: str, course_name: str, details: str = "") -> dict:
    """Send a scheduled reminder (exam, fee, class) via WhatsApp Node bot gateway."""
    templates = {
        "exam": f"📚 Hi {name}! Heads up — you have an *exam/quiz tomorrow* for *{course_name}*. {details} All the best! 💪",
        "fee": f"💳 Hi {name}! Friendly reminder — your fee instalment for *{course_name}* is *due in 2 days*. {details} Pay via the student portal to avoid any interruption.",
        "class": f"📅 Hi {name}! Your *{course_name}* class is *tomorrow*. {details} Don't forget to review the pre-class material! 🎓",
        "reschedule": f"⚠️ Hi {name}! Important update — your *{course_name}* class has been *rescheduled*. {details} Sorry for the inconvenience!",
    }
    message = templates.get(reminder_type, f"Hi {name}! EduFlow reminder: {details}")
    
    to_display = f"+91 {phone[:5]} {phone[5:]}"
    entry = _log_to_analytics("reminder", to_display, name, message)

    if _is_configured():
        _send_via_node_bot(phone, message, name, "reminder")
        return {"success": True, "simulated": False}

    return {"success": True, "simulated": True, "entry": entry}


def send_review_request(phone: str, name: str, course_name: str) -> dict:
    """Send a post-course review request via WhatsApp Node bot gateway."""
    message = (
        f"Hi {name}! 🌟 Congratulations on completing *{course_name}*!\n\n"
        f"Your journey means the world to us. We'd love to hear your feedback — "
        f"it takes just 2 minutes and helps future students make better decisions.\n\n"
        f"Click here to leave your review: https://eduflow.ai/review?phone={phone}\n\n"
        f"Thank you for being part of the EduFlow family! 🎓"
    )
    
    to_display = f"+91 {phone[:5]} {phone[5:]}"
    entry = _log_to_analytics("review_request", to_display, name, message)

    if _is_configured():
        _send_via_node_bot(phone, message, name, "review_request")
        return {"success": True, "simulated": False}

    return {"success": True, "simulated": True, "entry": entry}


def send_custom_message(phone: str, name: str, message: str) -> dict:
    """Send a custom/arbitrary WhatsApp message to the student via Node bot gateway."""
    to_display = f"+91 {phone[:5]} {phone[5:]}"
    entry = _log_to_analytics("custom_message", to_display, name, message)

    if _is_configured():
        _send_via_node_bot(phone, message, name, "custom_message")
        return {"success": True, "simulated": False}

    return {"success": True, "simulated": True, "entry": entry}
