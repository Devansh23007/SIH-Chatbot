import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai


# Find the project root
project_root = Path(__file__).resolve().parent.parent.parent

# Load .env
load_dotenv(project_root / ".env")

# Get API key
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY was not found in .env")

# Create Gemini client
client = genai.Client(api_key=api_key)


def generate_response(message: str) -> str:
    """Send a normal message to Gemini."""

    interaction = client.interactions.create(
        model="gemini-3.6-flash",
        input=message
    )

    return interaction.output_text


def generate_career_response(
    question: str,
    retrieved_context: str
) -> str:
    """Generate a career counseling response using retrieved career knowledge."""

    prompt = f"""
You are an AI Career Counseling Assistant.

Your job is to help students explore career options, understand
required skills, identify learning needs, and plan their career path.

Use the career knowledge provided below as the primary source
for your answer.

Do not invent career information that is not supported by the
provided knowledge.

If the provided knowledge is insufficient to answer something,
clearly say that more information is needed.

Career Knowledge:
-----------------
{retrieved_context}
-----------------

Student Question:
{question}

Instructions:
1. Answer the student's question clearly.
2. Use the retrieved career knowledge.
3. Explain why the career information is relevant.
4. Mention relevant skills, education, courses, or roles when appropriate.
5. Do not claim that the recommendation is a scientifically validated
   career assessment.
6. The final answer should feel like career counseling, not a raw
   database lookup.
"""

    interaction = client.interactions.create(
        model="gemini-3.6-flash",
        input=prompt
    )

    return interaction.output_text