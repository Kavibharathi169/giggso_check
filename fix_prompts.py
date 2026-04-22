with open('llm/prompt_templates.py', 'r', encoding='utf-8') as f:
    t = f.read()

t = t.replace('5. Traceability: Accurately capture the source section for traceability.', '5. Traceability: Accurately capture the chunk_id and source_section for traceability.')

t = t.replace('    "source_section"   : "Section 3.1: Board Meetings",\\n    "priority"         : "High",', '    "source_section"   : "Section 3.1: Board Meetings",\\n    "chunk_id"         : "a1b2c3d4e5f6g7h8",\\n    "priority"         : "High",')

with open('llm/prompt_templates.py', 'w', encoding='utf-8') as f:
    f.write(t)
