"""
rag/retriever.py — מנוע חיפוש RAG ב-ChromaDB עם Fallback מדורג.

3 רמות Fallback:
1. System Prompt Strictness  — ChromaDB מחזיר רק תוצאות רלוונטיות
2. Distance Threshold        — סינון לפי מרחק cosine (< SIMILARITY_THRESHOLD)
3. Graceful Fallback         — אם לא נמצא, מחזיר None (הבוט מטפל)
"""

from typing import Optional
from rag.knowledge_base import get_or_create_collection, seed_chromadb

# סף דמיון: מתחת לו — תוצאה לא נחשבת רלוונטית
# cosine distance: 0 = זהה, 2 = הפוכים לגמרי. 0.5 = ערך מאוזן לעברית
SIMILARITY_THRESHOLD = 0.6

# מספר תוצאות מקסימלי להחזיר מ-ChromaDB
N_RESULTS = 3

_initialized = False


def _ensure_initialized():
    """מוודא שה-ChromaDB אוכלס לפחות פעם אחת."""
    global _initialized
    if not _initialized:
        seed_chromadb()
        _initialized = True


def get_relevant_answer(query: str) -> Optional[str]:
    """
    מחפש תשובה רלוונטית ל-query ב-ChromaDB.

    מחזיר:
    - str עם התשובה הרלוונטית ביותר אם נמצאה (distance < SIMILARITY_THRESHOLD)
    - None אם לא נמצאה תשובה מספיק רלוונטית (Graceful Fallback)
    """
    _ensure_initialized()

    try:
        collection = get_or_create_collection()

        if collection.count() == 0:
            return None

        results = collection.query(
            query_texts=[query],
            n_results=min(N_RESULTS, collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        distances = results.get("distances", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        if not distances:
            return None

        best_distance = distances[0]
        best_metadata = metadatas[0] if metadatas else {}

        # ---- רמה 2: Distance Threshold ----
        if best_distance > SIMILARITY_THRESHOLD:
            # התוצאה לא מספיק רלוונטית → Fallback
            return None

        # ---- תוצאה רלוונטית ----
        return best_metadata.get("answer", "")

    except Exception as e:
        # כשל טכני — לא נחשוף שגיאה למשתמש
        return None


def search_debug(query: str) -> list:
    """
    גרסת Debug לחיפוש — מחזיר את כל התוצאות עם המרחקים.
    שימושי לבדיקות ואבחון.
    """
    _ensure_initialized()
    collection = get_or_create_collection()

    if collection.count() == 0:
        return []

    results = collection.query(
        query_texts=[query],
        n_results=min(5, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    output = []
    for dist, meta in zip(
        results.get("distances", [[]])[0],
        results.get("metadatas", [[]])[0],
    ):
        output.append(
            {
                "question": meta.get("question", ""),
                "answer": meta.get("answer", ""),
                "distance": round(dist, 4),
                "relevant": dist < SIMILARITY_THRESHOLD,
            }
        )
    return output
