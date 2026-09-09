"""
=============================================================
chatbot/agent.py — הלוגיקה המרכזית של הצ'אטבוט
=============================================================

מטרה:
    מנהל את מחזור חיי השיחה כולו: מקבל הודעת משתמש,
    מנתב לשלב המתאים, מבצע אימות זהות, שולף נתונים אמיתיים,
    ומחזיר תשובה בעברית.

ארכיטקטורה (State Machine):
    כל הודעת משתמש עוברת דרך process_message() →
    מנותבת לפי state.stage → מחזירה תשובה טקסטואלית.

    GREETING → IDENTIFY_NAME → IDENTIFY_ID → ANSWERED (אם אומת)
                                           → GREETING (הצעת הרשמה אם לא אומת)
                                           → BLOCKED (אחרי 3 כשלונות בת.ז)

    כל שלב יכול לעבור ל-RAG_MODE לשאלות כלליות.

שינוי ל-PythonAnywhere:
    במקום HTTP requests ל-localhost:8000 (FastAPI),
    משתמשים ב-db_service.py שפונה ישירות ל-SQLite.
    זה מאפשר הפעלה כתהליך יחיד ב-PythonAnywhere.
"""

import re
from chatbot.state import ConversationState, MAX_AUTH_ATTEMPTS
from chatbot.nlu import extract_intent, generate_response
from chatbot import db_service
from services.wod_service import register_member_to_wod
from logger_setup import logger


# ===========================================================
# הודעות קבועות (Hardcoded messages)
# ===========================================================
# הודעות אלו אינן עוברות דרך Gemini — הן תמיד זהות ומאובטחות

MSG_GREETING = (
    "שלום! אני הבוט של FitStudio 🏋️\n"
    "כדי שאוכל לעזור לך באופן אישי, אנא כתוב לי את שמך המלא."
)

MSG_ASK_NAME = "מה שמך המלא?"

def MSG_ASK_ID(name: str, attempts_left: int) -> str:
    """
    בקשה להזנת תעודת זהות לאימות.
    מציין כמה ניסיונות נותרו.
    """
    return (
        f"נעים מאוד {name}! 🔐\n"
        f"לאימות זהות ולמציאת המנוי שלך, אנא הזן את מספר תעודת הזהות שלך.\n"
        f"(נותרו {attempts_left} ניסיונות)"
    )

def MSG_WRONG_ID(attempts_left: int) -> str:
    """הודעה כשתעודת הזהות שגויה או לא נרשמה — מבקש שוב."""
    if attempts_left == 1:
        warning = "⚠️ נותר ניסיון אחד בלבד!"
    else:
        warning = f"נותרו {attempts_left} ניסיונות."
    return f"תעודת הזהות שהזנת אינה תקינה (יש להזין 7-9 ספרות). אנא נסה שנית.\n{warning}"

MSG_BLOCKED = (
    "חרגת ממגבלת הניסיונות המותרת (3 ניסיונות). 🔒\n"
    "לביטחון פרטיך, השיחה נחסמת.\n"
    "אנא פנה אלינו ישירות לסיוע.\n"
    "📞 טלפון: 050-0000000"
)

MSG_RESET = "✅ השיחה אופסה. שלום! כיצד אוכל לעזור? אנא כתוב לי את שמך המלא."

MSG_FALLBACK = (
    "לא מצאתי מידע ספציפי על שאלתך.\n"
    "אנא פנה אלינו ישירות:\n"
    "📞 טלפון: 050-0000000\n"
    "🏠 כתובת: רחוב הספורט 1, תל אביב"
)


# ===========================================================
# ChatbotAgent — מחלקה ראשית
# ===========================================================

