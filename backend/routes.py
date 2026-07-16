# backend/routes.py
from fastapi import APIRouter, HTTPException
from backend.schemas import FileLoadRequest, QuestionRequest, ChatResponse
from backend.chatbot import chatbot
from usage_tracker import get_total_usage_today, get_usage_summary

router = APIRouter()

@router.post("/load")
async def load_file(request: FileLoadRequest):
    result = chatbot.initialize(request.file_path)
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@router.post("/ask", response_model=ChatResponse)
async def ask_question(request: QuestionRequest):
    if not chatbot.is_initialized:
        raise HTTPException(status_code=400, detail="No file loaded. Please load a file first.")
    try:
        answer = chatbot.ask(request.question)
        return ChatResponse(answer=answer)
    except Exception as e:
        # Catch any unexpected errors and return a proper JSON response
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/usage")
async def get_usage():
    return {
        "today_tokens": get_total_usage_today(),
        "total_tokens": get_usage_summary()["total_tokens"],
        "total_requests": get_usage_summary()["total_requests"],
        "daily_limit": 100000
    }