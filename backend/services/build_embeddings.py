import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai


# --------------------------------------------------
# Project paths
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

CAREER_DATA_PATH = (
    PROJECT_ROOT
    / "knowledge_base"
    / "documents"
    / "careers.json"
)

EMBEDDINGS_PATH = (
    PROJECT_ROOT
    / "knowledge_base"
    / "career_embeddings.json"
)


# --------------------------------------------------
# Load environment
# --------------------------------------------------

load_dotenv(PROJECT_ROOT / ".env")

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY was not found in .env")


# --------------------------------------------------
# Gemini client
# --------------------------------------------------

client = genai.Client(api_key=api_key)


# --------------------------------------------------
# Load career data
# --------------------------------------------------

with open(CAREER_DATA_PATH, "r", encoding="utf-8") as file:
    careers = json.load(file)


# --------------------------------------------------
# Generate embeddings
# --------------------------------------------------

embedded_careers = []

for career in careers:

    text = f"""
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

    response = client.models.embed_content(
        model="models/gemini-embedding-2",
        contents=text
    )

    embedding = response.embeddings[0].values

    embedded_careers.append({
        "career": career["career"],
        "text": text,
        "embedding": embedding
    })

    print(f"Embedded: {career['career']}")


# --------------------------------------------------
# Save embeddings
# --------------------------------------------------

with open(EMBEDDINGS_PATH, "w", encoding="utf-8") as file:
    json.dump(embedded_careers, file, indent=2)


print()
print(f"Saved {len(embedded_careers)} career embeddings.")
print(f"File: {EMBEDDINGS_PATH}")