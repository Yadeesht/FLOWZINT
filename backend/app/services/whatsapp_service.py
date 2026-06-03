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
    """Check if the WhatsApp bot configuration is active."""
    phone = os.getenv("WHATSAPP_PHONE", "").strip()
    if phone == "YOUR_WHATSAPP_PHONE":
        return False
    return True


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

    # Use the phone number configured in .env as recipient, or fallback to target phone parameter
    env_phone = os.getenv("WHATSAPP_PHONE", "").strip()
    if env_phone and env_phone != "YOUR_WHATSAPP_PHONE":
        target_phone = env_phone
    else:
        target_phone = phone

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
    message = (
        f"🔐 *EduFlow Security Verification*\n\n"
        f"Hey {name}! Your EduFlow One-Time Password is:\n"
        f"👉 *{otp}*\n\n"
        f"⌛ This code is valid for *10 minutes*. Please do not share it with anyone. "
        f"Let's get you set up! 🚀"
    )
    
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
        # If the custom message is a simple raw paragraph (lacks standard quote/spacing layout),
        # wrap it in a beautiful, structured template ourselves.
        custom_clean = custom_message.strip()
        if "_" not in custom_clean and "—" not in custom_clean:
            message = (
                f"✨ *EduFlow Career Acceleration* ✨\n\n"
                f"{custom_clean}\n\n"
                f"💬 _\"The best way to predict the future is to create it.\"_ — Peter Drucker\n\n"
                f"⚡ *Limited-Time Offer:* Reply here or return to the chat portal to claim your *{discount}% discount* and lock in your spot! 🚀"
            )
        else:
            message = custom_clean
    else:
        message = (
            f"✨ *EduFlow Special Invitation* ✨\n\n"
            f"Hey {name}! 👋 We noticed you were exploring our *{course_interest}* bootcamp. "
            f"To help you take the leap, we've unlocked a special gift for you! 🎁\n\n"
            f"⚡ *Exclusive Limited-Time Offer:*\n"
            f"💥 Enjoy *{discount}% OFF* on your enrollment today!\n"
            f"🔑 Use Coupon Code: *COMEBACK{discount}*\n\n"
            f"💬 _\"The best investment you can make is in yourself.\"_ — Warren Buffett\n\n"
            f"⏳ *Hurry, only a few seats left!* This code is valid for the next 30 minutes only. "
            f"Reply to this message or return to the chat portal to claim your spot and launch your career! 🚀"
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
        f"🎉 *Welcome to the EduFlow Family, {name}!* 🎉\n\n"
        f"Congratulations! Your spot is officially secured. We are absolutely thrilled to have you join us! 🎓\n\n"
        f"📌 *Your Enrollment Details:*\n"
        f"🎓 *Course:* {course['name']}\n"
        f"📅 *Batch ID:* {batch['id']}\n"
        f"🗓️ *Starts On:* {batch['start_date']}\n"
        f"⏰ *Timing:* {batch['time']} ({batch['days']})\n"
        f"👨‍🏫 *Instructor:* {batch['instructor']}\n"
        f"🖥️ *Mode:* {batch['mode'].title()}\n\n"
        f"🔗 *Classroom Joining Link:*\n"
        f"{batch['joining_link']}\n\n"
        f"💬 _\"The secret of getting ahead is getting started.\"_ — Mark Twain\n\n"
        f"An onboarding coordinator will reach out to you shortly. Prepare to build amazing things! See you in class! 🚀"
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
        "exam": (
            f"📚 *EduFlow Exam Alert: Ready to Shine!* 🌟\n\n"
            f"Hi {name}! Friendly heads-up: you have an upcoming *exam/quiz tomorrow* for *{course_name}*.\n\n"
            f"📝 *Details:* {details}\n\n"
            f"💬 _\"Believe you can and you're halfway there.\"_ — Theodore Roosevelt\n\n"
            f"Get a good night's rest and give it your best shot! We believe in you! 💪🔥"
        ),
        "fee": (
            f"💳 *EduFlow Account Notice: Fee Instalment* 🔔\n\n"
            f"Hi {name}! This is a friendly reminder that your next fee instalment for *{course_name}* is *due in 2 days*.\n\n"
            f"💵 *Instalment Details:* {details}\n\n"
            f"Secure your learning journey! Please complete the payment through your student portal to ensure uninterrupted access to live classes and recordings. Thank you! 💙"
        ),
        "class": (
            f"📅 *EduFlow Class Alert: Pre-Class Check!* 🎓\n\n"
            f"Hi {name}! Get ready: your next class for *{course_name}* is scheduled for *tomorrow*.\n\n"
            f"💡 *Pre-class Details:* {details}\n\n"
            f"Please make sure to review the pre-class materials and assignments so we can make the most of our live session. See you there! 🚀"
        ),
        "reschedule": (
            f"⚠️ *EduFlow Class Update: Schedule Change* 🔄\n\n"
            f"Hi {name}! Important update: your *{course_name}* class has been rescheduled.\n\n"
            f"🗓️ *New Schedule:* {details}\n\n"
            f"We sincerely apologize for any inconvenience caused. The recorded session will be uploaded to the portal as usual if you cannot make it live. Thank you for your flexibility! 🙏"
        ),
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
        f"🌟 *Congratulations, {name}!* 🎓\n\n"
        f"You have officially completed *{course_name}*! We are incredibly proud of your dedication and hard work. 🎉\n\n"
        f"Your experience and journey mean the absolute world to us. Could you take 2 minutes to share your feedback? "
        f"It helps future students make the right choice and helps us keep improving!\n\n"
        f"👉 *Share your review here:*\n"
        f"https://eduflow.ai/review?phone={phone}\n\n"
        f"💬 _\"Education is the passport to the future.\"_ — Malcolm X\n\n"
        f"Thank you for being a part of EduFlow, and all the best for your bright career ahead! 🚀"
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
