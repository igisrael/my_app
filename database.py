"""
=============================================================
database.py — מודול ניהול בסיס הנתונים של FitStudio
=============================================================

מטרה:
    מודול זה אחראי על כל הקשר עם SQLite.
    הוא מגדיר את סכמת הטבלאות, מספק חיבור בטוח,
    ומבצע migrations בטוחים לשמירת תאימות לאחור.

טבלאות:
    - members          : מנויים פעילים (שם, טלפון, תעודת זהות)
    - leads            : מתעניינים שטרם הפכו למנויים
    - wod_classes      : משבצות זמן לאימוני WOD
    - wod_registrations: קשר בין מנויים לאימונים

שימוש:
    from database import get_connection, init_db
    init_db()  # קריאה אחת בתחילת האפליקציה
    with get_connection() as conn:
        conn.execute("SELECT ...")
"""

import sqlite3

# שם קובץ בסיס הנתונים (נשמר בתיקיית הפרויקט)
DB_NAME = "studio.db"

# ===========================================================
# הגדרת סכמת הטבלאות — SQL מוטמע כמחרוזת
# ===========================================================
SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

-- טבלת מנויים: שומרת את כל המנויים הפעילים והלא-פעילים
-- id_number: תעודת זהות — משמשת לאימות זהות בצ'אטבוט
CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT NOT NULL UNIQUE,
    email TEXT,
    id_number TEXT UNIQUE,            -- תעודת זהות לאימות בצ'אטבוט
    is_active BOOLEAN DEFAULT 1,      -- 1=פעיל, 0=לא פעיל
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- טבלת לידים: מתעניינים שפנו אך טרם נרשמו כמנויים
-- status: NEW → IN_PROGRESS → CONVERTED / REJECTED
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    source TEXT,                       -- מקור הפנייה (פייסבוק, אינסטגרם וכו')
    status TEXT CHECK(status IN ('NEW', 'IN_PROGRESS', 'CONVERTED', 'REJECTED')) DEFAULT 'NEW',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- טבלת שיעורי WOD: יומן האימונים
-- UNIQUE(class_date, start_time) מונע יצירת אימון כפול באותו יום ושעה
CREATE TABLE IF NOT EXISTS wod_classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    max_capacity INTEGER DEFAULT 18,   -- מקסימום 18 משתתפים לפי חוקי הסטודיו
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(class_date, start_time)
);

-- טבלת הרשמות: מקשרת בין מנוי לאימון
-- UNIQUE(wod_class_id, member_id) מונע הרשמה כפולה של אותו מנוי לאותו אימון
CREATE TABLE IF NOT EXISTS wod_registrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wod_class_id INTEGER NOT NULL,
    member_id INTEGER NOT NULL,
    status TEXT CHECK(status IN ('REGISTERED', 'CANCELED')) DEFAULT 'REGISTERED',
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (wod_class_id) REFERENCES wod_classes(id) ON DELETE CASCADE,
    FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE,
    UNIQUE(wod_class_id, member_id)    -- מניעת הרשמה כפולה
);
"""


def get_connection() -> sqlite3.Connection:
    """
    יוצר ומחזיר חיבור פעיל לבסיס הנתונים SQLite.

    מאפיינים:
        - row_factory = sqlite3.Row: מאפשר גישה לשדות לפי שם (row["name"])
          במקום לפי אינדקס (row[0])
        - foreign_keys = ON: אוכף מפתחות זרים (CASCADE deletes)

    שימוש (עדיף עם context manager):
        with get_connection() as conn:
            conn.execute("SELECT ...")
            # החיבור נסגר אוטומטית בצאת מה-with

    Returns:
        sqlite3.Connection: חיבור פתוח לבסיס הנתונים
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row      # גישה לשדות לפי שם
    conn.execute("PRAGMA foreign_keys = ON;")   # אכיפת FK constraints
    return conn


def init_db() -> None:
    """
    מאתחל את בסיס הנתונים: יוצר טבלאות אם אינן קיימות ומריץ migrations.

    מתי לקרוא:
        - פעם אחת בהפעלת האפליקציה (ב-app.py ו-flask_app.py)
        - בטוח לקריאה חוזרת — משתמש ב-CREATE TABLE IF NOT EXISTS

    תהליך:
        1. מריץ SCHEMA_SQL (יוצר טבלאות חסרות)
        2. קורא ל-migrate_db() (מוסיף עמודות חדשות בבטחה)
    """
    with get_connection() as conn:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    migrate_db()
    print("בסיס הנתונים ואתחול הטבלאות הושלמו בהצלחה.")


def migrate_db() -> None:
    """
    מבצע migration בטוח: מוסיף עמודות חדשות לטבלאות קיימות.

    למה זה נדרש:
        SQLite לא תומך ב-ALTER TABLE DROP COLUMN ואינו מתאים
        לשינויי סכמה דרמטיים. Migration זה מוסיף עמודת id_number
        לטבלאות קיימות מבלי לפגוע בנתונים קיימים.

    עמודות שנוספו:
        - members.id_number: תעודת זהות לאימות זהות בצ'אטבוט (v2)

    הגיון:
        בודק אם העמודה קיימת לפני ALTER TABLE —
        בטוח לקריאה חוזרת (idempotent).
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        # בדוק אילו עמודות קיימות בטבלת members
        cursor.execute("PRAGMA table_info(members)")
        columns = [row["name"] for row in cursor.fetchall()]

        # הוסף id_number רק אם עדיין לא קיים
        if "id_number" not in columns:
            # SQLite לא תומך ב-ADD COLUMN UNIQUE ישירות —
            # מוסיפים עמודה רגילה ואז index ייחודי נפרד
            conn.execute("ALTER TABLE members ADD COLUMN id_number TEXT")
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_members_id_number "
                "ON members(id_number)"
            )
            conn.commit()
            print("Migration: עמודת 'id_number' + unique index נוספו לטבלת members.")


# ===========================================================
# הרצה ישירה לבדיקה
# ===========================================================
if __name__ == "__main__":
    init_db()
    import os
    print(f"קובץ DB נמצא ב: {os.path.abspath(DB_NAME)}")
