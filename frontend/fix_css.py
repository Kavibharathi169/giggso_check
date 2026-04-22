import re

with open('frontend/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('.dropzone:hover', '.dropzone:hover, .dragover')

with open('frontend/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Replaced indiscriminately")
