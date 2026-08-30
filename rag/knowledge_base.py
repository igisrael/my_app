"""
rag/knowledge_base.py — מאגר הידע של FitStudio ל-RAG.

מכיל 25 זוגות שאלה-תשובה על הסטודיו (שעות, מחירים, חוקים וכו').
פונקציית seed_chromadb() מזרימה אותם ל-ChromaDB לחיפוש similarity.

ChromaDB נשמר locally בתיקיית ./chroma_db
"""

import os
import chromadb
from chromadb.config import Settings

# ===========================================================
# 25 זוגות שאלה-תשובה (מאגר הידע)
# ===========================================================
KNOWLEDGE_BASE = [
    {
        "id": "kb_01",
        "question": "מהן שעות הפעילות של הסטודיו?",
        "answer": "הסטודיו פתוח ימים א'-ה' בשעות 06:00-22:00, ובסוף שבוע (שישי-שבת) בשעות 07:00-14:00.",
    },
    {
        "id": "kb_02",
        "question": "כמה אנשים יכולים להשתתף באימון?",
        "answer": "כל אימון WOD מוגבל ל-18 משתתפים. כשהאימון מלא, לא ניתן להירשם.",
    },
    {
        "id": "kb_03",
        "question": "מה כוללת תוכנית האימונים?",
        "answer": "הסטודיו מציע אימוני פונקציונלי וקרוספיט, כולל אימוני כוח, סיבולת ומתיחות.",
    },
    {
        "id": "kb_04",
        "question": "מה המחיר של מנוי חודשי?",
        "answer": "מחיר המנוי החודשי הוא כ-400 ש\"ח לחודש. יש מסלולים נוספים — צור קשר לפרטים.",
    },
    {
        "id": "kb_05",
        "question": "כמה אימונים ניתן לעשות בשבוע?",
        "answer": "ניתן להירשם עד 16 אימונים בחודש. מעל 16 — יש להוסיף תשלום נוסף.",
    },
    {
        "id": "kb_06",
        "question": "האם ניתן לבטל הרשמה לאימון?",
        "answer": "כן, ניתן לבטל הרשמה. מומלץ לבטל לפחות 2 שעות לפני האימון.",
    },
    {
        "id": "kb_07",
        "question": "מה קורה אם לא הגעתי ולא ביטלתי (No Show)?",
        "answer": "No Show נרשם בחשבונך. לאחר 3 No Shows בחודש תיחסם האפשרות להירשם לאימונים מראש.",
    },
    {
        "id": "kb_08",
        "question": "מה מסלולי המנוי הקיימים?",
        "answer": "קיימים 3 מסלולים: מנוי בסיסי (8 אימונים), מנוי מלא (ללא הגבלה), ומנוי ביסיסי של תשלום לפי אימון.",
    },
    {
        "id": "kb_09",
        "question": "כמה זמן נמשך כל אימון?",
        "answer": "כל אימון WOD נמשך בדיוק 60 דקות ומתחיל בשעה עגולה.",
    },
    {
        "id": "kb_10",
        "question": "האם יש אימון ניסיון לחדשים?",
        "answer": "כן! ניתן לנסות אימון ראשון בחינם. צור קשר לתיאום.",
    },
    {
        "id": "kb_11",
        "question": "האם מתאימים לגילאים מעל 60? מה הגבלת הגיל?",
        "answer": "הסטודיו מתאים לכל הגילאים. אין הגבלת גיל, אך מומלץ לקבל אישור רפואי.",
    },
    {
        "id": "kb_12",
        "question": "האם יש חניה ליד הסטודיו?",
        "answer": "כן, יש חניה חופשית בצמוד לסטודיו לכל לקוחות המועדון.",
    },
    {
        "id": "kb_13",
        "question": "איפה הסטודיו ממוקם?",
        "answer": "הסטודיו ממוקם ברחוב הספורט 1, תל אביב, ליד הפארק המרכזי.",
    },
    {
        "id": "kb_14",
        "question": "האם יש מלתחות ומקלחות?",
        "answer": "כן, יש מלתחות מאובזרות ומקלחות נפרדות לגברים ולנשים.",
    },
    {
        "id": "kb_15",
        "question": "מה ה-No Show ומה ההשלכות?",
        "answer": "No Show הוא כשנרשמת ולא הגעת ולא ביטלת. לאחר 3 No Shows חסימה מלהירשם מראש.",
    },
    {
        "id": "kb_16",
        "question": "האם ניתן להגיע לאימון ללא רישום מראש (Drop-in)?",
        "answer": "כן, ניתן להגיע כ-Drop-in אם יש מקום פנוי. תשלום לפי אימון בודד.",
    },
    {
        "id": "kb_17",
        "question": "האם יש אימונים אישיים?",
        "answer": "כן, מציעים אימונים אישיים (1-on-1). יש לתאם מראש עם אחד המאמנים.",
    },
    {
        "id": "kb_18",
        "question": "מה ציוד האימון שצריך להביא?",
        "answer": "מומלץ להביא: בגדי ספורט, נעלי ספורט, מגבת, ובקבוק מים. הציוד לאימון קיים בסטודיו.",
    },
    {
        "id": "kb_19",
        "question": "האם יש תפריט תזונה לחברים?",
        "answer": "יש ייעוץ תזונתי בתשלום נפרד. ניתן לשאול את המאמנים לפרטים נוספים.",
    },
    {
        "id": "kb_20",
        "question": "האם שולחים תזכורות לפני אימון?",
        "answer": "כן, שולחים הודעת SMS שעה לפני האימון לכל מי שנרשם.",
    },
    {
        "id": "kb_21",
        "question": "האם יש אפליקציה של הסטודיו?",
        "answer": "בקרוב! האפליקציה בפיתוח ותהיה זמינה ב-App Store וב-Google Play.",
    },
    {
        "id": "kb_22",
        "question": "מה שעות ההתחלה ביום שישי?",
        "answer": "בשישי האימונים מתחילים בשעות 07:00-12:00 (4 משבצות בוקר בלבד).",
    },
    {
        "id": "kb_23",
        "question": "מה המחיר לאימון בודד?",
        "answer": "מחיר אימון בודד (Drop-in) הוא כ-50-55 ש\"ח, בהתאם לסוג האימון.",
    },
    {
        "id": "kb_24",
        "question": "האם ניתן להקפיא מנוי?",
        "answer": "כן, ניתן להקפיא מנוי עד חודשיים בשנה. יש לפנות לאדמין.",
    },
    {
        "id": "kb_25",
        "question": "מה קורה אם אני רוצה לבטל את המנוי?",
        "answer": "ניתן לבטל בהתראה של חודש מראש. מחיר שולם לא מוחזר, אך ניתן להקפיא.",
    },
]


