"""
מודול אימות קלט (Validators).
מכיל פונקציות לבדיקת תקינות טלפונים, תאריכים ושעות פעילות בסטודיו.
"""

from datetime import datetime

def validate_phone(phone: str) -> bool:
    """
    מוודא שמספר הטלפון מכיל ספרות בלבד ובאורך תקין (9-10 ספרות).
    """
    cleaned = phone.replace("-", "").strip()
    return cleaned.isdigit() and len(cleaned) in [9, 10]

def validate_wod_time(date_str: str, time_str: str) -> tuple[bool, str]:
    """
    מוודא שאימון נקבע בשעות הפעילות המורשות של הסטודיו:
    ימי א'-ה': 06:00-09:00 ו-16:00-21:00 (שעות עגולות בלבד).
    """
    try:
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    except ValueError:
        return False, "פורמט תאריך (YYYY-MM-DD) או שעה (HH:MM) אינו תקין."

    # בדיקת יום בשבוע (6 = ראשון, 0 = שני, 1 = שלישי, 2 = רביעי, 3 = חמישי)
    weekday = dt.weekday()
    is_week_day = weekday in [6, 0, 1, 2, 3]
    hour = dt.hour
    minute = dt.minute

    # אימונים חייבים להתחיל בשעה עגולה
    if minute != 0:
        return False, "אימונים חייבים להתחיל בשעה עגולה (משך אימון: שעה בדיוק)."

    # אימות שעות פעילות בימי א'-ה'
    if is_week_day:
        morning_slot = 6 <= hour < 9
        evening_slot = 16 <= hour < 21
        if not (morning_slot or evening_slot):
            return False, "שעות הפעילות בימי א'-ה' הן 06:00-09:00 ו-16:00-21:00 בלבד."
    else:
        # שעות פעילות לסופ"ש (ו'-ש'): 08:00-12:00
        if not (8 <= hour < 12):
            return False, "שעות הפעילות בסופ\"ש הן 08:00-12:00 בלבד."

    return True, "OK"
