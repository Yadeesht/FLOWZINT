"""
twilio_service.py — Wrapper for backward compatibility redirecting to whatsapp_service.py.
"""

from app.services.whatsapp_service import (
    _is_configured,
    _log_to_analytics,
    send_otp,
    send_abandoned_nudge,
    send_enrollment_confirmation,
    send_reminder,
    send_review_request,
    send_custom_message
)


