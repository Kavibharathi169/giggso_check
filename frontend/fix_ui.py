import re

with open('frontend/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# I will carefully replace the JS fileInput listener area to add the chat listener
# And ensure e.preventDefault is there.

old_js = '''    fileInput.addEventListener("change", () => {
      if (!fileInput.files.length) return;
      startAnalysis(fileInput.files[0]);
    });'''

new_js = '''
    const chatForm = document.getElementById("chatForm");
    const chatInput = document.getElementById("chatInput");
    const chatMessages = document.getElementById("chatMessages");
    const chatSendBtn = document.getElementById("chatSendBtn");

    if (chatForm) {
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
          
          const res = await fetch(/api/chat, {
              method: "POST",
              headers: {"Content-Type": "application/json"},
              body: JSON.stringify(payload)
          });
          
          const data = await res.json();
          let htmlResp = data.response || "No response";
          htmlResp = htmlResp.replace(/\\n/g, "<br>");
          botDiv.innerHTML = htmlResp;
        } catch(err) {
          botDiv.textContent = "Error communicating with Assistant.";
        }
        
        chatSendBtn.disabled = false;
        chatInput.disabled = false;
        chatInput.focus();
        chatMessages.scrollTop = chatMessages.scrollHeight;
      });
    }

    fileInput.addEventListener("change", () => {
      if (!fileInput.files.length) return;
      startAnalysis(fileInput.files[0]);
    });'''

if old_js in text:
    text = text.replace(old_js, new_js)
    with open('frontend/index.html', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Injected Chat JS")
else:
    print("Could not find old_js")

