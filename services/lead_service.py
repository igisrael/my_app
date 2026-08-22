"""
שירות ניהול לידים (Lead Service).
מטפל בקליטת לידים חדשים והמרתם למנויים פעילים בטרנזקציה אטומית.
"""

from database import get_connection

def add_lead(name: str, phone: str, source: str = "", notes: str = "") -> dict:
    """
    מוסיף ליד חדש למערכת.
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
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # שליפת נתוני הליד
            cursor.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
            lead = cursor.fetchone()
            if not lead:
                return {"success": False, "message": "הליד לא נמצא."}

            if lead["status"] == "CONVERTED":
                return {"success": False, "message": "הליד כבר הומר בעבר למנוי."}

            # הוספת המנוי ועדכון הליד
            cursor.execute(
                "INSERT INTO members (name, phone, email) VALUES (?, ?, ?)",
                (lead["name"], lead["phone"], email)
            )
            new_member_id = cursor.lastrowid

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
        return {"success": False, "message": f"שגיאה בהמרת הליד: {str(e)}"}