def get_chroma_client():
    """מחזיר ChromaDB client עם persistent storage."""
    persist_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_db")
    os.makedirs(persist_dir, exist_ok=True)
    return chromadb.PersistentClient(path=persist_dir)


def get_or_create_collection():
    """מחזיר את ה-collection של הידע. יוצר אם לא קיים."""
    client = get_chroma_client()
    return client.get_or_create_collection(
        name="fitstudio_knowledge",
        metadata={"hnsw:space": "cosine"},  # similarity metric
    )


def seed_chromadb():
    """
    מזרים את 25 השאלות-תשובות ל-ChromaDB.
    בטוח להרצה מרובה — בודק אם כבר קיים לפני הכנסה.
    """
    collection = get_or_create_collection()

    # בדיקה אם כבר זרוע
    existing = collection.get(ids=[kb["id"] for kb in KNOWLEDGE_BASE])
    existing_ids = set(existing["ids"])

    new_docs = [kb for kb in KNOWLEDGE_BASE if kb["id"] not in existing_ids]

    if not new_docs:
        print(f"ChromaDB: כבר מכיל {len(KNOWLEDGE_BASE)} מסמכים. דילוג על זריעה.")
        return

    collection.add(
        ids=[kb["id"] for kb in new_docs],
        documents=[
            # שדה הטקסט לחיפוש = שאלה + תשובה ביחד
            f"שאלה: {kb['question']}\nתשובה: {kb['answer']}"
            for kb in new_docs
        ],
        metadatas=[
            {"question": kb["question"], "answer": kb["answer"]}
            for kb in new_docs
        ],
    )

    print(f"ChromaDB: נוספו {len(new_docs)} מסמכים חדשים לאוסף.")


if __name__ == "__main__":
    seed_chromadb()
    collection = get_or_create_collection()
    print(f"סה\"כ מסמכים ב-ChromaDB: {collection.count()}")
