"""
=============================================================
chatbot/db_service.py — שירות גישה ישיר לבסיס הנתונים
=============================================================

מטרה:
    מודול זה מחליף את קריאות ה-HTTP API (localhost:8000)
    בגישה ישירה לבסיס הנתונים SQLite.

    למה זה נדרש ל-PythonAnywhere:
        PythonAnywhere מאפשר רק תהליך web אחד (Flask WSGI).
        אי אפשר להריץ גם FastAPI וגם Flask במקביל.
        לכן, הצ'אטבוט פונה לפונקציות כאן ישירות
        במקום לשלוח HTTP requests ל-localhost:8000.

    יתרון נוסף: ביצועים טובים יותר (אין overhead של HTTP).

פונקציות:
    search_members(name)            → חיפוש לפי שם חלקי
    get_member_appointments(id)     → תורים של מנוי
    verify_member_identity(id, tz)  → אימות תעודת זהות
    get_member_by_id(id)           → פרטי מנוי בודד
"""

import sqlite3
from typing import List, Dict, Optional
from database import get_connection


def search_members(name: str) -> Dict:
    """
    מחפש מנויים פעילים לפי שם חלקי (LIKE search).

    שימוש בצ'אטבוט:
        נקרא כשהמשתמש מוסר את שמו.
        אם מוחזר count=0 → לא נמצא.
        אם מוחזר count=1 → מנוי ייחודי, עובר לאימות.
        אם מוחזר count>1 → מבקש הבהרה (CLARIFY stage).

    Args:
        name: שם חלקי לחיפוש (לדוגמה: "רותם")

    Returns:
        dict עם מפתחות:
            "count"   : מספר תוצאות שנמצאו
            "results" : רשימת מנויים (id, name, phone, email, is_active)
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        # % לפני ואחרי → חיפוש LIKE חלקי גם במקרה של שם אמצעי
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

    # המרת sqlite3.Row ל-dict רגיל לנוחות
    results = [
        {
            "id": r["id"],
            "name": r["name"],
            "phone": r["phone"],
            "email": r["email"],
            "is_active": bool(r["is_active"]),
        }
        for r in rows
    ]
    return {"count": len(results), "results": results}


def get_member_appointments(member_id: int, status: str = "REGISTERED") -> Dict:
    """
    שולף את כל האימונים הרשומים של מנוי ספציפי.

    שימוש בצ'אטבוט:
        נקרא לאחר אימות זהות מוצלח כדי להביא
        את הנתונים האמיתיים של התור ולהשוות לתביעת המשתמש.

    Args:
        member_id: מזהה המנוי בטבלת members
        status   : סינון לפי סטטוס (ברירת מחדל: "REGISTERED")

    Returns:
        dict עם מפתחות:
            "member_id"   : ה-ID שנשאל
            "count"       : מספר אימונים שנמצאו
            "appointments": רשימת אימונים (class_date, start_time, status, ...)
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                r.wod_class_id,
                w.class_date,
                w.start_time,
                w.end_time,
                r.status
            FROM wod_registrations r
            JOIN wod_classes w ON r.wod_class_id = w.id
            WHERE r.member_id = ? AND r.status = ?
            ORDER BY w.class_date DESC, w.start_time DESC
            """,
            (member_id, status),
        )
        rows = cursor.fetchall()

    appointments = [
        {
            "wod_class_id": r["wod_class_id"],
            "class_date": r["class_date"],
            "start_time": r["start_time"],
            "end_time": r["end_time"],
            "status": r["status"],
        }
        for r in rows
    ]
    return {
        "member_id": member_id,
        "count": len(appointments),
        "appointments": appointments,
    }


def verify_member_identity(member_id: int, id_number: str) -> Dict:
    """
    מאמת תעודת זהות: משווה את הקלט עם הרשום בבסיס הנתונים.

    כלל אבטחה קשיח:
        - פונקציה זו לעולם לא מחזירה את תעודת הזהות האמיתית!
        - מחזירה רק True/False + הודעה כללית.
        - השוואה מדויקת (exact match) לאחר trim.

    Args:
        member_id: מזהה המנוי
        id_number: תעודת הזהות שהמשתמש הזין

    Returns:
        dict עם מפתחות:
            "verified": bool — האם ההתאמה הצליחה
            "message" : str  — הסבר קצר (לא חושף נתונים)
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        # שולף רק את עמודת id_number (לא שם, לא טלפון)
        cursor.execute(
            "SELECT id_number FROM members WHERE id = ? AND is_active = 1",
            (member_id,),
        )
        row = cursor.fetchone()

    # מנוי לא נמצא (כנראה לא פעיל)
    if not row:
        return {"verified": False, "message": "מנוי לא נמצא."}

    stored_id = row["id_number"]

    # מנוי קיים אך ללא תעודת זהות רשומה
    if stored_id is None:
        return {
            "verified": False,
            "message": "לא נמצאה תעודת זהות רשומה עבור מנוי זה.",
        }

    # השוואה מדויקת (strip להסרת רווחים מקרה של טעות הקלדה)
    if id_number.strip() == stored_id.strip():
        return {"verified": True, "message": "אימות הצליח!"}
    else:
        return {"verified": False, "message": "תעודת הזהות שגויה."}


def authenticate_member(name: str, id_number: str) -> Dict:
    """
    מאמת מנוי במקביל לפי שם (חיפוש חלקי) ומספר תעודת זהות מדויק.
    נקרא בשלב הזיהוי בצ'אטבוט.

    Args:
        name: השם שהמשתמש הזין
        id_number: תעודת הזהות שהמשתמש הזין

    Returns:
        dict עם מפתחות:
            "verified": bool — האם נמצא מנוי פעיל שתואם
            "member": dict של פרטי המנוי או None
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, name, phone, email, is_active 
            FROM members 
            WHERE name LIKE ? AND id_number = ? AND is_active = 1
            """,
            (f"%{name.strip()}%", id_number.strip()),
        )
        row = cursor.fetchone()

    if not row:
        return {"verified": False, "member": None}

    return {
        "verified": True,
        "member": {
            "id": row["id"],
            "name": row["name"],
            "phone": row["phone"],
            "email": row["email"],
            "is_active": bool(row["is_active"]),
        }
    }


def get_member_by_id(member_id: int) -> Optional[Dict]:
    """
    שולף פרטי מנוי יחיד לפי ID.

    Args:
        member_id: מזהה המנוי

    Returns:
        dict עם פרטי המנוי, או None אם לא נמצא
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, phone, email, is_active FROM members WHERE id = ?",
            (member_id,),
        )
        row = cursor.fetchone()

    if not row:
        return None

    return {
        "id": row["id"],
        "name": row["name"],
        "phone": row["phone"],
        "email": row["email"],
        "is_active": bool(row["is_active"]),
    }
