"""
ממשק משתמש ויזואלי (Streamlit UI) לניהול סטודיו האימונים FitStudio.
הממשק מחובר ישירות לשכבת ה-Services וה-Database שנוצרו בפרויקט.
"""

from datetime import date
import streamlit as st
from database import get_connection, init_db
from services.lead_service import add_lead, convert_lead_to_member
from services.member_service import add_member, get_all_members
from services.wod_service import get_or_create_wod_class, register_member_to_wod
from chatbot.agent import ChatbotAgent

# 1. הגדרת תצורת העמוד ב-Streamlit
st.set_page_config(
    page_title="FitStudio - ניהול אימונים ומנויים",
    page_icon="🏋️‍♂️",
    layout="wide",
)

# סגנון UI מותאם אישית (CSS)
st.markdown("""
<style>
    /* Premium Gym Palette: Dark Charcoal, Vibrant Red (#e63946), Slate (#457b9d), Ice White (#f1faee) */
    
    /* רקע כללי לאפליקציה עם תמונת חדר הכושר (כהה) וזכוכית אקרילית (Glassmorphism) */
    .stApp {
        background-image: linear-gradient(rgba(15, 23, 42, 0.8), rgba(15, 23, 42, 0.85)), url('https://images.unsplash.com/photo-1534438327276-14e5300c3a48?q=80&w=1470&auto=format&fit=crop');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        color: #f1faee;
    }
    
    /* כפתורים כלליים - עיצוב מודרני מבריק */
    div[data-testid="stButton"] button, 
    div[data-testid="stFormSubmitButton"] button,
    div[data-testid="stDownloadButton"] button {
        background: linear-gradient(135deg, #e63946, #c1121f) !important;
        color: white !important;
        border-radius: 8px !important;
        padding: 0.5rem 1rem !important;
        border: none !important;
        box-shadow: 0 4px 15px rgba(230, 57, 70, 0.4) !important;
        transition: all 0.3s ease !important;
        font-weight: 600 !important;
    }
    
    div[data-testid="stButton"] button:hover, 
    div[data-testid="stFormSubmitButton"] button:hover,
    div[data-testid="stDownloadButton"] button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(230, 57, 70, 0.6) !important;
        background: linear-gradient(135deg, #c1121f, #780000) !important;
    }
    
    /* פתרון לכיתוב בתוך כפתורים כך שתמיד יהיה לבן וברור */
    div[data-testid="stButton"] button *, 
    div[data-testid="stFormSubmitButton"] button *,
    div[data-testid="stDownloadButton"] button * {
        color: white !important;
    }
    
    /* מטריקות - תצוגת נתונים (Glassmorphism) */
    div[data-testid="stMetric"] {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
    }
    div[data-testid="stMetric"] label {
        color: #a8dadc !important;
        font-weight: 500;
    }
    div[data-testid="stMetric"] div {
        color: #f1faee !important;
    }
    
    /* עיצוב טפסים (Glassmorphism) */
    div[data-testid="stForm"] {
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 2rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
    }
    
    div[data-testid="stForm"] label, div[data-testid="stForm"] div, div[data-testid="stForm"] p {
        color: #f1faee !important;
    }
    
    /* כותרות ראשיות באפליקציה */
    h1, h2, h3 {
        color: #f1faee !important;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.6);
        font-weight: 700;
    }
    
    /* ====================================================
       כותרות הטאבים
       ==================================================== */
    
    /* הטאבים עצמם */
    div.stTabs button {
        background: rgba(15, 23, 42, 0.5) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-bottom: none !important;
        border-radius: 10px 10px 0 0 !important;
        margin-right: 4px !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.3s ease;
    }
    
    div.stTabs button p {
        font-weight: 600 !important;
        font-size: 1.1rem !important;
        color: #f1faee !important; /* תוספת למניעת טקסט אפור על רקע אפור */
    }

    div.stTabs button:hover {
        background: rgba(30, 41, 59, 0.8) !important;
        color: #ffffff !important;
    }
    
    /* הטאב הפעיל */
    div.stTabs button[aria-selected="true"] {
        background: rgba(230, 57, 70, 0.2) !important;
        border-bottom: 3px solid #e63946 !important;
    }
    
    /* הטקסט בטאב הפעיל */
    div.stTabs button[aria-selected="true"] p,
    div.stTabs button[aria-selected="true"] span,
    div.stTabs button[aria-selected="true"] div {
        color: #e63946 !important;
        text-shadow: 0 0 10px rgba(230, 57, 70, 0.5) !important;
    }

</style>
""", unsafe_allow_html=True)

