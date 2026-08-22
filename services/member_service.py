"""
שירות ניהול מנויים (Member Service).
מטפל בהוספת מנויים, שליפת מנויים ובדיקת תקינות.
"""

from database import get_connection
from validators import validate_phone

def add_member(name: str, phone: str, email: str = "") -> dict:
    """
    מוסיף מנוי חדש למערכת לאחר אימות תקינות טלפון וכפילויות.
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
        if "UNIQUE constraint failed: members.phone" in str(e):
            return {"success": False, "message": "קיים כבר מנוי עם מספר טלפון זה."}
        return {"success": False, "message": f"שגיאה ביצירת מנוי: {str(e)}"}

def get_all_members() -> list:
    """
    מחזיר רשימה של כל המנויים הרשומים במערכת.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM members ORDER BY id DESC")
        return [dict(row) for row in cursor.fetchall()]
