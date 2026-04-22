with open('retrieval/retriever.py', 'r', encoding='utf-8') as f:
    t = f.read()

old_context = \"\"\"        context_parts.append(
            f"[Chunk {i}]\\n"
            f"Section : {section}\\n"
            f"Source  : {source}\\n"
            f"Domain  : {domain}\\n"
            f"Score   : {score:.4f}\\n"
            f"Text    : {text}\\n"
        )\"\"\"

new_context = \"\"\"        context_parts.append(
            f"[Chunk {i}]\\n"
            f"Chunk ID: {r.get('chunk_id', '')}\\n"
            f"Section : {section}\\n"
            f"Source  : {source}\\n"
            f"Domain  : {domain}\\n"
            f"Score   : {score:.4f}\\n"
            f"Text    : {text}\\n"
        )\"\"\"

t = t.replace(old_context, new_context)

with open('retrieval/retriever.py', 'w', encoding='utf-8') as f:
    f.write(t)
