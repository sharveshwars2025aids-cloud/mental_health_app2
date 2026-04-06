from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from groq import Groq
from pydantic import BaseModel, Field
import os
import sqlite3
import uuid

# DB setup
conn = sqlite3.connect("chat.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT,
    title TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS chats(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    session_id TEXT,
    role TEXT,
    content TEXT
)
""")
conn.commit()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# SYSTEM PROMPT
SYSTEM_PROMPT = {
    "role": "system",
    "content": """
You are a professional, calm, and supportive mental health assistant.

Rules for response:
- Speak in simple, natural conversational English.
- Do NOT use emojis.
- Do NOT use markdown symbols.
- Do NOT format text.
- Keep responses short and human-like.
- Always feel connected to what the user said.

Special behavior:
- If the user says something simple like "hi", "hello", "hey":
  Respond warmly and ask how they are feeling.
- Do NOT overanalyze simple messages.

Your role:
- Listen empathetically.
- Provide emotional support.
- Never sound robotic.
"""
}

# Request models
class ChatRequest(BaseModel):
    user_id: str
    session_id: str
    user_message: str = Field(..., min_length=1)

class NewSessionRequest(BaseModel):
    user_id: str

user_sessions = {}
app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "Mental Health AI running"}

# Mood detection (internal use only)
def detect_mood(text):
    text = text.lower()
    if any(word in text for word in ["sad", "depressed", "unhappy", "cry"]):
        return "sad"
    elif any(word in text for word in ["happy", "excited", "good", "great"]):
        return "happy"
    elif any(word in text for word in ["stress", "tired", "anxious", "overwhelmed"]):
        return "stressed"
    else:
        return "neutral"

# Auto-generate a short session title from first user message
def generate_title(user_message: str) -> str:
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": "Generate a very short, 4-6 word title summarizing the user's message. No quotes, no punctuation, no emojis. Just plain words."
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        )
        return response.choices[0].message.content.strip()
    except:
        return "New Conversation"

# CREATE new session
@app.post("/sessions/new")
def new_session(request: NewSessionRequest):
    session_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO sessions (session_id, user_id, title) VALUES (?, ?, ?)",
        (session_id, request.user_id, "New Conversation")
    )
    conn.commit()
    return {"session_id": session_id, "title": "New Conversation"}

# GET all sessions for a user
@app.get("/sessions/{user_id}")
def get_sessions(user_id: str):
    cursor.execute(
        "SELECT session_id, title, created_at FROM sessions WHERE user_id=? ORDER BY created_at DESC",
        (user_id,)
    )
    rows = cursor.fetchall()
    return {
        "sessions": [
            {"session_id": r[0], "title": r[1], "created_at": r[2]}
            for r in rows
        ]
    }

# GET chat history for a session
@app.get("/history/{session_id}")
def get_history(session_id: str):
    cursor.execute(
        "SELECT role, content FROM chats WHERE session_id=? ORDER BY id ASC",
        (session_id,)
    )
    rows = cursor.fetchall()
    return {
        "messages": [{"role": r[0], "content": r[1]} for r in rows]
    }

# DELETE a session and its messages
@app.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    cursor.execute("DELETE FROM chats WHERE session_id=?", (session_id,))
    cursor.execute("DELETE FROM sessions WHERE session_id=?", (session_id,))
    conn.commit()
    if session_id in user_sessions:
        del user_sessions[session_id]
    return {"message": "Session deleted"}

# MAIN CHAT
@app.post("/chat")
def chat(request: ChatRequest):

    user_id = request.user_id
    session_id = request.session_id
    user_message = request.user_message.strip()

    if not user_message:
        return {"error": "Message cannot be empty"}

    # Greeting shortcut
    msg = user_message.lower()
    if any(word in msg for word in ["hi", "hello", "hey", "hai"]):
        greeting_reply = "Hey, I'm here with you. How are you feeling today?"

        # Still save greeting to DB
        cursor.execute(
            "INSERT INTO chats (user_id, session_id, role, content) VALUES (?,?,?,?)",
            (user_id, session_id, "user", user_message)
        )
        cursor.execute(
            "INSERT INTO chats (user_id, session_id, role, content) VALUES (?,?,?,?)",
            (user_id, session_id, "assistant", greeting_reply)
        )
        conn.commit()

        # Update title if this is the first message
        cursor.execute(
            "SELECT COUNT(*) FROM chats WHERE session_id=? AND role='user'",
            (session_id,)
        )
        count = cursor.fetchone()[0]
        if count == 1:
            title = generate_title(user_message)
            cursor.execute(
                "UPDATE sessions SET title=? WHERE session_id=?",
                (title, session_id)
            )
            conn.commit()

        return {"reply": greeting_reply}

    # Load session into memory if not already loaded
    if session_id not in user_sessions:
        cursor.execute(
            "SELECT role, content FROM chats WHERE session_id=? ORDER BY id ASC",
            (session_id,)
        )
        rows = cursor.fetchall()

        user_sessions[session_id] = [SYSTEM_PROMPT.copy()]

        for role, content in rows:
            user_sessions[session_id].append({"role": role, "content": content})

    user_sessions[session_id].append({"role": "user", "content": user_message})

    # Save user message
    cursor.execute(
        "INSERT INTO chats (user_id, session_id, role, content) VALUES (?,?,?,?)",
        (user_id, session_id, "user", user_message)
    )
    conn.commit()

    # Update session title from first message
    cursor.execute(
        "SELECT COUNT(*) FROM chats WHERE session_id=? AND role='user'",
        (session_id,)
    )
    count = cursor.fetchone()[0]
    if count == 1:
        title = generate_title(user_message)
        cursor.execute(
            "UPDATE sessions SET title=? WHERE session_id=?",
            (title, session_id)
        )
        conn.commit()

    # AI call
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=user_sessions[session_id]
    )

    reply = response.choices[0].message.content

    # Save reply
    cursor.execute(
        "INSERT INTO chats (user_id, session_id, role, content) VALUES (?,?,?,?)",
        (user_id, session_id, "assistant", reply)
    )
    conn.commit()

    user_sessions[session_id].append({"role": "assistant", "content": reply})

    return {"reply": reply}