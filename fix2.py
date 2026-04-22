import re, os
with open("app.py", "r", encoding="utf-8") as f:
    text = f.read()

text = re.sub(
    r"if not st\.session_state\.checklist:\n\s+import time\n.*?\]", 
    """if not st.session_state.checklist:
                            import time, json, os
                            time.sleep(0.5)
                            sample_path = os.path.join('data', 'checklist-governance_policy_sample.json')
                            if os.path.exists(sample_path):
                                with open(sample_path, 'r', encoding='utf-8') as jf:
                                    st.session_state.checklist = json.load(jf)
                            else:
                                st.session_state.checklist = []""", 
    text, 
    flags=re.DOTALL
)

text = re.sub(
    r"else:\n\s+st\.session_state\.checklist = \[\n.*?\]\n", 
    """else:
                        import json, os
                        sample_path = os.path.join('data', 'checklist-governance_policy_sample.json')
                        if os.path.exists(sample_path):
                            with open(sample_path, 'r', encoding='utf-8') as jf:
                                st.session_state.checklist = json.load(jf)
                        else:
                            st.session_state.checklist = []
""", 
    text, 
    flags=re.DOTALL
)

# Fix the badge domains and source mappings
text = re.sub(
    r"if \"badge\" not in c: c\[\"badge\"\], _ = get_badge_info\(c\.get\(\"domain\", \"\"\)\)\n\s+if \"source\" not in c: c\[\"source\"\] = c\.get\(\"source_section\", c\.get\(\"source\", \"N/A\"\)\)",
    """domain_str = str(c.get("domain", "")).lower().replace(" ", "_")
                            if "badge" not in c: c["badge"], _ = get_badge_info(domain_str)
                            if "source" not in c: c["source"] = c.get("sourceSection", c.get("source_section", c.get("source", "N/A")))""",
    text,
    flags=re.DOTALL
)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(text)
