import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai


# Find the project root
project_root = Path(__file__).resolve().parent.parent.parent

# Load .env
load_dotenv(project_root / ".env")

gemini_key = os.getenv("GEMINI_API_KEY")
groq_key = os.getenv("GROQ_API_KEY")

if not gemini_key and not groq_key:
    raise ValueError("Set GEMINI_API_KEY and/or GROQ_API_KEY in .env")

GROQ_MODEL = "openai/gpt-oss-120b"     # swap to "openai/gpt-oss-20b" for faster replies
GEMINI_MODEL = "gemini-3.6-flash"

FRIENDLY_ERROR = (
    "Sorry, I'm getting a lot of requests right now. "
    "Please try again in a few seconds."
)

gemini_client = genai.Client(api_key=gemini_key) if gemini_key else None

groq_client = None
if groq_key:
    from groq import Groq
    groq_client = Groq(api_key=groq_key)


# --------------------------------------------------
# Provider calls
# --------------------------------------------------

def _groq(prompt: str) -> str:
    resp = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=1500,          # answers are short now; this leaves room for reasoning
        reasoning_effort="low",   # gpt-oss only: keep hidden thinking short
    )
    return resp.choices[0].message.content


def _gemini(prompt: str) -> str:
    interaction = gemini_client.interactions.create(
        model=GEMINI_MODEL,
        input=prompt
    )
    return interaction.output_text


# Groq FIRST (fast, saves Gemini quota for embeddings), Gemini as fallback
PROVIDERS = []
if groq_client:
    PROVIDERS.append(("groq", _groq))
if gemini_client:
    PROVIDERS.append(("gemini", _gemini))


def _generate(prompt: str) -> str:
    """Try each provider (2 quick attempts). Never raises."""
    for name, call in PROVIDERS:
        for attempt in range(2):
            try:
                return call(prompt)
            except Exception as exc:
                print(f"[llm] {name} attempt {attempt + 1} failed: "
                      f"{type(exc).__name__}: {str(exc)[:100]}")
                time.sleep(1.5)

    return FRIENDLY_ERROR


# --------------------------------------------------
# Public functions
# --------------------------------------------------

def generate_response(message: str) -> str:
    """Send a normal message to the LLM."""
    return _generate(message)


def generate_career_response(
    question: str,
    retrieved_context: str,
    similar_careers: str = "",
    history_text: str = ""
) -> str:
    """
    Conversation-aware career answer.
    retrieved_context = the ONE matched career.
    similar_careers   = names only, of 1-2 neighbouring careers.
    history_text      = the recent chat, so the answer builds on it.
    """

    prompt = f"""
You are a friendly AI Career Counselor for Indian students, in an ongoing chat.

CAREER KNOWLEDGE (the matched career):
-----------------
{retrieved_context}
-----------------

OTHER SIMILAR CAREERS (names only): {similar_careers or "none"}

RECENT CONVERSATION (context only; the LAST 'Assistant' message is your previous answer, shown in full):
{history_text or "(this is the start of the chat)"}

STUDENT'S LATEST QUESTION (already clarified):
{question}

RULES:
FACTS
- Take every fact (education paths, skills, courses, certifications, roles,
  career progression) ONLY from the career knowledge above. Never invent
  salaries, fees, exam dates, cut-offs, college names, companies, or extra
  courses/certifications that are not listed.

WHAT YOU MAY DO
- Organise and explain the listed facts: put courses or skills in a sensible
  learning order, build a step-by-step plan, say where to start, or give
  general study tips (practice projects, building a portfolio). Keep these
  parts general and do not add new named courses, tools, or numbers.
- Build on the recent conversation. Do not repeat what you already said.
  If the student says "yes", continue with what you offered.
- If the student points at part of YOUR PREVIOUS ANSWER ("step 3", "the first
  one", "that certification", "explain more"), find that exact item in the last
  Assistant message and explain THAT item in more detail, using the career
  knowledge. Keep its title and number. Never replace it with a different item.

ONLY IF NEEDED
- If the student asks for something truly outside the knowledge (salary,
  fees, specific colleges, exam dates), say in one sentence that it is not in
  your database and to check official sources, then still help with what you can.

SHAPE
- Answer ONLY what was asked. If they ask about ONE aspect, give only that.
  Give an overview only for general questions ("tell me about X").
- Length: under 130 words for a specific question, under 180 for an overview
  or a plan.
- Mention similar careers only if the student is comparing or exploring.

FORMAT (Markdown, only bold text and "-" bullets; no headings, tables, italics):
1. One short, warm sentence that directly answers.
2. The answer: bold title(s), at most 4 bullets each, each under 14 words.
3. Finish with ONE short follow-up question. It MUST offer only something you
   can really deliver from the knowledge, chosen from: explaining the next
   step or item in more detail, a small practice-project idea for the current
   step, the entry-level roles, how the career grows over time, which skills to
   build first, the education paths, or a similar career to compare.
   Never offer what you just gave. If you gave a step-by-step plan or explained
   one of its steps, do NOT offer a learning order again.

Do not claim this is a scientifically validated career assessment.
"""

    return _generate(prompt)


