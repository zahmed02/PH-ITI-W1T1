# llm_interface.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("HF_API_TOKEN")
if not API_TOKEN:
    raise ValueError("HF_API_TOKEN not found in .env file.")

API_URL = "https://api-inference.huggingface.co/models/google/flan-t5-xl"
HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}

def ask_flant5(question: str, context: str = "") -> str:
    """
    Send a prompt to Flan-T5-XL and return the generated answer.
    """
    # Build a clear instruction prompt
    if context:
        prompt = f"Answer the question based on the context.\nContext: {context}\nQuestion: {question}\nAnswer:"
    else:
        prompt = f"Question: {question}\nAnswer:"

    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 150,
            "temperature": 0.3,   # lower for more factual answers
            "return_full_text": False
        }
    }

    try:
        response = requests.post(API_URL, headers=HEADERS, json=payload)
        response.raise_for_status()
        result = response.json()
        # The API returns a list of generated texts
        return result[0]['generated_text'].strip()
    except requests.exceptions.RequestException as e:
        print(f"API error: {e}")
        print("Response:", response.text if 'response' in locals() else "No response")
        return "I'm sorry, I couldn't process your question right now."