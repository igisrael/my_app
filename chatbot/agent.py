"""
chatbot/agent.py — הלוגיקה המרכזית של הצ'אטבוט FitStudio.

State Machine עם 7 שלבים:
  GREETING  → IDENTIFY → CLARIFY → VERIFY → ANSWERED
                                          ↓
                                        BLOCKED (אחרי 3 כשלונות)
  כל שלב יכול → RAG_MODE (שאלות כלליות)

כלל אבטחה קשיח: לפני ANSWERED אסור לחשוף שום פרט אישי.
"""

import httpx
from chatbot.state import ConversationState, MAX_AUTH_ATTEMPTS
from chatbot.nlu import extract_intent, generate_response

API_BASE = "http://localhost:8000"

# ===================================================================
# Helper: קריאות ל-REST API הפנימי
# ===================================================================

def _search_members(name: str) -> dict:
    """חיפוש מנוי לפי שם חלקי."""
    try:
        r = httpx.get(f"{API_BASE}/members/search", params={"name": name}, timeout=5)
        return r.json()
    except Exception:
        return {"count": 0, "results": []}


def _get_appointments(member_id: int) -> dict:
    """שליפת תורים של מנוי."""
    try:
        r = httpx.get(
            f"{API_BASE}/members/{member_id}/appointments",
            params={"status": "REGISTERED"},
            timeout=5,
        )
        return r.json()
    except Exception:
        return {"count": 0, "appointments": []}


def _verify_identity(member_id: int, id_number: str) -> dict:
    """אימות תעודת זהות מול ה-API."""
    try:
        r = httpx.post(
            f"{API_BASE}/members/{member_id}/verify-identity",
            json={"id_number": id_number},
            timeout=5,
        )
        return r.json()
    except Exception:
        return {"verified": False, "message": "שגיאת תקשורת עם השרת."}


# ===================================================================
# Helper: הודעות קבועות (Static Responses)
# ===================================================================

MSG_GREETING = (
    "שלום! אני הבוט של FitStudio 🏋️\n"
    "אני יכול לעזור לך לבדוק פרטי תור, שעות הסטודיו ועוד.\n"
    "ספר לי — מה שמך ומה תרצה לדעת?"
)

MSG_ASK_NAME = "מה שמך? (יש להזין שם פרטי לפחות)"

MSG_NOT_FOUND = lambda name: (
    f"לא מצאתי מנוי בשם \"{name}\" במערכת.\n"
    "ייתכן שהשם אינו תואם בדיוק. נסה שם אחר, או פנה אלינו ישירות."
)

MSG_CLARIFY = lambda candidates: (
    "מצאתי כמה מנויים עם שם דומה. מי מביניהם אתה?\n"
    + "\n".join(f"  {i+1}. {c['name']} ({c['phone'][-4:].rjust(10,'*')})"
                for i, c in enumerate(candidates))
    + "\nאנא ציין שם מלא."
)

MSG_ASK_ID = lambda name, attempts_left: (
    f"זיהיתי אותך כ-{name}.\n"
    f"לאימות זהות, אנא הזן את מספר תעודת הזהות שלך. "
    f"(נותרו {attempts_left} ניסיונות)"
)

MSG_WRONG_ID = lambda attempts_left: (
    f"תעודת הזהות שגויה. אנא נסה שנית.\n"
    f"{'נותר ניסיון אחד בלבד!' if attempts_left == 1 else f'נותרו {attempts_left} ניסיונות.'}"
)

MSG_BLOCKED = (
    "חרגת ממגבלת ניסיונות האימות המותרת.\n"
    "לביטחון פרטיך, השיחה נחסמת. אנא פנה אלינו ישירות.\n"
    "📞 לחצ/י 'התחל מחדש' לשיחה חדשה."
)

MSG_RESET = "השיחה אופסה. שלום! כיצד אוכל לעזור?"


# ===================================================================
# ChatbotAgent — הלוגיקה המרכזית
# ===================================================================

