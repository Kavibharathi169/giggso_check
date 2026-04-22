import re

with open('frontend/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace css inside <style> tags
# Since the css is large, I'll extract it, manipulate it, or just provide a carefully crafted replacement.

new_css = '''
    * { box-sizing: border-box; margin: 0; padding: 0; }
    
    body {
      font-family: "Inter", system-ui, -apple-system, sans-serif;
      /* Smooth gradient background for glass effect to shine */
      background: linear-gradient(135deg, #e0c3fc 0%, #8ec5fc 100%);
      background-attachment: fixed;
      color: #111827;
      -webkit-font-smoothing: antialiased;
    }
    
    /* Background blobs */
    body::before, body::after {
      content: '';
      position: fixed;
      border-radius: 50%;
      z-index: -1;
      filter: blur(80px);
    }
    body::before {
      width: 500px; height: 500px;
      top: -10%; right: -5%;
      background: rgba(167, 139, 250, 0.5);
    }
    body::after {
      width: 600px; height: 600px;
      bottom: -10%; left: -10%;
      background: rgba(59, 130, 246, 0.5);
    }

    .app {
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }
    
    /* Glassmorphism Base Styles */
    .glass {
      background: rgba(255, 255, 255, 0.4);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1px solid rgba(255, 255, 255, 0.6);
      box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07);
    }

    .topbar {
      height: 64px;
      background: rgba(255, 255, 255, 0.25);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border-bottom: 1px solid rgba(255, 255, 255, 0.4);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 28px;
      position: sticky;
      top: 0;
      z-index: 50;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      font-weight: 700;
      font-size: 1.125rem;
      color: #111827;
      letter-spacing: -0.02em;
    }
    .logo-mark {
      width: 40px;
      height: 40px;
      border-radius: 10px;
      background: rgba(37, 99, 235, 0.85);
      backdrop-filter: blur(4px);
      display: grid;
      place-items: center;
      flex-shrink: 0;
      box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
    }
    .logo-mark svg { width: 22px; height: 22px; color: #fff; }
    .tagline {
      color: #4b5563;
      font-size: 0.8125rem;
      font-weight: 500;
      max-width: 320px;
      text-align: right;
      line-height: 1.35;
    }
    
    .page {
      width: min(960px, 94%);
      margin: 0 auto;
      padding: 48px 0 40px;
      flex: 1;
    }
    .center {
      text-align: center;
      margin-bottom: 36px;
    }
    h1 {
      font-size: clamp(1.875rem, 4vw, 2.5rem);
      font-weight: 800;
      color: #111827;
      letter-spacing: -0.03em;
      margin-bottom: 12px;
      line-height: 1.2;
      text-shadow: 0 2px 10px rgba(255,255,255,0.3);
    }
    .sub {
      font-size: 1rem;
      color: #4b5563;
      max-width: 560px;
      margin: 0 auto;
      line-height: 1.6;
      font-weight: 500;
      text-shadow: 0 1px 2px rgba(255,255,255,0.5);
    }
    
    .card {
      background: rgba(255, 255, 255, 0.4);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1px solid rgba(255, 255, 255, 0.6);
      border-radius: 16px;
      box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07);
    }
    .upload-wrap {
      max-width: 720px;
      margin: 0 auto;
    }
    .tabs {
      display: grid;
      grid-template-columns: 1fr 1fr;
      border-bottom: 1px solid rgba(255, 255, 255, 0.3);
    }
    .tab {
      border: 0;
      background: transparent;
      height: 52px;
      font-size: 0.9375rem;
      font-weight: 600;
      color: #4b5563;
      cursor: pointer;
      border-bottom: 3px solid transparent;
      transition: color 0.15s, border-color 0.15s;
    }
    .tab.active {
      color: #2563eb;
      border-color: #2563eb;
      text-shadow: 0 0 10px rgba(37,99,235,0.2);
    }
    .panel { padding: 28px; }
    
    .dropzone {
      border: 2px dashed rgba(255, 255, 255, 0.8);
      border-radius: 12px;
      min-height: 260px;
      display: grid;
      place-items: center;
      cursor: pointer;
      text-align: center;
      color: #4b5563;
      padding: 32px 24px;
      transition: all 0.3s ease;
      background: rgba(255, 255, 255, 0.2);
    }
    .dropzone:hover, .dragover {
      border-color: #3b82f6;
      background: rgba(255, 255, 255, 0.5);
      box-shadow: inset 0 0 20px rgba(255,255,255,0.5);
    }
    .drop-icn {
      width: 56px;
      height: 56px;
      border-radius: 50%;
      background: rgba(255, 255, 255, 0.6);
      border: 1px solid rgba(255, 255, 255, 0.8);
      display: grid;
      place-items: center;
      margin: 0 auto 16px;
      box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    }
    .drop-icn svg { width: 26px; height: 26px; color: #2563eb; }
    .drop-title {
      color: #111827;
      font-size: 1rem;
      font-weight: 700;
      margin-bottom: 6px;
    }
    .drop-sub { font-size: 0.875rem; color: #4b5563; font-weight: 500; }
    
    .cloud {
      display: none;
      grid-template-columns: 1fr auto;
      gap: 12px;
      align-items: center;
      padding: 8px 0;
    }
    .cloud input {
      height: 48px;
      border-radius: 12px;
      border: 1px solid rgba(255, 255, 255, 0.6);
      background: rgba(255, 255, 255, 0.3);
      backdrop-filter: blur(10px);
      padding: 0 14px;
      font-size: 0.9375rem;
      font-family: inherit;
      color: #111827;
      transition: all 0.2s;
    }
    .cloud input:focus {
      outline: none;
      border-color: #2563eb;
      background: rgba(255, 255, 255, 0.6);
      box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.2);
    }
    .btn {
      border: 0;
      border-radius: 12px;
      background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
      box-shadow: 0 4px 15px rgba(37,99,235,0.3);
      color: #fff;
      height: 48px;
      padding: 0 24px;
      font-weight: 600;
      font-size: 0.9375rem;
      cursor: pointer;
      font-family: inherit;
      transition: transform 0.1s, box-shadow 0.2s;
    }
    .btn:hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(37,99,235,0.4); }
    
    .view { display: none; }
    .view.active { display: block; }

    .analysis {
      min-height: calc(100vh - 180px);
      display: grid;
      place-items: center;
      text-align: center;
    }
    .spinner {
      width: 64px;
      height: 64px;
      border-radius: 50%;
      border: 4px solid rgba(255,255,255,0.4);
      border-top-color: #2563eb;
      margin: 0 auto 20px;
      animation: spin 0.9s cubic-bezier(0.68, -0.55, 0.265, 1.55) infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    .analysis h2 {
      font-size: 1.5rem;
      font-weight: 700;
      margin-bottom: 8px;
      color: #111827;
      text-shadow: 0 2px 10px rgba(255,255,255,0.4);
    }
    .analysis p {
      color: #4b5563;
      font-size: 1rem;
      font-weight: 500;
    }
    .progress {
      margin-top: 28px;
      width: min(400px, 90vw);
    }
    .bar {
      height: 10px;
      background: rgba(255,255,255,0.3);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255,255,255,0.5);
      border-radius: 999px;
      overflow: hidden;
    }
    .bar > div {
      height: 100%;
      width: 0%;
      background: linear-gradient(90deg, #60a5fa 0%, #2563eb 100%);
      border-radius: 999px;
      transition: width 0.4s ease;
    }
    .steps {
      margin-top: 10px;
      display: flex;
      justify-content: space-between;
      font-size: 0.75rem;
      color: #4b5563;
      font-weight: 600;
    }

    .file-summary {
      padding: 18px 20px;
      margin-bottom: 20px;
    }
    .result-head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      flex-wrap: wrap;
    }
    .doc-info {
      display: flex;
      align-items: center;
      gap: 14px;
    }
    .doc-thumb {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.6);
      border: 1px solid rgba(255,255,255,0.8);
      display: grid;
      place-items: center;
      flex-shrink: 0;
      box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    .doc-thumb svg { width: 24px; height: 24px; color: #2563eb; }
    .doc-title {
      font-size: 1rem;
      font-weight: 700;
      color: #111827;
    }
    .doc-meta {
      font-size: 0.8125rem;
      color: #4b5563;
      margin-top: 4px;
      font-weight: 500;
    }
    .result-actions {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }
    .btn-outline {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border: 1px solid rgba(255,255,255,0.6);
      background: rgba(255,255,255,0.3);
      backdrop-filter: blur(10px);
      color: #111827;
      height: 40px;
      border-radius: 10px;
      padding: 0 14px;
      font-weight: 600;
      font-size: 0.8125rem;
      cursor: pointer;
      font-family: inherit;
      transition: all 0.2s;
    }
    .btn-outline:hover { background: rgba(255,255,255,0.6); }
    
    .btn-primary {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border: 0;
      background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
      box-shadow: 0 4px 15px rgba(37,99,235,0.3);
      color: #fff;
      height: 40px;
      border-radius: 10px;
      padding: 0 14px;
      font-weight: 600;
      font-size: 0.8125rem;
      cursor: pointer;
      font-family: inherit;
      transition: transform 0.1s, box-shadow 0.2s;
    }
    .btn-primary:hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(37,99,235,0.4); }
    
    .btn-icon {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      border: 1px solid rgba(255,255,255,0.6);
      background: rgba(255,255,255,0.3);
      backdrop-filter: blur(10px);
      display: grid;
      place-items: center;
      cursor: pointer;
      color: #4b5563;
      transition: all 0.2s;
    }
    .btn-icon:hover { background: rgba(255,255,255,0.6); color: #111827; }

    .panel-grid {
      display: grid;
      grid-template-columns: 220px 1fr;
      gap: 20px;
      align-items: start;
    }

    .domains {
      padding: 18px 14px;
      background: rgba(255, 255, 255, 0.4);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1px solid rgba(255, 255, 255, 0.6);
      border-radius: 16px;
      box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07);
    }
    .domains h3 {
      font-size: 0.6875rem;
      font-weight: 800;
      color: #4b5563;
      margin: 0 8px 12px;
      letter-spacing: 0.06em;
    }
    .domain-item {
      width: 100%;
      border: 0;
      background: transparent;
      display: flex;
      justify-content: space-between;
      align-items: center;
      min-height: 44px;
      border-radius: 10px;
      padding: 8px 12px;
      cursor: pointer;
      color: #374151;
      text-align: left;
      font-size: 0.8125rem;
      font-family: inherit;
      font-weight: 600;
      gap: 8px;
      transition: background 0.15s;
    }
    .domain-item:hover { background: rgba(255,255,255,0.5); }
    .domain-item.active {
      background: rgba(255,255,255,0.8);
      color: #2563eb;
      box-shadow: 0 2px 10px rgba(0,0,0,0.03);
    }
    .badge {
      min-width: 24px;
      height: 24px;
      padding: 0 8px;
      border-radius: 999px;
      background: rgba(255,255,255,0.6);
      border: 1px solid rgba(255,255,255,0.8);
      display: grid;
      place-items: center;
      font-size: 0.6875rem;
      font-weight: 700;
      color: #4b5563;
    }
    .domain-item.active .badge {
      background: #dbeafe;
      color: #1d4ed8;
      border-color: #bfdbfe;
    }
    .content {
      display: grid;
      gap: 16px;
    }
    
    .readiness {
      background: rgba(255, 255, 255, 0.4);
      backdrop-filter: blur(16px);
      border: 1px solid rgba(255, 255, 255, 0.6);
      border-radius: 16px;
      padding: 16px 20px;
      box-shadow: 0 8px 32px rgba(31, 38, 135, 0.05);
    }
    .readiness-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }
    .readiness-label {
      color: #4b5563;
      font-size: 0.6875rem;
      font-weight: 800;
      letter-spacing: 0.06em;
    }
    .readiness-pct {
      font-size: 1rem;
      font-weight: 800;
      color: #111827;
    }
    .readiness .bar {
      height: 12px;
      background: rgba(255,255,255,0.4);
      backdrop-filter: blur(5px);
      border: 1px solid rgba(255,255,255,0.6);
      border-radius: 999px;
      overflow: hidden;
    }
    .readiness .bar > div {
      height: 100%;
      background: linear-gradient(90deg, #60a5fa 0%, #2563eb 100%);
      border-radius: 999px;
      width: 100%;
    }

    .req-card {
      background: rgba(255, 255, 255, 0.4);
      backdrop-filter: blur(16px);
      border: 1px solid rgba(255, 255, 255, 0.6);
      border-radius: 16px;
      padding: 20px;
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 16px;
      align-items: start;
      box-shadow: 0 8px 32px rgba(31, 38, 135, 0.05);
      transition: transform 0.2s, box-shadow 0.2s;
    }
    .req-card:hover {
      transform: translateY(-2px);
      box-shadow: 0 12px 40px rgba(31, 38, 135, 0.08);
      background: rgba(255, 255, 255, 0.5);
    }
    .req-check {
      width: 24px;
      height: 24px;
      border-radius: 50%;
      border: 2px solid rgba(255, 255, 255, 0.8);
      background: rgba(255,255,255,0.4);
      margin-top: 2px;
      flex-shrink: 0;
      box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);
    }
    .req-body { min-width: 0; }
    .req-top {
      display: flex;
      gap: 10px;
      align-items: center;
      margin-bottom: 12px;
      flex-wrap: wrap;
    }
    .pill {
      padding: 4px 12px;
      border-radius: 8px;
      font-size: 0.625rem;
      font-weight: 800;
      letter-spacing: 0.04em;
      border: 1px solid rgba(255,255,255,0.5);
      backdrop-filter: blur(5px);
    }
    .mandatory { background: rgba(254, 226, 226, 0.7); color: #991b1b; }
    .privacy { background: rgba(224, 242, 254, 0.7); color: #075985; }
    .req-title {
      font-size: 1rem;
      font-weight: 700;
      line-height: 1.45;
      color: #111827;
      margin-bottom: 10px;
    }
    .req-note {
      font-size: 0.8125rem;
      color: #4b5563;
      line-height: 1.6;
      margin-bottom: 16px;
      font-weight: 500;
    }
    .req-foot {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 8px;
      font-size: 0.75rem;
      color: #4b5563;
      font-weight: 600;
    }
    .req-foot a {
      color: #2563eb;
      text-decoration: none;
    }
    .req-foot a:hover { text-decoration: underline; }

    .chatbot {
      background: rgba(255, 255, 255, 0.35);
      backdrop-filter: blur(24px);
      -webkit-backdrop-filter: blur(24px);
      border: 1px solid rgba(255, 255, 255, 0.5);
      border-radius: 16px;
      display: flex;
      flex-direction: column;
      height: 480px;
      width: 360px;
      position: fixed;
      bottom: 24px;
      right: 24px;
      box-shadow: 0 15px 45px rgba(0,0,0,0.1);
      z-index: 9999;
      overflow: hidden;
    }
    .chat-header {
      padding: 16px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.4);
      font-weight: 700;
      color: #111827;
      background: rgba(255, 255, 255, 0.2);
    }
    .chat-messages {
      flex: 1;
      padding: 16px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 14px;
      font-size: 0.875rem;
    }
    .chat-msg {
      max-width: 85%;
      padding: 12px 16px;
      border-radius: 16px;
      line-height: 1.5;
      font-weight: 500;
    }
    .chat-msg.user {
      background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
      color: #fff;
      align-self: flex-end;
      border-bottom-right-radius: 4px;
      box-shadow: 0 4px 15px rgba(37,99,235,0.2);
    }
    .chat-msg.bot {
      background: rgba(255, 255, 255, 0.6);
      border: 1px solid rgba(255, 255, 255, 0.8);
      color: #111827;
      align-self: flex-start;
      border-bottom-left-radius: 4px;
      box-shadow: 0 4px 15px rgba(0,0,0,0.03);
    }
    .chat-input-area {
      padding: 14px;
      border-top: 1px solid rgba(255, 255, 255, 0.4);
      display: flex;
      gap: 10px;
      background: rgba(255, 255, 255, 0.2);
    }
    .chat-input-area input {
      flex: 1;
      height: 44px;
      border-radius: 12px;
      border: 1px solid rgba(255, 255, 255, 0.6);
      background: rgba(255, 255, 255, 0.4);
      padding: 0 14px;
      font-size: 0.875rem;
      font-family: inherit;
      color: #111827;
    }
    .chat-input-area input:focus {
       outline: none;
       border-color: #3b82f6;
       background: rgba(255, 255, 255, 0.7);
    }
    .chat-input-area button {
      background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
      color: #fff;
      border: none;
      border-radius: 12px;
      padding: 0 16px;
      font-weight: 600;
      cursor: pointer;
      box-shadow: 0 4px 15px rgba(37,99,235,0.3);
      transition: transform 0.1s;
    }
    .chat-input-area button:hover { transform: translateY(-1px); }

    .footer {
      margin-top: auto;
      min-height: 52px;
      border-top: 1px solid rgba(255,255,255,0.4);
      background: rgba(255,255,255,0.25);
      backdrop-filter: blur(16px);
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 12px;
      padding: 14px 28px;
      color: #4b5563;
      font-size: 0.8125rem;
      font-weight: 500;
    }
    .footer a {
      color: #4b5563;
      text-decoration: none;
      margin-left: 16px;
      font-weight: 600;
    }
    .footer a:hover { color: #2563eb; }

    @media (max-width: 768px) {
      .tagline { display: none; }
      .panel-grid { grid-template-columns: 1fr; }
      .chatbot {
          width: calc(100% - 40px);
          bottom: 20px;
          right: 20px;
          height: 400px;
      }
    }
'''

# Use regex to replace ALL contents within <style> and </style>
pattern = re.compile(r'<style>.*?</style>', re.DOTALL)
text = pattern.sub('<style>\n' + new_css + '\n  </style>', text)

with open('frontend/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Glassmorphism style applied!")
