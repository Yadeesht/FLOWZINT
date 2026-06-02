"""
verify_nudges.py — Automated Verification Script for Inactivity Nudges

This script runs tests against the /inactive endpoint logic in-memory.
It backs up students.json, configures test student scenarios, tests the
route logic (sentiment-based message, nudge limit, enrolled skip, active session lookup),
and restores the original data on completion.
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime

# Setup paths to import from app
backend_dir = Path(__file__).parent.resolve()
sys.path.insert(0, str(backend_dir))

from app.routes.inactive import trigger_abandoned_nudge, NudgeRequest
from app.routes import chat

DATA_DIR = backend_dir / "app" / "data"
STUDENTS_FILE = DATA_DIR / "students.json"
BACKUP_FILE = DATA_DIR / "students.json.bak"

# ANSI Colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

def print_header(title):
    print(f"\n{BOLD}{CYAN}{'='*60}\n{title}\n{'='*60}{RESET}")

def print_result(case_name, success, message, details=None):
    status = f"{GREEN}[PASS]{RESET}" if success else f"{RED}[FAIL]{RESET}"
    print(f"{status} {BOLD}{case_name}{RESET}: {message}")
    if details:
        print(f"       Details: {details}")

def backup_data():
    if STUDENTS_FILE.exists():
        with open(STUDENTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        with open(BACKUP_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"{GREEN}✓ Created backup of students.json at {BACKUP_FILE.name}{RESET}")
    else:
        print(f"{YELLOW}! Warning: students.json does not exist. A new empty one will be created.{RESET}")

def restore_data():
    if BACKUP_FILE.exists():
        with open(BACKUP_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        with open(STUDENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.remove(BACKUP_FILE)
        print(f"{GREEN}✓ Restored original students.json and cleaned up backup.{RESET}")
    else:
        print(f"{RED}! Error: Backup file not found to restore.{RESET}")

def prepare_test_students():
    test_data = {
        "sessions": {},
        "verified_students": [
            {
                "phone": "9999999991",
                "name": "Test Enrolled",
                "verified": True,
                "course_interest": "AI/ML Bootcamp",
                "enrolled": True,
                "enrolled_course": "ai-ml-bootcamp",
                "enrolled_batch": "batch-ai-jun",
                "enrolled_at": datetime.now().isoformat(),
                "message_count": 5,
                "sentiment_history": ["positive"],
                "last_active": datetime.now().isoformat(),
                "frustrated_count": 0,
                "nudge_count": 0
            },
            {
                "phone": "9999999992",
                "name": "Test Nudge Capped",
                "verified": True,
                "course_interest": "Full Stack Web Development",
                "enrolled": False,
                "enrolled_course": None,
                "enrolled_batch": None,
                "enrolled_at": None,
                "message_count": 8,
                "sentiment_history": ["neutral", "positive"],
                "last_active": datetime.now().isoformat(),
                "frustrated_count": 0,
                "nudge_count": 2
            },
            {
                "phone": "9999999993",
                "name": "Test Frustrated",
                "verified": True,
                "course_interest": "Data Science Pro",
                "enrolled": False,
                "enrolled_course": None,
                "enrolled_batch": None,
                "enrolled_at": None,
                "message_count": 4,
                "sentiment_history": ["frustrated"],
                "last_active": datetime.now().isoformat(),
                "frustrated_count": 1,
                "nudge_count": 0
            },
            {
                "phone": "9999999994",
                "name": "Test Confused",
                "verified": True,
                "course_interest": "Cloud Computing",
                "enrolled": False,
                "enrolled_course": None,
                "enrolled_batch": None,
                "enrolled_at": None,
                "message_count": 3,
                "sentiment_history": ["confused"],
                "last_active": datetime.now().isoformat(),
                "frustrated_count": 0,
                "nudge_count": 0
            },
            {
                "phone": "9999999995",
                "name": "Test Positive",
                "verified": True,
                "course_interest": "AI/ML Bootcamp",
                "enrolled": False,
                "enrolled_course": None,
                "enrolled_batch": None,
                "enrolled_at": None,
                "message_count": 2,
                "sentiment_history": ["positive"],
                "last_active": datetime.now().isoformat(),
                "frustrated_count": 0,
                "nudge_count": 0
            }
        ]
    }
    with open(STUDENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(test_data, f, indent=2, ensure_ascii=False)
    print(f"{GREEN}✓ Populated students.json with test scenarios.{RESET}")

async def run_tests():
    backup_data()
    try:
        prepare_test_students()
        
        # Setup in-memory sessions mock
        chat._sessions.clear()
        
        # Test Case 1: Already Enrolled student
        print_header("Test Case 1: Already Enrolled Student")
        req = NudgeRequest(
            phone="9999999991",
            name="Test Enrolled",
            course_interest="AI/ML Bootcamp",
            session_token="token-enrolled"
        )
        # Mock active session
        chat._sessions["token-enrolled"] = {
            "student": chat.get_persistent_student("9999999991"),
            "history": [{"role": "user", "content": "I joined!"}]
        }
        
        res = await trigger_abandoned_nudge(req)
        is_pass = res.get("success") is False and res.get("reason") == "already_enrolled"
        print_result(
            "Enrolled Skip Check", 
            is_pass, 
            res.get("message"), 
            f"Response: {res}"
        )

        # Test Case 2: Automated Nudge Limit Capped
        print_header("Test Case 2: Inactivity Nudge Limit (Automated)")
        req = NudgeRequest(
            phone="9999999992",
            name="Test Nudge Capped",
            course_interest="Full Stack Web Development",
            session_token="token-capped"
        )
        chat._sessions["token-capped"] = {
            "student": chat.get_persistent_student("9999999992"),
            "history": []
        }
        res = await trigger_abandoned_nudge(req)
        is_pass = res.get("success") is False and res.get("reason") == "nudge_limit_exceeded"
        print_result(
            "Automated Nudge Cap", 
            is_pass, 
            res.get("message"), 
            f"Response: {res}"
        )

        # Test Case 3: Manual Nudge Override (Bypassing Cap)
        print_header("Test Case 3: Manual Admin Nudge Override")
        req_manual = NudgeRequest(
            phone="9999999992",
            name="Test Nudge Capped",
            course_interest="Full Stack Web Development",
            session_token=None # None means manual admin action
        )
        res_manual = await trigger_abandoned_nudge(req_manual)
        is_pass = res_manual.get("success") is True and res_manual.get("nudge_count") == 3
        print_result(
            "Manual Cap Bypass", 
            is_pass, 
            res_manual.get("message"), 
            f"Response: {res_manual}"
        )

        # Test Case 4: AI Personalization (Frustrated)
        print_header("Test Case 4: AI Personalization (Frustrated Student)")
        req = NudgeRequest(
            phone="9999999993",
            name="Test Frustrated",
            course_interest="Data Science Pro",
            session_token="token-frustrated"
        )
        chat._sessions["token-frustrated"] = {
            "student": chat.get_persistent_student("9999999993"),
            "history": [{"role": "user", "content": "This is too hard, I don't understand."}]
        }
        res = await trigger_abandoned_nudge(req)
        custom_message = res.get("custom_message", "")
        # Should not contain discount info (e.g. 15% or COMEBACK15)
        # Should be empathetic (e.g., support, help, manager, apologies)
        has_discount = "15%" in custom_message or "COMEBACK15" in custom_message
        is_empathetic = any(w in custom_message.lower() for w in ["support", "manager", "help", "apolog", "sorry"])
        is_pass = res.get("success") is True and not has_discount and is_empathetic
        print_result(
            "Empathetic Apology & Escalation Nudge", 
            is_pass, 
            f"Sent message: '{custom_message}'", 
            f"Response: {res}"
        )

        # Test Case 5: AI Personalization (Confused)
        print_header("Test Case 5: AI Personalization (Confused Student)")
        req = NudgeRequest(
            phone="9999999994",
            name="Test Confused",
            course_interest="Cloud Computing",
            session_token="token-confused"
        )
        chat._sessions["token-confused"] = {
            "student": chat.get_persistent_student("9999999994"),
            "history": [{"role": "user", "content": "I am not sure about timing or syllabus."}]
        }
        res = await trigger_abandoned_nudge(req)
        custom_message = res.get("custom_message", "")
        # Should not contain discount info
        # Should offer to clarify details
        has_discount = "15%" in custom_message or "COMEBACK15" in custom_message
        offers_clarification = any(w in custom_message.lower() for w in ["clarify", "doubt", "timing", "syllabus", "schedule", "fee"])
        is_pass = res.get("success") is True and not has_discount and offers_clarification
        print_result(
            "Clarification Nudge", 
            is_pass, 
            f"Sent message: '{custom_message}'", 
            f"Response: {res}"
        )

        # Test Case 6: AI Personalization (Positive/Neutral)
        print_header("Test Case 6: AI Personalization (Positive/Neutral Student)")
        req = NudgeRequest(
            phone="9999999995",
            name="Test Positive",
            course_interest="AI/ML Bootcamp",
            session_token="token-positive"
        )
        chat._sessions["token-positive"] = {
            "student": chat.get_persistent_student("9999999995"),
            "history": [{"role": "user", "content": "The syllabus looks very good!"}]
        }
        res = await trigger_abandoned_nudge(req)
        custom_message = res.get("custom_message", "")
        # Should offer discount
        has_discount = "COMEBACK15" in custom_message or "15%" in custom_message
        is_pass = res.get("success") is True and has_discount
        print_result(
            "Discount Offer Nudge", 
            is_pass, 
            f"Sent message: '{custom_message}'", 
            f"Response: {res}"
        )

    finally:
        restore_data()

if __name__ == "__main__":
    asyncio.run(run_tests())
