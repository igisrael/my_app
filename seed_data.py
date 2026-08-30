"""
seed_data.py — סקריפט זריעת נתונים לפרויקט FitStudio.
מזרים נתוני דמו אמיתיים: מנויים, לידים, אימוני WOD והרשמות.
מריץ migration לפני הכל כדי לוודא שהסכמה מעודכנת.

הרצה: python seed_data.py
"""

import sqlite3
from datetime import date, timedelta
from database import get_connection, init_db

# ============================================================
# נתוני מנויים (8 מנויים עם תעודות זהות לאימות)
# ============================================================
MEMBERS = [
    {
        "name": "רותם מירון",
        "phone": "050-1111111",
        "email": "rotem@example.com",
        "id_number": "123456789",
    },
    {
        "name": "רותם כהן",
        "phone": "050-2222222",
        "email": "rotem.cohen@example.com",
        "id_number": "987654321",
    },
    {
        "name": "ניר לוי",
        "phone": "050-3333333",
        "email": "nir@example.com",
        "id_number": "111222333",
    },
    {
        "name": "מיכל אברהם",
        "phone": "050-4444444",
        "email": "michal@example.com",
        "id_number": "444555666",
    },
    {
        "name": "עומר דוד",
        "phone": "050-5555555",
        "email": "omer@example.com",
        "id_number": "777888999",
    },
    {
        "name": "שירה גולן",
        "phone": "050-6666666",
        "email": "shira@example.com",
        "id_number": "112233445",
    },
    {
        "name": "יוסי בן-דוד",
        "phone": "050-7777777",
        "email": "yossi@example.com",
        "id_number": "556677889",
    },
    {
        "name": "דנה שמיר",
        "phone": "050-8888888",
        "email": "dana@example.com",
        "id_number": "334455667",
    },
]

# ============================================================
# נתוני לידים (6 לידים בסטטוסים שונים)
# ============================================================
LEADS = [
    {
        "name": "אבי כץ",
        "phone": "052-1010101",
        "source": "פייסבוק",
        "status": "NEW",
        "notes": "מתעניין במנוי חודשי, ביקש פרטים על לו\"ז",
    },
    {
        "name": "טל שפירא",
        "phone": "052-2020202",
        "source": "אינסטגרם",
        "status": "IN_PROGRESS",
        "notes": "שוחחנו, שולחים הצעת מחיר",
    },
    {
        "name": "נועה ברנר",
        "phone": "052-3030303",
        "source": "חבר מביא חבר",
        "status": "IN_PROGRESS",
        "notes": "חבר שלה - ניר לוי - הפנה אותה",
    },
    {
        "name": "גיל מזרחי",
        "phone": "052-4040404",
        "source": "שלט/רחוב",
        "status": "NEW",
        "notes": "עבר ליד הסטודיו ראה שלט",
    },
    {
        "name": "ליאת פרץ",
        "phone": "052-5050505",
        "source": "אחר",
        "status": "REJECTED",
        "notes": "לא מתאים לה הלו\"ז, תחזור בעתיד",
    },
    {
        "name": "בועז הלוי",
        "phone": "052-6060606",
        "source": "פייסבוק",
        "status": "NEW",
        "notes": "מתעניין באימונים בבוקר בלבד",
    },
]

