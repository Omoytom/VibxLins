import asyncio
import re
from datetime import datetime

async def run_twitch_listener(output_queue: asyncio.Queue, target_channel: str):
    """Connects to a live Twitch channel and pushes messages to the AI engine."""
    
    server = 'irc.chat.twitch.tv'
    port = 6667
    nickname = 'justinfan12345' # Twitch allows 'justinfan' accounts for anonymous read-only access
    
    print(f"🔗 [Twitch] Connecting to channel: {target_channel}...")
    
    # Open standard TCP connection to Twitch
    reader, writer = await asyncio.open_connection(server, port)
    
    # Send login credentials (Anonymous)
    writer.write(f"PASS SCHMOOPIIE\r\n".encode('utf-8'))
    writer.write(f"NICK {nickname}\r\n".encode('utf-8'))
    writer.write(f"JOIN #{target_channel.lower()}\r\n".encode('utf-8'))
    await writer.drain()
    
    print(f" [Twitch] Connected! Listening for real vibes in #{target_channel}...\n")
    
    # Regex to grab the username and the message from the raw IRC text
    # Raw IRC looks like: :username!username@username.tmi.twitch.tv PRIVMSG #channel :Hello world!
    chat_regex = re.compile(r"^:(\w+)!\w+@\w+\.tmi\.twitch\.tv PRIVMSG #\w+ :(.*)")
    
    try:
        while True:
            data = await reader.readline()
            if not data:
                break
                
            raw_message = data.decode('utf-8', errors='ignore').strip()
            
            # Twitch sends 'PING' every few minutes. We MUST reply 'PONG' or they kick us.
            if raw_message.startswith("PING"):
                writer.write("PONG :tmi.twitch.tv\r\n".encode('utf-8'))
                await writer.drain()
                continue
                
            # Parse actual chat messages
            match = chat_regex.match(raw_message)
            if match:
                username = match.group(1)
                chat_text = match.group(2)
                
                # Format it exactly like our Simulator did, so the AI doesn't know the difference!
                payload = {
                    "username": username,
                    "message": chat_text,
                    "platform": "twitch",
                    "timestamp": datetime.now().isoformat()
                }
                
                # Send it to the AI pipeline
                await output_queue.put(payload)
                
    except asyncio.CancelledError:
        print("\n [Twitch] Disconnecting from channel...")
    except Exception as e:
        print(f" [Twitch] Connection Error: {e}")
    finally:
        writer.close()
        await writer.wait_closed()

# --- Test the Listener standalone ---
if __name__ == "__main__":
    async def test_run():
        q = asyncio.Queue()
        # Put any live Twitch streamer's name here (e.g., "tarik", "xqc", "kai_cenat")
        test_channel = "hasanabi" 
        
        asyncio.create_task(run_twitch_listener(q, test_channel))
        while True:
            item = await q.get()
            print(f"[{item['timestamp'][11:19]}] {item['username']}: {item['message']}")

    try:
        asyncio.run(test_run())
    except KeyboardInterrupt:
        pass