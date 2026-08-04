import os
import time
from typing import Dict
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Esports Easy Verification Gateway", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TELEGRAM_BOT_URL = os.getenv("TELEGRAM_BOT_URL", "https://t.me/YourFreeFireBot")

# মেমোরিতে সেশন স্টোরেজ
active_sessions: Dict[str, dict] = {}

class SessionStartModel(BaseModel):
    auth_token: str

@app.post("/api/gate/start")
async def start_gate_session(data: SessionStartModel):
    token = data.auth_token.strip()
    if not token:
        raise HTTPException(status_code=400, detail="টোকেন পাওয়া যায়নি!")
        
    session_id = f"SESS_{int(time.time())}_{token[:8]}"
    
    # সেশন শুরু করার সময় স্টোর করা
    active_sessions[session_id] = {
        "token": token,
        "start_time": time.time(),
        "verified": False
    }
    return {"status": "ok", "session_id": session_id}

@app.post("/api/gate/verify/{session_id}")
async def complete_gate_session(session_id: str):
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="ভুল বা মেয়াদোত্তীর্ণ সেশন!")
    
    sess = active_sessions[session_id]
    elapsed = time.time() - sess["start_time"]
    
    # ১৫ সেকেন্ডের কম সময়ে ক্লিক করলে ব্লক করবে
    if elapsed < 14.0:
        raise HTTPException(status_code=400, detail="১৫ সেকেন্ড পূর্ণ হওয়ার আগেই বাটন প্রেস করা হয়েছে!")
    
    sess["verified"] = True
    return {"status": "success", "message": "১৫ সেকেন্ড অবস্থান সফলভাবে ভেরিফাই হয়েছে!"}

@app.get("/sdk.js")
async def serve_sdk():
    js_code = f"""
(function() {{
    // URL থেকে টোকেন সংগ্রহ
    const urlParams = new URLSearchParams(window.location.search);
    const authToken = urlParams.get("token") || "";
    
    const GATEWAY_URL = window.location.origin;
    const BOT_URL = "{TELEGRAM_BOT_URL}";

    // যে পাত্রে বাটন বসবে
    let container = document.getElementById("esports-verify-widget");
    if (!container) {{
        container = document.createElement("div");
        container.id = "esports-verify-widget";
        document.body.prepend(container);
    }}

    // বাটন ও উইজেট কার্ড
    const widgetBox = document.createElement("div");
    widgetBox.style.cssText = "background:#0f141c; border:2px solid #ff4500; border-radius:12px; padding:20px; max-width:380px; margin:20px auto; text-align:center; font-family:-apple-system, sans-serif; color:#ffffff; box-shadow:0 0 15px rgba(255, 69, 0, 0.4);";

    widgetBox.innerHTML = `
        <div style="font-size:18px; font-weight:bold; color:#ffb700; margin-bottom:8px;">🔥 Free Fire Verification</div>
        <div id="role-display" style="font-size:13px; color:#a0aec0; margin-bottom:14px;">যাচাই করা হচ্ছে...</div>
        <button id="btn-gate-action" disabled style="width:100%; background:#2d3748; color:#a0aec0; border:none; padding:12px; font-size:16px; font-weight:bold; border-radius:8px; cursor:not-allowed; transition:0.3s;">
            অপেক্ষা করুন (15s)...
        </button>
        <div id="gate-timer-msg" style="font-size:12px; color:#ffb700; margin-top:10px;">ওয়েবসাইটে ১৫ সেকেন্ড অবস্থান করুন</div>
    `;

    container.appendChild(widgetBox);

    if (!authToken) {{
        widgetBox.querySelector("#role-display").innerText = "❌ কোনো ভ্যালিড রেজিস্ট্রেশন টোকেন পাওয়া যায়নি!";
        widgetBox.querySelector("#role-display").style.color = "#e53e3e";
        return;
    }}

    let sessionId = "";

    // সেশন তৈরি করার রিকোয়েস্ট
    fetch(`${{GATEWAY_URL}}/api/gate/start`, {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{ auth_token: authToken }})
    }})
    .then(r => r.json())
    .then(data => {{
        if(data.session_id) {{
            sessionId = data.session_id;
            startTimer();
        }} else {{
            widgetBox.querySelector("#role-display").innerText = "⚠️ টোকেন সেশন তৈরি করা যায়নি!";
        }}
    }})
    .catch(() => {{
        widgetBox.querySelector("#role-display").innerText = "⚠️ গেইটওয়ে কানেকশন এরর!";
    }});

    function startTimer() {{
        const roleDisplay = widgetBox.querySelector("#role-display");
        const isLeader = authToken.includes("leader");
        roleDisplay.innerText = isLeader ? "👑 Squad Leader Registration Verification" : "👥 Squad Member Join Verification";

        let timeLeft = 15;
        const btnAction = widgetBox.querySelector("#btn-gate-action");
        const timerMsg = widgetBox.querySelector("#gate-timer-msg");

        const countdown = setInterval(() => {{
            timeLeft--;
            if (timeLeft > 0) {{
                btnAction.innerText = `অপেক্ষা করুন (${{timeLeft}}s)...`;
            }} else {{
                clearInterval(countdown);
                btnAction.disabled = false;
                btnAction.style.background = "linear-gradient(135deg, #ffb700, #ff4500)";
                btnAction.style.color = "#000000";
                btnAction.style.cursor = "pointer";
                btnAction.style.boxShadow = "0 0 15px rgba(255, 69, 0, 0.8)";
                btnAction.innerText = isLeader ? "Registration Now 🚀" : "Join Now 🚀";
                timerMsg.innerText = "✅ সময় সম্পন্ন হয়েছে! বাটনে ক্লিক করুন";
                timerMsg.style.color = "#388e3c";
            }}
        }}, 1000);

        // বাটনে ক্লিক করলে ভেরিফিকেশন হবে
        btnAction.addEventListener("click", async function() {{
            btnAction.disabled = true;
            btnAction.innerText = "যাচাই করা হচ্ছে...";

            try {{
                const res = await fetch(`${{GATEWAY_URL}}/api/gate/verify/${{sessionId}}`, {{ method: "POST" }});
                const result = await res.json();
                
                if (res.ok) {{
                    alert("🎉 আপনার ১৫ সেকেন্ড অবস্থান সফলভাবে ভেরিফাই হয়েছে!");
                    window.location.href = BOT_URL;
                }} else {{
                    alert("⚠️ " + (result.detail || "ভেরিফিকেশন ব্যর্থ!"));
                    btnAction.disabled = false;
                    btnAction.innerText = isLeader ? "Registration Now 🚀" : "Join Now 🚀";
                }}
            }} catch (err) {{
                alert("⚠️ সার্ভার কানেকশন ত্রুটি!");
                btnAction.disabled = false;
            }}
        }});
    }}

}})();
    """
    return Response(content=js_code, media_type="application/javascript")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8001))
    uvicorn.run("verification_server:app", host="0.0.0.0", port=port, reload=True)

