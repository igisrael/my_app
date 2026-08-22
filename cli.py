"""
קובץ ההרצה הראשי (Main Entry Point).
מציג ממשק משתמש טקסטואלי (CLI) בטרמינל עבור VS Code.
"""

import sys
from database import init_db
from services.member_service import add_member, get_all_members
from services.lead_service import add_lead, convert_lead_to_member
from services.wod_service import register_member_to_wod

def print_menu():
    """
    מציג את תפריט האפשרויות הראשי.
    """
    print("\n" + "="*40)
    print("   מערכת לניהול WODs ולידים - FitStudio")
    print("="*40)
    print("1. הוספת מנוי חדש")
    print("2. הצגת כל המנויים")
    print("3. הוספת ליד חדש")
    print("4. המרת ליד למנוי")
    print("5. הרשמת מנוי לאימון WOD")
    print("6. יציאה")
    print("="*40)

def main():
    """
    לולאת התוכנית הראשית.
    """
    init_db() # אתחול בסיס הנתונים בהרצה הראשונה
    while True:
        print_menu()
        choice = input("בחר אפשרות (1-6): ").strip()

        if choice == "1":
            name = input("שם המנוי: ")
            phone = input("טלפון: ")
            email = input("אימייל (אופציונלי): ")
            res = add_member(name, phone, email)
            print(f"\nתוצאה: {res['message']}")

        elif choice == "2":
            members = get_all_members()
            print("\n--- רשימת מנויים ---")
            for m in members:
                status = "פעיל" if m["is_active"] else "לא פעיל"
                print(f"ID: {m['id']} | שם: {m['name']} | טלפון: {m['phone']} | סטטוס: {status}")

        elif choice == "3":
            name = input("שם הליד: ")
            phone = input("טלפון: ")
            source = input("מקור פנייה (פייסבוק/אינסטגרם/חבר): ")
            res = add_lead(name, phone, source)
            print(f"\nתוצאה: {res['message']}")

        elif choice == "4":
            lead_id = input("הכנס מזהה ליד (ID): ")
            if lead_id.isdigit():
                res = convert_lead_to_member(int(lead_id))
                print(f"\nתוצאה: {res['message']}")
            else:
                print("\nמזהה לא תקין.")

        elif choice == "5":
            member_id = input("מזהה מנוי (ID): ")
            date_str = input("תאריך האימון (YYYY-MM-DD): ")
            time_str = input("שעת התחלה (HH:MM): ")
            if member_id.isdigit():
                res = register_member_to_wod(int(member_id), date_str, time_str)
                print(f"\nתוצאה: {res['message']}")
            else:
                print("\nמזהה לא תקין.")

        elif choice == "6":
            print("\nלהתראות!")
            sys.exit(0)
        else:
            print("\nבחירה לא תקינה, נסה שוב.")

if __name__ == "__main__":
    main()
