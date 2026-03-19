from fastapi import FastAPI
from pydantic import BaseModel
from groq import Groq
import os

client=Groq(api_key =os.getenv("GROQ_API_KEY"))

class chatrequest(BaseModel):
    message: str

app=FastAPI()

@app.get("/")
def home():
    return{"message": "API working"}

@app.post("/chat")
def chat(request:chatrequest):
    user_msg = request.message
    if user_msg.lower() == "hi":
        return{"reply":"Hello! How can i help you"}
    else:
        response = client.chat.completions.create(
            model = "openai/gpt-oss-120b",
            messages=[{
                "role": "system", "content": "You are a helpful assistant. Answer clearly."
            },  
                {
                "role":"user","content":user_msg
            }

            ]
        )

        reply = response.choices[0].message.content

        return{"reply":reply}
