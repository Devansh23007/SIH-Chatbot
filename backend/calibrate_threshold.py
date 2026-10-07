"""
calibrate_threshold.py - find good STRONG_MATCH / WEAK_MATCH values.

Put this file in backend/ (next to main.py) and run from inside backend/:
    python calibrate_threshold.py

Edit the two lists with questions that match YOUR knowledge base.
"""

import time

from services.rag_service import search_careers

# Careers you KNOW are in careers.json
IN_KB = [
    "I want to become a data engineer",
    "how do I become a pilot",
    "what should I study to be a doctor",
    "tell me about being an architect",
    "career in graphic design",
]

# Careers you KNOW are NOT in careers.json (check your file!) plus off-topic
NOT_IN_KB = [
    "I want to become a cybersecurity analyst",
    "how to become a sommelier",
    "career as a lighthouse keeper",
    "hello how are you",
    "what is the weather today",
]


def run(label, questions):
    print(f"\n--- {label} ---")
    scores = []
    for q in questions:
        top = search_careers(q, top_k=1)[0]
        scores.append(top["similarity"])
        print(f"{top['similarity']:.3f}  {top['career']:<28}  <- {q}")
        time.sleep(1)           # be gentle with the embedding quota
    return scores


in_scores = run("IN knowledge base", IN_KB)
out_scores = run("NOT in knowledge base", NOT_IN_KB)

print("\nLowest 'in KB' score  :", round(min(in_scores), 3))
print("Highest 'not in KB'   :", round(max(out_scores), 3))
print("Pick STRONG_MATCH just below the lowest 'in KB' score,")
print("and WEAK_MATCH a bit above the highest 'not in KB' score.")
