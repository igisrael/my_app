# מדריך פריסה - FitStudio 🚀

קובץ זה מכיל את ההוראות לפריסת המערכת בשרת אמיתי (Production) ישירות מתוך המאגר ב-GitHub. 
ההוראות מתאימות לפריסה על שרתי לינוקס (כגון Ubuntu ב-AWS, DigitalOcean או פלטפורמות ענן אחרות), וכוללות התקנה דרך Git, הגדרת סביבה, וריצה כסרביס.

## דרישות קדם (Prerequisites)
1. גישת SSH לשרת היעד.
2. מותקנים על השרת:
   - Python 3.10 ומעלה
   - Git
   - pip, venv
   - (אופציונלי) Docker & Docker Compose - במידה ותרצו לפרוס באמצעות Docker.

## פריסה (Deployment) - סביבת לינוקס מסורתית

### 1. משיכת הקוד מ-GitHub
התחברו לשרת באמצעות SSH והריצו את הפקודות הבאות:

```bash
# היכנסו לתיקייה בה תרצו לפרוס את הפרויקט (לדוגמה /var/www)
cd /var/www

# שכפלו את המאגר (יש להחליף ל-URL שלכם)
git clone https://github.com/your-username/fitstudio.git
cd fitstudio

# אם רוצים לפרוס מענף Dev (כמו בפרויקט שלנו)
git checkout Dev
```

### 2. הקמת סביבה וירטואלית (Virtual Environment)
לא מומלץ להתקין חבילות באופן גלובלי.
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. התקנת תלויות
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. הגדרת משתני סביבה (.env)
צרו קובץ `.env` והכניסו את מפתח ה-API שלכם:
```bash
nano .env
```
בתוך הקובץ, כתבו:
```env
GEMINI_API_KEY=YOUR_PRODUCTION_API_KEY_HERE
```
שמרו וצאו (Ctrl+X -> Y -> Enter).

### 5. הקמת מסד הנתונים
הריצו את סקריפט הזרקת הנתונים על מנת לאתחל את בסיס הנתונים:
```bash
python seed_data.py
```

### 6. הפעלת המערכת כ-Service (Systemd)
כדי ש-Streamlit ירוץ תמיד ברקע ויחזור במקרה שהשרת קורס או מאותחל, ניצור Systemd service.

```bash
sudo nano /etc/systemd/system/fitstudio.service
```

הכניסו את התוכן הבא (התאימו נתיבים לשלכם):
```ini
[Unit]
Description=FitStudio Streamlit App
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/var/www/fitstudio
ExecStart=/var/www/fitstudio/venv/bin/streamlit run app.py --server.port 8501 --server.address 0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
```

הפעילו את הסרביס:
```bash
sudo systemctl daemon-reload
sudo systemctl enable fitstudio
sudo systemctl start fitstudio
```

כעת האפליקציה תרוץ באופן קבוע על פורט 8501. 

## פריסה חלופית באמצעות Docker

אם השרת תומך ב-Docker, ניתן לעשות זאת בצורה קלה יותר:

1. ודאו שהקוד נמצא בשרת (`git clone`).
2. בנו את ה-Image:
   ```bash
   docker build -t fitstudio-app .
   ```
3. הריצו את הקונטיינר (וודאו שקובץ ה-`.env` קיים):
   ```bash
   docker run -d -p 8501:8501 --env-file .env --name fitstudio-bot fitstudio-app
   ```

## עדכון גרסה עתידי (Update / CI/CD)
כדי לעדכן את השרת לאחר שדחפתם שינויים חדשים ל-GitHub, הריצו:
```bash
cd /var/www/fitstudio
git pull origin Dev
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart fitstudio
```
ניתן לבצע אוטומציה של תהליך זה באמצעות GitHub Actions (CD).

## אבטחה
- שימו לב לא לפתוח את פורט 8501 החוצה ללא הגנה, מומלץ להשתמש ב-Nginx בתור Reverse Proxy ולהוסיף תעודת SSL דרך Let's Encrypt.
- ודאו שהגישה לקובץ `.env` ול-`database.db` מוגבלת למשתמש השרת בלבד (`chmod 600`).
