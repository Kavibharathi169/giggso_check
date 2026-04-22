import asyncio
from retrieval.retriever import retrieve_and_format
from vectorstore.chroma_store import count_records

async def test():
    print("Records in DB:", count_records())
    r, c = retrieve_and_format("compliance requirements", top_k=2)
    print(f"Results: {len(r)}")
    if r:
        print(r[0])

asyncio.run(test())
