"""
expand_kb.py — Auto-grow the career knowledge base using Gemini.
Hardened version: retries 503s with backoff, NEVER crashes the run,
saves failed names so a re-run picks them up automatically.

Place in: backend/services/expand_kb.py
Run from PROJECT ROOT:  python -m backend.services.expand_kb
After it finishes:      python -m backend.services.build_embeddings
"""

import json
import os
import random
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai


# --------------------------------------------------
# Paths
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

CAREER_DATA_PATH = (
    PROJECT_ROOT / "knowledge_base" / "documents" / "careers.json"
)

SEED_LIST_PATH = (
    PROJECT_ROOT / "knowledge_base" / "career_seed_list.txt"
)

FAILED_LIST_PATH = (
    PROJECT_ROOT / "knowledge_base" / "failed_careers.txt"
)


# --------------------------------------------------
# Config - tweak these if the API keeps complaining
# --------------------------------------------------

MODEL_NAME = "gemini-3.6-flash"   # if 503s persist, list available models
                                  # (see list_models.py note below) and swap
MAX_ATTEMPTS = 8                  # retries per career
BASE_DELAY = 5                    # seconds; doubles each retry + random jitter
DELAY_BETWEEN_CAREERS = 3         # pause after each career (rate-limit friendly)


# --------------------------------------------------
# Env + client
# --------------------------------------------------

load_dotenv(PROJECT_ROOT / ".env")

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY was not found in .env")

client = genai.Client(api_key=api_key)


# --------------------------------------------------
# Prompt
# --------------------------------------------------

PROMPT_TEMPLATE = """
You are building a career counseling knowledge base for Indian students.

Generate a knowledge entry for the career: "{career_name}"

Return ONLY a valid JSON object with exactly these keys:
- "career": the career name
- "description": 2-3 sentences about what the work involves
- "education": list of realistic education paths
  (Indian context: degrees, diplomas, entrance exams like NEET, JEE, NATA, CLAT, UPSC, CA)
- "skills": list of 5-8 technical or hard skills
- "soft_skills": list of 4-6 soft skills
- "courses": list of 4-6 courses or subjects a student should learn
- "certifications": list of 2-4 recognized certifications
- "entry_level_roles": list of 2-4 job titles a fresher can apply for
- "career_progression": ordered list from junior to senior roles

Rules:
- Be specific and accurate, not generic.
- Keep each list to 3-8 short items.
- If the career is niche or new, describe the realistic path in India honestly.
"""


# --------------------------------------------------
# Helpers
# --------------------------------------------------

REQUIRED_KEYS = {
    "career", "description", "education", "skills",
    "soft_skills", "courses", "certifications",
    "entry_level_roles", "career_progression"
}


def load_existing() -> list:
    if not CAREER_DATA_PATH.exists():
        return []
    with open(CAREER_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_failed_names() -> list:
    if not FAILED_LIST_PATH.exists():
        return []
    return [
        line.strip()
        for line in FAILED_LIST_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]


def load_seed_names() -> list:
    if not SEED_LIST_PATH.exists():
        raise FileNotFoundError(
            f"Seed list not found: {SEED_LIST_PATH}\n"
            "Create it with one career name per line."
        )
    return [
        line.strip()
        for line in SEED_LIST_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]


def call_gemini(career_name: str):
    """
    One Gemini call with full retry logic.
    Returns the parsed entry dict, or None if all attempts failed.
    NEVER raises - failures are handled gracefully.
    """
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=PROMPT_TEMPLATE.format(career_name=career_name),
                config={"response_mime_type": "application/json"},
            )
            entry = json.loads(response.text)

            if REQUIRED_KEYS.issubset(entry.keys()):
                return entry

            print(f"  ! {career_name}: bad format, retrying ({attempt}/{MAX_ATTEMPTS})")

        except Exception as exc:
            wait = BASE_DELAY * (2 ** (attempt - 1)) + random.uniform(0, 2)
            print(f"  ! {career_name}: {type(exc).__name__} "
                  f"({attempt}/{MAX_ATTEMPTS}) - waiting {wait:.0f}s")
            time.sleep(wait)

    return None


def save_failed_name(career_name: str):
    """Record a career that failed after all retries."""
    already = set(load_failed_names())
    if career_name not in already:
        with open(FAILED_LIST_PATH, "a", encoding="utf-8") as f:
            f.write(career_name + "\n")


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():
    existing = load_existing()
    existing_names = {c["career"].lower() for c in existing}
    failed_names = set(load_failed_names())

    seed_names = load_seed_names()
    new_names = [
        n for n in seed_names
        if n.lower() not in existing_names and n not in failed_names
    ]

    print(f"Existing careers : {len(existing)}")
    print(f"Seed list        : {len(seed_names)}")
    print(f"Previously failed: {len(failed_names)}")
    print(f"New to generate  : {len(new_names)}")
    print()

    added, failed = 0, 0

    for i, name in enumerate(new_names, start=1):
        print(f"[{i}/{len(new_names)}] Generating: {name}")

        entry = call_gemini(name)

        if entry:
            existing.append(entry)
            added += 1
            # Save after every success so progress is never lost
            with open(CAREER_DATA_PATH, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2, ensure_ascii=False)
            print(f"  + saved ({len(existing)} total)")
        else:
            failed += 1
            save_failed_name(name)
            print(f"  x FAILED after {MAX_ATTEMPTS} attempts - saved to failed_careers.txt")

        time.sleep(DELAY_BETWEEN_CAREERS)

    print()
    print(f"Done. Added {added}, failed {failed}.")
    print(f"Total careers in KB: {len(existing)}")
    if failed:
        print("Re-run the script later - failed careers are skipped, "
              "delete knowledge_base/failed_careers.txt to retry them.")
    print()
    print("NEXT STEP - rebuild embeddings:")
    print("    python -m backend.services.build_embeddings")


if __name__ == "__main__":
    main()