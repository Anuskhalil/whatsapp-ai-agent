from fastapi import FastAPI
from pydantic import BaseModel

from app.config import APP_NAME, APP_VERSION, ENVIRONMENT

app = FastAPI(title=APP_NAME, version=APP_VERSION)


class MessageRequest(BaseModel):
    user_id: str
    message: str


def process_message(message: str):

    message = message.lower()

    if "hello" in message:
        return "Hello! How can I help you today?"
    if "bye" in message:
        return "Goodbye! Have a great day!"
    if "help" in message:
        return "I can help you with your questions. How can I assist you?"
    if "who are you" in message:
        return "I am NexusAI, your AI assistant."
    else:
        return "I received your message."


@app.get("/")
def home():
    return {"message": "Whatsapp Agent is Working!", "status": "success"}


@app.get("/about")
def about():
    return {
        "name": f"{APP_NAME} is Running",
        "type": "Whatsapp Agent",
        "version": APP_VERSION,
        "environment": ENVIRONMENT,
    }


@app.get("/health")
def health():
    return {"Status": "Healthy", "message": "Whatsapp Agent is Running"}


@app.post("/message")
def receive_message(data: MessageRequest):

    response = process_message(data.message)

    return {"status": "success", "user_id": data.user_id, "response": response}
