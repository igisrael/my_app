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

# 1. הגדרת תצורת העמוד ב-Streamlit
st.set_page_config(
    page_title="FitStudio - ניהול אימונים ומנויים",
    page_icon="🏋️‍♂️",
    layout="wide",
)

# סגנון UI מותאם אישית (CSS)
st.markdown("""
<style>
    /* רקע כללי לאפליקציה (בהיר) */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa, #c3cfe2);
        color: #2c3e50;
    }
    
    /* עיצוב כפתורים */
    div[data-testid="stButton"] button, div[data-testid="stFormSubmitButton"] button {
        background: linear-gradient(90deg, #ff4b4b, #ff7676);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 10px rgba(255, 75, 75, 0.2);
    }
    
    div[data-testid="stButton"] button:hover, div[data-testid="stFormSubmitButton"] button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 15px rgba(255, 75, 75, 0.4);
    }
    
    /* עיצוב ה-KPIs (st.metric) */
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.8);
        border: 1px solid rgba(0, 0, 0, 0.05);
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
        backdrop-filter: blur(10px);
        transition: transform 0.3s ease;
    }
    
    div[data-testid="stMetric"]:hover {
        transform: translateY(-5px);
        border-color: rgba(255, 75, 75, 0.4);
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
    }
    
    /* עיצוב טפסים */
    div[data-testid="stForm"] {
        background: rgba(255, 255, 255, 0.6);
        border: 1px solid rgba(0, 0, 0, 0.05);
        border-radius: 12px;
        padding: 1.5rem;
    }
    
    /* כותרות וטקסטים */
    h1, h2, h3 {
        color: #1a202c !important;
    }
    
    /* טאבים */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background: rgba(0, 0, 0, 0.03);
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(255, 75, 75, 0.1) !important;
        border-bottom: 2px solid #ff4b4b !important;
        color: #ff4b4b !important;
    }
</style>
""", unsafe_allow_html=True)

# אתחול בסיס הנתונים בעת טעינת האפליקציה
init_db()

st.title("🏋️‍♂️ FitStudio - מערכת ניהול אימונים, מנויים ולידים")

# 2. חלוקת הממשק לטאבים לפי תהליכים
tab1, tab2, tab3 = st.tabs(
    ["📅 יומן אימונים ושריון תור", "👤 קליטת לקוח חדש / מנויים", "🎯 ניהול לידים"]
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