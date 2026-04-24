import sys
import os
sys.stdout.reconfigure(line_buffering=True)

from dotenv import load_dotenv
load_dotenv()

from ingestion.pdf_loader import load_pdf
from chunking.chunker import process_blocks
from classification.rule_classifier import classify_chunk, assign_compliance_framework
from embedding.embedder import embed_chunks, build_sentence_embedding_units
from vectorstore.chroma_store import upsert_chunks, count_records

PDF_PATH = "output/Tamilnadu_policy_notes.pdf"

print("Step 1: Extracting PDF...")
blocks = load_pdf(PDF_PATH, "governance_policy", "TamilNadu Government")        
print(f"  Blocks extracted: {len(blocks)}")
if not blocks:
    print("ERROR: No blocks extracted. Exiting.")
    sys.exit(1)

print("Step 2: Chunking...")
chunks = process_blocks(blocks)

print("Step 3: Classifying...")
classified = []
for c in chunks:
    c = classify_chunk(c)
    if not c.get("compliance_framework"):
        c["compliance_framework"] = assign_compliance_framework(
            c.get("text", ""), c.get("source_url", "")
        )
    classified.append(c)
print(f"  Classified: {len(classified)}")

print("Step 4: Embedding...")
sentence_units = build_sentence_embedding_units(classified)
vectors = embed_chunks(sentence_units)
print(f"  Vectors produced: {len(vectors)}")

print("Step 5: Upserting into ChromaDB...")
upsert_chunks(sentence_units, vectors)
final_count = count_records()
print(f"  Records in DB: {final_count}")

print("\nPipeline complete. ChromaDB is ready.")
