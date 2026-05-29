# Google ADK A2A Demo

A minimal but complete end-to-end example of the **Google Agent-to-Agent (A2A)** protocol.

```
┌─────────────────┐     HTTP (REST)      ┌──────────────────────────┐
│                 │ ──────────────────▶  │                          │
│  Spring Boot    │   /api/products       │   A2A Agent (Python)     │
│  REST API       │   /api/orders         │   ─────────────────────  │
│  :8080          │   /api/weather        │   Google ADK + Gemini    │
│                 │ ◀──────────────────  │   :8001                  │
└─────────────────┘                      └───────────────┬──────────┘
                                                          │  A2A Protocol
                                                          │  (JSON-RPC 2.0)
                                         ┌────────────────▼──────────┐
                                         │   A2A Client (Python)     │
                                         │   client.py               │
                                         └───────────────────────────┘
```

## What is A2A?

The **A2A protocol** (Agent-to-Agent) is Google's open standard for inter-agent communication.
An agent exposes two HTTP endpoints:

| Endpoint | Purpose |
|---|---|
| `GET /.well-known/agent.json` | **Agent Card** — capabilities, skills, supported modes |
| `POST /` | **JSON-RPC** — send tasks, receive results |

A task request looks like this:
```json
{
  "jsonrpc": "2.0",
  "method": "tasks/send",
  "id": "<rpc-id>",
  "params": {
    "id": "<task-id>",
    "sessionId": "<session>",
    "message": {
      "role": "user",
      "parts": [{ "type": "text", "text": "Show me all products" }]
    }
  }
}
```

The response carries output in `artifacts`:
```json
{
  "jsonrpc": "2.0",
  "id": "<rpc-id>",
  "result": {
    "id": "<task-id>",
    "status": { "state": "completed" },
    "artifacts": [
      { "parts": [{ "type": "text", "text": "Here are the products…" }] }
    ]
  }
}
```

## Components

### 1. Spring Boot REST API (`spring-boot-app/`)
Three controllers, all in-memory (no database needed):

| Controller | Endpoints |
|---|---|
| `ProductController` | `GET /api/products`, `GET /api/products/{id}`, `GET /api/products/category/{cat}`, `POST /api/products` |
| `OrderController` | `GET /api/orders`, `GET /api/orders/{id}`, `POST /api/orders`, `PATCH /api/orders/{id}/cancel` |
| `WeatherController` | `GET /api/weather/{city}` |

### 2. A2A Agent (`a2a-agent/`)
- **`agent/agent.py`** — defines the ADK `root_agent` with 6 tools that call the Spring Boot API
- **`server.py`** — FastAPI app that implements the A2A protocol and uses ADK's `Runner` to process messages

### 3. A2A Client (`a2a-client/client.py`)
A plain `httpx` client that follows the A2A protocol — no ADK dependency needed.
Supports scripted demo mode and interactive mode.

## Quick Start

### Terminal 1 — Spring Boot API
```bash
cd spring-boot-app
./mvnw spring-boot:run
# API now running at http://localhost:8080
```

### Terminal 2 — A2A Agent
```bash
cd a2a-agent
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY
pip install -r requirements.txt
source .env  # or: export GOOGLE_API_KEY=...
python server.py
# Agent now running at http://localhost:8001
```

### Terminal 3 — A2A Client
```bash
cd a2a-client
pip install -r requirements.txt

python client.py                  # scripted demo
python client.py --interactive    # interactive chat
python client.py --show-raw       # print raw JSON-RPC payloads
```

## Key Files

```
a2a/
├── spring-boot-app/
│   └── src/main/java/com/example/demo/
│       ├── controller/
│       │   ├── ProductController.java
│       │   ├── OrderController.java
│       │   └── WeatherController.java
│       └── model/
│           ├── Product.java
│           └── Order.java
├── a2a-agent/
│   ├── agent/
│   │   └── agent.py        ← ADK tools + root_agent definition
│   └── server.py           ← A2A protocol server (FastAPI)
└── a2a-client/
    └── client.py           ← A2A protocol client
```

## Getting a Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create a new API key
3. Paste it into `a2a-agent/.env`
