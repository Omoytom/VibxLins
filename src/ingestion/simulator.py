import asyncio
import random
from datetime import datetime

# --- MOCK DATA ---
MOCK_USERS = ["PixelKnight", "StreamSniper99", "VibeQueen", "GG_EzReal", "ChatLag_Ref", "NoobMaster", "ProGamer007"]

EMOTES = {
    "positive": ["POG", "LUL", "KEKW", "Love it!", "HYPE", "W", "Insane play!"],
    "negative": ["L", "Cringe", "RageQuit", "Mid", "Bruh...", "Throwing", "Reported"],
    "neutral": ["?", "Song name?", "Hello from 🇳🇬", "Is it laggy?", "anyone there?", "what game is this?"]
}

# --- GLOBAL STREAM STATE ---
class StreamState:
    current_event = "normal"  # normal, hype_train, toxic_spike
    velocity = 1.0            # Speed multiplier for chats

state = StreamState()

async def event_manager():
    """Runs in the background and randomly triggers stream events."""
    while True:
        # Stay in normal mode for 10-15 seconds
        await asyncio.sleep(random.uniform(10, 15))
        
        # Trigger a sudden event!
        event_type = random.choice(["hype_train", "toxic_spike"])
        print(f"\n🚨 [SIMULATOR] EVENT TRIGGERED: {event_type.upper()}! Chat velocity increasing... 🚨\n")
        
        state.current_event = event_type
        state.velocity = 0.2  # Make chat 5x faster!
        
        # Event lasts for 5-8 seconds
        await asyncio.sleep(random.uniform(5, 8))
        
        # Return to normal
        print(f"\n🌊 [SIMULATOR] Event over. Returning to normal chat.\n")
        state.current_event = "normal"
        state.velocity = 1.0

async def generate_chat_message():
    """Generates a message based on the current stream state."""
    # Adjust probability weights based on the current event
    if state.current_event == "hype_train":
        weights = [85, 5, 10]  # 85% Positive
    elif state.current_event == "toxic_spike":
        weights = [5, 85, 10]  # 85% Negative
    else:
        weights = [40, 20, 40] # Normal distribution
        
    vibe_choice = random.choices(["positive", "negative", "neutral"], weights=weights)[0]
    
    user = random.choice(MOCK_USERS)
    text = random.choice(EMOTES[vibe_choice])
    
    return {
        "username": user,
        "message": text,
        "platform": "twitch_mock",
        "timestamp": datetime.now().isoformat(),
        "is_subscriber": random.choice([True, False])
    }

async def run_simulator(output_queue: asyncio.Queue):
    """Continuously generates messages and puts them into a queue."""
    print("🚀 [Simulator] Starting mock chat stream with Event Engine...")
    
    # Fire up the event manager in the background
    asyncio.create_task(event_manager())
    
    while True:
        msg = await generate_chat_message()
        await output_queue.put(msg)
        
        # Sleep base time multiplied by our velocity state
        base_sleep = random.uniform(0.5, 1.5)
        await asyncio.sleep(base_sleep * state.velocity)

# --- Test the Simulator standalone ---
if __name__ == "__main__":
    async def test_run():
        q = asyncio.Queue()
        asyncio.create_task(run_simulator(q))
        while True:
            item = await q.get()
            print(f"[{item['timestamp'][11:19]}] {item['username']}: {item['message']}")

    try:
        asyncio.run(test_run())
    except KeyboardInterrupt:
        print("\nSimulator stopped.")