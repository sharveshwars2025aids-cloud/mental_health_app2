from fastapi import FastAPI
from groq import Groq
from pydantic import BaseModel,Field
import os
import sqlite3

conn = sqlite3.connect("chat.db", check_same_thread = False)
cursor=conn.cursor()
cursor.execute("""                                                      
               CREATE TABLE IF NOT EXISTS chats(
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               user_id TEXT,
               role TEXT,
               content TEXT
               )
""")

conn.commit()
client = Groq(api_key = os.getenv("GROQ_API_KEY"))  

messages=[
            {"role": "system", "content": """
You are a professional, calm, and supportive mental health assistant.

Your role is to:
- Listen empathetically and respond with understanding and respect.
- Provide general emotional support, stress management tips, and coping strategies.
- Encourage positive thinking and healthy habits.

Guidelines:
- Do not provide medical or psychiatric diagnoses.
- Do not suggest harmful or unsafe actions.
- If the user expresses severe distress or crisis, gently encourage seeking help from a trusted person or professional.
- Maintain a non-judgmental and reassuring tone at all times.

Keep responses clear, concise, and supportive.
"""}
]

class ChatRequest(BaseModel):
    user_id: str
    user_message:str = Field(...,min_length=3)
user_sessions = {}
app = FastAPI()

@app.get("/")
def home():
    return {"message": "Mental Health AI running"}

@app.post("/chat")
def chat(request: ChatRequest):

    user_id = request.user_id
    user_message = request.user_message.strip()

    if not user_message:
        return {"error": "Message cannot be empty"}

    if user_id not in user_sessions:

        cursor.execute(
            "SELECT role, content FROM chats WHERE user_id=? ORDER BY id DESC LIMIT 10",
            (user_id,)
        )

        rows = cursor.fetchall()
        rows.reverse()

        user_sessions[user_id] = messages.copy()

        for role, content in rows:
            user_sessions[user_id].append({
                "role": role,
                "content": content
            })

    user_sessions[user_id].append({
        "role": "user",
        "content": user_message
    })

    cursor.execute(
        "INSERT INTO chats (user_id, role, content) VALUES (?,?,?)",
        (user_id, "user", user_message)
    )
    conn.commit()

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=user_sessions[user_id]
    )

    reply = response.choices[0].message.content

    cursor.execute(
        "INSERT INTO chats(user_id, role, content) VALUES(?,?,?)",
        (user_id, "assistant", reply)
    )
    conn.commit()

    user_sessions[user_id].append({
        "role": "assistant",
        "content": reply
    })

    return {"reply": reply}