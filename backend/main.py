from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from services.llm_service import (
    generate_response,
    generate_career_response
)

from services.rag_service import search_careers


app = FastAPI(title="SIH Career Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str


@app.get("/")
def root():
    return {
        "message": "SIH Career Chatbot backend is running"
    }


@app.post("/api/chat")
def chat(request: ChatRequest):

    response = generate_response(request.message)

    return {
        "response": response
    }

@app.post("/api/career-chat")
def career_chat(request: ChatRequest):

    results = search_careers(
        request.message,
        top_k=1
    )

    retrieved_context = results[0]["text"]

    response = generate_career_response(
        question=request.message,
        retrieved_context=retrieved_context
    )

    return {
        "response": response,
        "career": results[0]["career"],
        "similarity": results[0]["similarity"]
    }