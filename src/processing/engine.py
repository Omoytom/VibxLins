import os

# 1. Force Hugging Face to save the model locally
os.environ["HF_HOME"] = "./ai_cache"
# 2. Stop the annoying symlink warnings
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
# 3. THE FIX: Reroute the download through a global mirror to bypass network blocks
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

import torch
from transformers import pipeline

class VibeEngine:
    def __init__(self):
        print("🧠 [Engine] Loading Ethical AI Model via Mirror...")
        self.classifier = pipeline(
            "sentiment-analysis", 
            model="cardiffnlp/twitter-roberta-base-sentiment-latest",
            device=-1,
            use_safetensors=False 
        )
        print("✅ [Engine] RoBERTa Model loaded and ready.")

    def analyze_vibe(self, message: str):
        if not message or len(message.strip()) == 0:
            return 0.0
            
        safe_message = message[:512] 
        result = self.classifier(safe_message)[0]
        label = result['label'].lower() 
        score = result['score']

        if label == "label_2" or label == "positive": 
            return round(score, 3)
        elif label == "label_0" or label == "negative":
            return round(-score, 3)
        else:
            return 0.0 

if __name__ == "__main__":
    engine = VibeEngine()
    test_messages = ["THIS GAME IS AMAZING POG!! 😭🔥", "that play was absolutely sick"]
    print("\n--- Testing Upgraded VibeLine Analysis ---")
    for msg in test_messages:
        vibe_score = engine.analyze_vibe(msg)
        sentiment = "🟢 POSITIVE" if vibe_score > 0.4 else "🔴 NEGATIVE" if vibe_score < -0.4 else "⚪ NEUTRAL"
        print(f"[{vibe_score:>6.3f}] {sentiment}: {msg}")