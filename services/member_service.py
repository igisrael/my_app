"""
=============================================================
services/member_service.py — שירות ניהול מנויים
=============================================================

מטרה:
    מודול זה אחראי על ניהול מנויים קיימים בסטודיו.
    מטפל בהוספת מנויים חדשים באופן ידני (לא דרך ליד),
    שליפת כלל המנויים לתצוגה בממשק, ואכיפת תקינות (Validation).
"""

from database import get_connection
from validators import validate_phone

def add_member(name: str, phone: str, email: str = "") -> dict:
    """
    מוסיף מנוי חדש למערכת לאחר אימות תקינות טלפון וכפילויות.

    תהליך:
        1. בודק תקינות טלפון בעזרת validators.validate_phone.
        2. מנסה להכניס לבסיס הנתונים.
        3. אם הטלפון כבר קיים (UNIQUE constraint failed),
           לוכד את השגיאה ומחזיר הודעה ברורה למשתמש.

    Args:
        name  : שם המנוי
        phone : מספר טלפון ישראלי
        email : דוא"ל (אופציונלי)

    Returns:
        dict המכיל "success" (bool), "member_id" בהצלחה, ו-"message".
    """
    if not validate_phone(phone):
        return {"success": False, "message": "מספר טלפון לא תקין."}

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO members (name, phone, email) VALUES (?, ?, ?)",
                (name.strip(), phone.strip(), email.strip())
            )
            conn.commit()
            return {"success": True, "member_id": cursor.lastrowid, "message": "מנוי נוצר בהצלחה."}
    except Exception as e:
        # טיפול בשגיאת כפילות (מנוי כבר קיים עם אותו טלפון)
        if "UNIQUE constraint failed: members.phone" in str(e):
            return {"success": False, "message": "קיים כבר מנוי עם מספר טלפון זה."}
        return {"success": False, "message": f"שגיאה ביצירת מנוי: {str(e)}"}

def get_all_members() -> list:
    """
    מחזיר רשימה של כל המנויים הרשומים במערכת.

    שימוש:
        נקרא על ידי ה-UI (Streamlit / Flask) כדי להציג את רשימת
        הלקוחות ולבחור מנוי עבור הרשמה לאימון.

    Returns:
        רשימה (list) של מילונים (dict), כאשר כל מילון מייצג מנוי.
        מוין לפי ה-ID בסדר יורד (חדשים קודם).
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM members ORDER BY id DESC")
        # המרת sqlite3.Row ל-dict
        return [dict(row) for row in cursor.fetchall()]