def classify_question(question: str):
    """
    Returns "career", "other", or None if the AI could not be reached.
    Used only when retrieval finds no good match.
    """

    prompt = f"""
Is this message from a student about careers, jobs, professions, studies,
courses, exams, skills, or choosing a career path?

Message: "{question}"

Reply with exactly one word: CAREER or OTHER.
"""

    answer = _generate(prompt)

    if answer == FRIENDLY_ERROR:
        return None

    return "career" if "CAREER" in answer.upper() else "other"


def generate_general_response(question: str, nearby_careers: str = "") -> str:
    """
    Fallback for questions the knowledge base doesn't cover.
    Short, general guidance only - NOT presented as verified data.
    """

    prompt = f"""
You are a friendly AI Career Counselor for Indian students, replying in a chat window.

The student's question is NOT covered by our verified career database.

STUDENT QUESTION:
{question}

Careers we DO have in the database that may be loosely related: {nearby_careers or "none"}

RULES:
- If the question is not about careers, education, or skills (for example a
  greeting or an off-topic question), reply politely in one or two sentences
  and invite them to ask about careers.
- Otherwise give brief, general guidance in under 110 words.
- Do NOT state specific salaries, exam fees, exam dates, college rankings, or
  exact cut-offs. Keep to well-known, stable facts (typical degree paths,
  common skills, general direction).
- If you are unsure about something, say so instead of guessing.
- Markdown: one short sentence, then at most 3 bold section titles with at
  most 3 short bullets each. End with one short follow-up question.
- Use ONLY bold text and "-" bullet lists. No headings (#), tables, or italics.
- Do NOT add any disclaimer yourself; the app adds it.
"""

    return _generate(prompt)


def _parse_rewrite(raw: str, message: str):
    """Parse the rewriter's JSON. Returns (question, same_topic)."""
    import json
    import re

    match = re.search(r"\{.*\}", raw or "", re.DOTALL)
    if not match:
        return message, False
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return message, False

    question = data.get("question")
    same_topic = data.get("same_topic")

    if not isinstance(question, str) or not question.strip() or len(question) > 300:
        return message, False

    return question.strip(), bool(same_topic is True)


def rewrite_followup(history_text: str, message: str, current_career: str = ""):
    """
    Understand a message in the context of the chat.
    Returns (standalone_question, same_topic).
      same_topic=True  -> the student continues talking about current_career
      same_topic=False -> a new topic; the question is the original message
    Falls back to (message, False) if anything goes wrong.
    """

    prompt = f"""
You help a career chatbot understand a conversation.

CURRENT TOPIC (career being discussed): {current_career or "unknown"}

CHAT HISTORY:
{history_text}

LATEST MESSAGE FROM THE STUDENT: {message}

Return ONLY a JSON object: {{"same_topic": true or false, "question": "..."}}

- same_topic is true when the latest message continues the conversation about
  the current career. This includes short replies such as "yes", "ok",
  "skill building", "what next", or picking one of the options the assistant
  just offered.
- same_topic is false when the student switches to a different career or an
  unrelated subject.
- "question": the latest message rewritten as ONE standalone question.
  * If same_topic is true, the question MUST name the career
    "{current_career}".
  * If the message is just agreement ("yes", "sure", "please"), turn it into a
    request for exactly what the assistant offered at the end of its last
    message.
  * If the student points at part of the assistant's LAST message ("step 3",
    "the second one", "the last certification", "explain that"), the question
    MUST copy that item's number and title from the last message, e.g.
    "Explain step 3 (Big Data & Cloud Specialization) of the learning path for
    Data Engineer in more detail".
  * If same_topic is false, return the latest message unchanged.
- Do not answer the question.
"""

    raw = _generate(prompt)
    if raw == FRIENDLY_ERROR:
        return message, False

    return _parse_rewrite(raw, message)