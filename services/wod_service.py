"""
שירות ניהול אימוני WOD (WOD Service).
מטפל בהרשמת מנויים, אכיפת מגבלת 18 משתתפים ומניעת הרשמות כפולות.
"""

from datetime import datetime, timedelta
from database import get_connection
from validators import validate_wod_time

def get_or_create_wod_class(class_date: str, start_time: str) -> int:
    """
    מחזיר מזהה אימון WOD. במידה ואינו קיים, מיוצר אוטומטית.
    """
    start_dt = datetime.strptime(start_time, "%H:%M")
    end_time = (start_dt + timedelta(hours=1)).strftime("%H:%M")

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM wod_classes WHERE class_date = ? AND start_time = ?",
            (class_date, start_time)
        )
        row = cursor.fetchone()
        if row:
            return row["id"]

        cursor.execute(
            "INSERT INTO wod_classes (class_date, start_time, end_time, max_capacity) VALUES (?, ?, ?, 18)",
            (class_date, start_time, end_time)
        )
        conn.commit()
        return cursor.lastrowid

def register_member_to_wod(member_id: int, class_date: str, start_time: str) -> dict:
    """
    מוסיף מנוי לאימון WOD תוך אכיפת מגבלת 18 משתתפים ושעות מורשות.
    """
    # אימות שעות פעילות
    is_valid, msg = validate_wod_time(class_date, start_time)
    if not is_valid:
        return {"success": False, "message": msg}

    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # בדיקת תקינות המנוי
            cursor.execute("SELECT is_active FROM members WHERE id = ?", (member_id,))
            member = cursor.fetchone()
            if not member:
                return {"success": False, "message": "המנוי לא קיים במערכת."}
            if not member["is_active"]:
                return {"success": False, "message": "המנוי אינו פעיל."}

            # אכיפת חוק עסקי: מנוי יכול להירשם רק לאימון אחד ביום
            cursor.execute('''
                SELECT COUNT(*) as count 
                FROM wod_registrations wr
                JOIN wod_classes wc ON wr.wod_class_id = wc.id
                WHERE wr.member_id = ? AND wc.class_date = ? AND wr.status = 'REGISTERED'
            ''', (member_id, class_date))
            
            if cursor.fetchone()["count"] > 0:
                return {"success": False, "message": "המנוי כבר רשום לאימון בתאריך זה. מותר להירשם לאימון אחד בלבד ביום!"}

            wod_class_id = get_or_create_wod_class(class_date, start_time)

            # בדיקת תפוסת האימון (מקסימום 18)
            cursor.execute(
                "SELECT COUNT(*) as count FROM wod_registrations WHERE wod_class_id = ? AND status = 'REGISTERED'",
                (wod_class_id,)
            )
            current_count = cursor.fetchone()["count"]
            if current_count >= 18:
                return {"success": False, "message": "האימון מלא! (18/18 משתתפים)." }

            # הרשמה לאימון
            cursor.execute(
                "INSERT INTO wod_registrations (wod_class_id, member_id, status) VALUES (?, ?, 'REGISTERED')",
                (wod_class_id, member_id)
            )
            conn.commit()
            return {
                "success": True,
                "message": f"נרשמת בהצלחה לאימון WOD! מקום {current_count + 1}/18."
            }

    except Exception as e:
        if "UNIQUE constraint failed: wod_registrations.wod_class_id, wod_registrations.member_id" in str(e):
            return {"success": False, "message": "המנוי כבר רשום לאימון זה."}
        return {"success": False, "message": f"שגיאה בהרשמה: {str(e)}"}
