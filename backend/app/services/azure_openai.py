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

from app.services import whatsapp_service

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
Enrolled Batch: {enrolled_batch}

RULES:
1. Always address the student by their first name ({student_name}).
2. Be highly constructive, clear, and informative. Avoid generic filler text; give direct, structured answers with clear headings, bold details, and bullet points. Never use markdown tables.
3. Never say "I don't know" — if uncertain, offer to connect them with the team.
4. Keep responses concise (under 100 words) unless explaining a syllabus.
5. After every response, output on a new line: SENTIMENT: [positive|neutral|frustrated|confused]
6. If student seems frustrated (2+ complaints), offer human escalation.
7. If student asks to enroll, confirm their preferred batch and enroll them using the 'enroll_in_batch' tool once they confirm they want to proceed.
8. Never make up fees, dates, or data not in the provided context.
9. Use emojis warmly and consistently to make the conversation visually engaging and friendly.
10. If a student asks about course details, always mention the specific fee and batch timing.
11. You are fully capable of sending WhatsApp messages directly. Never say you cannot send WhatsApp messages. If a student asks you to send batch details, discount codes, confirmations, or information to their WhatsApp, or says "whatsapp me" / "send this to whatsapp", use the 'send_whatsapp_message' tool to send it to their phone number, and then confirm in your text reply that you have sent it.
12. Proactively offer to send details to their WhatsApp when explaining batches, schedules, or enrolling (e.g. "Would you like me to send these batch details to your WhatsApp?").
13. You can enroll students directly. If a student confirms they want to enroll, call the 'enroll_in_batch' tool to process their enrollment. Confirm in your text response that they are enrolled. Tell them that WhatsApp is a one-way notification/updates channel where they will receive their confirmation details, and that the enrollment is processed instantly right here in this chat (they do NOT need to reply on WhatsApp to confirm).
14. Never format course lists, fee structures, or batch schedules as tables. Instead, always present them as clean, pointwise bullet lists with relevant emojis next to each item and bold text for key details (like names, fees, dates, and timings) so that they are visually engaging, clean, and easy to read.
15. If explaining a single course or batch, use a clean list with emojis next to each point.

