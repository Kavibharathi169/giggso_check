import re

with open('frontend/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Revert panel-grid to 2 columns
old_grid = '''.panel-grid {
      display: grid;
      grid-template-columns: 220px 1fr 340px;
      gap: 20px;
      align-items: start;
    }'''

new_grid = '''.panel-grid {
      display: grid;
      grid-template-columns: 220px 1fr;
      gap: 20px;
      align-items: start;
    }'''

if old_grid in text:
    text = text.replace(old_grid, new_grid)

# Make chatbot a floating widget
old_chat_css = '''.chatbot {
      background: #fff;
      border: 1px solid #e5e7eb;
      border-radius: 12px;
      display: flex;
      flex-direction: column;
      height: calc(100vh - 230px);
      overflow: hidden;
    }'''

new_chat_css = '''.chatbot {
      background: #fff;
      border: 1px solid #e5e7eb;
      border-radius: 12px;
      display: flex;
      flex-direction: column;
      height: 450px;
      width: 350px;
      position: fixed;
      bottom: 20px;
      right: 20px;
      box-shadow: 0 10px 25px rgba(0,0,0,0.1);
      z-index: 9999;
      overflow: hidden;
    }'''

if old_chat_css in text:
    text = text.replace(old_chat_css, new_chat_css)

with open('frontend/index.html', 'w', encoding='utf-8') as f:
    f.write(text)

