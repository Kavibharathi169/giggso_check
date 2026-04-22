import re

with open('frontend/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

old_code = '''    localTab.addEventListener("click", () => setTab("local"));
    cloudTab.addEventListener("click", () => setTab("cloud"));
    dropzone.addEventListener("click", () => fileInput.click());'''

new_code = '''    localTab.addEventListener("click", () => setTab("local"));
    cloudTab.addEventListener("click", () => setTab("cloud"));'''

old_code_2 = '''      localTab.addEventListener("click", () => setTab("local"));
      cloudTab.addEventListener("click", () => setTab("cloud"));
      dropzone.addEventListener("click", () => fileInput.click());'''

new_code_2 = '''      localTab.addEventListener("click", () => setTab("local"));
      cloudTab.addEventListener("click", () => setTab("cloud"));'''

if old_code in text:
    text = text.replace(old_code, new_code)
if old_code_2 in text:
    text = text.replace(old_code_2, new_code_2)

with open('frontend/index.html', 'w', encoding='utf-8') as f:
    f.write(text)

