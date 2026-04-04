import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.ingestion.twitch_listner import run_twitch_listener
from src.processing.engine import VibeEngine

app = FastAPI(title="VibeLine API")
engine = VibeEngine()

# SECURITY: Restrict which domains can connect to your backend
# Replace with your actual frontend domain when you deploy to production
ALLOWED_ORIGINS = [
    "http://localhost:5500",  # Common for VS Code Live Server
    "http://127.0.0.1:5500",
    "http://localhost:8000",
    "http://127.0.0.1:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"], # Only allow specific methods instead of ["*"]
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.max_connections = 10 #  SECURITY: Hard limit to prevent DDoS

    async def connect(self, websocket: WebSocket):
        if len(self.active_connections) >= self.max_connections:
            # Code 1008 means "Policy Violation"
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

async def process_chat_pipeline():
    print("📡 [Pipeline] AI Processing loop started...")
    while True:
        chat_data = await chat_queue.get()
        score = await asyncio.to_thread(engine.analyze_vibe, chat_data['message'])
        
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
    TARGET_CHANNEL = "xQc"
    # Create the tasks
    t1 = asyncio.create_task(run_twitch_listener(chat_queue, TARGET_CHANNEL))
    t2 = asyncio.create_task(process_chat_pipeline())
    
    # Add them to our "safe" set so Python doesn't delete them
    active_tasks.add(t1)
    active_tasks.add(t2)
    
    # Tell Python it's okay to delete them ONLY when they finish
    t1.add_done_callback(active_tasks.discard)
    t2.add_done_callback(active_tasks.discard)

@app.get("/")
def read_root():
    return {"status": "VibeLine Server is Running!"}

@app.websocket("/ws/pulse")
async def websocket_endpoint(websocket: WebSocket):
    # Check if the connection was allowed
    is_connected = await manager.connect(websocket)
    
    if not is_connected:
        return # Kill the process if max capacity is reached
        
    try:
        while True:
            await websocket.receive_text() 
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("🔌 Client disconnected.")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)