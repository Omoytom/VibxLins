import asyncio
import httpx 
import os 
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.ingestion.twitch_listner import run_twitch_listener

app = FastAPI(title="VibeLine API")

# SERVERLESS AI CONFIGURATION
HF_API_TOKEN = os.getenv("HF_API_TOKEN") 
HEADERS = {"Authorization": f"Bearer {HF_API_TOKEN}"}

# AI Model Endpoints
SENTIMENT_URL = "https://router.huggingface.co/hf-inference/models/cardiffnlp/twitter-roberta-base-sentiment-latest"
NER_URL = "https://router.huggingface.co/hf-inference/models/dslim/bert-base-NER"

# SECURITY: Restrict which domains can connect to the backend
ALLOWED_ORIGINS = [
    "http://localhost:5500",  
    "http://127.0.0.1:5500",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://omoytom.github.io" 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"], 
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.max_connections = 10 # SECURITY: Hard limit to prevent DDoS

    async def connect(self, websocket: WebSocket):
        if len(self.active_connections) >= self.max_connections:
            await websocket.close(code=1008) 
            print(" [Security] Connection rejected: Max capacity reached.")
            return False
            
        await websocket.accept()
        self.active_connections.append(websocket)
        return True

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Failed to send message: {e}")

manager = ConnectionManager()
chat_queue = asyncio.Queue()

active_bot_task = None
current_bot_channel = None


http_client = httpx.AsyncClient()

# --- UPGRADED AI PROCESSING PIPELINE ---

async def fetch_hf_inference(url: str, text: str):
    """Generic async fetcher for Hugging Face APIs."""
    try:
        response = await http_client.post(
            url, 
            headers=HEADERS, 
            json={"inputs": text},
            timeout=5.0 
        )
        data = response.json()
        
        if isinstance(data, dict) and "error" in data:
            print(f" API Error ({url.split('/')[-1]}): {data['error']}")
            return None 
            
        return data
    except Exception as e:
        print(f"Network Error ({url.split('/')[-1]}): {e}")
        return None 

def extract_entities(ner_raw_data) -> list:
    """Parses raw token data from the NER model into clean entity strings."""
    if not ner_raw_data or isinstance(ner_raw_data, dict): 
        return []

    entities = set()
    current_entity = ""

    for token_data in ner_raw_data:
        word = token_data.get("word", "")
        entity_type = token_data.get("entity_group", token_data.get("entity", ""))

        if word.startswith("##"):
            current_entity += word.replace("##", "")
        elif entity_type.startswith("B-"):
            if current_entity:
                entities.add(current_entity)
            current_entity = word
        elif entity_type.startswith("I-"):
            current_entity += f" {word}" if current_entity else word
        else:
            if current_entity:
                entities.add(current_entity)
                current_entity = ""
                
    if current_entity:
        entities.add(current_entity)

    return list(entities)

async def analyze_message(text: str):
    """Fires Sentiment and NER API requests concurrently."""
    sentiment_task = fetch_hf_inference(SENTIMENT_URL, text)
    ner_task = fetch_hf_inference(NER_URL, text)
    
    sentiment_raw, ner_raw = await asyncio.gather(sentiment_task, ner_task)
    
    # 1. Parse Sentiment
    score = 0.0
    if sentiment_raw and isinstance(sentiment_raw, list) and len(sentiment_raw) > 0:
        predictions = sentiment_raw[0] if isinstance(sentiment_raw[0], list) else sentiment_raw
        best_match = max(predictions, key=lambda x: x['score'])
        label = best_match['label'].lower()
        
        if label == 'positive': score = best_match['score']
        elif label == 'negative': score = -best_match['score']
    
    # 2. Parse Entities
    entities = extract_entities(ner_raw)
    
    return score, entities

async def process_chat_pipeline():
    print("📡 [Pipeline] Serverless AI Processing loop started...")
    while True:
        if chat_queue.qsize() > 50:
            print(f" Queue too large ({chat_queue.qsize()}). Dropping old messages to save memory...")
            while chat_queue.qsize() > 10:
                try:
                    chat_queue.get_nowait()
                    chat_queue.task_done()
                except asyncio.QueueEmpty:
                    break

        chat_data = await chat_queue.get()
        
        # Unpack both the score and the detected entities
        score, entities = await analyze_message(chat_data['message']) 
        
        payload = {
            "username": chat_data["username"],
            "message": chat_data["message"],
            "score": score,
            "entities": entities,  # Injecting the new NER array here
            "timestamp": chat_data["timestamp"]
        }
        
        status = "🟢 POSITIVE" if score > 0.4 else "🔴 NEGATIVE" if score < -0.4 else "⚪ NEUTRAL"
        entities_display = f" | 🏷️ {entities}" if entities else ""
        
        # Updated terminal output to include detected topics
        print(f"{chat_data['username']:<15} | {status:<8} | Score: {score:>6.2f}{entities_display} | {chat_data['message']}")
        
        await manager.broadcast(payload)
        chat_queue.task_done()

active_tasks = set()

@app.on_event("startup")
async def startup_event():
    t2 = asyncio.create_task(process_chat_pipeline())
    active_tasks.add(t2)
    t2.add_done_callback(active_tasks.discard)

@app.get("/")
def read_root():
    return {"status": "VibeLine Server is Running on Serverless API!"}

@app.websocket("/ws/pulse")
async def websocket_endpoint(websocket: WebSocket, channel: str = "eslcs"):
    global active_bot_task, current_bot_channel
    
    is_connected = await manager.connect(websocket)
    
    if not is_connected:
        return 
        
    print(f"🔗 Client connected. Requested channel: #{channel}")
    
    if channel != current_bot_channel:
        print(f"🔄 Switching Twitch bot to listen to #{channel}...")
        if active_bot_task:
            active_bot_task.cancel() 
        
        current_bot_channel = channel
        active_bot_task = asyncio.create_task(run_twitch_listener(chat_queue, channel))
        
        active_tasks.add(active_bot_task)
        active_bot_task.add_done_callback(active_tasks.discard)

    try:
        while True:
            await websocket.receive_text() 
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("🔌 Client disconnected.")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)