"""
build_embeddings.py - Incremental embedding builder.

- Re-uses embeddings for careers whose text hasn't changed (so adding 90 new
  careers only embeds 90, not everything again).
- Retries on 503/429 with backoff and saves progress as it goes.

Run from PROJECT ROOT:  python -m backend.services.build_embeddings
"""

import json
import os
import random
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai


# --------------------------------------------------
# Project paths
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

CAREER_DATA_PATH = PROJECT_ROOT / "knowledge_base" / "documents" / "careers.json"
EMBEDDINGS_PATH = PROJECT_ROOT / "knowledge_base" / "career_embeddings.json"

# IMPORTANT: must be the SAME model used in rag_service.py for queries.
EMBEDDING_MODEL = "models/gemini-embedding-2"

MAX_ATTEMPTS = 6
BASE_DELAY = 4
DELAY_BETWEEN_CALLS = 0.5


# --------------------------------------------------
# Environment + client
# --------------------------------------------------

load_dotenv(PROJECT_ROOT / ".env")

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY was not found in .env")

client = genai.Client(api_key=api_key)


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def build_text(career: dict) -> str:
    """Same format as before, so old embeddings stay reusable."""
    return f"""
Career: {career["career"]}

Description:
{career["description"]}

Education:
{", ".join(career["education"])}

Skills:
{", ".join(career["skills"])}

Soft Skills:
{", ".join(career["soft_skills"])}

Courses:
{", ".join(career["courses"])}

Certifications:
{", ".join(career["certifications"])}

Entry Level Roles:
{", ".join(career["entry_level_roles"])}

Career Progression:
{" -> ".join(career["career_progression"])}
""".strip()


def embed_with_retry(text: str):
    """Returns the embedding vector, or None after all retries fail."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=text,
            )
            return response.embeddings[0].values
        except Exception as exc:
            wait = BASE_DELAY * (2 ** (attempt - 1)) + random.uniform(0, 2)
            print(f"  ! {type(exc).__name__} ({attempt}/{MAX_ATTEMPTS}) "
                  f"- waiting {wait:.0f}s")
            time.sleep(wait)
    return None


def save(embedded: list):
    with open(EMBEDDINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(embedded, f)  # no indent: much smaller file


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():
    with open(CAREER_DATA_PATH, "r", encoding="utf-8") as f:
        careers = json.load(f)

    # Load previous embeddings, keyed by career name
    old = {}
    if EMBEDDINGS_PATH.exists():
        with open(EMBEDDINGS_PATH, "r", encoding="utf-8") as f:
            old = {item["career"]: item for item in json.load(f)}

    embedded = []
    reused, created, failed = 0, 0, []

    for i, career in enumerate(careers, start=1):
        name = career["career"]
        text = build_text(career)

        prev = old.get(name)
        if prev and prev["text"] == text:
            embedded.append(prev)
            reused += 1
            continue

        print(f"[{i}/{len(careers)}] Embedding: {name}")
        vector = embed_with_retry(text)

        if vector is None:
            failed.append(name)
            print("  x FAILED")
            continue

        embedded.append({"career": name, "text": text, "embedding": vector})
        created += 1
        save(embedded)  # keep progress
        time.sleep(DELAY_BETWEEN_CALLS)

    save(embedded)

    print()
    print(f"Reused {reused}, newly embedded {created}, failed {len(failed)}.")
    print(f"Total saved: {len(embedded)}  ->  {EMBEDDINGS_PATH}")
    if failed:
        print("Failed (just re-run to retry):", ", ".join(failed))


if __name__ == "__main__":
    main()
