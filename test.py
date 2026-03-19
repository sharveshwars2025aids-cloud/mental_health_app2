from fastapi import FastAPI
from pydantic import BaseModel
from groq import Groq
import os

client = Groq(api_key = os.getenv("GROQ_API_KEY"))

messages = [
    {"role": "system","content": "you are a geopolitics expert. Answer clearly and briefly."}
]
class chatrequest(BaseModel):
    message: str

app = FastAPI()

@app.get("/")
def home():
    return {"message":"Geo politics chat bot"}

@app.post("/chat")
def chat(request: chatrequest):
    user_msg = request.message

    messages.append({"role": "user", "content": user_msg})

    response = client.chat.completions.create(
        model = "openai/gpt-oss-120b",
        messages=[
            {
                "role": "system",
                "content": "you are a geopolitics expert. Use previous conversation context when replying. Answer clearly and briefly in a serious manner."  
            },
            {
                "role": "user",
                "content": user_msg
            }
        ]
    )

    reply = response.choices[0].message.content

    messages.append({"role": "assistant", "content": reply})

    return{"reply": reply}