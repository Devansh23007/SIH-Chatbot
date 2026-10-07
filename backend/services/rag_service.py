import json
import os
from pathlib import Path

import numpy as np
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
# Load original career information
# --------------------------------------------------

def load_careers():
    """Load structured career information."""

    with open(CAREER_DATA_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


# --------------------------------------------------
# Load stored embeddings
# --------------------------------------------------

_EMBEDDINGS_CACHE = None

def load_embeddings():
    global _EMBEDDINGS_CACHE
    if _EMBEDDINGS_CACHE is None:
        with open(EMBEDDINGS_PATH, "r", encoding="utf-8") as file:
            _EMBEDDINGS_CACHE = json.load(file)
    return _EMBEDDINGS_CACHE


# --------------------------------------------------
# Create embedding for a question
# --------------------------------------------------

def create_query_embedding(question: str):
    """Convert the student's question into an embedding."""

    response = client.models.embed_content(
        model="models/gemini-embedding-2",
        contents=question
    )

    return np.array(response.embeddings[0].values)


# --------------------------------------------------
# Cosine similarity
# --------------------------------------------------

def cosine_similarity(vector_a, vector_b):
    """Calculate cosine similarity between two vectors."""

    return np.dot(vector_a, vector_b) / (
        np.linalg.norm(vector_a) * np.linalg.norm(vector_b)
    )


# --------------------------------------------------
# Search careers
# --------------------------------------------------

def search_careers(question: str, top_k: int = 3):
    """
    Find the most relevant careers for a student question.
    """

    question_embedding = create_query_embedding(question)

    career_embeddings = load_embeddings()

    results = []

    for career in career_embeddings:

        career_vector = np.array(career["embedding"])

        similarity = cosine_similarity(
            question_embedding,
            career_vector
        )

        results.append({
            "career": career["career"],
            "similarity": float(similarity),
            "text": career["text"]
        })

    # Highest similarity first
    results.sort(
        key=lambda item: item["similarity"],
        reverse=True
    )

    return results[:top_k]