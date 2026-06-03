"""
enrollment.py — Shared enrollment logic for EduFlow AI
"""

import json
from datetime import datetime
from pathlib import Path
from app.services import whatsapp_service

DATA_DIR = Path(__file__).parent.parent / "data"


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


def enroll_student_in_batch(phone: str, batch_id: str, student_session_dict: dict = None) -> dict:
    """
    Shared enrollment logic used by both API routes and LLM chatbot tools.
    """
    # Load batch data
    batches = _load_json("batches.json")
    batch = next((b for b in batches if b["id"] == batch_id), None)
    if not batch:
        return {"success": False, "error": f"Batch '{batch_id}' not found."}

    if batch["seats_left"] <= 0:
        return {"success": False, "error": "Sorry, this batch is full."}

    # Load course data
    courses = _load_json("courses.json")
    course = next((c for c in courses if c["id"] == batch["course_id"]), None)
    if not course:
        return {"success": False, "error": "Course not found."}

    # Update batch seats
    batch["seats_left"] -= 1
    _save_json("batches.json", batches)

    # Enrollment data
    enrollment_data = {
        "enrolled": True,
        "enrolled_course": course["id"],
        "enrolled_batch": batch["id"],
        "enrolled_at": datetime.now().isoformat(timespec="seconds"),
        "course_interest": course["name"],
    }

    # Update active session dict in-place if passed
    if student_session_dict is not None:
        student_session_dict.update(enrollment_data)

    # Persist to students.json
    students = _load_json("students.json")
    student_name = "Student"
    for s in students.get("verified_students", []):
        if s["phone"] == phone:
            s.update(enrollment_data)
            student_name = s.get("name", "Student")
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
    wa_result = whatsapp_service.send_enrollment_confirmation(
        phone=phone,
        name=student_name,
        course=course,
        batch=batch,
    )

    return {
        "success": True,
        "student_name": student_name,
        "course": course,
        "batch": batch,
        "wa_result": wa_result,
    }
