import re

with open('frontend/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Add view animations
css_view_pattern = r'\.view\s*{\s*display:\s*none;\s*}\s*\.view\.active\s*{\s*display:\s*block;\s*}'
css_view_replacement = '''
    .view { display: none; opacity: 0; }
    .view.active { display: block; animation: fadeIn 0.4s ease forwards; }
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }
'''
if re.search(css_view_pattern, html):
    html = re.sub(css_view_pattern, css_view_replacement, html)

# 2. Add Top Navigation Styles
css_nav = '''
    .top-nav {
      display: flex;
      gap: 32px;
      align-items: center;
    }
    .top-nav a {
      text-decoration: none;
      color: #4b5563;
      font-weight: 600;
      font-size: 0.9375rem;
      transition: color 0.2s;
      cursor: pointer;
    }
    .top-nav a:hover, .top-nav a.active {
      color: #2563eb;
    }
    .brand { cursor: pointer; }
'''
# inject css_nav before .tagline
html = html.replace('.tagline {', css_nav + '\n    .tagline {')

# 3. Add toggleable chatbot Styles
css_chat = '''
    .chatbot {
      transform: translateY(120%);
      opacity: 0;
      transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.3s;
      pointer-events: none;
    }
    .chatbot.open {
      transform: translateY(0);
      opacity: 1;
      pointer-events: auto;
    }
    .chat-toggler {
      position: fixed;
      bottom: 24px;
      right: 24px;
      width: 60px;
      height: 60px;
      border-radius: 50%;
      background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
      box-shadow: 0 4px 15px rgba(37,99,235,0.4);
      border: 2px solid rgba(255,255,255,0.4);
      display: grid;
      place-items: center;
      color: white;
      cursor: pointer;
      z-index: 10000;
      transition: transform 0.2s;
    }
    .chat-toggler:hover { transform: scale(1.05); }
    .chat-toggler svg { width: 28px; height: 28px; }
'''
html = html.replace('.chat-header {', css_chat + '\n    .chat-header {')

# 4. Modify Topbar HTML
topbar_pattern = r'(<header class="topbar">)(.*?)(</header>)'
def topbar_replacer(m):
    original = m.group(2)
    # Add onclick to brand
    original = original.replace('<div class="brand">', '<div class="brand" onclick="location.reload()">')
    # Add nav
    nav_html = '''
      <nav class="top-nav">
        <a class="active" onclick="location.reload()">Home</a>
        <a onclick="alert('Document history coming soon!')">History</a>
        <a onclick="alert('Settings coming soon!')">Settings</a>
      </nav>
    '''
    # We replace tagline with the nav
    original_without_tagline = re.sub(r'<div class="tagline">.*?</div>', nav_html, original)
    return f"{m.group(1)}{original_without_tagline}{m.group(3)}"

html = re.sub(topbar_pattern, topbar_replacer, html, flags=re.DOTALL)

# 5. Modify resultView's "Start Over" button
btn_icon_pattern = r'<button type="button" class="btn-icon" title="New Document" aria-label="New Document" id="newDocBtn">.*?</button>'
new_btn = '''<button type="button" class="btn-outline" title="Start Over" id="newDocBtn">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
                Start Over
              </button>'''
html = re.sub(btn_icon_pattern, new_btn, html, flags=re.DOTALL)

# 6. Add Chat Toggler Button and Header Close logic
body_end_pattern = r'(<script>)'
toggler_html = '''
  <button class="chat-toggler" id="chatToggleBtn" aria-label="Toggle AI Assistant" title="Open AI Assistant">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
    </svg>
  </button>
'''
html = html.replace('</body>', toggler_html + '\n</body>')

# Replace chat header to add close button
chat_header_new = '''
    <div class="chat-header" style="display:flex; justify-content:space-between; align-items:center;">
        <span>AI Assistant Governance Guide</span>
        <button id="closeChatBtn" style="background:none;border:none;color:#111827;cursor:pointer;font-size:1.2rem;">&times;</button>
    </div>
'''
html = re.sub(r'<div class="chat-header">.*?</div>', chat_header_new, html, flags=re.DOTALL)

# Inject JS for chat toggler
js_append = '''
    const chatToggleBtn = document.getElementById("chatToggleBtn");
    const closeChatBtn = document.getElementById("closeChatBtn");
    const chatbotWin = document.querySelector(".chatbot");
    
    if(chatToggleBtn && chatbotWin) {
      chatToggleBtn.addEventListener("click", () => {
        chatbotWin.classList.add("open");
        chatToggleBtn.style.display = "none";
      });
    }
    if(closeChatBtn && chatbotWin) {
      closeChatBtn.addEventListener("click", () => {
        chatbotWin.classList.remove("open");
        chatToggleBtn.style.display = "grid";
      });
    }
'''
html = html.replace('</script>', js_append + '\n  </script>')

with open('frontend/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("Navigation and UI improvements applied!")
