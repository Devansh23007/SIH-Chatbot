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
    similar_careers: str = ""
) -> str:
    """
    Focused, chat-friendly career answer.
    retrieved_context = the ONE matched career.
    similar_careers   = names only, of 1-2 neighbouring careers.
    """

    prompt = f"""
You are a friendly AI Career Counselor for Indian students, replying in a chat window.

CAREER KNOWLEDGE (the matched career):
-----------------
{retrieved_context}
-----------------

OTHER SIMILAR CAREERS (names only): {similar_careers or "none"}

STUDENT QUESTION:
{question}

RULES:
- Use ONLY the career knowledge above. Do NOT add certifications, courses,
  salaries, exam fees, or companies that are not in it. If the knowledge does
  not cover something the student asked, say so briefly.
- Answer ONLY the specific thing asked.
  * If the student asks about ONE aspect (certifications, courses, skills,
    education, entry-level roles, career growth), give ONLY that aspect.
    Do not add the other sections.
  * Only if the question is general ("tell me about X", "how do I become X")
    give a short overview with at most 3 small sections.
- After the main answer you may add at most 2 bullets under the bold title
  "Also useful:", and only if they are DIRECTLY connected to what was asked
  (for example, for certifications: a course that prepares for them).
  Never add unrelated information.
- Mention similar careers only if the student is comparing or exploring options.
- Length: under 120 words for a specific question, under 170 for an overview.

FORMAT (Markdown):
1. One short, warm sentence that directly answers the question.
2. The answer as a bold title with at most 4 bullets, each under 12 words.
3. The optional "Also useful:" bullets (max 2).
4. One short follow-up question offering something closely related.

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
- Do NOT add any disclaimer yourself; the app adds it.
"""

    return _generate(prompt)