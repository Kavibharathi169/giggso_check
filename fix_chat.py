import re, os
with open("app.py", "r", encoding="utf-8") as text_file:
    text = text_file.read()

pattern = r'q_col, d_col, btn_col = st\.columns\(\[5, 1\.5, 1\]\)\n\s+with q_col:\n\s+query = st\.chat_input\("Ask about the policies\.\.\."\)'
new_chat = 'query = st.chat_input("Ask about the policies...")'

text = re.sub(pattern, new_chat, text)

with open("app.py", "w", encoding="utf-8") as text_file:
    text_file.write(text)
print("done chat fix")
