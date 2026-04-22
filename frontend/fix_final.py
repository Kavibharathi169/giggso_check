import re

with open('frontend/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Add Chatbot HTML if missing
chatbot_html = '''
    <div class="chatbot">
      <div class="chat-header" style="display:flex; justify-content:space-between; align-items:center;">
        <span>AI Assistant</span>
        <button id="closeChatBtn" style="background:none;border:none;color:#111827;cursor:pointer;font-size:1.2rem;">&times;</button>
      </div>
      <div class="chat-messages" id="chatMessages">
        <div class="chat-msg bot">Hi! Ask me anything about the requirements or compliance items!</div>
      </div>
      <form class="chat-input-area" id="chatForm">
        <input type="text" id="chatInput" placeholder="Ask a question..." autocomplete="off" />
        <button type="submit" id="chatSendBtn">Send</button>
      </form>
    </div>
'''
if '<div class="chatbot' not in html:
    html = html.replace('</main>', '</main>\n' + chatbot_html)

# 2. Fix the syntax error in fetch for chat
html = html.replace('fetch(/api/chat,', 'fetch(${API_BASE}/api/chat,')

with open('frontend/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("Perfected index.html!")
