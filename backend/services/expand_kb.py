"""
expand_kb.py - Auto-grow the career knowledge base.

Provider order: Groq (fast, free tier)  ->  Gemini (fallback).
- Saves after every successful career (safe to Ctrl+C and re-run).
- Never crashes on API errors; careers that fail are written to
  failed_careers.txt and RETRIED automatically on the next run.

Place in: backend/services/expand_kb.py
Run from PROJECT ROOT:  python -m backend.services.expand_kb
Then rebuild embeddings: python -m backend.services.build_embeddings

Setup:
    pip install groq
    add  GROQ_API_KEY=...  to .env   (free key: console.groq.com)
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

CAREER_DATA_PATH = PROJECT_ROOT / "knowledge_base" / "documents" / "careers.json"
SEED_LIST_PATH = PROJECT_ROOT / "knowledge_base" / "career_seed_list.txt"
FAILED_LIST_PATH = PROJECT_ROOT / "knowledge_base" / "failed_careers.txt"


# --------------------------------------------------
# Config
# --------------------------------------------------

GROQ_MODEL = "openai/gpt-oss-120b"   # free tier: 30 RPM, ~8K tokens/min, ~200K tokens/day
GEMINI_MODEL = "gemini-3.6-flash"

ATTEMPTS_PER_PROVIDER = 4     # tries on one provider before switching
BASE_DELAY = 4                # seconds, doubles each retry (+ jitter)
DELAY_BETWEEN_CAREERS = 8     # the TOKENS-per-minute cap binds first, not requests


# --------------------------------------------------
# Env + clients
# --------------------------------------------------

load_dotenv(PROJECT_ROOT / ".env")

gemini_key = os.getenv("GEMINI_API_KEY")
groq_key = os.getenv("GROQ_API_KEY")

if not gemini_key and not groq_key:
    raise ValueError("Set GROQ_API_KEY and/or GEMINI_API_KEY in .env")

gemini_client = genai.Client(api_key=gemini_key) if gemini_key else None

groq_client = None
if groq_key:
    from groq import Groq
    groq_client = Groq(api_key=groq_key)


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
- Keep each list to 3-8 short items, each item a plain string.
- Do not invent exact salary figures, college rankings, or exam dates.
- If the career is niche or new, describe the realistic path in India honestly.
"""

STRING_KEYS = {"career", "description"}
LIST_KEYS = {
    "education", "skills", "soft_skills", "courses",
    "certifications", "entry_level_roles", "career_progression",
}


# --------------------------------------------------
# Provider calls (each returns raw JSON text)
# --------------------------------------------------

def _call_groq(prompt: str) -> str:
    kwargs = {}
    if "gpt-oss" in GROQ_MODEL:
        # gpt-oss are reasoning models: hidden "thinking" tokens count toward
        # max_tokens. Keep thinking short so the JSON isn't cut off mid-way.
        kwargs["reasoning_effort"] = "low"

    resp = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": "You output only valid JSON."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.4,
        max_tokens=3000,
        **kwargs,
    )
    return resp.choices[0].message.content


def _call_gemini(prompt: str) -> str:
    resp = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config={"response_mime_type": "application/json"},
    )
    return resp.text


PROVIDERS = []
if groq_client:
    PROVIDERS.append(("groq", _call_groq))
if gemini_client:
    PROVIDERS.append(("gemini", _call_gemini))


# --------------------------------------------------
# Validation
# --------------------------------------------------

def clean_entry(entry, career_name: str):
    """Return a validated/normalised entry, or None if unusable."""
    if not isinstance(entry, dict):
        return None
    if not (STRING_KEYS | LIST_KEYS).issubset(entry.keys()):
        return None

    cleaned = {"career": career_name}  # keep the seed-list name exactly

    desc = entry["description"]
    if not isinstance(desc, str) or len(desc.strip()) < 20:
        return None
    cleaned["description"] = desc.strip()

    for key in LIST_KEYS:
        value = entry[key]
        if not isinstance(value, list) or not value:
            return None
        cleaned[key] = [str(item).strip() for item in value if str(item).strip()]
        if not cleaned[key]:
            return None

    return cleaned


# --------------------------------------------------
# Generation with provider fallback
# --------------------------------------------------

def generate_entry(career_name: str):
    """Try each provider in order. Returns an entry dict or None. Never raises."""
    prompt = PROMPT_TEMPLATE.format(career_name=career_name)

    for provider_name, call in PROVIDERS:
        for attempt in range(1, ATTEMPTS_PER_PROVIDER + 1):
            try:
                raw = call(prompt)
                entry = clean_entry(json.loads(raw), career_name)
                if entry:
                    return entry
                print(f"  ! {provider_name}: bad format "
                      f"({attempt}/{ATTEMPTS_PER_PROVIDER})")
            except Exception as exc:
                wait = BASE_DELAY * (2 ** (attempt - 1)) + random.uniform(0, 2)
                msg = str(exc).replace("\n", " ")[:90]
                print(f"  ! {provider_name}: {type(exc).__name__} "
                      f"({attempt}/{ATTEMPTS_PER_PROVIDER}) {msg} "
                      f"- waiting {wait:.0f}s")
                time.sleep(wait)

        print(f"  > {provider_name} exhausted, switching provider")

    return None


# --------------------------------------------------
# File helpers
# --------------------------------------------------

def read_name_list(path: Path) -> list:
    if not path.exists():
        return []
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]


def load_existing() -> list:
    if not CAREER_DATA_PATH.exists():
        return []
    with open(CAREER_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_careers(careers: list):
    CAREER_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CAREER_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(careers, f, indent=2, ensure_ascii=False)


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():
    existing = load_existing()
    existing_names = {c["career"].lower() for c in existing}

    seed_names = read_name_list(SEED_LIST_PATH)
    if not seed_names:
        raise FileNotFoundError(f"No career names found in {SEED_LIST_PATH}")

    previously_failed = read_name_list(FAILED_LIST_PATH)

    # Failed careers are retried automatically (they're still in the seed list).
    new_names = [n for n in seed_names if n.lower() not in existing_names]

    print(f"Providers        : {[p[0] for p in PROVIDERS]}")
    print(f"Existing careers : {len(existing)}")
    print(f"Seed list        : {len(seed_names)}")
    print(f"Retrying failed  : {len(previously_failed)}")
    print(f"To generate      : {len(new_names)}")
    print()

    still_failed = []
    added = 0

    for i, name in enumerate(new_names, start=1):
        print(f"[{i}/{len(new_names)}] Generating: {name}")

        entry = generate_entry(name)

        if entry:
            existing.append(entry)
            existing_names.add(name.lower())
            added += 1
            save_careers(existing)  # progress is never lost
            print(f"  + saved ({len(existing)} total)")
        else:
            still_failed.append(name)
            print("  x FAILED on all providers")

        time.sleep(DELAY_BETWEEN_CAREERS)

    # Rewrite failed list with ONLY the ones that still failed
    if still_failed:
        FAILED_LIST_PATH.write_text("\n".join(still_failed) + "\n", encoding="utf-8")
    elif FAILED_LIST_PATH.exists():
        FAILED_LIST_PATH.unlink()

    print()
    print(f"Done. Added {added}, failed {len(still_failed)}.")
    print(f"Total careers in KB: {len(existing)}")
    if still_failed:
        print("Just re-run this script later to retry the failed ones.")
    print()
    print("NEXT STEP - rebuild embeddings:")
    print("    python -m backend.services.build_embeddings")


if __name__ == "__main__":
    main()
