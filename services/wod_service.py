"""
=============================================================
services/wod_service.py — שירות ניהול אימוני WOD
=============================================================

מטרה:
    מטפל בכל הלוגיקה העסקית הקשורה לאימונים:
    יצירת אימונים אוטומטית לפי דרישה, הרשמת מנויים לאימון,
    ואכיפת חוקי הסטודיו.

חוקים עסקיים הנאכפים כאן:
    1. משך אימון: תמיד 60 דקות.
    2. תפוסה: מקסימום 18 משתתפים לאימון.
    3. תדירות: מנוי יכול להירשם לאימון אחד בלבד ביום.
    4. כפילות: לא ניתן להירשם פעמיים לאותו אימון.
    5. שעות פעילות: נאכף דרך validators.validate_wod_time.
"""

from datetime import datetime, timedelta
from database import get_connection
from validators import validate_wod_time

def get_or_create_wod_class(class_date: str, start_time: str) -> int:
    """
    מחזיר מזהה (ID) של אימון WOD עבור התאריך והשעה.
    אם האימון לא קיים עדיין בטבלת wod_classes, הוא מיוצר אוטומטית.

    תהליך:
        1. חישוב שעת הסיום (start_time + שעה 1).
        2. חיפוש ב-DB האם אימון זה כבר קיים.
        3. אם קיים — החזרת ה-ID שלו.
        4. אם לא קיים — יצירתו (עם max_capacity=18) והחזרת ה-ID החדש.

    Args:
        class_date : תאריך האימון (פורמט YYYY-MM-DD)
        start_time : שעת התחלה (פורמט HH:MM)

    Returns:
        int: מזהה האימון (wod_class_id) בבסיס הנתונים.
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

        # יצירת אימון חדש אם לא נמצא
        cursor.execute(
            "INSERT INTO wod_classes (class_date, start_time, end_time, max_capacity) VALUES (?, ?, ?, 18)",
            (class_date, start_time, end_time)
        )
        conn.commit()
        return cursor.lastrowid

def register_member_to_wod(member_id: int, class_date: str, start_time: str) -> dict:
    """
    מוסיף מנוי לאימון WOD תוך אכיפת חוקי הסטודיו (תפוסה, כפילות).

    אכיפות המבוצעות בפונקציה זו:
        1. שעות מורשות: הפעלת validate_wod_time.
        2. סטטוס מנוי: חובה להיות מנוי פעיל (is_active=1).
        3. הגבלת אימון יומי: אימון אחד בלבד באותו תאריך לכל מנוי.
        4. תפוסה מקסימלית: לא מאפשר הרשמה אם יש כבר 18 נרשמים.
        5. הרשמה כפולה לאותו אימון: נאכף דרך UNIQUE בבסיס הנתונים (נלכד ב-Exception).

    Args:
        member_id  : מזהה המנוי
        class_date : תאריך האימון
        start_time : שעת האימון

    Returns:
        dict המכיל "success" (bool) ו-"message" עם הסבר למשתמש.
    """
    # 1. אימות שעות פעילות חוקיות
    is_valid, msg = validate_wod_time(class_date, start_time)
    if not is_valid:
        return {"success": False, "message": msg}

    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # 2. בדיקת תקינות המנוי (קיים ופעיל)
            cursor.execute("SELECT is_active FROM members WHERE id = ?", (member_id,))
            member = cursor.fetchone()
            if not member:
                return {"success": False, "message": "המנוי לא קיים במערכת."}
            if not member["is_active"]:
                return {"success": False, "message": "המנוי אינו פעיל."}

            # 3. אכיפת חוק עסקי: מנוי יכול להירשם רק לאימון אחד ביום
            cursor.execute('''
                SELECT COUNT(*) as count 
                FROM wod_registrations wr
                JOIN wod_classes wc ON wr.wod_class_id = wc.id
                WHERE wr.member_id = ? AND wc.class_date = ? AND wr.status = 'REGISTERED'
            ''', (member_id, class_date))
            
            if cursor.fetchone()["count"] > 0:
                return {"success": False, "message": "המנוי כבר רשום לאימון בתאריך זה. מותר להירשם לאימון אחד בלבד ביום!"}

            # שלוף או צור את האימון הרלוונטי
            wod_class_id = get_or_create_wod_class(class_date, start_time)

            # 4. בדיקת תפוסת האימון (מקסימום 18)
            cursor.execute(
                "SELECT COUNT(*) as count FROM wod_registrations WHERE wod_class_id = ? AND status = 'REGISTERED'",
                (wod_class_id,)
            )
            current_count = cursor.fetchone()["count"]
            if current_count >= 18:
                return {"success": False, "message": "האימון מלא! (18/18 משתתפים)." }

            # 5. ביצוע ההרשמה בפועל
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
        # 6. טיפול בשגיאת הרשמה כפולה על ידי לכידת ה-Constraint
        if "UNIQUE constraint failed: wod_registrations.wod_class_id, wod_registrations.member_id" in str(e):
            return {"success": False, "message": "המנוי כבר רשום לאימון זה."}
        return {"success": False, "message": f"שגיאה בהרשמה: {str(e)}"}
