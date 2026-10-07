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
    retrieved_context: str
) -> str:
    """
    Short, chat-friendly career answer.
    retrieved_context may contain several careers; the FIRST is the best match.
    """

    prompt = f"""
You are a friendly AI Career Counselor for Indian students, replying in a chat window.

CAREER KNOWLEDGE (best match first):
-----------------
{retrieved_context}
-----------------

STUDENT QUESTION:
{question}

RULES:
- Use ONLY the career knowledge above. Do NOT add certifications, courses,
  salaries, exam fees, or companies that are not in it. If the knowledge does
  not cover something the student asked, say so briefly.
- Focus on the FIRST career. Mention another career only if the student is
  exploring options or the question clearly fits it better.
- Keep the whole answer under 170 words. Students will not read long text.
- Answer ONLY what was asked. If they ask for courses and certifications,
  show just those sections, not education, skills, or progression.

FORMAT (Markdown):
1. One short, warm sentence that directly answers the question.
2. Bold section titles, each with at most 4 bullets. Every bullet under 12 words.
3. A final line starting with "Next step:" giving ONE concrete action.
4. One short follow-up question offering more help
   (e.g. a learning roadmap, entry-level roles, or comparing with a similar career).

Do not claim this is a scientifically validated career assessment.
"""

    return _generate(prompt)


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