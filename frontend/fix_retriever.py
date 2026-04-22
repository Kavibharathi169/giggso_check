import re

with open('retrieval/retriever.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_logic = '''    # Intercept generic checklist prompt and transform it to semantic keywords  
    if "Strictly format as JSON" in query:
        search_query = "compliance requirement rule policy obligation procedure control standard"
    else:
        search_query = query'''

new_logic = '''    # Intercept generic checklist prompt and transform it to semantic keywords  
    if "checklist" in query.lower() or "compliance rules" in query.lower() or "strictly format as json" in query.lower():
        search_query = "compliance requirement rule policy obligation procedure control standard"
    else:
        search_query = query'''

content = content.replace(old_logic, new_logic)

with open('retrieval/retriever.py', 'w', encoding='utf-8') as f:
    f.write(content)
