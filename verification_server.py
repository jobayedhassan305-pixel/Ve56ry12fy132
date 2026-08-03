
import os
import time
import hmac
import hashlib
from typing import Dict
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Esports Verification Gate Server", version="2.5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SERVER_SECRET_KEY = os.getenv("SERVER_SECRET_KEY", "FF_ESPORTS_SUPER_SECRET_KEY_998877")
TELEGRAM_BOT_URL = os.getenv("TELEGRAM_BOT_URL", "[https://t.me](https://t.me)")

active_sessions: Dict[str, dict] = {}

class SessionStartModel(BaseModel):
    auth_token: str

def parse_and_validate_token(token: str) -> dict:
    try:
        parts = token.split(":")
        if len(parts) != 5:
            raise ValueError("Invalid token format")
        tg_id, role, squad_code, exp, signature = parts
        
        if int(time.time()) > int(exp):
            raise ValueError("Token expired")
            
        payload = f"{tg_id}:{role}:{squad_code}:{exp}"
        expected_sig = hmac.new(SERVER_SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
        
        if not hmac.compare_digest(signature, expected_sig):
            raise ValueError("Invalid signature")
            
        return {
            "telegram_id": int(tg_id),
            "role": role,
            "squad_code": squad_code,
            "exp": int(exp)
        }
    except Exception as e:
        raise HTTPException(status_code=403, detail=f"টোকেন ভেরিফিকেশন ব্যর্থ: {str(e)}")

@app.post("/api/gate/start")
async def start_gate_session(data: SessionStartModel):
    token_info = parse_and_validate_token(data.auth_token)
    session_id = f"SESS_{hashlib.md5(data.auth_token.encode()).hexdigest()[:12]}"
    
    active_sessions[session_id] = {
        "info": token_info,
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
    
    if elapsed < 14.0:
        raise HTTPException(status_code=400, detail="১৫ সেকেন্ড পূর্ণ হওয়ার আগেই বাটন প্রেস করা হয়েছে!")
    
    sess["verified"] = True
    return {"status": "success", "message": "১৫ সেকেন্ড অবস্থান সফলভাবে ভেরিফাই হয়েছে!"}

@app.get("/sdk.js")
async def serve_sdk():
    js_code = f"""
(function() {{
    const urlParams = new URLSearchParams(window.location.search);
    const authToken = urlParams.get("token") || "";
    
    const GATEWAY_URL = window.location.origin;
    const BOT_URL = "{TELEGRAM_BOT_URL}";

    const container = document.getElementById("esports-verify-widget") || document.body;

    const widgetBox = document.createElement("div");
    widgetBox.style.cssText = "background:#121824; border:1px solid #ff4500; border-radius:12px; padding:16px; max-width:380px; margin:20px auto; text-align:center; font-family:-apple-system,sans-serif; color:#fff; box-shadow:0 4px 15px rgba(255,69,0,0.3);";

    widgetBox.innerHTML = `
        <div style="font-size:16px; font-weight:bold; color:#ffb700; margin-bottom:6px;">🔥 Free Fire Verification Widget</div>
        <div id="role-display" style="font-size:12px; color:#a0aec0; margin-bottom:12px;">টোকেন চেক করা হচ্ছে...</div>
        <button id="btn-gate-action" disabled style="width:100%; background:#4a5568; color:#cbd5e0; border:none; padding:12px; font-size:15px; font-weight:bold; border-radius:8px; cursor:not-allowed; transition:0.3s;">
            অপেক্ষা করুন (15s)...
        </button>
        <div id="gate-timer-msg" style="font-size:11px; color:#ffb700; margin-top:8px;">ওয়েবসাইটে ১৫ সেকেন্ড অবস্থান করুন</div>
    `;

    container.appendChild(widgetBox);

    if (!authToken) {{
        widgetBox.querySelector("#role-display").innerText = "❌ কোনো ভ্যালিড টোকেন পাওয়া যায়নি!";
        widgetBox.querySelector("#role-display").style.color = "#e53e3e";
        return;
    }}

    let sessionId = "";

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
            widgetBox.querySelector("#role-display").innerText = "⚠️ টোকেনটির মেয়াদ শেষ বা অবৈধ!";
        }}
    }})
    .catch(() => {{
        widgetBox.querySelector("#role-display").innerText = "⚠️ গেইটওয়ে কানেকশন এরর!";
    }});

    function startTimer() {{
        const roleDisplay = widgetBox.querySelector("#role-display");
        const isLeader = authToken.includes(":leader:");
        roleDisplay.innerText = isLeader ? "👑 Squad Leader - Registration" : "👥 Squad Member - Join";

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
                btnAction.style.background = "#ff4500";
                btnAction.style.color = "#ffffff";
                btnAction.style.cursor = "pointer";
                btnAction.style.boxShadow = "0 0 12px rgba(255, 69, 0, 0.6)";
                btnAction.innerText = isLeader ? "Registration Now" : "Join Now";
                timerMsg.innerText = "✅ সময় সম্পন্ন হয়েছে! বাটনে ক্লিক করুন";
                timerMsg.style.color = "#2e7d32";
            }}
        }}, 1000);

        btnAction.addEventListener("click", async function() {{
            btnAction.disabled = true;
            btnAction.innerText = "যাচাই করা হচ্ছে...";

            try {{
                const res = await fetch(`${{GATEWAY_URL}}/api/gate/verify/${{sessionId}}`, {{ method: "POST" }});
                const result = await res.json();
                
                if (res.ok) {{
                    alert("✅ আপনার ১৫ সেকেন্ড অবস্থান সফলভাবে ভেরিফাই হয়েছে!");
                    window.location.href = BOT_URL;
                }} else {{
                    alert("⚠️ " + (result.detail || "ভেরিফিকেশন ব্যর্থ!"));
                }}
            }} catch (err) {{
                alert("⚠️ সার্ভার কানেকশন ত্রুটি!");
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