# ============================================================
# יצירת אימוני WOD והרשמות
# ============================================================
def get_or_create_wod(conn, date_str: str, start_time: str) -> int:
    """יוצר אימון WOD אם לא קיים ומחזיר את ה-ID שלו."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM wod_classes WHERE class_date = ? AND start_time = ?",
        (date_str, start_time),
    )
    row = cursor.fetchone()
    if row:
        return row["id"]

    # חישוב שעת סיום (60 דקות אחרי)
    hour = int(start_time.split(":")[0])
    end_time = f"{hour + 1:02d}:00"

    cursor.execute(
        "INSERT INTO wod_classes (class_date, start_time, end_time) VALUES (?, ?, ?)",
        (date_str, start_time, end_time),
    )
    conn.commit()
    return cursor.lastrowid


def seed_wod_registrations(conn, member_ids: dict):
    """
    יוצר 12+ הרשמות לאימוני WOD בתאריכים שונים.
    member_ids: dict של {שם: id}
    """
    today = date.today()

    # אימונים לשבוע הנוכחי והבא
    wod_schedule = [
        # תאריך, שעה, שם מנוי
        (today.strftime("%Y-%m-%d"), "07:00", "רותם מירון"),
        (today.strftime("%Y-%m-%d"), "07:00", "ניר לוי"),
        (today.strftime("%Y-%m-%d"), "07:00", "מיכל אברהם"),
        (today.strftime("%Y-%m-%d"), "18:00", "עומר דוד"),
        (today.strftime("%Y-%m-%d"), "18:00", "שירה גולן"),
        ((today + timedelta(days=1)).strftime("%Y-%m-%d"), "06:00", "רותם כהן"),
        ((today + timedelta(days=1)).strftime("%Y-%m-%d"), "06:00", "יוסי בן-דוד"),
        ((today + timedelta(days=1)).strftime("%Y-%m-%d"), "17:00", "דנה שמיר"),
        ((today + timedelta(days=1)).strftime("%Y-%m-%d"), "17:00", "רותם מירון"),
        ((today + timedelta(days=2)).strftime("%Y-%m-%d"), "08:00", "ניר לוי"),
        ((today + timedelta(days=2)).strftime("%Y-%m-%d"), "08:00", "מיכל אברהם"),
        ((today + timedelta(days=3)).strftime("%Y-%m-%d"), "19:00", "עומר דוד"),
        ((today + timedelta(days=3)).strftime("%Y-%m-%d"), "19:00", "שירה גולן"),
        ((today + timedelta(days=3)).strftime("%Y-%m-%d"), "19:00", "יוסי בן-דוד"),
    ]

    cursor = conn.cursor()
    registered = 0
    for date_str, start_time, member_name in wod_schedule:
        if member_name not in member_ids:
            continue
        m_id = member_ids[member_name]
        wod_id = get_or_create_wod(conn, date_str, start_time)

        # בדיקה שהמנוי לא כבר רשום
        cursor.execute(
            "SELECT id FROM wod_registrations WHERE wod_class_id = ? AND member_id = ?",
            (wod_id, m_id),
        )
        if cursor.fetchone():
            continue

        cursor.execute(
            "INSERT INTO wod_registrations (wod_class_id, member_id, status) VALUES (?, ?, 'REGISTERED')",
            (wod_id, m_id),
        )
        registered += 1

    conn.commit()
    return registered


# ============================================================
# פונקציית main
# ============================================================
def seed():
    print("=" * 50)
    print("🌱 מתחיל זריעת נתוני דמו ל-FitStudio")
    print("=" * 50)

    # 1. אתחול + migration
    init_db()

    with get_connection() as conn:
        cursor = conn.cursor()

        # ---- מנויים ----
        print("\n📋 מזרים מנויים...")
        member_ids = {}
        for m in MEMBERS:
            try:
                cursor.execute(
                    """
                    INSERT INTO members (name, phone, email, id_number, is_active)
                    VALUES (?, ?, ?, ?, 1)
                    """,
                    (m["name"], m["phone"], m["email"], m["id_number"]),
                )
                conn.commit()
                member_ids[m["name"]] = cursor.lastrowid
                print(f"   ✅ {m['name']} (ת.ז.: {m['id_number']})")
            except sqlite3.IntegrityError:
                # המנוי כבר קיים — שלוף את ה-ID
                cursor.execute("SELECT id FROM members WHERE phone = ?", (m["phone"],))
                row = cursor.fetchone()
                if row:
                    member_ids[m["name"]] = row["id"]
                print(f"   ⚠️  {m['name']} — כבר קיים במערכת")

        # ---- לידים ----
        print("\n🎯 מזרים לידים...")
        for l in LEADS:
            try:
                cursor.execute(
                    """
                    INSERT INTO leads (name, phone, source, status, notes)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (l["name"], l["phone"], l["source"], l["status"], l["notes"]),
                )
                conn.commit()
                print(f"   ✅ {l['name']} [{l['status']}] — {l['source']}")
            except sqlite3.IntegrityError:
                print(f"   ⚠️  {l['name']} — כבר קיים")

        # ---- אימוני WOD + הרשמות ----
        print("\n🏋️  מזרים אימוני WOD והרשמות...")
        count = seed_wod_registrations(conn, member_ids)
        print(f"   ✅ נוצרו {count} הרשמות לאימונים")

    # סיכום
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as c FROM members")
        n_members = cursor.fetchone()["c"]
        cursor.execute("SELECT COUNT(*) as c FROM leads")
        n_leads = cursor.fetchone()["c"]
        cursor.execute("SELECT COUNT(*) as c FROM wod_classes")
        n_wods = cursor.fetchone()["c"]
        cursor.execute("SELECT COUNT(*) as c FROM wod_registrations")
        n_regs = cursor.fetchone()["c"]

    print("\n" + "=" * 50)
    print("✨ זריעה הושלמה בהצלחה!")
    print(f"   👥 מנויים:    {n_members}")
    print(f"   🎯 לידים:     {n_leads}")
    print(f"   📅 אימונים:   {n_wods}")
    print(f"   📝 הרשמות:    {n_regs}")
    print("=" * 50)


if __name__ == "__main__":
    seed()
