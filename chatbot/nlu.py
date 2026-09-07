"""
=============================================================
chatbot/nlu.py — Natural Language Understanding עם Gemini
=============================================================

מטרה:
    ממשק בין הצ'אטבוט ל-Gemini API.
    מבצע שני סוגי משימות:
        1. EXTRACTION (חילוץ): טקסט חופשי → JSON מובנה
           (שם, תאריך, תעודת זהות וכו')
        2. GENERATION (ניסוח): מצב + נתונים → תשובה טבעית בעברית

    גרסת SDK:
        משתמש ב-google-genai (החדש, 2024+)
        ולא ב-google-generativeai (ישן, deprecated).

    מפתח API:
        נטען מ-.env דרך python-dotenv.
        לעולם לא מקודד ישירות בקוד!

טמפרטורות Gemini:
    - Extraction: temperature=0 (דטרמיניסטי — חייבים JSON מדויק)
    - Generation: temperature=0.7 (יצירתי — תשובות טבעיות)
"""

import json
import os
import re
from dotenv import load_dotenv
from google import genai
from google.genai import types

# טעינת משתני סביבה מ-.env (GEMINI_API_KEY)
load_dotenv()

# ===========================================================
# אתחול לקוח Gemini
# ===========================================================
# os.getenv מחזיר None אם המפתח לא מוגדר → השגיאה תהיה ברורה
_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# מודל Gemini בשימוש
MODEL_ID = "gemini-3.5-flash"


# ===========================================================
# PART 1: Extraction — חילוץ Intent מטקסט חופשי
# ===========================================================

EXTRACTION_PROMPT = """
אתה מנוע חילוץ מידע (NLU) למערכת תורים של סטודיו ספורט.
המשתמש שלח הודעה בעברית. עליך לחלץ ממנה מידע ולהחזיר JSON בלבד — ללא טקסט נוסף.

הודעת המשתמש: "{user_message}"

החזר JSON בפורמט הבא (החזר null לשדות חסרים):
{{
  "intent": "APPOINTMENT_INQUIRY" | "BOOK_CLASS" | "GENERAL_QUESTION" | "IDENTITY_RESPONSE" | "CLARIFICATION" | "GREETING" | "RESET" | "OTHER",
  "name": "<כל שם פרטי או מלא שהוזכר, למשל 'יעל חדד', 'ישראל', 'רותם', או null>",
  "claimed_date": "<תאריך בפורמט YYYY-MM-DD, או null>",
  "claimed_time": "<שעה בפורמט HH:MM, או null>",
  "id_number": "<תעודת זהות אם הוזנה (7-9 ספרות), או null>",
  "raw_text": "{user_message}"
}}

חוקי סיווג intent:
- APPOINTMENT_INQUIRY  : המשתמש מבקש מידע על תור, מתי התור שלו או של מישהו אחר, או ביטול תור (למשל 'מתי התור של יעל חדד?', 'לאיזה אימון אני רשום?', 'לאיזה אימון יעל חדד רשומה?').
- BOOK_CLASS           : המשתמש מבקש להירשם לאימון, לקבוע תור, או לשריין מקום לאימון.
- GENERAL_QUESTION     : המשתמש שואל כל שאלה כללית על הסטודיו (שעות, מאמנים, מחירים, חוקים, שירותים, ציוד).
- IDENTITY_RESPONSE    : המשתמש עונה על שאלת זיהוי - מספק שם, או ת.ז.
- CLARIFICATION        : מספק הבהרה (שם מלא, אישור).
- RESET                : "התחל מחדש" / "חדש" / "reset"
- GREETING             : "שלום" / "היי" / "בוקר טוב"
- OTHER                : כל דבר אחר שלא נופל לקטגוריות לעיל.

חוקי פורמט (קריטי):
- name: חובה לחלץ כל שם של אדם שהוזכר במשפט (למשל "לאיזה אימון יעל חדד רשומה?" -> "יעל חדד").
- תאריכים: המר פורמטים כמו 18.01.2027 → 2027-01-18
- ת.ז.: 7-9 ספרות ברצף
- החזר JSON תקין בלבד, ללא markdown, ללא ```
"""


def extract_intent(user_message: str) -> dict:
    """
    מחלץ intent ומידע מובנה מהודעת משתמש באמצעות Gemini.

    מתי להשתמש:
        בכל הודעת משתמש שמגיעה לצ'אטבוט.

    גישה:
        שולח prompt קשיח ל-Gemini עם temperature=0
        כדי לקבל JSON מדויק וחזור (לא יצירתי).
        מנקה markdown אם Gemini הוסיף ```json```.

    Fallback:
        אם Gemini נכשל או מחזיר JSON לא תקין →
        מחזיר dict עם intent="OTHER" (לא קורס).

    Args:
        user_message: טקסט חופשי בעברית מהמשתמש

    Returns:
        dict עם מפתחות: intent, name, claimed_date, claimed_time,
        id_number, raw_text. ערכים חסרים = None.
    """
    # הכנסת הודעת המשתמש לתוך ה-prompt
    prompt = EXTRACTION_PROMPT.format(user_message=user_message)

    try:
        response = _client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,        # דטרמיניסטי — JSON מדויק
            ),
        )
        raw = response.text.strip()

        # ניקוי: Gemini לעיתים עוטף ב-```json ... ```
        raw = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()

        # פרסור JSON → dict
        data = json.loads(raw)
        return data

    except (json.JSONDecodeError, Exception) as e:
        # כשל: מחזיר dict בטוח עם intent=OTHER
        return {
            "intent": "OTHER",
            "name": None,
            "claimed_date": None,
            "claimed_time": None,
            "id_number": None,
            "raw_text": user_message,
            "error": str(e),  # לצרכי debugging (לא מוצג למשתמש)
        }


