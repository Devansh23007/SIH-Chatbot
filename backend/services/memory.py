"""
memory.py - short-term conversation memory (kept in the server's RAM).

Stores the last few messages per conversation plus the career being discussed,
so follow-ups like "yes", "tell me more" or "what about certifications?" make sense.

Place in: backend/services/memory.py

NOTE: memory lives in this Python process only. It is lost when the server
restarts and is NOT shared between several server processes. That is fine for a
demo. For production, swap the dict below for Redis or a database.
"""

import re
import threading
import time
import uuid
from collections import OrderedDict


MAX_MESSAGES = 8             # remembered messages per conversation (user + bot)
MAX_CONVERSATIONS = 500      # oldest conversations are dropped beyond this
TTL_SECONDS = 60 * 60        # forget a conversation after 1 hour of silence
MAX_BOT_CHARS = 500          # OLDER bot answers are shortened to this in history
HEAD_CHARS = 200             # ...keeping this many characters from the start
MAX_LAST_BOT_CHARS = 4000    # the NEWEST bot answer is kept (almost) in full

_store = OrderedDict()       # conversation_id -> {"messages": [...], "career": str|None, "updated": float}
_lock = threading.Lock()


def new_id() -> str:
    return uuid.uuid4().hex


def _prune(now: float):
    """Drop expired and surplus conversations. Caller holds the lock."""
    for cid in [c for c, s in _store.items() if now - s["updated"] > TTL_SECONDS]:
        del _store[cid]
    while len(_store) > MAX_CONVERSATIONS:
        _store.popitem(last=False)


def _shorten(text: str) -> str:
    """
    Shorten an OLD answer: keep the start and the end. The end usually holds the
    question the bot asked. The result is at most MAX_BOT_CHARS long, and
    shortening an already shortened text changes nothing.
    """
    text = text.strip()
    if len(text) <= MAX_BOT_CHARS:
        return text
    tail = MAX_BOT_CHARS - HEAD_CHARS - len(" ... ")
    return text[:HEAD_CHARS] + " ... " + text[-tail:]


def get_state(conversation_id):
    """Return a COPY of the stored state, or None."""
    if not conversation_id:
        return None
    with _lock:
        state = _store.get(conversation_id)
        if not state:
            return None
        return {"messages": list(state["messages"]), "career": state["career"]}


def remember(conversation_id: str, user_text: str, bot_text: str, career=None):
    """Save one exchange. `career` updates the topic only when it is not None."""
    now = time.time()
    with _lock:
        _prune(now)
        state = _store.setdefault(
            conversation_id, {"messages": [], "career": None, "updated": now}
        )
        state["messages"].append(("Student", user_text.strip()))
        state["messages"].append(("Assistant", bot_text.strip()[:MAX_LAST_BOT_CHARS]))

        # Only the NEWEST answer stays in full: it is what the student's next
        # message ("step 3", "the first one", "yes") usually points at.
        last = len(state["messages"]) - 1
        state["messages"] = [
            (who, _shorten(text) if who == "Assistant" and i != last else text)
            for i, (who, text) in enumerate(state["messages"])
        ]
        state["messages"] = state["messages"][-MAX_MESSAGES:]
        if career:
            state["career"] = career
        state["updated"] = now
        _store.move_to_end(conversation_id)


def format_history(state) -> str:
    """Turn stored messages into plain text for the AI prompt."""
    if not state:
        return ""
    return "\n".join(f"{who}: {text}" for who, text in state["messages"])


# --------------------------------------------------
# Follow-up detection
# --------------------------------------------------

# Messages that normally continue the previous topic
_FOLLOWUP_START = re.compile(
    r"^\s*(yes|yeah|yep|yup|ok|okay|sure|please|more|go on|continue|and|also|"
    r"what about|how about|tell me more|why|how long|how much|how many|then|so)\b",
    re.IGNORECASE,
)

# Words that point back at something said earlier
_REFERS_BACK = re.compile(r"\b(it|its|that|this|those|these|them|they|there)\b", re.IGNORECASE)


def looks_like_followup(message: str) -> bool:
    """
    True if the message probably depends on earlier messages.
    Long messages are treated as self-contained.
    """
    words = message.split()
    if not words or len(words) > 12:
        return False
    return bool(_FOLLOWUP_START.match(message) or _REFERS_BACK.search(message))