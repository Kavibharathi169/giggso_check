import re

with open('frontend/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

old_code = '''    localTab.addEventListener("click", () => setTab("local"));
    cloudTab.addEventListener("click", () => setTab("cloud"));'''

old_code_2 = '''      localTab.addEventListener("click", () => setTab("local"));
      cloudTab.addEventListener("click", () => setTab("cloud"));'''

new_code = '''      localTab.addEventListener("click", () => setTab("local"));
      cloudTab.addEventListener("click", () => setTab("cloud"));

      dropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropzone.classList.add("dragover");
      });
      dropzone.addEventListener("dragleave", (e) => {
        e.preventDefault();
        dropzone.classList.remove("dragover");
      });
      dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropzone.classList.remove("dragover");
        if (e.dataTransfer.files.length) {
          fileInput.files = e.dataTransfer.files;
          fileInput.dispatchEvent(new Event("change"));
        }
      });
      dropzone.addEventListener("click", (e) => {
        if (e.target !== fileInput) {
          e.preventDefault();
          fileInput.click();
        }
      });'''

if old_code_2 in text:
    text = text.replace(old_code_2, new_code)
elif old_code in text:
    text = text.replace(old_code, new_code)

with open('frontend/index.html', 'w', encoding='utf-8') as f:
    f.write(text)

