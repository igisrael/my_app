"""
=============================================================
flask_app.py — אפליקציית Web ל-PythonAnywhere
=============================================================

מטרה:
    PythonAnywhere חינמי אינו תומך בהרצת Streamlit או FastAPI
    כשרתים נפרדים שמדברים זה עם זה דרך localhost.
    הוא תומך רק באפליקציית WSGI אחת (Flask או Django).

    קובץ זה מספק ממשק משתמש (HTML+JS) פשוט ויפה
    שתקשר ישירות ללוגיקת ה-Agent של הצ'אטבוט שלנו
    (שבתורו פונה ל-SQLite דרך db_service).

הגדרת WSGI ב-PythonAnywhere:
    import sys
    path = '/home/yourusername/fitstudio'
    if path not in sys.path:
        sys.path.append(path)
    from flask_app import app as application
"""

from flask import Flask, render_template, request, jsonify, session
import os
from database import init_db
from chatbot.agent import ChatbotAgent
import pickle
import base64

# יצירת מופע Flask
app = Flask(__name__)
# סוד חזק לצורך חתימת קובצי ה-Cookies של ה-session
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super-secret-fitstudio-key-2026")

# אתחול בסיס הנתונים (יוצר טבלאות אם חסרות)
init_db()


def get_agent_from_session() -> ChatbotAgent:
    """
    שולף את מצב הצ'אטבוט מה-session של Flask.
    אם אין, יוצר חדש עם הודעת GREETING.
    """
    agent_data = session.get("agent_state")
    if agent_data:
        try:
            agent = pickle.loads(base64.b64decode(agent_data))
            return agent
        except Exception as e:
            print("Error loading session:", e)

    # אם לא קיים או שגיאה בטעינה, יוצר חדש
    agent = ChatbotAgent()
    welcome = (
        "שלום! אני הבוט של FitStudio 🏋️\n"
        "אני יכול לעזור לך לבדוק פרטי תור, שעות הסטודיו ועוד.\n"
        "ספר לי — מה שמך ומה תרצה לדעת?"
    )
    agent.state.add_message("bot", welcome)
    agent.state.stage = "IDENTIFY_NAME"
    return agent


def save_agent_to_session(agent: ChatbotAgent):
    """שומר את מצב הבוט בחזרה ל-session (כ-base64)."""
    session["agent_state"] = base64.b64encode(pickle.dumps(agent)).decode('utf-8')


@app.route("/")
def home():
    """
    נקודת הכניסה הראשית.
    מרנדרת את ממשק הצ'אטבוט מתוך תבנית HTML.
    """
    agent = get_agent_from_session()
    save_agent_to_session(agent)
    return render_template("chat.html", history=agent.history, stage=agent.state.stage)


@app.route("/chat", methods=["POST"])
def chat():
    """
    נקודת קצה ל-API שאליה ה-JavaScript פונה (AJAX).
    מקבלת טקסט, מעבירה ל-agent, ומחזירה את התשובה.
    """
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "No message provided"}), 400

    user_message = data["message"]
    
    agent = get_agent_from_session()
    
    # עיבוד ההודעה (מפעיל NLU + DB וכו')
    bot_response = agent.process_message(user_message)
    
    # שמירת המצב המעודכן ל-session
    save_agent_to_session(agent)

    return jsonify({
        "response": bot_response,
        "stage": agent.state.stage,
        "is_blocked": agent.state.is_blocked
    })


@app.route("/reset", methods=["POST"])
def reset():
    """
    מאפס את השיחה ומוחק את ה-session.
    """
    session.pop("agent_state", None)
    return jsonify({"success": True})


if __name__ == "__main__":
    # הרצה מקומית בלבד (ב-PythonAnywhere זה רץ דרך שרת WSGI)
    app.run(debug=True, port=5000)
