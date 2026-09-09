"""
=============================================================
chatbot/state.py — State Machine לניהול מצב שיחה
=============================================================

מטרה:
    מחלקה זו מייצגת את "הזיכרון" של הצ'אטבוט בין הודעה להודעה.
    ב-Streamlit, היא נשמרת ב-st.session_state.
    ב-Flask, היא נשמרת ב-flask.session (או בזיכרון).

    בלי state management, הבוט היה שוכח את שם המשתמש,
    את שלב האימות, ואת מספר הניסיונות הכושלים.

שלבי שיחה (Stages):
    GREETING      → ברכה ראשונית, בקשת שם מלא
    IDENTIFY_NAME → המתנה לשם מלא מהמשתמש
    IDENTIFY_ID   → המתנה לתעודת זהות לאימות (לאחר קבלת שם)
    ANSWERED      → אימות הצליח (שם+ת.ז תואמים), חשיפת פרטי מנוי
    BLOCKED       → חצה מגבלת 3 ניסיונות אימות
    RAG_MODE      → שאלה כללית (שעות, מחירים) — לא שאילתת תור

מגבלת אבטחה:
    MAX_AUTH_ATTEMPTS = 3 (לפי האיפיון)
    לאחר 3 כשלונות → stage = BLOCKED → אסור לחשוף מידע
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict

# ===========================================================
# קבוע: מספר ניסיונות אימות מקסימלי (לפי האיפיון)
# ===========================================================
MAX_AUTH_ATTEMPTS = 3


@dataclass
class ConversationState:
    """
    מייצג את מצב השיחה המלא בין הבוט למשתמש.

    משמש כ-"זיכרון" בין הודעות:
    - מי הלקוח המועמד (לפני אימות)
    - מה שלב השיחה הנוכחי
    - כמה ניסיונות אימות נוצלו
    - מה המשתמש טען (תאריך/שעה)
    - היסטוריית ההודעות להצגה

    שימוש:
        state = ConversationState()
        state.stage = "VERIFY"
        state.add_message("user", "123456789")
    """

    # ---- שלב השיחה הנוכחי ----
    stage: str = "GREETING"

    # ---- מידע על הלקוח שזוהה (לפני אימות מלא) ----
    candidate_member_id: Optional[int] = None      # ID בטבלת members
    candidate_member_name: Optional[str] = None    # שם מלא לתצוגה

    # ---- תביעות המשתמש (מה הוא אמר שיש לו) ----
    claimed_date: Optional[str] = None   # תאריך שהמשתמש טען (YYYY-MM-DD)
    claimed_time: Optional[str] = None   # שעה שהמשתמש טען (HH:MM)

    # ---- פעולות ממתינות (למשל הרשמה לאימון לפני אימות) ----
    pending_intent: Optional[str] = None
    pending_date: Optional[str] = None
    pending_time: Optional[str] = None

    # ---- אימות זהות ----
    verified: bool = False       # True = אומת בהצלחה, מותר לחשוף פרטים
    auth_attempts: int = 0       # מונה ניסיונות אימות

    # ---- היסטוריית שיחה לתצוגה (רשימת {"role": ..., "content": ...}) ----
    history: List[Dict] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Methods
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """
        מאפס את כל מצב השיחה — מחזיר ל-GREETING.

        נקרא כאשר המשתמש כותב "התחל מחדש" או לוחץ כפתור reset.
        לא מנקה את history (הצגה היסטורית נשמרת).
        """
        self.stage = "GREETING"
        self.candidate_member_id = None
        self.candidate_member_name = None
        self.claimed_date = None
        self.claimed_time = None
        self.pending_intent = None
        self.pending_date = None
        self.pending_time = None
        self.verified = False
        self.auth_attempts = 0

    def add_message(self, role: str, content: str) -> None:
        """
        מוסיף הודעה להיסטוריית השיחה.

        Args:
            role    : "user" (המשתמש) או "bot" (הבוט)
            content : תוכן ההודעה
        """
        self.history.append({"role": role, "content": content})

    @property
    def is_blocked(self) -> bool:
        """
        Property: בודק אם השיחה חסומה.

        Returns:
            True אם המשתמש חצה את מגבלת ניסיונות האימות
        """
        return self.stage == "BLOCKED"

    @property
    def is_verified(self) -> bool:
        """
        Property: בודק אם המשתמש אומת בהצלחה.

        Returns:
            True רק אם גם verified=True וגם stage="ANSWERED"
        """
        return self.verified and self.stage == "ANSWERED"

    @property
    def attempts_left(self) -> int:
        """
        Property: כמה ניסיונות אימות נותרו.

        Returns:
            מספר שלם בין 0 ל-MAX_AUTH_ATTEMPTS
        """
        return MAX_AUTH_ATTEMPTS - self.auth_attempts
