import asyncio
from vectorstore.chroma_store import upsert_chunks
from embedding.embedder import embed_chunks, build_sentence_embedding_units
import logging

logging.basicConfig(level=logging.INFO)

chunk = {
    "chunk_id": "test_1",
    "text": "The company must maintain records of all financial transactions for a minimum of 10 years. All data must be encrypted.",
    "user_id": "test_user_123",
    "section_title": "Financial Policy",
    "content_domain": "financial_compliance"
}

units = build_sentence_embedding_units([chunk])
vectors = embed_chunks(units)
upsert_chunks(units, vectors)

payload = {
    'query': 'Extract all compliance policies, requirements, and checklist items. Strictly format as JSON.',
    'domain': 'all',
    'user_id': 'test_user_123'
}
import requests
res = requests.post('http://127.0.0.1:8000/api/chat', json=payload)
data = res.json()
print("DATA received:")
print(data.get('raw_data'))