# אתחול בסיס הנתונים בעת טעינת האפליקציה
init_db()

st.title("🏋️‍♂️ FitStudio - מערכת ניהול אימונים, מנויים ולידים")

# 2. חלוקת הממשק לטאבים לפי תהליכים
tab1, tab2, tab3, tab4 = st.tabs(
    ["📅 יומן אימונים ושריון תור", "👤 קליטת לקוח חדש / מנויים", "🎯 ניהול לידים", "💬 צ'אטבוט חכם"]
)


# =========================================================
# טאב 1: יומן אימונים ושריון תור
# =========================================================
with tab1:
    st.header("לוח אימונים זמין ושריון מקום")

    col_date, col_space = st.columns([1, 2])

    with col_date:
        selected_date = st.date_input("בחר תאריך לצפייה ביומן", value=date.today())
        date_str = selected_date.strftime("%Y-%m-%d")

    # בדיקת יום בשבוע (א'-ה': ראשון עד חמישי)
    weekday = selected_date.weekday()
    is_weekday = weekday in [6, 0, 1, 2, 3]

    slots = (
        ["06:00", "07:00", "08:00", "16:00", "17:00", "18:00", "19:00", "20:00"]
        if is_weekday
        else ["08:00", "09:00", "10:00", "11:00"]
    )

    st.subheader(f"תפוסת אימונים לתאריך: {date_str}")

    # הצגת כרטיסיות תפוסה לכל אימון WOD
    grid_cols = st.columns(4)
    with get_connection() as conn:
        cursor = conn.cursor()
        for idx, slot in enumerate(slots):
            wod_id = get_or_create_wod_class(date_str, slot)
            cursor.execute(
                "SELECT COUNT(*) as count FROM wod_registrations WHERE wod_class_id = ? AND status = 'REGISTERED'",
                (wod_id,),
            )
            count = cursor.fetchone()["count"]
            spots_left = 18 - count

            with grid_cols[idx % 4]:
                st.metric(
                    label=f"אימון {slot}",
                    value=f"{count}/18 רשומים",
                    delta=f"{spots_left} מקומות פנויים",
                    delta_color="normal" if spots_left > 0 else "off",
                )

    st.markdown("---")
    st.subheader("שריון מקום לאימון")

    members = get_all_members()
    active_members = [m for m in members if m["is_active"]]

    if not active_members:
        st.warning("אין מנויים פעילים במערכת. יש להזין מנוי חדש בטאב לקוחות.")
    else:
        member_options = {
            f"{m['name']} ({m['phone']}) - ID: {m['id']}": m["id"]
            for m in active_members
        }

        with st.form("booking_form"):
            selected_member = st.selectbox("בחר מנוי", list(member_options.keys()))
            selected_slot = st.selectbox("בחר שעת אימון", slots)

            submit_booking = st.form_submit_button("שריון מקום באימון 🏋️")

            if submit_booking:
                m_id = member_options[selected_member]
                res = register_member_to_wod(m_id, date_str, selected_slot)
                if res["success"]:
                    st.success(res["message"])
                    st.rerun()
                else:
                    st.error(res["message"])


