import re

with open('frontend/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

js_blocks = re.findall(r'<script>(.*?)</script>', text, flags=re.DOTALL)
for i, b in enumerate(js_blocks):
    print(f'JS Block {i} Length: {len(b)}')
    
