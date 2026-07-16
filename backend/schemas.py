from pydantic import BaseModel

class FileLoadRequest(BaseModel):
    file_path: str

class QuestionRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    answer: str
    status: str = "success"