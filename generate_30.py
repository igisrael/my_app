import sqlite3
import random

# רשימת שמות פרטיים
first_names = ["אורי", "נועם", "דניאל", "דוד", "יוסף", "איתי", "אריאל", "משה", "רועי", "אברהם", 
               "תמר", "מאיה", "נועה", "שרה", "יעל", "אדל", "רומי", "אביגיל", "אילה", "שירה",
               "עומר", "עידו", "יהונתן", "לביא", "ארז", "אלון", "גיא", "עמית", "רון", "שחר",
               "מיכל", "עדי", "דנה", "רונה", "גל", "טלי", "ימית", "סיון", "נטע", "יובל"]

# רשימת שמות משפחה
last_names = ["כהן", "לוי", "מזרחי", "פרץ", "ביטון", "דהן", "אברהם", "פרידמן", "מלכה", "אזולאי",
              "כץ", "יוסף", "דוד", "עמר", "אוחיון", "חדד", "גבאי", "בן דוד", "אדרי", "לוין",
              "טל", "גולן", "שפירא", "ברק", "שור", "רובין", "אטיאס", "יצחקי", "שושן", "פלג"]

sources = ["פייסבוק", "אינסטגרם", "חבר מביא חבר", "אחר", "שלט/רחוב"]
statuses = ["NEW", "IN_PROGRESS", "REJECTED", "CONVERTED"]

def generate_phone(prefix="050"):
    return f"{prefix}-{random.randint(1000000, 9999999)}"

def generate_id():
    return str(random.randint(100000000, 999999999))

def generate_30_records():
    conn = sqlite3.connect("studio.db")
    cursor = conn.cursor()
    
    # Generate 30 Members
    print("Generating 30 Members...")
    for _ in range(30):
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        phone = generate_phone(random.choice(["050", "052", "054", "053", "058"]))
        email = f"user_{random.randint(1000,9999)}@example.com"
        id_number = generate_id()
        
        try:
            cursor.execute(
                "INSERT INTO members (name, phone, email, id_number, is_active) VALUES (?, ?, ?, ?, 1)",
                (name, phone, email, id_number)
            )
        except sqlite3.IntegrityError:
            pass # ignore duplicates

    # Generate 30 Leads
    print("Generating 30 Leads...")
    for _ in range(30):
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        phone = generate_phone(random.choice(["050", "052", "054", "053", "058"]))
        source = random.choice(sources)
        status = random.choice(statuses)
        notes = "משתמש פיקטיבי"
        
        try:
            cursor.execute(
                "INSERT INTO leads (name, phone, source, status, notes) VALUES (?, ?, ?, ?, ?)",
                (name, phone, source, status, notes)
            )
        except sqlite3.IntegrityError:
            pass # ignore duplicates

    conn.commit()
    
    # Check count
    cursor.execute("SELECT COUNT(*) FROM members")
    print(f"Total Members in DB: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM leads")
    print(f"Total Leads in DB: {cursor.fetchone()[0]}")
    
    conn.close()

if __name__ == "__main__":
    generate_30_records()
