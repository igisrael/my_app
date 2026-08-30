"""
chatbot/state.py — ניהול מצב שיחה (State Machine) לצ'אטבוט FitStudio.

מחזיק את כל מה שהצ'אטבוט צריך לזכור בין הודעה להודעה:
- מי הלקוח המועמד
- באיזה שלב השיחה נמצאת
- כמה ניסיונות אימות בוצעו

Stages (שלבי שיחה):
  GREETING    - ברכה / תחילת שיחה
  IDENTIFY    - מחפש לקוח לפי שם
  CLARIFY     - מבקש הבהרה (כמה תוצאות עם אותו שם)
  VERIFY      - מבקש תעודת זהות
  ANSWERED    - אומת בהצלחה, ניתן לחשוף פרטים
  BLOCKED     - חצה מגבלת ניסיונות, שיחה נחסמת
  RAG_MODE    - שאלה כללית (לא על תור ספציפי)
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict

MAX_AUTH_ATTEMPTS = 3  # מגבלת ניסיונות אימות לפי האיפיון


@dataclass
class ConversationState:
    """מייצג את מצב השיחה הנוכחית."""

    # שלב נוכחי
    stage: str = "GREETING"

    # מידע על הלקוח המועמד (לפני אימות)
    candidate_member_id: Optional[int] = None
    candidate_member_name: Optional[str] = None

    # תביעות המשתמש (מה הוא אמר)
    claimed_date: Optional[str] = None
    claimed_time: Optional[str] = None

    # אימות
    verified: bool = False
    auth_attempts: int = 0

    # רשימת מועמדים אם יש כמה תוצאות לשם
    multiple_candidates: List[Dict] = field(default_factory=list)

    # היסטוריית שיחה (לDisplay)
    history: List[Dict] = field(default_factory=list)

    def reset(self):
        """איפוס מוחלט של השיחה — מתחיל מחדש."""
        self.stage = "GREETING"
        self.candidate_member_id = None
        self.candidate_member_name = None
        self.claimed_date = None
        self.claimed_time = None
        self.verified = False
        self.auth_attempts = 0
        self.multiple_candidates = []

    def add_message(self, role: str, content: str):
        """הוספת הודעה להיסטוריה. role: 'user' | 'bot'"""
        self.history.append({"role": role, "content": content})

    @property
    def is_blocked(self) -> bool:
        return self.stage == "BLOCKED"

    @property
    def is_verified(self) -> bool:
        return self.verified and self.stage == "ANSWERED"

    @property
    def attempts_left(self) -> int:
        return MAX_AUTH_ATTEMPTS - self.auth_attempts
