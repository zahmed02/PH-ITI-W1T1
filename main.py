from file_loader import load_file
from vector_store import VectorStore
from llm_interface import ask_flant5

# 1. Load and chunk the file
file_path = "company_sales.xlsx"   # change to your file
full_text = load_file(file_path)

store = VectorStore()
chunks = store.chunk_text(full_text)
store.build_index(chunks)
print(f"Indexed {len(chunks)} chunks.")

# 2. Interactive Q&A loop
while True:
    query = input("\nAsk a question (or type 'exit'): ")
    if query.lower() == 'exit':
        break
    relevant_chunks = store.search(query, top_k=3)
    context = "\n".join(relevant_chunks)
    answer = ask_flant5(query, context)
    print(f"\nAnswer: {answer}")
