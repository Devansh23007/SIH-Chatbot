import json
import os
import re
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from services.llm_service import (
    generate_response,
    generate_career_response,
    generate_general_response,
)

from services.rag_service import search_careers


app = FastAPI(title="SIH Career Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# Relevance thresholds  (CALIBRATE THESE - see calibrate_threshold.py)
# --------------------------------------------------

STRONG_MATCH = float(os.getenv("STRONG_MATCH", 0.70))   # confident: answer from KB
WEAK_MATCH = float(os.getenv("WEAK_MATCH", 0.55))       # related: closest career, flagged

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MISSING_LOG = PROJECT_ROOT / "knowledge_base" / "missing_queries.jsonl"

GENERAL_NOTICE = (
    "ℹ️ *This isn't in my verified career database yet, so this is general "
    "guidance only. Please double-check details with official sources.*\n\n"
)

CLOSEST_NOTICE = (
    "ℹ️ *I don't have an exact match for that, so here is the closest "
    "career in my database: **{career}**.*\n\n"
)


def log_missing(question: str, results: list):
    """Remember questions the KB couldn't answer well, so you can add those careers."""
    try:
        MISSING_LOG.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "time": datetime.now().isoformat(timespec="seconds"),
            "question": question,
            "closest": [(r["career"], round(r["similarity"], 3)) for r in results],
        }
        with open(MISSING_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as exc:
        print(f"[log] could not write missing log: {exc}")



def promote_named_career(question: str, results: list):
    """
    If the student literally names one of the retrieved careers
    (e.g. "architect"), move it to the front and report a name hit.
    """
    q = question.lower()
    for i, r in enumerate(results):
        name = r["career"].lower()
        if re.search(rf"\b{re.escape(name)}\b", q):
            return [results[i]] + results[:i] + results[i + 1:], True
    return results, False


class ChatRequest(BaseModel):
    message: str


@app.get("/")
def root():
    return {
        "message": "SIH Career Chatbot backend is running"
    }


@app.post("/api/chat")
def chat(request: ChatRequest):

    response = generate_response(request.message)

    return {
        "response": response
    }


@app.post("/api/career-chat")
def career_chat(request: ChatRequest):

    # 1) Retrieve the 3 closest careers
    try:
        results = search_careers(request.message, top_k=3)
    except Exception as exc:
        print(f"[rag] search failed: {type(exc).__name__}: {str(exc)[:120]}")
        return {
            "response": "Sorry, I couldn't search the career database right now. "
                        "Please try again in a few seconds.",
            "source": "error",
            "career": None,
            "similarity": None,
            "related_careers": [],
        }

    results, name_hit = promote_named_career(request.message, results)
    top = results[0]
    related = [
        {"career": r["career"], "similarity": round(r["similarity"], 3)}
        for r in results
    ]

    print("[rag] top matches:",
          [(r["career"], round(r["similarity"], 3)) for r in results])

    # 2) Decide how good the match is
    if name_hit or top["similarity"] >= STRONG_MATCH:
        # Confident: answer from the knowledge base
        context = "\n\n=====\n\n".join(r["text"] for r in results)
        answer = generate_career_response(request.message, context)
        source = "knowledge_base"

    elif top["similarity"] >= WEAK_MATCH:
        # Related career exists: answer from closest, but say so
        log_missing(request.message, results)
        context = "\n\n=====\n\n".join(r["text"] for r in results)
        answer = CLOSEST_NOTICE.format(career=top["career"]) + \
            generate_career_response(request.message, context)
        source = "knowledge_base_closest"

    else:
        # Not in the KB: general guidance, clearly labelled
        log_missing(request.message, results)
        nearby = ", ".join(r["career"] for r in results)
        answer = GENERAL_NOTICE + generate_general_response(request.message, nearby)
        source = "general"

    return {
        "response": answer,
        "source": source,                 # "knowledge_base" | "knowledge_base_closest" | "general"
        "career": top["career"] if source != "general" else None,
        "similarity": top["similarity"],
        "related_careers": related,
    }