"""
מודול ניהול בסיס הנתונים (SQLite).
מאתחל את הטבלאות ומספק חיבור בטוח לבסיס הנתונים.
"""

import sqlite3

DB_NAME = "studio.db"

# סכמת הטבלאות בפורמט SQL מוטמע במחרוזת multi-line
SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT NOT NULL UNIQUE,
    email TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    source TEXT,
    status TEXT CHECK(status IN ('NEW', 'IN_PROGRESS', 'CONVERTED', 'REJECTED')) DEFAULT 'NEW',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS wod_classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    max_capacity INTEGER DEFAULT 18,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(class_date, start_time)
);

CREATE TABLE IF NOT EXISTS wod_registrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wod_class_id INTEGER NOT NULL,
    member_id INTEGER NOT NULL,
    status TEXT CHECK(status IN ('REGISTERED', 'CANCELED')) DEFAULT 'REGISTERED',
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (wod_class_id) REFERENCES wod_classes(id) ON DELETE CASCADE,
    FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE,
    UNIQUE(wod_class_id, member_id)
);
"""

def get_connection():
    """
    יוצר ומחזיר חיבור פעיל ל-SQLite עם התאמת Row Factory.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """
    מאתחל את בסיס הנתונים והטבלאות במידה ואינן קיימות.
    """
    with get_connection() as conn:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    print("בסיס הנתונים ואתחול הטבלאות הושלמו בהצלחה.")

if __name__ == "__main__":
    init_db()
    import os; print(os.path.abspath('studio.db'))