# =========================================================
# טאב 2: קליטת לקוח חדש / מנויים
# =========================================================
with tab2:
    st.header("קליטת לקוח חדש למועדון")

    col_add, col_list = st.columns([1, 1])

    with col_add:
        st.subheader("הרשמת מנוי חדש")
        with st.form("add_member_form"):
            m_name = st.text_input("שם מלא")
            m_phone = st.text_input("מספר טלפון")
            m_email = st.text_input("אימייל (אופציונלי)")

            submit_m = st.form_submit_button("הוסף מנוי חדש ➕")
            if submit_m:
                if not m_name or not m_phone:
                    st.error("יש למלא שם וטלפון.")
                else:
                    res = add_member(m_name, m_phone, m_email)
                    if res["success"]:
                        st.success(res["message"])
                        st.rerun()
                    else:
                        st.error(res["message"])

    with col_list:
        st.subheader("רשימת מנויים קיימים במועדון")
        members_list = get_all_members()
        if members_list:
            st.dataframe(members_list)
        else:
            st.info("אין מנויים רשומים במערכת עדיין.")


# =========================================================
# טאב 3: ניהול לידים
# =========================================================
with tab3:
    st.header("קליטת מתעניינים (לידים)")

    col_l_add, col_l_convert = st.columns([1, 1])

    with col_l_add:
        st.subheader("הזנת ליד חדש")
        with st.form("add_lead_form"):
            l_name = st.text_input("שם מלא")
            l_phone = st.text_input("מספר טלפון")
            l_source = st.selectbox(
                "מקור פנייה",
                ["פייסבוק", "אינסטגרם", "חבר מביא חבר", "שלט/רחוב", "אחר"],
            )
            l_notes = st.text_area("הערות")

            submit_l = st.form_submit_button("שמור ליד חדש 🎯")
            if submit_l:
                if not l_name or not l_phone:
                    st.error("יש למלא שם וטלפון.")
                else:
                    res = add_lead(l_name, l_phone, l_source, l_notes)
                    if res["success"]:
                        st.success(res["message"])
                        st.rerun()
                    else:
                        st.error(res["message"])

    with col_l_convert:
        st.subheader("המרת ליד למנוי פעיל במועדון")

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM leads WHERE status != 'CONVERTED'")
            unconverted = [dict(row) for row in cursor.fetchall()]

        if unconverted:
            lead_options = {
                f"{l['name']} ({l['phone']}) - מקור: {l['source']}": l["id"]
                for l in unconverted
            }

            with st.form("convert_lead_form"):
                selected_lead = st.selectbox("בחר ליד להמרה", list(lead_options.keys()))
                c_email = st.text_input("אימייל למנוי החדש (אופציונלי)")

                submit_c = st.form_submit_button("המר למנוי פעיל ✨")
                if submit_c:
                    l_id = lead_options[selected_lead]
                    res = convert_lead_to_member(l_id, c_email)
                    if res["success"]:
                        st.success(res["message"])
                        st.rerun()
                    else:
                        st.error(res["message"])
        else:
            st.info("אין לידים הממתינים להמרה.")


