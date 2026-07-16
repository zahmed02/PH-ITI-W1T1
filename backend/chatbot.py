import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from file_loader import load_file
from vector_store import VectorStore
from llm_interface import ask_flant5

class Chatbot:
    def __init__(self):
        self.store = None
        self.chunks = []
        self.is_initialized = False
    
    def initialize(self, file_path: str):
        try:
            full_text = load_file(file_path)
            self.store = VectorStore()
            self.chunks = self.store.chunk_text(full_text)
            self.store.build_index(self.chunks)
            self.is_initialized = True
            return {"status": "success", "chunks": len(self.chunks)}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def ask(self, question: str) -> str:
        if not self.is_initialized:
            return "Please load a file first."
        relevant_chunks = self.store.search(question, top_k=3)
        context = "\n".join(relevant_chunks)
        answer = ask_flant5(question, context)
        return answer

chatbot = Chatbot()