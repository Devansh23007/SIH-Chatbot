import os
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from google import genai

from services.rag_service import load_career_documents


# --------------------------------------------------
# 1. Load environment
# --------------------------------------------------

project_root = Path(__file__).resolve().parent.parent

load_dotenv(project_root / ".env")

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY was not found in .env")


# --------------------------------------------------
# 2. Create Gemini client
# --------------------------------------------------

client = genai.Client(api_key=api_key)


# --------------------------------------------------
# 3. Function to create an embedding
# --------------------------------------------------

def create_embedding(text: str):
    response = client.models.embed_content(
        model="models/gemini-embedding-2",
        contents=text
    )

    return np.array(response.embeddings[0].values)


# --------------------------------------------------
# 4. Cosine similarity
# --------------------------------------------------

def cosine_similarity(vector_a, vector_b):
    return np.dot(vector_a, vector_b) / (
        np.linalg.norm(vector_a) * np.linalg.norm(vector_b)
    )


# --------------------------------------------------
# 5. Load our career knowledge
# --------------------------------------------------

documents = load_career_documents()

print(f"Loaded {len(documents)} career documents")


# --------------------------------------------------
# 6. Create embeddings for each career
# --------------------------------------------------

career_embeddings = []

for document in documents:

    embedding = create_embedding(document["text"])

    career_embeddings.append({
        "career": document["career"],
        "text": document["text"],
        "embedding": embedding
    })

    print(f"Embedded: {document['career']}")


# --------------------------------------------------
# 7. Ask a student-style question
# --------------------------------------------------

question = "I enjoy working with Excel, numbers and analyzing data."

print("\nStudent question:")
print(question)


# --------------------------------------------------
# 8. Embed the question
# --------------------------------------------------

question_embedding = create_embedding(question)


# --------------------------------------------------
# 9. Calculate similarity with every career
# --------------------------------------------------

results = []

for career in career_embeddings:

    similarity = cosine_similarity(
        question_embedding,
        career["embedding"]
    )

    results.append({
        "career": career["career"],
        "similarity": similarity
    })


# --------------------------------------------------
# 10. Sort by similarity
# --------------------------------------------------

results.sort(
    key=lambda item: item["similarity"],
    reverse=True
)


# --------------------------------------------------
# 11. Display ranking
# --------------------------------------------------

print("\nCareer similarity ranking:")

for result in results:
    print(
        f"{result['career']}: "
        f"{result['similarity']:.4f}"
    )