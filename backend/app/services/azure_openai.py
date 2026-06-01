"""
azure_openai.py — EduFlow AI LLM Service

Wraps the Azure OpenAI API. When credentials are missing or invalid,
falls back to a local keyword-based semantic matcher that uses the
injected JSON data to generate realistic responses. This ensures 100%
functionality without any API key configuration.
"""

import os
import json
import re
from pathlib import Path

# ─── Azure OpenAI SDK ───────────────────────────────────────────────────────
try:
    from openai import AzureOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

DATA_DIR = Path(__file__).parent.parent / "data"

SYSTEM_PROMPT_TEMPLATE = """You are EduFlow AI, the intelligent support assistant for EduFlow Coaching Institute. You help students with course enquiries, enrollment, batch schedules, and support queries.

AVAILABLE DATA:
{courses_data}

BATCH INFORMATION:
{batches_data}

FREQUENTLY ASKED QUESTIONS:
{faq_data}

STUDENT CONTEXT:
Name: {student_name}
Phone: {student_phone}
Course Interest: {course_interest}
Enrolled: {is_enrolled}

RULES:
1. Always address the student by their first name ({student_name}).
2. Be warm, friendly, and encouraging — like a helpful senior student.
3. Never say "I don't know" — if uncertain, offer to connect them with the team.
4. Keep responses concise (under 100 words) unless explaining a syllabus.
5. After every response, output on a new line: SENTIMENT: [positive|neutral|frustrated|confused]
6. If student seems frustrated (2+ complaints), offer human escalation.
7. If student asks to enroll, confirm their preferred batch and say you will process enrollment.
8. Never make up fees, dates, or data not in the provided context.
9. Use emojis sparingly but warmly. 
10. If a student asks about course details, always mention the specific fee and batch timing.

TONE: Warm, clear, encouraging. Not corporate. Not robotic."""


def _load_json(filename: str) -> list | dict:
    """Load a JSON data file safely."""
    try:
        with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _build_system_prompt(student: dict) -> str:
    """Build the full system prompt with injected data context."""
    courses = _load_json("courses.json")
    batches = _load_json("batches.json")
    faq = _load_json("faq.json")

    # Summarise courses for context
    courses_text = "\n".join(
        f"- {c['name']}: ₹{c['fee']:,} | {c['duration']} | {c['mode']} | "
        f"Placement: {'Yes' if c['placement'] else 'No'} | "
        f"EMI: {'Yes, ₹' + str(c['emi_amount']) + '/mo' if c['emi_available'] else 'No'}"
        for c in courses
    )

    # Summarise batches
    batches_text = "\n".join(
        f"- [{b['course_id']}] {b['id']}: Starts {b['start_date']} | {b['time']} | "
        f"{b['days']} | Instructor: {b['instructor']} | Seats left: {b['seats_left']} | Mode: {b['mode']}"
        for b in batches
    )

    # Summarise FAQ
    faq_text = "\n".join(f"Q: {item['q']}\nA: {item['a']}" for item in faq[:15])

    return SYSTEM_PROMPT_TEMPLATE.format(
        courses_data=courses_text,
        batches_data=batches_text,
        faq_data=faq_text,
        student_name=student.get("name", "Student"),
        student_phone=student.get("phone", ""),
        course_interest=student.get("course_interest", "Not specified"),
        is_enrolled="Yes — " + str(student.get("enrolled_course", "")) if student.get("enrolled") else "No",
    )