# ===========================================================
# PART 2: Generation — ניסוח תשובות טבעיות
# ===========================================================

# מילון תבניות Prompt לפי מצב (situation)
# כל תבנית מקבלת **data כ-format arguments
_SITUATION_PROMPTS = {
    # תרחיש 1: תיקון תאריך שגוי
    "appointment_correction": """
המשתמש {name} בדק תור. התאריך שהוא טען: {claimed_date}.
התאריך האמיתי במערכת: {real_date} בשעה {real_time}.
כתוב תשובה בעברית ידידותית שמתקנת את הטעות ומדגישה את הפרטים הנכונים.
חשוב: ציין בבירור שהתאריך שציין שגוי, וכתוב את הנכון.
""",
    # תרחיש: תאריך נכון
    "appointment_correct": """
המשתמש {name} בדק תור. התאריך שציין ({claimed_date}) נכון!
האימון ב-{real_date} בשעה {real_time}.
כתוב תשובה קצרה בעברית שמאשרת את המידע ומשרה ביטחון.
""",
    # תרחיש 4: אין תורים
    "no_appointments": """
המשתמש {name} בדק תורים, אך אין לו אימונים רשומים פעילים במערכת.
כתוב תשובה בעברית ידידותית שמסבירה זאת ומציעה לפנות לסטודיו לתיאום.
""",
    # תרחיש 5: שם לא קיים
    "not_found": """
חיפשנו במערכת לקוח בשם '{name}' אך לא מצאנו התאמה.
כתוב תשובה בעברית ידידותית שמציעה לנסות שם אחר או לפנות לסטודיו.
""",
    # חשיפת פרטי מנוי ואימון קרוב (לאחר זיהוי תקין)
    "subscription_details": """
המשתמש {name} זוהה בהצלחה. 
פרטי האימון הקרוב שלו: תאריך {real_date} בשעה {real_time}.
כתוב תשובה קצרה, מסבירת פנים ושמחה שמציגה לו את האימון הקרוב שלו.
""",
    # הצעת הרשמה (לאחר שזיהוי שם + ת.ז נכשל)
    "offer_registration": """
חיפשנו משתמש בשם {name} עם תעודת זהות {id_number} ולא מצאנו התאמה במסד הנתונים של הסטודיו.
כתוב הודעה נעימה וידידותית שמסבירה שלא מצאנו אותו, והצע לו בחביבות להירשם או ליצור קשר כדי להצטרף אלינו.
""",
    # הרשמה לאימון בוצעה בהצלחה
    "booking_success": """
המשתמש {name} נרשם בהצלחה לאימון בתאריך {date} בשעה {time}.
הודעת המערכת: {sys_message}.
כתוב תשובה שמחה ונלהבת בעברית המאשרת את ההרשמה ומצפה לראות אותו באימון. התייחס להודעת המערכת אם יש צורך (למשל מספר מקום).
""",
    # הרשמה לאימון נכשלה (מלא, כפילות וכו')
    "booking_failure": """
המשתמש {name} ניסה להירשם לאימון בתאריך {date} בשעה {time} אך ההרשמה נכשלה.
הודעת המערכת לגבי סיבת הכישלון: {sys_message}.
כתוב תשובה מנומסת ואמפתית בעברית המסבירה מדוע אי אפשר היה לבצע את ההרשמה (לפי הודעת המערכת) והצע עזרה או מועד חלופי.
""",
    # RAG: תשובה כללית מהמאגר
    "general_answer": """
שאלת המשתמש: {question}
תשובה ממאגר הידע: {answer}
נסח תשובה בעברית טבעית וידידותית בהתבסס על המידע לעיל.
""",
    # Fallback: לא נמצא מידע
    "fallback": """
המשתמש שאל: {question}
לא נמצאה תשובה במאגר הידע.
כתוב תשובה קצרה ומנומסת בעברית שמציעה לפנות לסטודיו ישירות.
""",
}

# Prefix משותף לכל prompt של generation
_GENERATION_PREFIX = (
    "אתה עוזר ידידותי של סטודיו ספורט FitStudio. "
    "ענה בעברית בלבד, בטון חם, מקצועי וקצר. "
    "אסור לך להוסיף הערות פנימיות, מחשבות, או מטא-טקסט. החזר אך ורק את התשובה הסופית ללקוח.\n\n"
)


def generate_response(situation: str, data: dict) -> str:
    """
    מנסח תשובה טבעית בעברית בהתאם למצב השיחה, בעזרת Gemini.

    מתי להשתמש:
        כאשר התשובה צריכה להיות 'חכמה' ולא hardcoded —
        כמו תיקון תאריך, אישור תור, הסבר על RAG.

    Args:
        situation: מזהה המצב — מפתח ב-_SITUATION_PROMPTS
                   (לדוגמה: "appointment_correction", "not_found")
        data     : מילון עם ערכים לתוך תבנית ה-prompt
                   (לדוגמה: {"name": "רותם", "real_date": "2026-08-19"})

    Returns:
        תשובה בעברית (str). במקרה של כשל — הודעת שגיאה כללית.
    """
    # בחר תבנית לפי situation, fallback לתבנית כללית
    template = _SITUATION_PROMPTS.get(situation, _SITUATION_PROMPTS["fallback"])

    # הכנס ערכים לתוך התבנית (המר הכל ל-str למניעת שגיאות)
    filled = template.format(**{k: str(v) for k, v in data.items()})
    prompt = _GENERATION_PREFIX + filled

    try:
        response = _client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,        # יצירתי — תשובות טבעיות
            ),
        )
        return response.text.strip()

    except Exception as e:
        # Fallback במקרה של כשל ב-API
        return f"מצטערים, אירעה שגיאה זמנית. אנא נסה שנית. (שגיאה: {e})"
