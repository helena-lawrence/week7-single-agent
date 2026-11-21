
from qdrant_retriever import query_notes

question = "How does LangGraph manage state?"

print("Question:", question)
print("\nRetrieved documents:\n")

results = query_notes(question)

print(results)
