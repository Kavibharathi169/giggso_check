with open('llm/generator.py', 'r', encoding='utf-8') as f:
    t = f.read()

import re

# Update _validate_items
t = t.replace('            \\"source_url\\"         : \\"\\",\\n            \\"chunk_id\\"           : \\"\\",', '            \\"source_url\\"         : \\"\\",\\n            \\"chunk_id\\"           : str(item.get(\\"chunk_id\\", \\"\\")),')

# Update _enrich_with_metadata
old_enrich = \"\"\"    # Build lookup: section_title -> metadata
    section_map = {}
    for r in results:
        meta    = r.get("metadata", {})
        section = meta.get("section_title", "")
        if section and section not in section_map:
            section_map[section] = meta

    for item in items:
        source_section = item.get("source_section", "")

        # Try exact match first
        meta = section_map.get(source_section)

        # Try partial match if no exact match
        if not meta:
            for sec, m in section_map.items():
                if (
                    source_section.lower() in sec.lower()
                    or sec.lower() in source_section.lower()
                ):
                    meta = m
                    break

        if meta:
            item["source_url"]           = meta.get("source_url","")
            item["chunk_id"]             = meta.get("chunk_id","")  if "chunk_id" in meta else ""
            item["compliance_framework"] = meta.get("compliance_framework","")  \"\"\"

new_enrich = \"\"\"    # Build lookup: chunk_id -> metadata
    chunk_map = {}
    for r in results:
        cid  = r.get("chunk_id", "")
        meta = r.get("metadata", {})
        if cid:
            chunk_map[cid] = meta

    for item in items:
        cid = item.get("chunk_id", "")
        meta = chunk_map.get(cid)

        if meta:
            item["source_url"]           = meta.get("source_url","")
            item["compliance_framework"] = meta.get("compliance_framework","")  
        else:
            item["source_url"]           = ""
            item["compliance_framework"] = "" \"\"\"

t = t.replace(old_enrich, new_enrich)

with open('llm/generator.py', 'w', encoding='utf-8') as f:
    f.write(t)
