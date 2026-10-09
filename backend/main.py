import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from services.llm_service import (
    generate_response,
    generate_career_response,
    generate_general_response,
    classify_question,
    rewrite_followup,
)

from services.rag_service import search_careers, load_embeddings
from services.small_talk import small_talk_reply, OFF_TOPIC
from services import memory


app = FastAPI(title="SIH Career Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# Relevance thresholds (calibrate with calibrate_threshold.py)
# --------------------------------------------------

STRONG_MATCH = float(os.getenv("STRONG_MATCH", 0.70))   # confident: answer from KB
WEAK_MATCH = float(os.getenv("WEAK_MATCH", 0.55))       # related: closest career, flagged

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MISSING_LOG = PROJECT_ROOT / "knowledge_base" / "missing_queries.jsonl"

GENERAL_NOTICE = (
    "ℹ️ **Note:** This isn't in my verified career database yet, so this is "
    "general guidance only. Please double-check details with official sources.\n\n"
)

CLOSEST_NOTICE = (
    "ℹ️ I don't have an exact match for that, so here is the closest "
    "career in my database: **{career}**.\n\n"
)


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def log_missing(question: str, results: list):
    """Remember CAREER questions the KB couldn't answer well."""
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


def mentions_known_career(text: str) -> bool:
    """True if the message literally names a career we have (so it is self-contained)."""
    try:
        names = [c["career"].lower() for c in load_embeddings()]
    except Exception as exc:
        print(f"[memory] could not load career names: {exc}")
        return False
    t = text.lower()
    return any(re.search(rf"\b{re.escape(n)}\b", t) for n in names)


def reply(text, source, results=None, career=None, similarity=None, cid=None):
    """Build a consistent API response."""
    return {
        "conversation_id": cid,
        "response": text,
        "source": source,
        "career": career,
        "similarity": similarity,
        "related_careers": [
            {"career": r["career"], "similarity": round(r["similarity"], 3)}
            for r in (results or [])
        ],
    }


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


# --------------------------------------------------
# Routes
# --------------------------------------------------

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

    message = request.message.strip()

    # The frontend sends no id on the first message, so we create one
    cid = request.conversation_id or memory.new_id()

    def respond(text, source, results=None, career=None, similarity=None,
                remember_career=None):
        """Save the exchange in memory, then build the API response."""
        memory.remember(cid, message, text, career=remember_career)
        return reply(text, source, results, career, similarity, cid=cid)

    # 0) Empty message
    if not message:
        return reply("Please type a question and I'll be happy to help. 😊",
                     "small_talk", cid=cid)

    # 1) Greetings, "what are you", thanks, bye -> instant answer,
    #    no API call, never logged
    talk = small_talk_reply(message)
    if talk:
        return respond(talk, "small_talk")

    # 2) Understand the message in the context of the chat.
    #    If a career is being discussed and the message does not name another
    #    career, ask the AI whether the student is continuing the same topic
    #    ("yes", "skill building", "what next"...) and turn it into a standalone question.
    state = memory.get_state(request.conversation_id)
    print(f"[memory] id={request.conversation_id} "
          f"remembered_career={state['career'] if state else None}")

    question = message
    history_text = memory.format_history(state) if state else ""

    if (state and state["career"]
            and not mentions_known_career(message)
            and len(message.split()) <= 40):
        current = state["career"]
        question, same_topic = rewrite_followup(history_text, message, current)

        # Make sure a continued topic really carries the career name
        if same_topic and current.lower() not in question.lower():
            question = f"{question} (about {current})"

        if not same_topic:
            history_text = ""   # new topic: do not drag old context along
        print(f"[memory] same_topic={same_topic}: {message!r} -> {question!r}")

    # 3) Retrieve the 3 closest careers
    try:
        results = search_careers(question, top_k=3)
    except Exception as exc:
        print(f"[rag] search failed: {type(exc).__name__}: {str(exc)[:120]}")
        return reply("Sorry, I couldn't search the career database right now. "
                     "Please try again in a few seconds.", "error", cid=cid)

    results, name_hit = promote_named_career(question, results)
    top = results[0]
    others = ", ".join(r["career"] for r in results[1:3])

    print("[rag] top matches:",
          [(r["career"], round(r["similarity"], 3)) for r in results])

    # 4a) Strong match (or career named): focused answer from the KB.
    if name_hit or top["similarity"] >= STRONG_MATCH:
        answer = generate_career_response(question, top["text"], others, history_text)
        return respond(answer, "knowledge_base", results,
                       career=top["career"], similarity=top["similarity"],
                       remember_career=top["career"])

    # 4b) Weak match: related career exists, say it's the closest one
    if top["similarity"] >= WEAK_MATCH:
        log_missing(question, results)
        answer = CLOSEST_NOTICE.format(career=top["career"]) + \
            generate_career_response(question, top["text"], others, history_text)
        return respond(answer, "knowledge_base_closest", results,
                       career=top["career"], similarity=top["similarity"],
                       remember_career=top["career"])

    # 4c) No good match: is it even a career question?
    kind = classify_question(question)

    if kind is None:
        # AI unreachable: don't guess, don't log, don't remember
        return reply("Sorry, I'm getting a lot of requests right now. "
                     "Please try again in a few seconds.", "error", cid=cid)

    if kind == "other":
        # Not career related: friendly redirect, NOT logged as missing
        return respond(OFF_TOPIC, "off_topic")

    # Career question we don't have: general guidance + log it
    log_missing(question, results)
    nearby = ", ".join(r["career"] for r in results)
    answer = GENERAL_NOTICE + generate_general_response(question, nearby)
    return respond(answer, "general", results, similarity=top["similarity"])