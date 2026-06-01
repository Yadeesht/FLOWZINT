"""
review.py — EduFlow AI Review Collection Route

Stores post-course student reviews to reviews.json and returns
the full review list for the Admin Dashboard.
"""

import json
import uuid
from datetime import date
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()
DATA_DIR = Path(__file__).parent.parent / "data"


# ─── Models ─────────────────────────────────────────────────────────────────

class ReviewSubmit(BaseModel):
    student_name: str
    course: str
    rating: int = Field(..., ge=1, le=5)
    comment: str


# ─── Helpers ────────────────────────────────────────────────────────────────

def _load_reviews() -> list:
    try:
        with open(DATA_DIR / "reviews.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_reviews(reviews: list):
    try:
        with open(DATA_DIR / "reviews.json", "w", encoding="utf-8") as f:
            json.dump(reviews, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Review Save Error] {e}")


# ─── Routes ─────────────────────────────────────────────────────────────────

@router.post("/review")
async def submit_review(req: ReviewSubmit):
    """Submit a new course review."""
    reviews = _load_reviews()
    new_review = {
        "id": f"rev-{uuid.uuid4().hex[:6]}",
        "student_name": req.student_name.strip(),
        "course": req.course.strip(),
        "rating": req.rating,
        "comment": req.comment.strip(),
        "date": date.today().isoformat(),
    }
    reviews.insert(0, new_review)
    _save_reviews(reviews)

    return {
        "success": True,
        "message": "Thank you for your review! 🌟",
        "review": new_review,
    }


@router.get("/reviews")
async def get_reviews():
    """Return all reviews (for Admin Dashboard)."""
    reviews = _load_reviews()
    avg_rating = round(sum(r["rating"] for r in reviews) / max(len(reviews), 1), 1)
    return {
        "reviews": reviews,
        "total": len(reviews),
        "average_rating": avg_rating,
    }