TONE: Constructive, encouraging, warm, and highly structured. Not corporate. Not robotic."""


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
        enrolled_batch=student.get("enrolled_batch", "None"),
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
    # ── WhatsApp Trigger Check ──────────────────────────────────────────────
    whatsapp_keywords = ["whatsapp", "text me", "send me", "message me", "ping me", "share on", "forward to", "send to"]
    if any(w in msg_lower for w in whatsapp_keywords):
        # 1. Look for quoted string in message
        quotes = re.findall(r'"([^"]*)"', message)
        if not quotes:
            quotes = re.findall(r"'([^']*)'", message)
        
        custom_msg = quotes[0] if quotes else None
        
        # 2. Look for "saying ..." or "texting ..." or "message ..."
        if not custom_msg:
            match = re.search(r'(?:saying|texting|message|content|with)\s+(.+)$', message, re.IGNORECASE)
            if match:
                custom_msg = match.group(1).strip()
                custom_msg = re.sub(r'^["\'\s]+|["\'\s]+$', '', custom_msg)
        
        # 3. If no custom message, check if there is a last reply in history
        if not custom_msg:
            last_reply = None
            for h in reversed(history):
                if h.get("role") in ["assistant", "bot"]:
                    last_reply = h.get("content")
                    break
            if last_reply:
                custom_msg = last_reply
        
        # 4. If still no custom message, send batch/course details
        if not custom_msg or any(w in msg_lower for w in ["batch", "course", "schedule", "detail", "timing"]):
            course_interest = student.get("course_interest", "AI/ML Bootcamp") or "AI/ML Bootcamp"
            course_obj = next((c for c in courses if course_interest.lower() in c["name"].lower()), courses[0])
            batch_obj = next((b for b in batches if b["course_id"] == course_obj["id"]), batches[0])
            
            custom_msg = (
                f"Hey {name}! 🎓 Here are the batch details you requested:\n\n"
                f"📍 *Course:* {course_obj['name']}\n"
                f"🗓️ *Starts:* {batch_obj['start_date']}\n"
                f"⏰ *Timing:* {batch_obj['time']} | {batch_obj['days']}\n"
                f"👨‍🏫 *Instructor:* {batch_obj['instructor']}\n"
                f"🚪 *Seats Left:* {batch_obj['seats_left']} slots\n\n"
                f"Let us know if you want to enroll! 🚀"
            )
        
        whatsapp_service.send_custom_message(
            phone=student.get("phone", ""),
            name=name,
            message=custom_msg
        )
        return (
            f"I have successfully sent those details directly to your WhatsApp number (+91 {student.get('phone')})! 🚀 Check your phone and let me know if you need anything else.",
            "positive"
        )

    # ── Already Enrolled Check ──────────────────────────────────────────────
    if student.get("enrolled"):
        course_id = student.get("enrolled_course", "")
        batch_id = student.get("enrolled_batch", "")
        course_obj = next((c for c in courses if c["id"] == course_id), None)
        batch_obj = next((b for b in batches if b["id"] == batch_id), None)
        course_name = course_obj["name"] if course_obj else "AI/ML Bootcamp"
        batch_time = batch_obj["time"] if batch_obj else "7-9 PM"
        batch_start = batch_obj["start_date"] if batch_obj else "2026-07-10"
        
        if any(w in msg_lower for w in ["not have that info", "not have info", "why do you ask", "i already enrolled", "am i not enrolled", "tracked", "dont have"]):
            return (
                f"Oh, my apologies, {name}! 🌟 I definitely have your details tracked:\n\n"
                f"🎓 **Course:** {course_name}\n"
                f"📌 **Batch:** {batch_id.replace('-', ' ').title()}\n"
                f"🗓️ **Starts:** {batch_start}\n"
                f"⏰ **Timing:** {batch_time} ({batch_obj['days'] if batch_obj else 'Mon, Wed, Fri'})\n\n"
                "All your enrollment details are fully secured in our system! 🚀",
                "positive",
            )

        if any(w in msg_lower for w in ["hi", "hello", "hey", "namaste", "good"]):
            return (
                f"Hey {name}! 👋 Great to have you back!\n\n"
                f"You are currently enrolled in **{course_name}**:\n"
                f"🗓️ **Starts:** {batch_start}\n"
                f"⏰ **Timing:** {batch_time} ({batch_obj['days'] if batch_obj else 'Mon, Wed, Fri'})\n\n"
                "I'm here to help you prepare. You can ask me about batch schedules, course instructors, placement support, or fee installments! 😊",
                "positive"
            )

    # ── Intent: confirm enrollment (yes/sure/y) ──────────────────────────────
    if any(w in msg_lower for w in ["yes", "confirm", "sure", "ok", "y", "correct", "go ahead"]):
        last_bot_msg = ""
        for h in reversed(history):
            if h.get("role") in ["assistant", "bot"]:
                last_bot_msg = h.get("content", "").lower()
                break
        if "process your enrollment" in last_bot_msg or "lock in your spot" in last_bot_msg:
            from app.services.enrollment import enroll_student_in_batch
            interest = student.get("course_interest", "AI/ML Bootcamp")
            course = next((c for c in courses if c["name"].lower() in interest.lower()), courses[0])
            batch = next((b for b in batches if b["course_id"] == course["id"]), batches[0])
            
            res = enroll_student_in_batch(
                phone=student.get("phone", ""),
                batch_id=batch["id"],
                student_session_dict=student
            )
            if res["success"]:
                return (
                    f"🎉 Congratulations, {name}! You have been successfully enrolled in **{course['name']}** (Batch: {batch['id']})! "
                    f"I have processed your registration directly in the database. "
                    f"We have sent your official schedule and joining details to your WhatsApp (+91 {student.get('phone')}). "
                    f"Please note that WhatsApp is just a one-way notification channel where you'll receive updates — you're fully enrolled right now! 🚀",
                    "positive"
                )
            else:
                return (
                    f"I tried to process your enrollment, but it failed: {res.get('error')}. "
                    "You can also use the 'Enroll now' button in the header to pick a batch and complete it! 🛠️",
                    "confused"
                )

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
        points = []
        for c in courses:
            emi_note = f"(EMI: ₹{c['emi_amount']:,}/mo)" if c["emi_available"] else "(No EMI option)"
            points.append(f"• 🎓 **{c['name']}**: Total fee of **₹{c['fee']:,}** {emi_note}")
        points_text = "\n".join(points)
        return (
            f"Here is our course fee breakdown, {name}: 💰\n\n"
            f"{points_text}\n\n"
            f"All fees include live interactive classes, lifetime access to recordings, verified ISO certificates, and 1-on-1 mentorship. Do you have a specific course in mind? 😊",
            "positive"
        )

    # ── Intent: batch / schedule / timing ───────────────────────────────────
    if any(w in msg_lower for w in ["batch", "timing", "schedule", "when", "start", "date", "time", "slot"]):
        interest = student.get("course_interest", "")
        relevant = [b for b in batches if interest.lower() in b["course_id"].replace("-", " ")] if interest else batches[:3]
        if not relevant:
            relevant = batches[:3]
        
        points = []
        for b in relevant[:3]:
            clean_batch_name = b['id'].replace('-', ' ').title()
            points.append(
                f"• 📌 **{clean_batch_name}**:\n"
                f"  🗓️ Starts: **{b['start_date']}**\n"
                f"  ⏰ Time: **{b['time']}** ({b['days']})\n"
                f"  🚪 Seats left: **{b['seats_left']}**\n"
                f"  💻 Mode: **{b['mode'].title()}**"
            )
        points_text = "\n\n".join(points)
        return (
            f"Here are the upcoming batches for you, {name}: 🎓\n\n"
            f"{points_text}\n\n"
            f"Which timing works best for you? 😊",
            "positive"
        )

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

    # ── Intent: internship ───────────────────────────────────────────────────
    if any(w in msg_lower for w in ["internship", "intern", "flowzint"]):
        return (
            f"Build your future with **FlowZint Corporate Internships**, {name}! 🚀\n\n"
            "This is an elite, intensive **30-Day corporate program** engineered for ambitious freshers and students. "
            "Execute real-world enterprise projects, secure an industry-recognized selection letter & certification, and unlock direct placement opportunities with our 50+ corporate hiring partners! Flat registration fee is only **₹1,999**.\n\n"
            "**Curated Technical Tracks:**\n"
            "1. 🧠 **Artificial Intelligence**: ML models, Neural Networks, Generative AI & LLM integration.\n"
            "2. 📊 **Power BI Data Analytics**: Ingestion, ETL pipelines, DAX & interactive executive dashboards.\n"
            "3. 💻 **Website Development**: Component-driven UI engineering, React.js, Responsive & APIs.\n"
            "4. 📱 **App Development**: Cross-platform mobile engineering (Flutter / React Native) for iOS & Android.\n"
            "5. 🌐 **Full Stack Engineering (Master Program)**: Microservices, database schema, secure JWT authentication & AWS/Vercel deployment.\n\n"
            "Would you like to start your application or learn more about a specific domain? 😊",
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
        "confused",
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

            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "send_whatsapp_message",
                        "description": "Send a WhatsApp message directly to the student's phone number with course details, batch schedules, reminders, or general announcements.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "phone": {
                                    "type": "string",
                                    "description": "The 10-digit phone number of the student (e.g., '917010599822')."
                                },
                                "message": {
                                    "type": "string",
                                    "description": "The full text message to send to the student's WhatsApp."
                                }
                            },
                            "required": ["phone", "message"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "enroll_in_batch",
                        "description": "Enroll the student into a specific course batch. Use this when the student explicitly confirms they want to enroll and has chosen a batch.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "batch_id": {
                                    "type": "string",
                                    "description": "The exact ID of the batch to enroll in (e.g., 'batch-ai-jun', 'batch-fs-jun')."
                                }
                            },
                            "required": ["batch_id"]
                        }
                    }
                }
            ]

            response = client.chat.completions.create(
                model=deployment,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=400,
            )

            response_message = response.choices[0].message
            tool_calls = getattr(response_message, "tool_calls", None)

            if tool_calls:
                # Safely serialize tool calls to dictionary format
                tool_calls_list = []
                for tc in tool_calls:
                    tool_calls_list.append({
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    })
                messages.append({
                    "role": "assistant",
                    "content": response_message.content,
                    "tool_calls": tool_calls_list
                })

                # Process all tool calls
                for tool_call in tool_calls:
                    if tool_call.function.name == "send_whatsapp_message":
                        args = json.loads(tool_call.function.arguments)
                        whatsapp_service.send_custom_message(
                            phone=args.get("phone"),
                            name=student.get("name", "Student"),
                            message=args.get("message")
                        )

                        # Append tool response
                        messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": "send_whatsapp_message",
                            "content": json.dumps({"status": "success", "message": "WhatsApp message sent successfully"})
                        })
                    elif tool_call.function.name == "enroll_in_batch":
                        args = json.loads(tool_call.function.arguments)
                        from app.services.enrollment import enroll_student_in_batch
                        res = enroll_student_in_batch(
                            phone=student.get("phone", ""),
                            batch_id=args.get("batch_id"),
                            student_session_dict=student
                        )

                        # Append tool response
                        messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": "enroll_in_batch",
                            "content": json.dumps(res)
                        })

                # Retrieve final text response from model
                final_response = client.chat.completions.create(
                    model=deployment,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=400,
                )
                raw = final_response.choices[0].message.content
                return parse_sentiment(raw)

            raw = response_message.content
            return parse_sentiment(raw)

        except Exception as e:
            print(f"[Azure OpenAI Error] {e} — falling back to local responder")

    # Local fallback
    response, sentiment = _local_fallback(message, student, history)
    return response, sentiment


def _local_nudge_fallback(student: dict, history: list) -> tuple[bool, str]:
    if student.get("enrolled"):
        return False, ""

    name = student.get("name", "there")
    course_interest = student.get("course_interest", "AI/ML Bootcamp")
    sentiments = student.get("sentiment_history", [])
    last_sentiment = sentiments[-1] if sentiments else "neutral"

    if last_sentiment == "frustrated":
        message = (
            f"💙 *EduFlow Support Team* 💙\n\n"
            f"Hey {name}! We noticed you had some frustrations during our chat. "
            f"We value your experience above all else and want to make things right immediately.\n\n"
            f"💬 _Would you like me to connect you with our Senior Support Manager directly?_ "
            f"Reply with *'yes'* and we'll flag this as a priority. Let's get it resolved! 🤝"
        )
    elif last_sentiment == "confused":
        message = (
            f"👋 *Hey {name}! Quick Check-in* 🎓\n\n"
            f"I'm here to clear up any confusion or doubts about our *{course_interest}* bootcamp! "
            f"Whether it's batch timings, fees, installments, or the placement guarantee, no question is too small.\n\n"
            f"💬 _Ask me anything right here!_ What's the main doubt holding you back? Let's talk! 😊"
        )
    else:
        message = (
            f"✨ *EduFlow Special Invitation* ✨\n\n"
            f"Hey {name}! 👋 Still thinking about joining our *{course_interest}* bootcamp? "
            f"We have just 2 slots left in the upcoming batch! ⏳\n\n"
            f"⚡ *Exclusive Recovery Gift:*\n"
            f"🎁 Enjoy *15% OFF* on your enrollment!\n"
            f"🔑 Code: *COMEBACK15*\n\n"
            f"💬 _\"The best way to predict the future is to create it.\"_ — Peter Drucker\n\n"
            f"Reply here or jump back into the chat to lock in your spot! 🚀"
        )

    return True, message


def generate_nudge_with_llm(student: dict, history: list) -> tuple[bool, str]:
    """
    Use Azure OpenAI (or local fallback) to check if a nudge is needed
    based on the student's history and sentiment, and customize the message.
    """
    if _is_configured():
        try:
            from openai import AzureOpenAI
            client = AzureOpenAI(
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            )
            deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")

            # Extract last sentiment
            sentiments = student.get("sentiment_history", [])
            last_sentiment = sentiments[-1] if sentiments else "neutral"
            course_interest = student.get("course_interest", "AI/ML Bootcamp")
            name = student.get("name", "Student")

            # Format history for prompt
            history_text = ""
            for h in history[-6:]:
                history_text += f"{h['role'].capitalize()}: {h['content']}\n"

            system_prompt = (
                "You are the Lead Student Counselor at EduFlow. A student has gone inactive mid-conversation.\n"
                "Your job is to decide if we should nudge them, and write a highly personalized, empathetic, non-repetitive nudge message.\n\n"
                "RULES FOR DECISION:\n"
                "1. SHOULD_NUDGE should be 'yes' only if the student has engaged but paused. If history is empty, SHOULD_NUDGE is 'yes' (we send a friendly greeting).\n"
                "2. If the student is already enrolled, SHOULD_NUDGE must be 'no'.\n"
                "3. If the student is frustrated, SHOULD_NUDGE is 'yes' but do NOT offer a discount or sales pitch. Instead, apologize warmly and ask if they would like to speak to a senior manager or have us call them.\n"
                "4. If the student is confused, SHOULD_NUDGE is 'yes'. Offer to clarify their specific doubt (e.g. fees, timings, syllabus) and ask how you can help.\n"
                "5. If the student is positive or neutral, SHOULD_NUDGE is 'yes'. Give them a friendly reminder and offer a warm 15% discount code (COMEBACK15) to help them get started.\n"
                "6. The MESSAGE must be warm, friendly, natural, and under 60 words. Avoid generic templates. Address them by name.\n\n"
                "Format your output EXACTLY as:\n"
                "SHOULD_NUDGE: [yes/no]\n"
                "REASON: [reason for decision]\n"
                "MESSAGE: [your customized WhatsApp message text]"
            )

            prompt = (
                f"Student Name: {name}\n"
                f"Course Interest: {course_interest}\n"
                f"Current Sentiment: {last_sentiment}\n"
                f"Conversation History:\n{history_text}\n"
            )

            response = client.chat.completions.create(
                model=deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200,
            )

            raw = response.choices[0].message.content.strip()
            print(f"[Nudge AI Output]\n{raw}")

            should_nudge = False
            msg_text = ""
            
            # Parse SHOULD_NUDGE: yes/no
            match_nudge = re.search(r"SHOULD_NUDGE:\s*(yes|no)", raw, re.IGNORECASE)
            if match_nudge and match_nudge.group(1).lower() == "yes":
                should_nudge = True

            # Parse MESSAGE: text
            match_msg = re.search(r"MESSAGE:\s*(.+)$", raw, re.IGNORECASE | re.DOTALL)
            if match_msg:
                msg_text = match_msg.group(1).strip()

            return should_nudge, msg_text

        except Exception as e:
            print(f"[Nudge AI Error] {e} — falling back to local nudge generation")

    # Local fallback
    return _local_nudge_fallback(student, history)
