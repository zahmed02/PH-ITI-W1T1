# main.py
from file_loader import load_file
from vector_store import VectorStore
from llm_interface import ask_flant5

file_path = "company_sales.xlsx"
full_text = load_file(file_path)

store = VectorStore()
chunks = store.chunk_text(full_text)
store.build_index(chunks)
print(f"Indexed {len(chunks)} chunks.")

while True:
    query = input("\nAsk a question (or type 'exit'): ")
    if query.lower() == 'exit':
        break
    relevant_chunks = store.search(query, top_k=3)
    context = "\n".join(relevant_chunks)
    answer = ask_flant5(query, context)
    print(f"\nAnswer: {answer}")