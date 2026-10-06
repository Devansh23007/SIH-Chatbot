import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai


# Find project root
project_root = Path(__file__).resolve().parent.parent

# Load .env
load_dotenv(project_root / ".env")

# Get API key
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY was not found in .env")

# Create Gemini client
client = genai.Client(api_key=api_key)


# Text we want to convert into an embedding
text = "I enjoy working with Excel, numbers, SQL and data."


# Generate embedding
response = client.models.embed_content(
    model="models/gemini-embedding-2",
    contents=text
)


# Get the embedding vector
embedding = response.embeddings[0].values


print("Embedding generated successfully!")
print("Vector dimensions:", len(embedding))
print("First 10 values:")
print(embedding[:10])