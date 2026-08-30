"""
api/main.py — FitStudio REST API (FastAPI)
מחשף את הלוגיקה הקיימת כ-REST API שהצ'אטבוט קורא אליה.

Endpoints:
  GET  /members/search?name=...         חיפוש מנוי לפי שם חלקי
  GET  /members/{id}                    פרטי מנוי בודד
  POST /members/{id}/verify-identity    אימות תעודת זהות
  GET  /members/{id}/appointments       תורים/אימונים של מנוי
  GET  /wod-classes?date=YYYY-MM-DD     אימונים לתאריך
  GET  /health                          בדיקת תקינות

הרצה: uvicorn api.main:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sys
import os

# הוספת תיקיית הפרויקט ל-path כדי שנוכל לייבא database ו-services
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_connection, init_db

# ===========================================================
# אתחול האפליקציה
# ===========================================================
app = FastAPI(
    title="FitStudio API",
    description="REST API לניהול מנויים, אימוני WOD ואימות זהות — FitStudio Chatbot Backend",
    version="2.0.0",
)

# CORS — מאפשר גישה מממשק Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# אתחול DB בהפעלת ה-API
@app.on_event("startup")
def startup():
    init_db()


# ===========================================================
# Schemas (Pydantic)
# ===========================================================
class VerifyIdentityRequest(BaseModel):
    id_number: str


class VerifyIdentityResponse(BaseModel):
    verified: bool
    message: str


class MemberOut(BaseModel):
    id: int
    name: str
    phone: str
    email: Optional[str]
    is_active: bool


class AppointmentOut(BaseModel):
    wod_class_id: int
    class_date: str
    start_time: str
    end_time: str
    status: str


# ===========================================================
# Endpoints
# ===========================================================

@app.get("/health", tags=["System"])
def health_check():
    """בדיקת תקינות — תמיד מחזיר 200 OK."""
    return {"status": "ok", "service": "FitStudio API v2"}


@app.get("/members/search", tags=["Members"])
def search_members(name: str = Query(..., min_length=2, description="שם חלקי לחיפוש")):
    """
    חיפוש מנויים לפי שם חלקי (LIKE).
    מחזיר רשימה — ריקה אם לא נמצא, רבים אם יש כמה תוצאות.
    הצ'אטבוט ישתמש בזה לזיהוי מול המשתמש.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, name, phone, email, is_active
            FROM members
            WHERE name LIKE ? AND is_active = 1
            ORDER BY name
            """,
            (f"%{name}%",),
        )
        rows = cursor.fetchall()

    return {
        "count": len(rows),
        "results": [
            {
                "id": r["id"],
                "name": r["name"],
                "phone": r["phone"],
                "email": r["email"],
                "is_active": bool(r["is_active"]),
            }
            for r in rows
        ],
    }


@app.get("/members/{member_id}", tags=["Members"])
def get_member(member_id: int):
    """שליפת פרטי מנוי בודד לפי ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, phone, email, is_active FROM members WHERE id = ?",
            (member_id,),
        )
        row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail=f"מנוי עם ID={member_id} לא נמצא")

    return {
        "id": row["id"],
        "name": row["name"],
        "phone": row["phone"],
        "email": row["email"],
        "is_active": bool(row["is_active"]),
    }


@app.post("/members/{member_id}/verify-identity", tags=["Auth"])
def verify_identity(member_id: int, body: VerifyIdentityRequest):
    """
    אימות זהות: משווה את ה-id_number שהוזן עם הרשום ב-DB.
    מחזיר verified=True רק אם ההתאמה מדויקת.

    SECURITY: לא מחזיר את ה-id_number האמיתי בשום מקרה.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id_number FROM members WHERE id = ? AND is_active = 1",
            (member_id,),
        )
        row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="מנוי לא נמצא")

    stored_id = row["id_number"]
    if stored_id is None:
        return VerifyIdentityResponse(
            verified=False,
            message="לא נמצאה תעודת זהות רשומה עבור מנוי זה.",
        )

    if body.id_number.strip() == stored_id.strip():
        return VerifyIdentityResponse(verified=True, message="אימות הצליח!")
    else:
        return VerifyIdentityResponse(
            verified=False,
            message="תעודת הזהות שגויה. אנא נסה שנית.",
        )


@app.get("/members/{member_id}/appointments", tags=["Appointments"])
def get_member_appointments(
    member_id: int,
    status: Optional[str] = Query(None, description="סינון לפי סטטוס: REGISTERED / CANCELED"),
):
    """
    שליפת כל האימונים הרשומים של מנוי.
    מחזיר רשימת אימונים עם תאריך, שעה וסטטוס.
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        # ודא שהמנוי קיים
        cursor.execute("SELECT id FROM members WHERE id = ?", (member_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="מנוי לא נמצא")

        query = """
            SELECT
                r.wod_class_id,
                w.class_date,
                w.start_time,
                w.end_time,
                r.status
            FROM wod_registrations r
            JOIN wod_classes w ON r.wod_class_id = w.id
            WHERE r.member_id = ?
        """
        params = [member_id]

        if status:
            query += " AND r.status = ?"
            params.append(status.upper())

        query += " ORDER BY w.class_date DESC, w.start_time DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()

    return {
        "member_id": member_id,
        "count": len(rows),
        "appointments": [
            {
                "wod_class_id": r["wod_class_id"],
                "class_date": r["class_date"],
                "start_time": r["start_time"],
                "end_time": r["end_time"],
                "status": r["status"],
            }
            for r in rows
        ],
    }


@app.get("/wod-classes", tags=["WOD"])
def get_wod_classes(
    date: Optional[str] = Query(None, description="תאריך בפורמט YYYY-MM-DD"),
):
    """שליפת אימוני WOD — כולם או לתאריך ספציפי."""
    with get_connection() as conn:
        cursor = conn.cursor()

        if date:
            cursor.execute(
                """
                SELECT w.id, w.class_date, w.start_time, w.end_time, w.max_capacity,
                       COUNT(r.id) as registered_count
                FROM wod_classes w
                LEFT JOIN wod_registrations r ON w.id = r.wod_class_id AND r.status = 'REGISTERED'
                WHERE w.class_date = ?
                GROUP BY w.id
                ORDER BY w.start_time
                """,
                (date,),
            )
        else:
            cursor.execute(
                """
                SELECT w.id, w.class_date, w.start_time, w.end_time, w.max_capacity,
                       COUNT(r.id) as registered_count
                FROM wod_classes w
                LEFT JOIN wod_registrations r ON w.id = r.wod_class_id AND r.status = 'REGISTERED'
                GROUP BY w.id
                ORDER BY w.class_date DESC, w.start_time
                LIMIT 50
                """
            )
        rows = cursor.fetchall()

    return {
        "count": len(rows),
        "classes": [
            {
                "id": r["id"],
                "class_date": r["class_date"],
                "start_time": r["start_time"],
                "end_time": r["end_time"],
                "max_capacity": r["max_capacity"],
                "registered_count": r["registered_count"],
                "spots_left": r["max_capacity"] - r["registered_count"],
            }
            for r in rows
        ],
    }