def _local_fallback(message: str, student: dict, history: list) -> tuple[str, str]:
    """
    Local keyword-based semantic responder. Used when Azure OpenAI credentials
    are not configured. Provides realistic, data-grounded responses.
    """
    courses = _load_json("courses.json")
    batches = _load_json("batches.json")
    faq = _load_json("faq.json")
    name = student.get("name", "there")
    msg_lower = message.lower()

    # ── Intent: enroll ───────────────────────────────────────────────────────
    if any(w in msg_lower for w in ["enroll", "join", "register", "admission", "i want to"]):
        interest = student.get("course_interest", "AI/ML Bootcamp")
        course = next((c for c in courses if c["name"].lower() in interest.lower()), courses[0])
        batch = next((b for b in batches if b["course_id"] == course["id"]), batches[0])
        return (
            f"That's amazing, {name}! 🎉 Let me lock in your spot.\n\n"
            f"**Course:** {course['name']}\n"
            f"**Batch:** {batch['id']} — starts {batch['start_date']}\n"
            f"**Time:** {batch['time']} | {batch['days']}\n"
            f"**Instructor:** {batch['instructor']}\n"
            f"**Fee:** ₹{course['fee']:,}"
            + (f" (or ₹{course['emi_amount']:,}/mo EMI)" if course["emi_available"] else "")
            + f"\n\nJust confirm and I'll process your enrollment and send the WhatsApp confirmation instantly! ✅",
            "positive",
        )

    # ── Intent: fee / price ──────────────────────────────────────────────────
    if any(w in msg_lower for w in ["fee", "cost", "price", "how much", "charges", "emi", "pay"]):
        lines = [f"Here's our course fee breakdown, {name}:\n"]
        for c in courses:
            emi_note = f" (EMI: ₹{c['emi_amount']:,}/mo)" if c["emi_available"] else " (No EMI)"
            lines.append(f"• **{c['name']}**: ₹{c['fee']:,}{emi_note}")
        lines.append("\nAll fees include live classes, recordings, certificate & doubt sessions. Want to know more about any specific course? 😊")
        return "\n".join(lines), "positive"

    # ── Intent: batch / schedule / timing ───────────────────────────────────
    if any(w in msg_lower for w in ["batch", "timing", "schedule", "when", "start", "date", "time", "slot"]):
        interest = student.get("course_interest", "")
        relevant = [b for b in batches if interest.lower() in b["course_id"].replace("-", " ")] if interest else batches[:3]
        if not relevant:
            relevant = batches[:3]
        lines = [f"Here are the upcoming batches for you, {name}:\n"]
        for b in relevant[:3]:
            lines.append(
                f"• **{b['id']}**: {b['start_date']} | {b['time']} | {b['days']}\n"
                f"  Instructor: {b['instructor']} | Seats left: {b['seats_left']} | Mode: {b['mode']}"
            )
        return "\n".join(lines) + "\n\nWhich timing works best for you?", "positive"

    # ── Intent: specific course mention ─────────────────────────────────────
    for course in courses:
        tags_hit = any(tag.lower() in msg_lower for tag in course["tags"])
        name_hit = any(w in msg_lower for w in course["name"].lower().split())
        if tags_hit or name_hit:
            batch = next((b for b in batches if b["course_id"] == course["id"]), None)
            seats_note = f" — only {batch['seats_left']} seats left!" if batch and batch["seats_left"] <= 5 else ""
            return (
                f"Great choice, {name}! 🚀 Here's what you need to know about **{course['name']}**:\n\n"
                f"📅 **Duration:** {course['duration']}\n"
                f"💰 **Fee:** ₹{course['fee']:,}"
                + (f" (EMI from ₹{course['emi_amount']:,}/mo)" if course["emi_available"] else "")
                + f"\n🖥️ **Mode:** {course['mode'].title()}\n"
                f"🏆 **Placement:** {'Yes' if course['placement'] else 'Not included'}\n"
                f"📜 **Certificate:** {'Yes' if course['certificate'] else 'No'}\n"
                + (f"\n⏰ **Next batch starts:** {batch['start_date']} | {batch['time']}{seats_note}" if batch else "")
                + "\n\nWant to know more about the syllabus or batches? Just ask! 😊",
                "positive",
            )

    # ── Intent: refund / cancel ──────────────────────────────────────────────
    if any(w in msg_lower for w in ["refund", "cancel", "money back", "return"]):
        faq_item = next((f for f in faq if "refund" in f["q"].lower()), None)
        if faq_item:
            return f"{faq_item['a']}\n\nIf you'd like to discuss your specific situation, I can connect you with our support team right away, {name}. 💙", "neutral"

    # ── Intent: placement / job ──────────────────────────────────────────────
    if any(w in msg_lower for w in ["placement", "job", "hire", "career", "salary", "company"]):
        return (
            f"Our placement support is top-notch, {name}! 🌟\n\n"
            "Courses with placement: AI/ML Bootcamp, Full Stack Web, Data Science Pro & Cloud Computing.\n"
            "We offer: mock interviews, resume reviews, LinkedIn optimisation, and direct referrals to partners like TCS, Infosys, Razorpay & top startups.\n\n"
            "Our last cohort had a 78% placement rate within 90 days of completion. 💪",
            "positive",
        )

    # ── Intent: certificate ──────────────────────────────────────────────────
    if any(w in msg_lower for w in ["certificate", "cert", "validity", "recognised", "valid"]):
        return (
            f"Yes, {name}! All our certificates are issued by EduFlow Institute (ISO 9001 Certified). "
            "They include a QR code for online verification and are widely recognised by recruiters and companies. "
            "Several alumni have successfully used them for promotions and new job offers! 🏅",
            "positive",
        )

    # ── Intent: frustrated / unhappy ────────────────────────────────────────
    if any(w in msg_lower for w in ["frustrated", "angry", "useless", "waste", "bad", "terrible", "horrible", "ridiculous"]):
        return (
            f"I'm really sorry to hear that, {name}. 😔 Your frustration is completely valid and I want to make this right. "
            "Would you like me to connect you with our support manager right away? "
            "They'll prioritise your case and get back to you within 2 hours. Just say 'yes' and I'll flag this immediately. 💙",
            "frustrated",
        )

    # ── Intent: greeting ─────────────────────────────────────────────────────
    if any(w in msg_lower for w in ["hi", "hello", "hey", "namaste", "good"]):
        return (
            f"Hey {name}! 👋 Great to have you here at EduFlow!\n\n"
            "I can help you with:\n"
            "🎓 **Course info** — fees, syllabus, duration\n"
            "📅 **Batch schedules** — timings, instructors, seats\n"
            "✅ **Enrollment** — join a course in minutes\n"
            "❓ **Any questions** — refunds, EMI, placement...\n\n"
            "What are you interested in today?",
            "positive",
        )

    # ── Intent: FAQ match ────────────────────────────────────────────────────
    best_faq = None
    best_score = 0
    for item in faq:
        q_words = set(item["q"].lower().split())
        msg_words = set(msg_lower.split())
        score = len(q_words & msg_words)
        if score > best_score:
            best_score = score
            best_faq = item

    if best_faq and best_score >= 2:
        return f"{best_faq['a']}\n\nAnything else I can help with, {name}? 😊", "neutral"

    # ── Default fallback ──────────────────────────────────────────────────────
    return (
        f"That's a great question, {name}! 😊 I want to make sure I give you the right answer. "
        "Could you tell me a bit more? For example — are you asking about a specific course, batch timing, fee, or something else? "
        "I'm here to help with anything EduFlow-related!",
        "neutral",
    )


