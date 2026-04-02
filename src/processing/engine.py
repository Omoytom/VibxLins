import torch
from transformers import pipeline

class VibeEngine:
    def __init__(self):
        print(" [Engine] Loading AI Model... (This may take a moment)")
        # We use a distilled model for high-speed 'Pulse' analysis
        self.classifier = pipeline(
            "sentiment-analysis", 
            model="distilbert-base-uncased-finetuned-sst-2-english",
            device=-1 # Set to 0 if you have an NVIDIA GPU, otherwise -1 for CPU
        )
        print(" [Engine] Model loaded and ready.")

    def analyze_vibe(self, message: str):
        """Analyzes text and returns a score between -1 (Salty) and 1 (Hype)."""
        if not message or len(message.strip()) == 0:
            return 0.0
            
        # Get the prediction from the AI model
        result = self.classifier(message)[0]
        label = result['label']
        score = result['score']

        # Convert POSITIVE/NEGATIVE labels into a numerical 'Pulse'
        # We want Positive to be up to +1.0, and Negative to be down to -1.0
        if label == "POSITIVE":
            return round(score, 3)
        else:
            return round(-score, 3)

# --- Test the engine standalone ---
if __name__ == "__main__":
    engine = VibeEngine()
    test_messages = [
        "THIS GAME IS AMAZING POG!!",
        "L streamer, actually throwing the game",
        "Anyone know the song name?",
        "Absolute clutch play! 🔥"
    ]

    print("\n--- Testing VibeLine Analysis ---")
    for msg in test_messages:
        vibe_score = engine.analyze_vibe(msg)
        
        # Simple logic to determine the vibe category
        sentiment = "🔥 HYPE" if vibe_score > 0.4 else "💀 SALT" if vibe_score < -0.4 else "😐 NEUTRAL"
        
        print(f"[{vibe_score:>6.3f}] {sentiment}: {msg}")