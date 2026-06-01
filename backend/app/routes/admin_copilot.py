"""
admin_copilot.py — EduFlow AI Admin Copilot Route

Exposes an interactive AI assistant specifically for administrators.
It loads the entire database state (analytics, students, courses, batches, reviews)
and lets the admin query statistics, pipelines, conversion metrics, and reviews.
"""

import json
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.azure_openai import parse_sentiment, _is_configured

try:
    from openai import AzureOpenAI
except ImportError:
    pass

router = APIRouter()
DATA_DIR = Path(__file__).parent.parent / "data"

class CopilotRequest(BaseModel):
    query: str
    history: list = []  # [{role, content}]

# Helper to load data
def _load_json(filename: str) -> dict | list:
    try:
        with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

SYSTEM_PROMPT = """You are EduFlow Admin Copilot, an advanced business intelligence assistant for the administrator of EduFlow Coaching Institute & FlowZint Internships.
You have real-time access to the entire institute's databases including student enquiries, active enrollments, course catalogs, upcoming batches, and course reviews.

INSTITUTE DATABASES:

1. ANALYTICS & METRICS:
{analytics_data}

2. STUDENT PIPELINES (Enrolled, Hot Leads, Investigated):
{students_data}

3. COURSE DIRECTORY & SPECIALIZATIONS:
{courses_data}

4. BATCH STATUSES:
{batches_data}

5. RECENT REVIEWS & RATINGS:
{reviews_data}

RULES:
1. Answer the administrator's question precisely using the database numbers above.
2. Be professional, analytical, and insightful. Highlight key business trends where relevant (e.g. drop-offs, popular courses, high conversion opportunities).
3. If asked to summarize reviews, provide a brief synthesis of student sentiment.
4. Keep responses clear and structured using markdown tables or bullet points where useful.
5. If the admin asks to "nudge" someone or check something, explain that they can do this directly from the pipeline tab.
"""