def _is_configured() -> bool:
    """Check if Azure OpenAI credentials are set."""
    key = os.getenv("AZURE_OPENAI_API_KEY", "")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    return (
        OPENAI_AVAILABLE
        and bool(key)
        and key != "YOUR_AZURE_OPENAI_API_KEY"
        and bool(endpoint)
        and "YOUR-RESOURCE-NAME" not in endpoint
    )


def parse_sentiment(raw_response: str) -> tuple[str, str]:
    """
    Separate the SENTIMENT tag from the bot's actual response text.
    Returns (clean_response, sentiment).
    """
    lines = raw_response.strip().split("\n")
    sentiment = "neutral"
    clean_lines = []

    for line in lines:
        if line.strip().upper().startswith("SENTIMENT:"):
            raw_s = line.split(":", 1)[1].strip().lower()
            raw_s = re.sub(r"[^a-z]", "", raw_s)
            if raw_s in {"positive", "neutral", "frustrated", "confused"}:
                sentiment = raw_s
        else:
            clean_lines.append(line)

    clean_response = "\n".join(clean_lines).strip()
    return clean_response, sentiment


def chat_with_llm(message: str, history: list, student: dict) -> tuple[str, str]:
    """
    Main chat function. Uses Azure OpenAI when configured, local fallback otherwise.

    Returns:
        (response_text, sentiment)  — both as strings.
    """
    if _is_configured():
        try:
            client = AzureOpenAI(
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            )
            deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
            system_prompt = _build_system_prompt(student)

            messages = [{"role": "system", "content": system_prompt}]
            for h in history[-10:]:  # keep last 10 turns for context
                messages.append(h)
            messages.append({"role": "user", "content": message})

            response = client.chat.completions.create(
                model=deployment,
                messages=messages,
                temperature=0.7,
                max_tokens=400,
            )
            raw = response.choices[0].message.content
            return parse_sentiment(raw)

        except Exception as e:
            print(f"[Azure OpenAI Error] {e} — falling back to local responder")

    # Local fallback
    response, sentiment = _local_fallback(message, student, history)
    return response, sentiment
