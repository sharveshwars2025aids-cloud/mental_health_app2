from fastapi import FastAPI
from groq import Groq
from pydantic import BaseModel,Field
import os

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
    user_message:str = Field(...,min_length=3)

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Mental Health AI running"}

@app.post("/chat")
def chat(request: ChatRequest):
    user_message = request.user_message

    messages.append({
        "role": "user",
        "content": user_message
    })
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=messages
    )
    
    reply = response.choices[0].message.content
    
    messages.append({
        "role": "assistant",
        "content": reply
    })

    return {"reply": reply}