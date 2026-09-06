"""
=============================================================
services/lead_service.py — שירות ניהול לידים
=============================================================

מטרה:
    מטפל בקליטת לידים חדשים (מתעניינים פוטנציאליים)
    ומספק מנגנון המרה (Conversion) של ליד למנוי פעיל.

הגיון עסקי (Business Logic):
    1. ליד נכנס למערכת בסטטוס "NEW".
    2. צוות המכירות יכול לדבר איתו.
    3. אם הליד נרשם, מופעלת ההמרה (convert_lead_to_member)
       אשר מבצעת העברה בטוחה (Transaction) בין הטבלאות,
       ומסמנת את הליד כ-"CONVERTED".
"""

from database import get_connection

def add_lead(name: str, phone: str, source: str = "", notes: str = "") -> dict:
    """
    מוסיף ליד חדש למערכת.

    Args:
        name   : שם הליד (חובה)
        phone  : מספר טלפון (חובה)
        source : מקור ההגעה (לדוגמה: "אינסטגרם", "חבר מביא חבר")
        notes  : הערות נוספות עבור צוות המכירות

    Returns:
        dict המכיל "success" (bool), "lead_id" במקרה של הצלחה,
        ו-"message" עם הסטטוס.
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO leads (name, phone, source, notes) VALUES (?, ?, ?, ?)",
                (name.strip(), phone.strip(), source.strip(), notes.strip())
            )
            conn.commit()
            return {"success": True, "lead_id": cursor.lastrowid, "message": "ליד נוצר בהצלחה."}
    except Exception as e:
        return {"success": False, "message": f"שגיאה בהוספת ליד: {str(e)}"}

def convert_lead_to_member(lead_id: int, email: str = "") -> dict:
    """
    ממיר ליד למנוי פעיל בתוך טרנזקציה אטומית.

    אטומיות (ACID):
        מבוצע כטרנזקציה אחת. אם יש שגיאה בהכנסה ל-members
        (למשל טלפון כבר קיים), כל הפעולה מבוטלת והליד
        לא מסומן כ-CONVERTED בטעות.

    Args:
        lead_id : המזהה הייחודי של הליד להמרה
        email   : דוא"ל אופציונלי להוספה לפרופיל המנוי החדש

    Returns:
        dict המכיל "success" (bool), "member_id" של המנוי שנוצר, ו-"message".
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # 1. שליפת נתוני הליד ווידוא תקינות
            cursor.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
            lead = cursor.fetchone()
            if not lead:
                return {"success": False, "message": "הליד לא נמצא."}

            if lead["status"] == "CONVERTED":
                return {"success": False, "message": "הליד כבר הומר בעבר למנוי."}

            # 2. הוספת המנוי לטבלת members
            cursor.execute(
                "INSERT INTO members (name, phone, email) VALUES (?, ?, ?)",
                (lead["name"], lead["phone"], email)
            )
            new_member_id = cursor.lastrowid

            # 3. עדכון סטטוס הליד
            cursor.execute(
                "UPDATE leads SET status = 'CONVERTED' WHERE id = ?",
                (lead_id,)
            )
            conn.commit()

            return {
                "success": True,
                "member_id": new_member_id,
                "message": f"הליד הומר בהצלחה למנוי חדש (מזהה מנוי: {new_member_id})."
            }
    except Exception as e:
        return {"success": False, "message": f"שגיאה בהמרת הליד (ייתכן שהטלפון כבר קיים במערכת): {str(e)}"}
