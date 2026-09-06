# DEPLOY.md — נוהל פריסה ועדכון שרת (PythonAnywhere) — FitStudio v2

> **גרסה**: 2.0 | **תאריך עדכון**: אוגוסט 2026

פרויקט זה הותאם להרצה על השרתים החינמיים של **PythonAnywhere**.
מכיוון שפלטפורמה זו אינה תומכת בהרצת `Streamlit` או `FastAPI` (היא דורשת WSGI Web App מסורתי), הומר ה-UI של הצ'אטבוט לאפליקציית **Flask**.

---

## 1. הרצה מקומית לצורך פיתוח (Local Development)

### שלבים

```bash
# 1. שכפל את הריפו
git clone https://github.com/<your-username>/fitstudio.git
cd fitstudio

# 2. התקן תלויות
pip install -r requirements.txt
pip install flask python-dotenv chromadb google-genai

# 3. הגדר API Key
# צור קובץ .env בתיקיית הפרויקט עם התוכן:
# GEMINI_API_KEY=your_key_here

# 4. אתחל נתוני דמו (פעם ראשונה בלבד)
python seed_data.py

# 5. הפעל את שרת ה-Flask (Web UI של הצ'אטבוט)
python flask_app.py
```

האפליקציה תרוץ בכתובת: `http://localhost:5000`

---

## 2. פריסה ב-PythonAnywhere (Deployment)

כדי להעלות את הפרויקט ל-PythonAnywhere בחינם, עקוב אחר השלבים הבאים בדיוק:

### שלב א' — העלאת הקוד לשרת
1. פתח חשבון חינמי ב- [PythonAnywhere.com](https://www.pythonanywhere.com/).
2. היכנס לטאב **Consoles** ופתח מסוף מסוג **Bash**.
3. שכפל את קוד הפרויקט מ-GitHub:
   ```bash
   git clone https://github.com/<your-username>/fitstudio.git
   cd fitstudio
   ```

### שלב ב' — יצירת סביבה וירטואלית והתקנת תלויות
בתוך אותו מסוף Bash:
```bash
# יצירת סביבה וירטואלית ל-Python 3.10
mkvirtualenv --python=/usr/bin/python3.10 fitstudio-env

# התקנת התלויות הדרושות
pip install flask python-dotenv google-genai
```

### שלב ג' — הגדרת משתני סביבה (.env)
במסוף Bash:
```bash
cd ~/fitstudio
nano .env
```
כתוב בפנים:
```
GEMINI_API_KEY=המפתח_שלך_כאן
FLASK_SECRET_KEY=super-secret-key-123
```
שמור וצא (`Ctrl+X` -> `Y` -> `Enter`).

### שלב ד' — הגדרת ה-Web App ב-PythonAnywhere
1. עבור לטאב **Web** בלוח הבקרה של PythonAnywhere.
2. לחץ על **Add a new web app**.
3. לחץ *Next*, בחר **Manual configuration** (חשוב! אל תבחר Flask), ובחר את גרסת הפייתון (למשל Python 3.10).
4. תחת סעיף **Virtualenv**, לחץ על הפס האדום והכנס את הנתיב:
   `/home/yourusername/.virtualenvs/fitstudio-env`
5. תחת סעיף **Code**, הגדר את ה-Source code ל:
   `/home/yourusername/fitstudio`

### שלב ה' — הגדרת ה-WSGI Configuration File
1. תחת סעיף **Code**, לחץ על הקישור לקובץ ה-WSGI (למשל `/var/www/yourusername_pythonanywhere_com_wsgi.py`).
2. מחק את כל מה שכתוב שם, והדבק את הקוד הבא:

```python
import sys
import os
from dotenv import load_dotenv

# נתיב התיקייה של הפרויקט
project_home = '/home/yourusername/fitstudio'
if project_home not in sys.path:
    sys.path = [project_home] + sys.path

# טעינת משתני הסביבה (GEMINI_API_KEY)
load_dotenv(os.path.join(project_home, '.env'))

# ייבוא של ה-Flask app שהכנו
from flask_app import app as application
```
*(אל תשכח להחליף את `yourusername` בשם המשתמש שלך ב-PythonAnywhere!)*
3. שמור את הקובץ.

### שלב ו' — הפעלה!
חזור לטאב **Web** ולחץ על הכפתור הירוק הגדול **Reload yourusername.pythonanywhere.com**.
היכנס ללינק של האתר שלך והצ'אטבוט מוכן לעבודה!

---

## 3. מבנה הפרויקט (גרסת Flask)

```
fitstudio/
├── flask_app.py         # אפליקציית ה-Flask הראשית שרצה בשרת
├── templates/
│   └── chat.html        # ממשק משתמש לצ'אט מודרני עם CSS/JS
├── chatbot/
│   ├── agent.py         # לוגיקת הצ'אטבוט (State Machine)
│   ├── db_service.py    # גישה ישירה ל-DB (במקום דרך API)
│   ├── nlu.py           # חיבור ל-Gemini
│   └── state.py         # ניהול מצב השיחה
├── rag/
│   ├── knowledge_base.py
│   └── retriever.py
├── services/            # שירותי מערכת מתועדים
├── database.py          # סכמת ה-DB ו-migrations
├── seed_data.py         # יצירת נתונים התחלתיים
├── requirements.txt
├── .env                 # חובה ליצור מקומית/בשרת (לא ב-Git)
└── DEPLOY.md            # מסמך זה
```
