# השתמש בתמונת פייתון רשמית וקלה
FROM python:3.10-slim

# הגדרת תיקיית העבודה בתוך הקונטיינר
WORKDIR /app

# העתקת קובץ הדרישות והתקנת התלויות
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# העתקת שאר קבצי הפרויקט
COPY . .

# חשיפת הפורט שבו Streamlit רץ כברירת מחדל
EXPOSE 8501

# הגדרת משתני סביבה כדי למנוע יצירת קבצי .pyc וכדי שהלוגים יודפסו בזמן אמת
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# הפקודה שתרוץ בעת הפעלת הקונטיינר - הפעלת אפליקציית ה-Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