class ChatbotAgent:
    """
    מנהל שיחה מול המשתמש.
    יש ליצור instance אחד לכל session משתמש ולשמור ב-st.session_state.
    """

    def __init__(self):
        self.state = ConversationState()

    def process_message(self, user_message: str) -> str:
        """
        מקבל הודעת משתמש ומחזיר תשובת בוט.
        זוהי נקודת הכניסה היחידה — כל ההיגיון עובר דרך כאן.
        """
        user_message = user_message.strip()
        self.state.add_message("user", user_message)

        # ---- שיחה חסומה ----
        if self.state.is_blocked:
            response = MSG_BLOCKED
            self.state.add_message("bot", response)
            return response

        # ---- NLU: חילוץ intent ----
        nlu = extract_intent(user_message)
        intent = nlu.get("intent", "OTHER")

        # ---- איפוס שיחה ----
        if intent == "RESET" or "התחל מחדש" in user_message or "חדש" == user_message.lower():
            self.state.reset()
            self.state.add_message("bot", MSG_RESET)
            return MSG_RESET

        # ---- ניתוב לפי שלב ----
        response = self._route(intent, nlu, user_message)
        self.state.add_message("bot", response)
        return response

    def _route(self, intent: str, nlu: dict, raw: str) -> str:
        """מנתב לפי שלב השיחה הנוכחי."""
        stage = self.state.stage

        # ---- שלב GREETING ----
        if stage == "GREETING":
            if intent == "GREETING":
                self.state.stage = "IDENTIFY"
                return MSG_GREETING
            # כל פנייה ראשונה — נעבור ל-IDENTIFY
            self.state.stage = "IDENTIFY"
            return self._handle_identify(intent, nlu, raw)

        # ---- שלב IDENTIFY ----
        if stage == "IDENTIFY":
            return self._handle_identify(intent, nlu, raw)

        # ---- שלב CLARIFY ----
        if stage == "CLARIFY":
            return self._handle_clarify(nlu, raw)

        # ---- שלב VERIFY ----
        if stage == "VERIFY":
            return self._handle_verify(intent, nlu, raw)

        # ---- שלב ANSWERED ----
        if stage == "ANSWERED":
            return self._handle_answered(intent, nlu, raw)

        # ---- שאלות כלליות (RAG) ----
        if stage == "RAG_MODE":
            return self._handle_rag(raw)

        return "מצטערים, אירעה שגיאה פנימית. נסה שוב."

    # ------------------------------------------------------------------
    # Handlers לכל שלב
    # ------------------------------------------------------------------

    def _handle_identify(self, intent: str, nlu: dict, raw: str) -> str:
        """שלב זיהוי לקוח לפי שם."""

        # שאלה כללית — עבור למצב RAG
        if intent == "GENERAL_QUESTION":
            self.state.stage = "RAG_MODE"
            return self._handle_rag(raw)

        name = nlu.get("name")
        if not name:
            # שמור תביעות לתאריך אם הוזן
            if nlu.get("claimed_date"):
                self.state.claimed_date = nlu["claimed_date"]
            if nlu.get("claimed_time"):
                self.state.claimed_time = nlu["claimed_time"]
            self.state.stage = "IDENTIFY"
            return MSG_ASK_NAME

        # שמור תביעות
        if nlu.get("claimed_date"):
            self.state.claimed_date = nlu["claimed_date"]

        # חיפוש ב-API
        result = _search_members(name)
        count = result.get("count", 0)
        candidates = result.get("results", [])

        if count == 0:
            return generate_response("not_found", {"name": name})

        if count == 1:
            # מנוי ייחודי — עבור לאימות
            m = candidates[0]
            self.state.candidate_member_id = m["id"]
            self.state.candidate_member_name = m["name"]
            self.state.stage = "VERIFY"
            return MSG_ASK_ID(m["name"], self.state.attempts_left)

        # כמה תוצאות — צריך הבהרה
        self.state.multiple_candidates = candidates
        self.state.stage = "CLARIFY"
        return MSG_CLARIFY(candidates)

    def _handle_clarify(self, nlu: dict, raw: str) -> str:
        """שלב הבהרה — בחירה מבין מספר מנויים עם שם דומה."""
        name = nlu.get("name") or raw.strip()

        # חיפוש מדויק יותר בין המועמדים
        for c in self.state.multiple_candidates:
            if name.strip() in c["name"] or c["name"] in name.strip():
                self.state.candidate_member_id = c["id"]
                self.state.candidate_member_name = c["name"]
                self.state.multiple_candidates = []
                self.state.stage = "VERIFY"
                return MSG_ASK_ID(c["name"], self.state.attempts_left)

        # לא זיהינו — שאל שוב
        return (
            "לא הצלחתי להתאים את השם שציינת. אנא ציין שם מלא (שם פרטי ומשפחה).\n"
            + "\n".join(f"  - {c['name']}" for c in self.state.multiple_candidates)
        )

    def _handle_verify(self, intent: str, nlu: dict, raw: str) -> str:
        """שלב אימות תעודת זהות."""

        # שאלה כללית בזמן שממתינים לת.ז.
        if intent == "GENERAL_QUESTION":
            self.state.stage = "RAG_MODE"
            return self._handle_rag(raw)

        # חילוץ ת.ז. מהנ-NLU או מהטקסט הגולמי
        id_number = nlu.get("id_number")
        if not id_number:
            # ניסיון לחלץ ת.ז. מהטקסט ישירות (7-9 ספרות)
            import re
            match = re.search(r'\b\d{7,9}\b', raw)
            if match:
                id_number = match.group()

        if not id_number:
            return (
                f"אנא הזן את מספר תעודת הזהות שלך (7-9 ספרות).\n"
                f"נותרו {self.state.attempts_left} ניסיונות."
            )

        # אימות מול ה-API
        self.state.auth_attempts += 1
        result = _verify_identity(self.state.candidate_member_id, id_number)

        if result.get("verified"):
            self.state.verified = True
            self.state.stage = "ANSWERED"
            return self._deliver_answer()

        # אימות נכשל
        if self.state.auth_attempts >= MAX_AUTH_ATTEMPTS:
            self.state.stage = "BLOCKED"
            return MSG_BLOCKED

        return MSG_WRONG_ID(self.state.attempts_left)

    def _handle_answered(self, intent: str, nlu: dict, raw: str) -> str:
        """שלב לאחר אימות — ניתן לחשוף פרטים. ממשיך לענות על שאלות."""
        if intent == "GENERAL_QUESTION":
            return self._handle_rag(raw)
        # עדכון תביעות אם המשתמש שואל שאלה חדשה על תור
        if nlu.get("claimed_date"):
            self.state.claimed_date = nlu["claimed_date"]
            return self._deliver_answer()
        return "כיצד אוכל לעוד לעזור לך? (לשיחה חדשה כתוב 'התחל מחדש')"

    def _deliver_answer(self) -> str:
        """
        שליפת תורים אמיתיים לאחר אימות מוצלח והשוואה לתביעת המשתמש.
        זהו ה'לב' של התרחיש המרכזי.
        """
        appts = _get_appointments(self.state.candidate_member_id)
        appointments = appts.get("appointments", [])
        name = self.state.candidate_member_name

        if not appointments:
            return generate_response("no_appointments", {"name": name})

        # נקח את התור הקרוב ביותר (ראשון ברשימה)
        next_appt = appointments[0]
        real_date = next_appt["class_date"]
        real_time = next_appt["start_time"]
        claimed_date = self.state.claimed_date

        if claimed_date and claimed_date != real_date:
            # ← התרחיש המרכזי: המשתמש טעה בתאריך!
            return generate_response(
                "appointment_correction",
                {
                    "name": name,
                    "claimed_date": claimed_date,
                    "real_date": real_date,
                    "real_time": real_time,
                },
            )
        else:
            return generate_response(
                "appointment_correct",
                {
                    "name": name,
                    "claimed_date": claimed_date or real_date,
                    "real_date": real_date,
                    "real_time": real_time,
                },
            )

    def _handle_rag(self, query: str) -> str:
        """
        שאלות כלליות — מנסה RAG ואם לא נמצא, Fallback מנומס.
        מיובא כאן ב-lazy import למניעת circular imports.
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
            pass

        # Graceful Fallback
        return (
            "לא מצאתי מידע ספציפי על שאלתך במאגר הידע שלי.\n"
            "אנא פנה אלינו ישירות:\n"
            "📞 טלפון: 050-0000000\n"
            "🏠 כתובת: רחוב הספורט 1, תל אביב"
        )

    @property
    def history(self):
        return self.state.history
