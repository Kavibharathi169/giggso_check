import re

with open('frontend/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix CSV download
text = text.replace(
'''       const a = document.createElement("a");
       a.href = URL.createObjectURL(blob);
       a.download = "governance_export.csv";
       a.click();''',
'''       const a = document.createElement("a");
       a.href = URL.createObjectURL(blob);
       a.download = "governance_export.csv";
       document.body.appendChild(a);
       a.click();
       document.body.removeChild(a);'''
)

# Fix JSON download
text = text.replace(
'''       const a = document.createElement("a");
       a.href = URL.createObjectURL(blob);
       a.download = "governance_export.json";
       a.click();''',
'''       const a = document.createElement("a");
       a.href = URL.createObjectURL(blob);
       a.download = "governance_export.json";
       document.body.appendChild(a);
       a.click();
       document.body.removeChild(a);'''
)

with open('frontend/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Fixed downloads")