class ChatbotAgent:
    """
    מנהל שיחה עם משתמש מקצה לקצה.

    יצירת instance:
        agent = ChatbotAgent()

    שימוש בכל הודעה:
        response = agent.process_message("קוראים לי רותם...")

    שמירה בין הודעות:
        ב-Streamlit: st.session_state["agent"] = agent
        ב-Flask:     session["agent_state"] = pickle.dumps(agent)

    Attributes:
        state: ConversationState — מחזיק את כל מצב השיחה
    """

    def __init__(self):
        """אתחול סוכן עם מצב שיחה חדש (GREETING)."""
        self.state = ConversationState()

    # ------------------------------------------------------------------
    # ← נקודת הכניסה הציבורית היחידה ←
    # ------------------------------------------------------------------

    def process_message(self, user_message: str) -> str:
        """
        זהו ה-entry point היחיד שצריך לקרוא מבחוץ.
        כל לוגיקת הניתוב מתרחשת כאן.

        תהליך:
            1. בדוק אם שיחה חסומה (BLOCKED)
            2. חלץ intent בעזרת Gemini NLU
            3. בדוק בקשת איפוס
            4. נתב ל-handler המתאים לפי stage
            5. הוסף הודעות להיסטוריה

        Args:
            user_message: טקסט חופשי בעברית מהמשתמש

        Returns:
            תשובת הבוט כטקסט (עברית)
        """
        user_message = user_message.strip()
        logger.info("--- תחילת עיבוד הודעה חדשה ---")
        logger.info(f"הודעת משתמש: '{user_message}'")
        logger.info(f"סטטוס שיחה נוכחי: {self.state.stage}")

        try:
            # שמור את הודעת המשתמש בהיסטוריה
            self.state.add_message("user", user_message)

            # ---- בדיקה: שיחה חסומה לאחר 3 כישלונות ----
            if self.state.is_blocked:
                logger.warning("השיחה חסומה עקב ריבוי כשלונות אימות. לא מבצע פעולה.")
                self.state.add_message("bot", MSG_BLOCKED)
                return MSG_BLOCKED

            # ---- NLU: חילוץ intent ומידע מובנה ----
            nlu = extract_intent(user_message)
            
            if nlu.get("error"):
                error_msg = "⚠️ אירעה שגיאת תקשורת עם מנוע ה-AI (ייתכן שמפתח ה-API שגוי או פג תוקף). אנא עדכן את קובץ ה-.env שלך."
                logger.error(f"API Key error or NLU failure detected. Details: {nlu.get('error')}")
                self.state.add_message("bot", error_msg)
                return error_msg

            intent = nlu.get("intent", "OTHER")

            # ---- שמירת כוונת הרשמה אם עדיין לא מאומת ----
            if intent == "BOOK_CLASS" and not self.state.is_verified:
                logger.info("זוהתה כוונת הרשמה לאימון. שומר בהמתנה עד לאימות.")
                self.state.pending_intent = "BOOK_CLASS"
                if nlu.get("claimed_date"):
                    self.state.pending_date = nlu.get("claimed_date")
                if nlu.get("claimed_time"):
                    self.state.pending_time = nlu.get("claimed_time")

            # ---- איפוס מפורש של השיחה ----
            reset_keywords = {"התחל מחדש", "חדש", "reset", "restart", "נתחיל מחדש"}
            if intent == "RESET" or user_message.strip().lower() in reset_keywords:
                logger.info("המשתמש ביקש איפוס שיחה. המצב אופס.")
                self.state.reset()
                self.state.add_message("bot", MSG_RESET)
                return MSG_RESET

            # ---- ניתוב לפי שלב השיחה ----
            logger.info(f"מנתב לשלב {self.state.stage} עם כוונה: {intent}")
            response = self._route(intent, nlu, user_message)
            
            self.state.add_message("bot", response)
            logger.info("--- סיום עיבוד בהצלחה ---")
            return response

        except Exception as e:
            logger.error(f"שגיאה חמורה בעיבוד ההודעה: {str(e)}", exc_info=True)
            error_reply = "מצטערים, אירעה שגיאה פנימית במערכת. אנא נסה שוב או פנה לתמיכה."
            self.state.add_message("bot", error_reply)
            return error_reply

    # ------------------------------------------------------------------
    # ניתוב (Router)
    # ------------------------------------------------------------------

    def _route(self, intent: str, nlu: dict, raw: str) -> str:
        """
        מנתב את ההודעה ל-handler המתאים לפי stage נוכחי.

        Args:
            intent: כוונת המשתמש (מ-NLU)
            nlu   : dict מלא של תוצאת NLU (שם, תאריך, ת.ז. וכו')
            raw   : הטקסט הגולמי של המשתמש

        Returns:
            תשובת הבוט
        """
        stage = self.state.stage

        if stage == "GREETING":
            # ברכה ראשונה — עובר ל-IDENTIFY מייד
            self.state.stage = "IDENTIFY_NAME"
            if intent == "GREETING":
                return MSG_GREETING
            # אם הזין שם מייד ללא ברכה — המשך לזיהוי שם
            return self._handle_identify_name(intent, nlu, raw)

        elif stage == "IDENTIFY_NAME" or stage == "IDENTIFY":
            return self._handle_identify_name(intent, nlu, raw)

        elif stage == "IDENTIFY_ID":
            return self._handle_identify_id(intent, nlu, raw)

        elif stage == "ANSWERED":
            return self._handle_answered(intent, nlu, raw)

        return f"מצטערים, אירעה שגיאה פנימית. נסה שוב. (Stage: {stage})"

    # ------------------------------------------------------------------
    # Handlers — handler לכל שלב שיחה
    # ------------------------------------------------------------------

    def _handle_identify_name(self, intent: str, nlu: dict, raw: str) -> str:
        """
        שלב IDENTIFY_NAME: קבלת שם מלא מהמשתמש.

        Args:
            intent: כוונת המשתמש
            nlu   : מידע מחולץ (name וכו')
            raw   : הטקסט הגולמי
        """
        # שאלה כללית (שעות, מחירים) או משפט כלשהו → עבור ל-RAG תחילה אם אין שם
        if intent in ["GENERAL_QUESTION", "OTHER"] and not nlu.get("name"):
            return self._handle_rag(raw)

        name = nlu.get("name")
        if not name:
            # לא נמצא שם בהודעה — בקש שוב
            return MSG_ASK_NAME

        # השם התקבל - שמור אותו במצב השיחה ועבור לשלב הבא (בקשת ת.ז.)
        self.state.candidate_member_name = name
        self.state.stage = "IDENTIFY_ID"
        return MSG_ASK_ID(name, self.state.attempts_left)

    def _handle_identify_id(self, intent: str, nlu: dict, raw: str) -> str:
        """
        שלב IDENTIFY_ID: קבלת ת.ז ואימות משולב (שם + ת.ז) במסד הנתונים.

        Args:
            intent: כוונת המשתמש 
            nlu   : מידע מחולץ (id_number אם זוהה)
            raw   : הטקסט הגולמי
        """
        # שאלה כללית בזמן ממתינים לת.ז. → RAG
        if intent == "GENERAL_QUESTION":
            return self._handle_rag(raw)

        # חילוץ ת.ז.: קודם מ-NLU, אחר כך regex על הטקסט הגולמי
        id_number = nlu.get("id_number")
        if not id_number:
            # regex: חפש רצף של 7-9 ספרות (פורמט ת.ז. ישראלית)
            match = re.search(r'\b\d{7,9}\b', raw)
            if match:
                id_number = match.group()

        if not id_number:
            # לא הוזנה ת.ז. תקינה
            return MSG_WRONG_ID(self.state.attempts_left)

        # ---- אימות מול בסיס הנתונים ----
        self.state.auth_attempts += 1  # הגדל מונה לפני הבדיקה
        name = self.state.candidate_member_name
        
        result = db_service.authenticate_member(name, id_number)

        if result.get("verified"):
            # ✅ אימות הצליח!
            self.state.verified = True
            self.state.candidate_member_id = result["member"]["id"]
            self.state.stage = "ANSWERED"
            return self._deliver_answer()

        # ❌ אימות נכשל (מנוי לא נמצא או שם ות.ז לא תואמים)
        if self.state.auth_attempts >= MAX_AUTH_ATTEMPTS:
            # תרחיש חסימה: חצה גבול
            self.state.stage = "BLOCKED"
            return MSG_BLOCKED

        # הלקוח לא נמצא או השם/ת.ז שגויים, מציעים הרשמה ומאפסים
        # שומרים את השם וה-ID לפני האיפוס כדי להעביר ל-Prompt
        offer_msg = generate_response("offer_registration", {"name": name, "id_number": id_number})
        
        # לא מאפסים את כל המצב כדי לשמור על מונה הניסיונות (auth_attempts)
        # נשארים בשלב IDENTIFY_ID כדי שהמשתמש יוכל לנסות שוב ת.ז.
        
        return offer_msg

    def _handle_answered(self, intent: str, nlu: dict, raw: str) -> str:
        """
        שלב ANSWERED: המשתמש אומת בהצלחה.

        Args:
            intent: כוונת המשתמש בשאלה הנוכחית
            nlu   : מידע מחולץ
            raw   : הטקסט הגולמי
        """
        # שאלה כללית → RAG
        if intent == "GENERAL_QUESTION":
            return self._handle_rag(raw)

        # הרשמה לאימון
        if intent == "BOOK_CLASS" or self.state.pending_intent == "BOOK_CLASS":
            date = nlu.get("claimed_date") or self.state.pending_date
            time = nlu.get("claimed_time") or self.state.pending_time
            return self._process_booking(date, time, self.state.candidate_member_name)

        # בירור על תור קיים
        if intent == "APPOINTMENT_INQUIRY":
            return self._deliver_answer()

        return (
            "✅ אתה מאומת! כיצד אוכל עוד לעזור לך?\n"
            "(לשיחה חדשה, כתוב 'התחל מחדש')"
        )

    def _deliver_answer(self) -> str:
        """
        מחזיר ללקוח את נתוני המנוי (אימון קרוב).

        ⚠️ נקרא רק לאחר אימות מוצלח (stage=ANSWERED, verified=True).
        """
        # אם המשתמש רצה להירשם לאימון לפני שהזדהה, נבצע זאת כעת
        if self.state.pending_intent == "BOOK_CLASS":
            return self._process_booking(self.state.pending_date, self.state.pending_time, self.state.candidate_member_name)

        appts_data = db_service.get_member_appointments(self.state.candidate_member_id)
        appointments = appts_data.get("appointments", [])
        name = self.state.candidate_member_name

        if not appointments:
            return generate_response("no_appointments", {"name": name})

        # לוקחים את התור הקרוב ביותר
        next_appt = appointments[0]
        real_date = next_appt["class_date"]
        real_time = next_appt["start_time"]

        return generate_response(
            "subscription_details",
            {
                "name": name,
                "real_date": real_date,
                "real_time": real_time,
            },
        )

    def _handle_rag(self, query: str) -> str:
        """
        RAG_MODE: חיפוש תשובה לשאלה כללית.
        """
        try:
            from rag.retriever import get_relevant_answer
            answer = get_relevant_answer(query)
            if answer:
                return generate_response(
                    "general_answer",
                    {"question": query, "answer": answer},
                )
        except Exception:
            pass  # כשל → fallback

        # Graceful Fallback: לא נמצא → הפנה לסטודיו
        return MSG_FALLBACK

    def _process_booking(self, date: str, time: str, name: str) -> str:
        """
        מטפל בלוגיקת ההרשמה לאימון עבור משתמש מאומת.
        אם חסר תאריך או שעה - שואל את המשתמש.
        אם יש את שניהם - מבצע הרשמה ומחזיר תוצאה.
        """
        if not date or not time:
            # שומרים את מה שיש לנו עד כה
            self.state.pending_intent = "BOOK_CLASS"
            if date:
                self.state.pending_date = date
            if time:
                self.state.pending_time = time
                
            missing = []
            if not date: missing.append("תאריך")
            if not time: missing.append("שעה")
            return f"בשמחה! לאיזה {' ו'.join(missing)} תרצה לקבוע את האימון?"
            
        # יש לנו גם תאריך וגם שעה - נבצע הרשמה
        result = register_member_to_wod(self.state.candidate_member_id, date, time)
        
        # מנקים את הבקשה הממתינה
        self.state.pending_intent = None
        self.state.pending_date = None
        self.state.pending_time = None
        
        if result["success"]:
            return generate_response("booking_success", {"name": name, "date": date, "time": time, "sys_message": result["message"]})
        else:
            return generate_response("booking_failure", {"name": name, "date": date, "time": time, "sys_message": result["message"]})

    # ------------------------------------------------------------------
    # Property נוחות
    # ------------------------------------------------------------------

    @property
    def history(self) -> list:
        """מחזיר את היסטוריית השיחה לתצוגה."""
        return self.state.history
