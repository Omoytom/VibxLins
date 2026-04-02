import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.ingestion.simulator import run_simulator
from src.processing.engine import VibeEngine

# Initialize the Web App and AI Engine
app = FastAPI(title="VibeLine API")
engine = VibeEngine()

# Allow connections from any browser or OBS source
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- WebSocket Manager ---
# This keeps track of whoever is viewing the dashboard (e.g., OBS)
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

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

# --- Background Tasks ---
async def process_chat_pipeline():
    """Reads from the simulator, analyzes sentiment, and broadcasts to the UI."""
    print("📡 [Pipeline] AI Processing loop started...")
    while True:
        # 1. Get raw message from simulator
        chat_data = await chat_queue.get()
        
        # 2. Analyze the vibe
        score = engine.analyze_vibe(chat_data['message'])
        
        # 3. Create the "Pulse Payload"
        payload = {
            "username": chat_data["username"],
            "message": chat_data["message"],
            "score": score,
            "timestamp": chat_data["timestamp"]
        }
        
        # Print to console so you can watch it run
        status = "🔥 HYPE" if score > 0.4 else "💀 SALT" if score < -0.4 else "😐 NEUTRAL"
        print(f"{chat_data['username']:<15} | {status:<8} | Score: {score:>6.2f} | {chat_data['message']}")
        
        # 4. Broadcast to OBS/Browser
        await manager.broadcast(payload)
        chat_queue.task_done()

# --- FastAPI Lifecycle Events ---
@app.on_event("startup")
async def startup_event():
    """Starts the simulator and pipeline when the server boots up."""
    asyncio.create_task(run_simulator(chat_queue))
    asyncio.create_task(process_chat_pipeline())

# --- API Endpoints ---
@app.get("/")
def read_root():
    return {"status": "VibeLine Server is Running! Connect your frontend to /ws/pulse for real-time data."}

@app.websocket("/ws/pulse")
async def websocket_endpoint(websocket: WebSocket):
    """The endpoint that OBS/Browsers will connect to."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection open to push data
            await websocket.receive_text() 
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("🔌 Client disconnected.")

# --- Runner ---
if __name__ == "__main__":
    # Run the server on port 8000
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)