import asyncio
import httpx # New import for the serverless API
import os 
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.ingestion.twitch_listner import run_twitch_listener

app = FastAPI(title="VibeLine API")

# ☁️ SERVERLESS AI CONFIGURATION
HF_API_TOKEN = os.getenv("HF_API_TOKEN") 
MODEL_URL = "https://api-inference.huggingface.co/models/cardiffnlp/twitter-roberta-base-sentiment-latest"
headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}

# SECURITY: Restrict which domains can connect to your backend
ALLOWED_ORIGINS = [
    "http://localhost:5500",  
    "http://127.0.0.1:5500",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://omoytom.github.io" # Added your GitHub Pages URL so the cloud frontend can connect
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
            # Code 1008 means "Policy Violation"
            await websocket.close(code=1008) 
            print("🚨 [Security] Connection rejected: Max capacity reached.")
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

# 🔄 DYNAMIC CHANNEL TRACKERS
active_bot_task = None
current_bot_channel = None

# 🧠 NEW SERVERLESS AI FUNCTION
# 🧠 UPGRADED SERVERLESS AI FUNCTION
async def analyze_sentiment(text: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                MODEL_URL, 
                headers=headers, 
                json={"inputs": text},
                timeout=10.0 
            )
            data = response.json()
            
            
            if isinstance(data, dict):
                if "error" in data:
                    print(f" Hugging Face API Status: {data['error']}")
                return 0.0 

            # Extract the sentiment from the HF API response format
            if isinstance(data, list) and len(data) > 0:
                predictions = data[0] if isinstance(data[0], list) else data
                best_match = max(predictions, key=lambda x: x['score'])
                
                
                label = best_match['label'].lower()
                
                # Convert to our numerical score (-1.0 to 1.0)
                if label == 'positive': return best_match['score']
                elif label == 'negative': return -best_match['score']
                else: return 0.0 
                
    except Exception as e:
        print(f"Network/Exception Error: {e}")
        return 0.0 
        
    return 0.0

async def process_chat_pipeline():
    print("📡 [Pipeline] Serverless AI Processing loop started...")
    while True:
        chat_data = await chat_queue.get()
        
        # Swapped local engine for the API call
        score = await analyze_sentiment(chat_data['message']) 
        
        payload = {
            "username": chat_data["username"],
            "message": chat_data["message"],
            "score": score,
            "timestamp": chat_data["timestamp"]
        }
        
        status = "🟢 POSITIVE" if score > 0.4 else "🔴 NEGATIVE" if score < -0.4 else "⚪ NEUTRAL"
        print(f"{chat_data['username']:<15} | {status:<8} | Score: {score:>6.2f} | {chat_data['message']}")
        
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
    # Tell Python we want to modify those global variables we made earlier
    global active_bot_task, current_bot_channel
    
    # Check if the connection was allowed
    is_connected = await manager.connect(websocket)
    
    if not is_connected:
        return # Kill the process if max capacity is reached
        
    print(f"🔗 Client connected. Requested channel: #{channel}")
    
    # THE MAGIC: If the bot isn't running, or is on the wrong channel, switch it!
    if channel != current_bot_channel:
        print(f" Switching Twitch bot to listen to #{channel}...")
        if active_bot_task:
            active_bot_task.cancel() # Kill the old Twitch connection
        
        # Start the new Twitch connection
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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)