@router.post("/admin/copilot")
async def admin_copilot(req: CopilotRequest):
    """Query the Admin Copilot with business intelligence requests."""
    # 1. Gather all databases
    analytics = _load_json("analytics.json")
    students_db = _load_json("students.json")
    courses = _load_json("courses.json")
    batches = _load_json("batches.json")
    reviews_db = _load_json("reviews.json")

    # Get verified students for pipeline counts
    verified = students_db.get("verified_students", [])
    enrolled = [s for s in verified if s.get("enrolled")]
    investigated = [s for s in verified if not s.get("enrolled")]
    hot_leads = [s for s in investigated if s.get("message_count", 0) >= 2]

    # Summarize database records
    analytics_text = json.dumps(analytics, indent=2)
    students_summary = {
        "total_verified_leads": len(verified),
        "total_enrolled": len(enrolled),
        "total_unenrolled_enquirers": len(investigated),
        "hot_leads_count": len(hot_leads),
        "hot_leads": [{"name": h["name"], "phone": h["phone"], "interest": h.get("course_interest", "AI/ML Bootcamp"), "msg_count": h.get("message_count", 0)} for h in hot_leads[:5]]
    }
    students_text = json.dumps(students_summary, indent=2)
    
    courses_text = json.dumps([{"id": c["id"], "name": c["name"], "fee": c["fee"], "duration": c["duration"]} for c in courses], indent=2)
    batches_text = json.dumps([{"id": b["id"], "course_id": b["course_id"], "seats_left": b["seats_left"], "instructor": b["instructor"]} for b in batches], indent=2)
    reviews_text = json.dumps(reviews_db, indent=2)

    # 2. Build full prompt
    full_prompt = SYSTEM_PROMPT.format(
        analytics_data=analytics_text,
        students_data=students_text,
        courses_data=courses_text,
        batches_data=batches_text,
        reviews_data=reviews_text
    )

    if _is_configured():
        try:
            client = AzureOpenAI(
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            )
            deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")

            messages = [{"role": "system", "content": full_prompt}]
            for h in req.history[-10:]:
                messages.append(h)
            messages.append({"role": "user", "content": req.query})

            response = client.chat.completions.create(
                model=deployment,
                messages=messages,
                temperature=0.4,
                max_tokens=500,
            )
            raw = response.choices[0].message.content
            return {"response": raw}
        except Exception as e:
            print(f"[Admin Copilot Azure Error] {e} — falling back")

    # Local Fallback Responder
    q_lower = req.query.lower()
    total_rating = sum(r["rating"] for r in reviews_db.get("reviews", [])) if isinstance(reviews_db, dict) else sum(r["rating"] for r in reviews_db)
    reviews_list = reviews_db.get("reviews", []) if isinstance(reviews_db, dict) else reviews_db
    avg_rating = round(total_rating / len(reviews_list), 1) if reviews_list else 4.8

    if any(w in q_lower for w in ["hot lead", "leads", "hottest"]):
        lead_list = "\n".join([f"- **{h['name']}** (+91 {h['phone']}) - interested in *{h.get('course_interest', 'AI/ML') }* ({h.get('message_count', 0)} messages)" for h in hot_leads])
        return {
            "response": f"Here is our **Hot Leads Pipeline** analysis:\n\n"
                        f"We currently have **{len(hot_leads)} hot leads** actively interacting but not yet enrolled:\n\n"
                        f"{lead_list if hot_leads else 'No hot leads at the moment.'}\n\n"
                        f"💡 *Recommendation*: You can nudge these students directly from the **Pipeline** panel with a 20% discount offer!"
        }

    if any(w in q_lower for w in ["enrolled", "enrollment", "conversion", "rate"]):
        rate = analytics.get("conversion_rate", 20.0)
        return {
            "response": f"📊 **Enrollment & Conversion Summary**:\n\n"
                        f"- **Total verified enquirers**: {len(verified)}\n"
                        f"- **Total enrolled students**: {len(enrolled)}\n"
                        f"- **Active Conversion Rate**: **{rate}%**\n\n"
                        f"Our primary driver remains the AI/ML Bootcamp. Conversion has increased since introducing the WhatsApp cart-abandonment nudges!"
        }

    if any(w in q_lower for w in ["review", "rating", "satisfaction", "stars"]):
        return {
            "response": f"⭐ **Student Satisfaction Analytics**:\n\n"
                        f"- **Average Rating**: **{avg_rating} / 5.0** stars\n"
                        f"- **Total Reviews Collected**: {len(reviews_list)}\n\n"
                        f"**Recent Feedback Highlights**:\n"
                        + "\n".join([f'- *"{r["comment"]}"* — **{r["student_name"]}** ({r["rating"]}★)' for r in reviews_list[:3]])
        }

    if any(w in q_lower for w in ["batch", "timing", "slots", "instructor"]):
        batch_list = "\n".join([f"- **{b['id']}** ({b['course_id']}): {b['seats_left']} seats left. Instructor: *{b['instructor']}*" for b in batches[:5]])
        return {
            "response": f"📅 **Batch Allocation Status**:\n\n"
                        f"Here is a status check on our upcoming slots:\n\n{batch_list}\n\n"
                        f"Full-stack and AI slots are filling up quickly (average 5-10 seats left per batch)!"
        }

    return {
        "response": f"Hello Administrator! I am your **Admin AI Copilot** 🤖. I have fully indexed our databases.\n\n"
                    f"Here is a quick snapshot of the system state:\n"
                    f"- **Active Sessions**: {analytics.get('total_sessions', 0)}\n"
                    f"- **Verified Enquirers**: {len(verified)}\n"
                    f"- **Successful Enrollments**: {len(enrolled)}\n"
                    f"- **Conversion Rate**: {avg_rating}★ Rating | {analytics.get('conversion_rate', 0)}% Conversion\n\n"
                    f"You can ask me specific details, like:\n"
                    f"- *'Who is our hottest lead right now?'*\n"
                    f"- *'Show me our average ratings and recent feedback'*\n"
                    f"- *'Tell me about our current enrollment rate'*\n"
                    f"- *'List active batches and seats'*."
    }
