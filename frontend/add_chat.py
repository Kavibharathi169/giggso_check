import re

with open('frontend/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Update grid template columns
old_css = '''.panel-grid {
      display: grid;
      grid-template-columns: 220px 1fr;
      gap: 20px;
      align-items: start;
    }'''
    
new_css = '''.panel-grid {
      display: grid;
      grid-template-columns: 220px 1fr 340px;
      gap: 20px;
      align-items: start;
    }

    .chatbot {
      background: #fff;
      border: 1px solid #e5e7eb;
      border-radius: 12px;
      display: flex;
      flex-direction: column;
      height: calc(100vh - 230px);
      overflow: hidden;
    }
    .chat-header {
      padding: 14px;
      border-bottom: 1px solid #e5e7eb;
      font-weight: 600;
      color: #111827;
      background: #f8fafc;
    }
    .chat-messages {
      flex: 1;
      padding: 14px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 12px;
      font-size: 0.875rem;
    }
    .chat-msg {
      max-width: 85%;
      padding: 10px 14px;
      border-radius: 12px;
      line-height: 1.4;
    }
    .chat-msg.user {
      background: #2563eb;
      color: #fff;
      align-self: flex-end;
      border-bottom-right-radius: 4px;
    }
    .chat-msg.bot {
      background: #f1f5f9;
      color: #111827;
      align-self: flex-start;
      border-bottom-left-radius: 4px;
    }
    .chat-input-area {
      padding: 12px;
      border-top: 1px solid #e5e7eb;
      display: flex;
      gap: 8px;
    }
    .chat-input-area input {
      flex: 1;
      height: 40px;
      border-radius: 8px;
      border: 1px solid #d1d5db;
      padding: 0 12px;
      font-size: 0.875rem;
      font-family: inherit;
    }
    .chat-input-area button {
      background: #2563eb;
      color: #fff;
      border: none;
      border-radius: 8px;
      padding: 0 14px;
      font-weight: 600;
      cursor: pointer;
    }
    .chat-input-area button:disabled {
      background: #9ca3af;
      cursor: not-allowed;
    }
'''

content = content.replace(old_css, new_css)

old_html = '''            <div class="content" id="resultsContent">
              <div class="readiness">
                <div class="readiness-top">
                  <span class="readiness-label">OVERALL COMPLIANCE READINESS</span>
                  <span class="readiness-pct" id="readinessPct">100%</span>
                </div>
                <div class="bar"><div style="width:100%;"></div></div>
              </div>
              <div id="checklistsContainer">
              <!-- Items inserted dynamically -->
              </div>
            </div>
          </div>
        </section>'''

new_html = '''            <div class="content" id="resultsContent">
              <div class="readiness">
                <div class="readiness-top">
                  <span class="readiness-label">OVERALL COMPLIANCE READINESS</span>
                  <span class="readiness-pct" id="readinessPct">100%</span>
                </div>
                <div class="bar"><div style="width:100%;"></div></div>
              </div>
              <div id="checklistsContainer">
              <!-- Items inserted dynamically -->
              </div>
            </div>
            
            <aside class="chatbot">
              <div class="chat-header">AI Compliance Assistant</div>
              <div class="chat-messages" id="chatMessages">
                <div class="chat-msg bot">Hello! I am ready to answer any questions about the uploaded document based on its extracted compliance data.</div>
              </div>
              <form class="chat-input-area" id="chatForm">
                <input type="text" id="chatInput" placeholder="Ask a question..." required />
                <button type="submit" id="chatSendBtn">Send</button>
              </form>
            </aside>
            
          </div>
        </section>'''

content = content.replace(old_html, new_html)

old_js = '''      fileInput.addEventListener("change", (e) => {'''

new_js = '''
      const chatForm = document.getElementById("chatForm");
      const chatInput = document.getElementById("chatInput");
      const chatMessages = document.getElementById("chatMessages");
      const chatSendBtn = document.getElementById("chatSendBtn");

      chatForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const text = chatInput.value.trim();
        if(!text) return;
        
        // Add User message
        const userDiv = document.createElement("div");
        userDiv.className = "chat-msg user";
        userDiv.textContent = text;
        chatMessages.appendChild(userDiv);
        
        chatInput.value = "";
        chatSendBtn.disabled = true;
        chatInput.disabled = true;
        
        // Add Bot placeholder
        const botDiv = document.createElement("div");
        botDiv.className = "chat-msg bot";
        botDiv.textContent = "Thinking...";
        chatMessages.appendChild(botDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        try {
          const payload = {
            query: text,
            domain: currentDomain || "all",
            user_id: sessionUserId
          };
          
          const res = await fetch(${API_BASE}/api/chat, {
              method: "POST",
              headers: {"Content-Type": "application/json"},
              body: JSON.stringify(payload)
          });
          
          const data = await res.json();
          botDiv.innerHTML = data.response.replace(/\\n/g, "<br>");
        } catch(err) {
          botDiv.textContent = "Error communicating with Assistant.";
        }
        
        chatSendBtn.disabled = false;
        chatInput.disabled = false;
        chatInput.focus();
        chatMessages.scrollTop = chatMessages.scrollHeight;
      });

      fileInput.addEventListener("change", (e) => {'''

content = content.replace(old_js, new_js)

with open('frontend/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

