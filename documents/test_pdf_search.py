"""Verify PDF retrieval and source/page metadata. Accept a custom question."""
import sys
from qdrant_retriever import query_notes

question = ' '.join(sys.argv[1:]).strip() or 'How does LangGraph handle checkpoints and state?'
print('Question:', question)
print('\nRetrieved evidence:\n')
print(query_notes(question))
