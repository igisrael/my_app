"""
chatbot/nlu.py — Natural Language Understanding עם Gemini API.

אחראי על:
1. חילוץ intent ומידע מובנה מטקסט חופשי (extraction)
2. ניסוח תשובות טבעיות בעברית עם Gemini

NOTE: משתמש ב-google-genai (החדש) ולא ב-google-generativeai (הישן שאינו נתמך עוד).
"""

import json
import os
import re
from typing import Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# אתחול הלקוח עם ה-API Key מקובץ .env
_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_ID = "gemini-2.0-flash"

# ===========================================================
# Extraction — חילוץ intent מטקסט חופשי
# ===========================================================

EXTRACTION_PROMPT = """
אתה מנוע חילוץ מידע (NLU) למערכת תורים של סטודיו ספורט.
המשתמש שלח הודעה בעברית. עליך לחלץ ממנה מידע ולהחזיר JSON בלבד — ללא טקסט נוסף.

הודעת המשתמש: "{user_message}"

החזר JSON בפורמט הבא (החזר null לשדות חסרים):
{{
  "intent": "APPOINTMENT_INQUIRY" | "GENERAL_QUESTION" | "IDENTITY_RESPONSE" | "CLARIFICATION" | "GREETING" | "RESET" | "OTHER",
  "name": "<שם שהמשתמש הזכיר, או null>",
  "claimed_date": "<תאריך בפורמט YYYY-MM-DD, או null>",
  "claimed_time": "<שעה בפורמט HH:MM, או null>",
  "id_number": "<תעודת זהות אם הוזנה, או null>",
  "raw_text": "{user_message}"
}}

חוקים:
- intent=APPOINTMENT_INQUIRY אם המשתמש שואל על תור/אימון שלו
- intent=GENERAL_QUESTION אם שואל על שעות סטודיו, מחירים, כללים
- intent=IDENTITY_RESPONSE אם הודעה נראית כמספר ת.ז (7-9 ספרות)
- intent=CLARIFICATION אם מספק הבהרה (שם מלא, אישור)
- intent=RESET אם כותב "התחל מחדש" / "חדש" / "reset"
- intent=GREETING אם אומר שלום / היי
- תאריכים: המר פורמטים כמו 18.01.2027 ל-2027-01-18
- החזר JSON תקין בלבד, ללא markdown
"""


def extract_intent(user_message: str) -> dict:
    """
    מחלץ intent ומידע מובנה מהודעת המשתמש.
    מחזיר dict עם שדות: intent, name, claimed_date, claimed_time, id_number.
    במקרה של כשל — מחזיר intent=OTHER.
    """
    prompt = EXTRACTION_PROMPT.format(user_message=user_message)

    try:
        response = _client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,  # דטרמיניסטי — חייבים JSON מדויק
                max_output_tokens=300,
            ),
        )
        raw = response.text.strip()

        # ניקוי markdown אם Gemini הוסיף ```json```
        raw = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()

        data = json.loads(raw)
        return data

    except (json.JSONDecodeError, Exception) as e:
        # fallback בטוח
        return {
            "intent": "OTHER",
            "name": None,
            "claimed_date": None,
            "claimed_time": None,
            "id_number": None,
            "raw_text": user_message,
            "error": str(e),
        }


# ===========================================================
# Response Generation — ניסוח תשובות טבעיות
# ===========================================================

def generate_response(
    situation: str,
    data: dict,
    language: str = "hebrew",
) -> str:
    """
    מנסח תשובה טבעית בעברית בהתאם למצב השיחה.

    situation: תיאור המצב (לדוגמה: "appointment_correction", "identity_required", "not_found")
    data: מידע רלוונטי (תאריכים, שמות, וכו')
    """

    situation_prompts = {
        "appointment_correction": """
המשתמש {name} בדק תור. התאריך שהוא טען: {claimed_date}.
התאריך האמיתי במערכת: {real_date} בשעה {real_time}.
כתוב תשובה בעברית ידידותית שמתקנת את הטעות, מדגישה את הפרטים הנכונים.
חשוב: הדגש שהתאריך שהוא ציין שגוי.
""",
        "appointment_correct": """
המשתמש {name} בדק תור. התאריך שציין ({claimed_date}) נכון!
האימון ב-{real_date} בשעה {real_time}.
כתוב תשובה בעברית ידידותית שמאשרת שהמידע שלו נכון.
""",
        "no_appointments": """
המשתמש {name} בדק תורים, אך אין לו תורים פעילים במערכת.
כתוב תשובה בעברית ידידותית שמסבירה זאת ומציעה לו לפנות לסטודיו לתיאום.
""",
        "not_found": """
המשתמש חיפש לקוח בשם '{name}' אך לא נמצא במערכת.
כתוב תשובה בעברית ידידותית שמסבירה שהשם לא נמצא, ומציעה לנסות שם אחר או לפנות לסטודיו.
""",
        "general_answer": """
שאלת המשתמש: {question}
תשובה מהמאגר: {answer}
כתוב תשובה בעברית טבעית וידידותית בהתבסס על המידע שניתן.
""",
        "fallback": """
המשתמש שאל: {question}
לא נמצאה תשובה במאגר הידע.
כתוב תשובה בעברית מנומסת שמסבירה שאינך יודע את התשובה ומציעה לפנות לסטודיו ישירות.
""",
    }

    prompt_template = situation_prompts.get(situation, situation_prompts["fallback"])
    prompt = f"אתה עוזר ידידותי של סטודיו ספורט FitStudio. ענה בעברית בלבד, בטון חם ומקצועי.\n\n"
    prompt += prompt_template.format(**{k: str(v) for k, v in data.items()})

    try:
        response = _client.models.generate_content(
            model=MODEL_ID,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=500,
            ),
        )
        return response.text.strip()
    except Exception as e:
        return f"מצטערים, אירעה שגיאה. אנא נסה שנית. (שגיאה: {e})"
