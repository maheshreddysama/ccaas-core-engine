import os
import time
from fastapi import FastAPI, Form, Response
import redis

app = FastAPI()

# --- UPDATE THIS SECTION WITH YOUR UPSTASH CREDENTIALS ---
# Format:

UPSTASH_REDIS_URL = "rediss://default:gQAAAAAAAiBgAAIgcDFkMWE2ZDQ2NTQ1OGM0MmZmYTAyOTA2ZjIzYjU5Nzk4NA@social-sloth-139360.upstash.io:6379"

# Connects to Upstash using the direct URL
r = redis.Redis.from_url(UPSTASH_REDIS_URL, decode_responses=True)
# --------------------------------------------------------

@app.on_event("startup")
def seed_agents():
    """Seeds our workforce automatically when the server boots."""
    mock_agents = {
        "agent_01": {"name": "Alice", "status": "Available", "skills": "support"},
        "agent_02": {"name": "Bob", "status": "Busy", "skills": "support"}
    }
    for agent_id, profile in mock_agents.items():
        r.hset(f"agent:{agent_id}", mapping=profile)
    print("✅ Workforce Agent Registry initialized in Upstash.")

@app.post("/webhook/voice")
def handle_cc_call(CallSid: str = Form(...), From: str = Form(...)):
    """Core ACD (Automatic Call Distribution) engine endpoint called by Twilio."""
    
    # 1. Query your Upstash cloud state to find an available worker
    all_agent_keys = r.keys("agent:*")
    assigned_agent = None

    for key in all_agent_keys:
        agent = r.hgetall(key)
        if agent.get("status") == "Available" and "support" in agent.get("skills", ""):
            assigned_agent = key.split(":")[-1]
            break

    # 2. Execute Architectural Routing Logic
    if assigned_agent:
        # Atomic State Modification to lock the agent profile
        r.hset(f"agent:{assigned_agent}", "status", "Busy")
        
        # Build TwiML instruction instructions instructing Twilio how to route the caller
        twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Say voice="Polly.Joanna">Thank you for calling. Routing you to senior engineer agent {assigned_agent}. Please hold.</Say>
        </Response>"""
    else:
        # No workforce capacity -> Shift the interaction state into a structural FIFO queue
        r.rpush("queue:support", CallSid)
        
        twiml_response = """<?xml version="1.0" encoding="UTF-8"?>
        <Response>
            <Say voice="Polly.Joanna">All specialists are handling spikes. You have been placed into our virtual queue.</Say>
        </Response>"""
        
    return Response(content=twiml_response, media_type="application/xml")