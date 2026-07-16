import os
from groq import Groq
from dotenv import load_dotenv
from usage_tracker import log_usage

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("GROQ_API_KEY not found in .env file.")

client = Groq(api_key=api_key)

def ask_flant5(question: str, context: str = "") -> str:
    if context:
        prompt = f"Answer the question based on the context.\nContext: {context}\nQuestion: {question}\nAnswer:"
    else:
        prompt = f"Question: {question}\nAnswer:"

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=150
        )
        # Extract usage
        usage = response.usage
        log_usage(
            question=question,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
            model="llama-3.3-70b-versatile"
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Groq API error: {e}")
        return "I'm sorry, I couldn't process your question right now."