# =========================================================
# טאב 4: צ'אטבוט חכם
# =========================================================
with tab4:
    st.header("💬 צ'אטבוט FitStudio — שאל אותי הכל!")
    st.caption("זהה תור, בדוק פרטים, שאל שאלות כלליות — הכל בשפה טבעית.")

    # --- CSS לבועות צ'אט ---
    st.markdown("""
    <style>
    .chat-container { display: flex; flex-direction: column; gap: 12px; }
    .chat-bubble {
        max-width: 75%;
        padding: 12px 16px;
        border-radius: 18px;
        font-size: 15px;
        line-height: 1.5;
        word-wrap: break-word;
    }
    .user-bubble {
        background: linear-gradient(135deg, #ff4b4b, #ff7676);
        color: white;
        align-self: flex-end;
        margin-left: auto;
        border-bottom-right-radius: 4px;
    }
    .bot-bubble {
        background: rgba(255,255,255,0.85);
        color: #2c3e50;
        align-self: flex-start;
        border-bottom-left-radius: 4px;
        border: 1px solid rgba(0,0,0,0.08);
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    .chat-wrapper { display: flex; flex-direction: column; }
    .user-wrap { align-items: flex-end; }
    .bot-wrap  { align-items: flex-start; }
    .chat-label { font-size: 11px; color: #888; margin-bottom: 3px; }
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 600;
    }
    .status-green { background: #d4edda; color: #155724; }
    .status-yellow { background: #fff3cd; color: #856404; }
    .status-red { background: #f8d7da; color: #721c24; }
    </style>
    """, unsafe_allow_html=True)

    # --- אתחול Session State ---
    if "chatbot_agent" not in st.session_state:
        st.session_state.chatbot_agent = ChatbotAgent()
        # הודעת פתיחה
        welcome = (
            "שלום! אני הבוט של FitStudio 🏋️\n"
            "אני יכול לעזור לך לבדוק פרטי תור, שעות הסטודיו ועוד.\n"
            "ספר לי — מה שמך ומה תרצה לדעת?"
        )
        st.session_state.chatbot_agent.state.add_message("bot", welcome)
        st.session_state.chatbot_agent.state.stage = "IDENTIFY_NAME"

    agent: ChatbotAgent = st.session_state.chatbot_agent

    # --- פס מצב עליון ---
    col_status, col_reset = st.columns([3, 1])
    with col_status:
        stage = agent.state.stage
        if stage == "ANSWERED":
            st.markdown('<span class="status-badge status-green">🔓 מאומת — פרטים זמינים</span>', unsafe_allow_html=True)
        elif stage == "BLOCKED":
            st.markdown('<span class="status-badge status-red">🔒 שיחה חסומה</span>', unsafe_allow_html=True)
        elif stage == "IDENTIFY_ID":
            st.markdown('<span class="status-badge status-yellow">🔐 ממתין לאימות זהות</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="status-badge status-yellow">💬 שיחה פעילה</span>', unsafe_allow_html=True)

    with col_reset:
        if st.button("🔄 התחל מחדש", key="chat_reset"):
            st.session_state.chatbot_agent = ChatbotAgent()
            welcome = (
                "שיחה חדשה! אני הבוט של FitStudio 🏋️\n"
                "במה אוכל לעזור לך?"
            )
            st.session_state.chatbot_agent.state.add_message("bot", welcome)
            st.session_state.chatbot_agent.state.stage = "IDENTIFY_NAME"
            st.rerun()

    st.markdown("---")

    # --- הצגת היסטוריית שיחה ---
    history = agent.history
    if history:
        chat_html = '<div class="chat-container">'
        for msg in history:
            role = msg["role"]
            content = msg["content"].replace("\n", "<br>")
            if role == "user":
                chat_html += f'''
                <div class="chat-wrapper user-wrap">
                    <div class="chat-label">אתה</div>
                    <div class="chat-bubble user-bubble">{content}</div>
                </div>'''
            else:
                chat_html += f'''
                <div class="chat-wrapper bot-wrap">
                    <div class="chat-label">🤖 FitBot</div>
                    <div class="chat-bubble bot-bubble">{content}</div>
                </div>'''
        chat_html += '</div>'
        st.markdown(chat_html, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- קלט משתמש ---
    if not agent.state.is_blocked:
        with st.form("chat_form", clear_on_submit=True):
            col_input, col_send = st.columns([5, 1])
            with col_input:
                user_input = st.text_input(
                    "הודעה",
                    placeholder="כתוב הודעה... (לדוגמה: 'קוראים לי רותם ויש לי תור ב-19.08.2026')",
                    label_visibility="collapsed",
                    key="chat_input",
                )
            with col_send:
                send = st.form_submit_button("שלח ➤")

            if send and user_input.strip():
                with st.spinner("FitBot מקליד..."):
                    agent.process_message(user_input.strip())
                st.rerun()
    else:
        st.error("השיחה חסומה לאחר מספר ניסיונות כושלים. לחץ 'התחל מחדש' לשיחה חדשה.")

    # --- טיפים בסרגל צד ---
    with st.expander("💡 דוגמאות לשאלות"):
        st.markdown("""
        **בדיקת תור:**
        - *"קוראים לי רותם ויש לי תור ב-19.08.2026"*
        - *"שמי ניר לוי, רוצה לבדוק את התור שלי"*

        **שאלות כלליות:**
        - *"מה שעות הפעילות?"*
        - *"כמה עולה מנוי חודשי?"*
        - *"מה קורה אם לא הגעתי לאימון?"*
        """)