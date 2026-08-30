# DEPLOY.md — נוהל פריסה ועדכון שרת — FitStudio v2

> **גרסה**: 2.0 | **תאריך עדכון**: אוגוסט 2026

---

## 1. הרצה מקומית (Local Development)

### דרישות מקדימות
- Python 3.11+
- Git

### שלבים

```bash
# 1. שכפל את הריפו
git clone https://github.com/<your-username>/fitstudio.git
cd fitstudio

# 2. התקן תלויות
pip install -r requirements.txt

# 3. הגדר API Key
# צור קובץ .env בתיקיית הפרויקט עם התוכן:
# GEMINI_API_KEY=your_key_here

# 4. אתחל נתוני דמו (פעם ראשונה בלבד)
python seed_data.py

# 5. הפעל את ה-API (בטרמינל נפרד)
uvicorn api.main:app --reload --port 8000

# 6. הפעל את ממשק Streamlit (בטרמינל נפרד)
streamlit run app.py
```

האפליקציה תרוץ על:
- **Streamlit UI**: http://localhost:8501
- **FastAPI**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs

---

## 2. עדכון שרת מ-GitHub (Manual Deployment)

### תנאי מוקדם
- גישת SSH לשרת
- הפרויקט כבר פרוס פעם אחת בשרת

### שלב 1 — כניסה לשרת
```bash
ssh user@your-server-ip
cd /opt/fitstudio
```

### שלב 2 — משיכת קוד עדכני מ-GitHub
```bash
git fetch origin
git pull origin main
```

### שלב 3 — עדכון תלויות (אם נוספו)
```bash
pip install -r requirements.txt
```

### שלב 4 — הפעלה מחדש של השירותים

```bash
# עצור תהליכים קיימים
pkill -f "uvicorn api.main" || true
pkill -f "streamlit run app.py" || true

# המתן שיתנקו
sleep 3

# הפעל מחדש ברקע
nohup uvicorn api.main:app --host 0.0.0.0 --port 8000 > logs/api.log 2>&1 &
nohup streamlit run app.py --server.port 8501 --server.address 0.0.0.0 > logs/streamlit.log 2>&1 &

echo "✅ השירותים הופעלו מחדש בהצלחה"
```

### שלב 5 — בדיקת תקינות
```bash
# בדיקת API
curl http://localhost:8000/health

# בדיקת Streamlit
curl -s -o /dev/null -w "%{http_code}" http://localhost:8501
```

---

## 3. תהליך DevOps — סיכום

```
קוד מקומי ← git push → GitHub
               ↓
           git pull (ידני על השרת)
               ↓
         pip install -r requirements.txt
               ↓
         pkill + nohup (הפעלה מחדש)
               ↓
         curl /health (בדיקת תקינות)
```

> **חשוב**: זהו תהליך **pull-based deployment** ידני — לא CI/CD אוטומטי.
> בכל עדכון יש לבצע את שלבים 1-5 לעיל.

---

## 4. משתני סביבה (.env)

| משתנה | תיאור | חובה |
|-------|--------|------|
| `GEMINI_API_KEY` | מפתח API של Google Gemini | ✅ |

> **אבטחה**: לעולם אל תעלה `.env` ל-GitHub! הוא כבר ב-`.gitignore`.

---

## 5. מבנה הפרויקט

```
fitstudio/
├── app.py               # Streamlit UI (4 טאבים כולל צ'אטבוט)
├── api/
│   └── main.py          # FastAPI REST endpoints
├── chatbot/
│   ├── agent.py         # State Machine + לוגיקה ראשית
│   ├── nlu.py           # Gemini NLU
│   └── state.py         # ניהול מצב שיחה
├── rag/
│   ├── knowledge_base.py # 25 שאלות-תשובות
│   └── retriever.py      # ChromaDB similarity search
├── services/
│   ├── lead_service.py
│   ├── member_service.py
│   └── wod_service.py
├── database.py          # SQLite + migrations
├── seed_data.py         # זריעת נתוני דמו
├── requirements.txt
├── .env                 # (לא ב-Git!)
└── DEPLOY.md
```

---

## 6. לוגים ואיתור שגיאות

```bash
# לוג API
tail -f logs/api.log

# לוג Streamlit
tail -f logs/streamlit.log

# בדיקת תהליכים רצים
ps aux | grep -E "uvicorn|streamlit"
```

---

## 7. גיבוי בסיס הנתונים

```bash
# גיבוי ידני
cp studio.db backups/studio_$(date +%Y%m%d_%H%M).db

# שחזור
cp backups/studio_YYYYMMDD_HHMM.db studio.db
```

---

*נכתב לפי דרישות פרויקט הסיום — FitStudio v2*
