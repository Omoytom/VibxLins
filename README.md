
# VibxLinx: Real-Time Twitch Sentiment Engine

VibxLinx is a real-time, serverless sentiment analysis engine designed for live Twitch broadcasts. It ingests high-velocity chat data via IRC, processes the text through a Natural Language Processing (NLP) model in the cloud, and broadcasts the emotional polarity (Positive, Negative, Neutral) to a sleek, OBS-friendly web overlay via WebSockets.

** [Live Demo](https://omoytom.github.io/VibxLins/frontend/index.html?channel=eslcs)** *(Note: Add `?channel=username` to the URL to analyze any live Twitch channel)*

## Key Features
* **Real-Time Data Streaming:** Uses WebSockets to push processed chat data to the frontend with sub-second latency.
* **Serverless AI Architecture:** Leverages the Hugging Face Inference API (`cardiffnlp/twitter-roberta-base-sentiment-latest`) to process NLP tasks without heavy local memory requirements.
* **Dynamic Channel Routing:** Connect to any live Twitch stream instantly via URL parameters (e.g., `?channel=tarik`), perfect for streamers using browser sources in OBS or Streamlabs.
* **XSS Security & Rate Limiting:** Built-in connection capping to prevent DDoS, and strict HTML escaping on the frontend to neutralize malicious chat inputs.

##  Tech Stack
* **Backend:** Python, FastAPI, Uvicorn, WebSockets, HTTPX, Asyncio
* **AI / ML:** Hugging Face Inference API (Twitter RoBERTa Base)
* **Frontend:** Vanilla JavaScript, HTML5, CSS3
* **Deployment:** Render (Backend), GitHub Pages (Frontend)

---

## Architectural Pivot: Solving the OOM Crisis
*A note on engineering trade-offs.*

**The Initial Architecture (Monolithic):**
Originally, the application was built to run the PyTorch/Transformers pipeline locally on the backend server. However, loading the 500MB+ RoBERTa model into memory consistently triggered `Out of Memory (OOM)` crashes on cloud providers with strict RAM limits (512MB free tiers). 

**The Solution (Serverless API):**
To ensure high availability and keep infrastructure costs at zero, the architecture was pivoted from a *Monolithic Edge* approach to a *Microservice API* approach. 
1. **Removed Heavy Dependencies:** Dropped `torch` and `transformers` from `requirements.txt`, replacing them with the lightweight `httpx` asynchronous client.
2. **Cloud Offloading:** Chat messages are now routed asynchronously to Hugging Face's dedicated inference routers.
3. **Graceful Degradation:** Implemented strict timeouts and fallback logic (`return 0.0`) so the stream overlay never crashes, even if the NLP API experiences rate limiting or cold starts.

**The Result:** Memory footprint was reduced by **over 90%** (from crashing at >512MB to sitting comfortably at ~40MB), resulting in lightning-fast deployment builds and 100% uptime.

---

##  How It Works
1. **Frontend Connection:** A client opens the web UI and specifies a channel (`?channel=xqc`).
2. **WebSocket Handshake:** The FastAPI backend accepts the connection and dynamically spins up an asynchronous Twitch IRC listener for that specific channel.
3. **Queueing & Processing:** Incoming messages are pushed to an `asyncio.Queue`, pulled by a background pipeline, and sent to the Hugging Face API for sentiment scoring (-1.0 to 1.0).
4. **Broadcast:** The scored payload is formatted and broadcasted back through the WebSocket to update the visual gauge and chat feed in real-time.

---

##  Local Setup & Installation

If you want to run this project locally, follow these steps:

**1. Clone the repository**
git clone [https://github.com/omoytom/VibxLins.git](https://github.com/omoytom/VibxLins.git)
cd VibxLins

**2. Set up your Virtual Environment**
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`

**3. Install Dependencies**
pip install -r requirements.txt

**4. Environment Variables**
Create a .env file in the root directory and add your free Hugging Face API token:
HF_API_TOKEN=your_hugging_face_read_token_here

**5. Run the Server**
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

**6. Launch the Frontend**
Open index.html in your browser, or run it through a local tool like VS Code Live Server.

**License**
Distributed under the MIT License. See LICENSE for more information.
