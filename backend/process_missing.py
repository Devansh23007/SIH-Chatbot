"""
process_missing.py - turn unanswered student questions into new KB careers.

Put this file in backend/ (next to main.py) and run from inside backend/:

    python process_missing.py            # review the list, confirm, add to seed list
    python process_missing.py --run      # ...and also generate + embed the new careers
    python process_missing.py --yes --run   # fully automatic (no confirmation)

What it does:
  1. Reads knowledge_base/missing_queries.jsonl (written by main.py)
  2. Asks the LLM which career each question was about (or none)
  3. Skips careers already in careers.json / the seed list
  4. Shows you the new names, with how many students asked for each
  5. On confirmation, appends them to career_seed_list.txt
  6. With --run: runs expand_kb (generate) and build_embeddings (embed)
"""

import argparse
import json
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

from services.llm_service import _generate, FRIENDLY_ERROR


PROJECT_ROOT = Path(__file__).resolve().parent.parent
KB_DIR = PROJECT_ROOT / "knowledge_base"

MISSING_PATH = KB_DIR / "missing_queries.jsonl"
DONE_PATH = KB_DIR / "missing_queries.done.jsonl"
SEED_PATH = KB_DIR / "career_seed_list.txt"
CAREERS_PATH = KB_DIR / "documents" / "careers.json"

MIN_COUNT = 1   # raise to 2-3 later so one-off typos/jokes are ignored


EXTRACT_PROMPT = """
A student asked a career counseling chatbot this question:
"{question}"

If the question is about ONE specific career or profession, return:
{{"career": "<standard career name, singular, Title Case, e.g. Cybersecurity Analyst>"}}

If it is NOT about a specific career (greeting, off-topic, vague, or about
several careers), return:
{{"career": null}}

Return ONLY the JSON object.
"""


def extract_career(question: str):
    """Ask the LLM for the career name. Returns a string or None."""
    raw = _generate(EXTRACT_PROMPT.format(question=question.replace('"', "'")))
    if raw == FRIENDLY_ERROR:
        return None
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return None
    try:
        name = json.loads(match.group(0)).get("career")
    except json.JSONDecodeError:
        return None
    if not isinstance(name, str):
        return None
    name = name.strip()
    return name if 2 < len(name) < 60 else None


def read_seed_names() -> set:
    if not SEED_PATH.exists():
        return set()
    return {
        line.strip().lower()
        for line in SEED_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }


def read_kb_names() -> set:
    if not CAREERS_PATH.exists():
        return set()
    with open(CAREERS_PATH, "r", encoding="utf-8") as f:
        return {c["career"].lower() for c in json.load(f)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--yes", action="store_true", help="skip confirmation")
    parser.add_argument("--run", action="store_true",
                        help="also run expand_kb and build_embeddings")
    args = parser.parse_args()

    if not MISSING_PATH.exists():
        print("No missing_queries.jsonl yet - nothing to process.")
        return

    lines = [l for l in MISSING_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    records = []
    for line in lines:
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            pass

    print(f"Questions to process: {len(records)}\n")

    counts = Counter()
    display_name = {}

    for i, rec in enumerate(records, start=1):
        question = rec.get("question", "")
        name = extract_career(question)
        shown = name if name else "(not a specific career)"
        print(f"[{i}/{len(records)}] {question[:60]!r:<64} -> {shown}")
        if name:
            counts[name.lower()] += 1
            display_name.setdefault(name.lower(), name)
        time.sleep(1)  # be gentle with rate limits

    known = read_kb_names() | read_seed_names()
    candidates = [
        (display_name[key], n)
        for key, n in counts.most_common()
        if key not in known and n >= MIN_COUNT
    ]

    print()
    if not candidates:
        print("No new careers to add (all already known, or not career questions).")
        _archive(lines)
        return

    print("New careers students asked about:")
    for name, n in candidates:
        print(f"  - {name}  (asked {n}x)")

    if not args.yes:
        answer = input("\nAdd these to career_seed_list.txt? [y/N] ").strip().lower()
        if answer != "y":
            print("Cancelled. Nothing changed (log kept for next time).")
            return

    text = SEED_PATH.read_text(encoding="utf-8") if SEED_PATH.exists() else ""
    if text and not text.endswith("\n"):
        text += "\n"
    text += "\n# --- Added from student questions ---\n"
    text += "\n".join(name for name, _ in candidates) + "\n"
    SEED_PATH.write_text(text, encoding="utf-8")
    print(f"\nAdded {len(candidates)} career(s) to {SEED_PATH.name}")

    _archive(lines)

    if args.run:
        print("\nGenerating entries (expand_kb)...")
        subprocess.run([sys.executable, "-m", "backend.services.expand_kb"],
                       cwd=PROJECT_ROOT)
        print("\nBuilding embeddings (build_embeddings)...")
        subprocess.run([sys.executable, "-m", "backend.services.build_embeddings"],
                       cwd=PROJECT_ROOT)
        print("\nDone. RESTART the backend so it loads the new embeddings.")
    else:
        print("\nNext:")
        print("  python -m backend.services.expand_kb")
        print("  python -m backend.services.build_embeddings")
        print("  then restart the backend")


def _archive(lines: list):
    """Move processed log lines to the .done file so they aren't counted twice."""
    with open(DONE_PATH, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    MISSING_PATH.unlink()


if __name__ == "__main__":
    main()
