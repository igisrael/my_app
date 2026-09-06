"""
rag/retriever.py — מנוע חיפוש RAG קל משקל באמצעות Google GenAI (ללא ChromaDB).

מכיוון ששרת PythonAnywhere החינמי מוגבל מאוד במקום האחסון (512MB),
הורדנו את ChromaDB ואנו מבצעים חיפוש סמנטי ישיר בעזרת מודל ה-Embeddings של Gemini.
"""

import os
import math
from typing import Optional
from dotenv import load_dotenv
from google import genai
from rag.knowledge_base import KNOWLEDGE_BASE

load_dotenv()
# אתחול הלקוח של Gemini
_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# מטמון לשמירת ההטבעות (Embeddings) בזיכרון, למניעת קריאות חוזרות
_kb_embeddings = []

# סף דמיון מינימלי (Cosine Similarity). 1.0 = זהה לחלוטין.
SIMILARITY_THRESHOLD = 0.55

def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """מחשב קרבה (Similarity) בין שני וקטורים"""
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm_a = math.sqrt(sum(a * a for a in vec1))
    norm_b = math.sqrt(sum(b * b for b in vec2))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)


def _get_embedding(text: str) -> list[float]:
    """מייצר וקטור יחיד עבור טקסט"""
    response = _client.models.embed_content(
        model='gemini-embedding-2',
        contents=text,
    )
    return response.embeddings[0].values


CACHE_FILE = os.path.join(os.path.dirname(__file__), "embeddings_cache.json")

def _ensure_initialized():
    """מטעין את מאגר הידע ומייצר וקטורים. משתמש בקובץ מטמון מקומי כדי לחסוך קריאות API מיותרות."""
    global _kb_embeddings
    if _kb_embeddings:
        return
        
    # ניסיון לטעון מהמטמון המקומי
    if os.path.exists(CACHE_FILE):
        try:
            import json
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                _kb_embeddings = json.load(f)
            print(f"RAG: Successfully loaded {len(_kb_embeddings)} embeddings from local cache.")
            return
        except Exception as e:
            print(f"RAG Error reading cache: {e}")
            _kb_embeddings = []

    # אם הגענו לכאן - אין מטמון או שהוא שגוי, נייצר וקטורים מול Gemini
    texts = [f"שאלה: {kb['question']}\nתשובה: {kb['answer']}" for kb in KNOWLEDGE_BASE]
    try:
        import json
        for i, text in enumerate(texts):
            response = _client.models.embed_content(
                model='gemini-embedding-2',
                contents=text,
            )
            _kb_embeddings.append({
                "id": KNOWLEDGE_BASE[i]["id"],
                "question": KNOWLEDGE_BASE[i]["question"],
                "answer": KNOWLEDGE_BASE[i]["answer"],
                "vector": response.embeddings[0].values
            })
        
        # שמירת הווקטורים לקובץ מטמון
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_kb_embeddings, f, ensure_ascii=False, indent=2)
            
        print(f"RAG: Successfully generated {len(_kb_embeddings)} embeddings and saved to cache.")
    except Exception as e:
        print(f"RAG Error initializing embeddings: {e}")


def get_relevant_answer(query: str) -> Optional[str]:
    """
    מחפש תשובה רלוונטית ל-query במאגר הידע הווירטואלי.
    מחזיר תשובה אם הדמיון גבוה מהסף.
    """
    _ensure_initialized()
    if not _kb_embeddings:
        return None
        
    try:
        query_vec = _get_embedding(query)
    except Exception:
        return None
        
    best_score = -1.0
    best_answer = None
    
    for kb in _kb_embeddings:
        score = _cosine_similarity(query_vec, kb["vector"])
        if score > best_score:
            best_score = score
            best_answer = kb["answer"]
            
    if best_score >= SIMILARITY_THRESHOLD:
        return best_answer
    
    return None


def search_debug(query: str) -> list:
    """פונקציית עזר לבדיקת רמת הדמיון של התוצאות (לצרכי Debug)"""
    _ensure_initialized()
    if not _kb_embeddings:
        return []
        
    try:
        query_vec = _get_embedding(query)
    except Exception:
        return []
        
    results = []
    for kb in _kb_embeddings:
        score = _cosine_similarity(query_vec, kb["vector"])
        results.append({
            "question": kb["question"],
            "answer": kb["answer"],
            "similarity": round(score, 4),
            "relevant": score >= SIMILARITY_THRESHOLD,
        })
        
    # מיון מהכי דומה להכי פחות דומה
    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:5]
