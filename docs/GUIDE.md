# Google ADK & A2A Protocol — Practical Guide

## What is A2A?

A2A (Agent-to-Agent) is Google's open protocol for communication between AI agents.
It defines a standard HTTP + JSON-RPC interface so that any client — another agent,
a CLI tool, a web app — can talk to any A2A-compliant agent without knowing what
model or framework powers it.

The protocol has exactly two endpoints:

| Endpoint | Method | Purpose |
|---|---|---|
| `/.well-known/agent.json` | GET | **Agent Card** — who am I, what can I do? |
| `/` | POST | **JSON-RPC** — send tasks, get results |

---

## Architecture of This Project

```
┌─────────────────────┐   HTTP (REST)    ┌──────────────────────────────┐
│  Spring Boot API    │ ◀──────────────▶ │  A2A Agent (Python)          │
│  :8080              │                  │  ─────────────────────────── │
│                     │                  │  Google ADK + Gemini          │
│  /api/products      │                  │  :8001                        │
│  /api/orders        │                  └──────────────┬───────────────┘
│  /api/weather       │                                 │
└─────────────────────┘                                 │  A2A Protocol
                                                        │  (JSON-RPC 2.0)
                                        ┌───────────────▼───────────────┐
                                        │  A2A Client (Python)          │
                                        │  client.py                    │
                                        └───────────────────────────────┘
```

Key point: the **client only speaks A2A**. It never knows about Gemini, Spring Boot,
or any internal tool. The agent handles all translation.

---

## How A2A Communication Works

### Step 1 — Discovery (Agent Card)

Before sending any task the client fetches the agent card to learn what the agent
can do. This is the A2A equivalent of an API's OpenAPI spec.

```
GET /.well-known/agent.json
```

Response:
```json
{
  "name": "store_assistant",
  "description": "Store assistant: browse products, place orders, check weather",
  "version": "1.0.0",
  "url": "http://localhost:8001",
  "capabilities": { "streaming": false },
  "skills": [
    { "id": "product-catalog", "name": "Product Catalog", "description": "..." },
    { "id": "order-management", "name": "Order Management", "description": "..." }
  ]
}
```

### Step 2 — Send a Task

```
POST /
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "method": "tasks/send",
  "id": "<rpc-request-id>",
  "params": {
    "id": "<task-id>",
    "sessionId": "<session-id>",
    "message": {
      "role": "user",
      "parts": [{ "type": "text", "text": "Show me all products" }]
    }
  }
}
```

- `id` (top level) — correlates the JSON-RPC request to its response
- `params.id` — unique ID for this task
- `params.sessionId` — keeps conversation context across multiple turns
- `params.message.parts` — supports text, files, or structured data

### Step 3 — Read the Result

```json
{
  "jsonrpc": "2.0",
  "id": "<rpc-request-id>",
  "result": {
    "id": "<task-id>",
    "status": { "state": "completed" },
    "artifacts": [
      {
        "parts": [{ "type": "text", "text": "Here are the products…" }]
      }
    ]
  }
}
```

The agent's reply lives in `result.artifacts[].parts`. Parts can be text, images,
files, or structured JSON — depending on what the agent produces.

---

## How the Agent Works (Google ADK)

### Core Concept: Tools

Tools are plain Python functions. The LLM reads the **docstring** to decide when
to call each tool. The **type annotations** become the JSON schema for parameters.

```python
from google.adk.agents import Agent

def get_all_products() -> dict:
    """Get the full list of products available in the store catalog."""
    resp = httpx.get("http://localhost:8080/api/products")
    return {"products": resp.json()}

def get_product_by_id(product_id: str) -> dict:
    """Get detailed information about a single product by its ID.

    Args:
        product_id: The numeric ID of the product (e.g. "1", "2").
    """
    resp = httpx.get(f"http://localhost:8080/api/products/{product_id}")
    return {"product": resp.json()}

root_agent = Agent(
    name="store_assistant",
    model="gemini-2.0-flash",
    instruction="You are a helpful store assistant. Use tools to answer accurately.",
    tools=[get_all_products, get_product_by_id],
)
```

### What Happens on Each Request

```
User message arrives
        │
        ▼
  ADK sends message + tool definitions to Gemini
        │
        ▼
  Gemini decides which tool(s) to call
        │
        ▼
  ADK executes the tool (your Python function)
        │
        ▼
  Tool result returned to Gemini
        │
        ▼
  Gemini writes final response
        │
        ▼
  A2A server wraps it in artifacts and returns
```

### Session Context

Pass the same `sessionId` across multiple `tasks/send` calls and the agent
remembers the conversation history (what was asked, what tools were called,
what the results were).

---

## Wrapping Any REST Service

You can expose **any** REST service through an A2A agent — it does not have to be
Spring Boot, Java, or running locally. The tool function is the only bridge.

### Basic Pattern

```python
def my_tool(param: str) -> dict:
    """Clear description of what this does and when to use it."""
    resp = httpx.get(f"https://my-service.example.com/endpoint/{param}")
    return resp.json()
```

### With Authentication

```python
import os

def get_customer(customer_id: str) -> dict:
    """Look up a customer record by ID."""
    resp = httpx.get(
        f"https://api.example.com/customers/{customer_id}",
        headers={"Authorization": f"Bearer {os.getenv('API_TOKEN')}"},
    )
    return resp.json()
```

### Third-Party APIs

```python
def charge_card(customer_id: str, amount_cents: int) -> dict:
    """Charge a customer's saved card. Amount is in cents (e.g. 1000 = $10.00)."""
    resp = httpx.post(
        "https://api.stripe.com/v1/charges",
        auth=(os.getenv("STRIPE_SECRET_KEY"), ""),
        data={"customer": customer_id, "amount": amount_cents, "currency": "usd"},
    )
    return resp.json()

def send_sms(to: str, body: str) -> dict:
    """Send an SMS message to a phone number."""
    resp = httpx.post(
        "https://api.twilio.com/2010-04-01/Accounts/.../Messages.json",
        auth=(os.getenv("TWILIO_SID"), os.getenv("TWILIO_TOKEN")),
        data={"To": to, "From": os.getenv("TWILIO_FROM"), "Body": body},
    )
    return resp.json()
```

### Internal Microservices

```python
def check_inventory(warehouse_id: str, sku: str) -> dict:
    """Check real-time stock level for a product SKU in a warehouse."""
    resp = httpx.get(f"http://inventory-service/stock/{warehouse_id}/{sku}")
    return resp.json()

def submit_to_erp(order_data: dict) -> dict:
    """Submit a confirmed order to the ERP system for fulfilment."""
    resp = httpx.post("http://erp-service/orders", json=order_data)
    return resp.json()
```

### Rules for a Good Tool Function

| Rule | Why |
|---|---|
| Return a `dict` | ADK serialises the result back to the LLM as JSON |
| Write a precise docstring | This is exactly what the LLM reads to choose the tool |
| Annotate every parameter | ADK builds the JSON schema from type hints |
| Handle errors gracefully | Return `{"success": False, "error": "..."}` instead of raising |
| Keep tools focused | One tool per action; don't combine unrelated operations |

---

## Model Options

Google ADK is not locked to Gemini. You can use other models via LiteLLM.

### Gemini (default)
```python
agent = Agent(model="gemini-2.0-flash", ...)
# needs: GOOGLE_API_KEY
```

### OpenAI
```python
agent = Agent(model="litellm/openai/gpt-4o", ...)
# needs: OPENAI_API_KEY
```

### Anthropic / Claude
```python
agent = Agent(model="litellm/anthropic/claude-sonnet-4-5", ...)
# needs: ANTHROPIC_API_KEY
```

### Vertex AI (GCP service account, no API key)
```python
agent = Agent(model="gemini-2.0-flash", ...)
# needs: GOOGLE_CLOUD_PROJECT + Application Default Credentials
```

The A2A server and client code is unchanged regardless of model.

---

## Running This Project

```
Terminal 1                Terminal 2                Terminal 3
──────────────────────    ──────────────────────    ──────────────────────
cd spring-boot-app        cd a2a-agent              cd a2a-client
mvn spring-boot:run       cp .env.example .env      pip install -r requirements.txt
                          # add API key to .env
                          pip install -r requirements.txt
                          source .env
                          python server.py
                                                    python client.py
                                                    python client.py --interactive
                                                    python client.py --show-raw
```

### Spring Boot Endpoints (port 8080)

```
GET  /api/products
GET  /api/products/{id}
GET  /api/products/category/{category}
POST /api/products

GET  /api/orders
GET  /api/orders/{id}
POST /api/orders             body: { productId, quantity, customerName }
PATCH /api/orders/{id}/cancel

GET  /api/weather/{city}
```

### A2A Agent Endpoints (port 8001)

```
GET  /.well-known/agent.json    Agent card (discovery)
POST /                          JSON-RPC: tasks/send
```

---

## Project File Map

```
a2a/
├── spring-boot-app/
│   └── src/main/java/com/example/demo/
│       ├── DemoApplication.java
│       ├── controller/
│       │   ├── ProductController.java   GET+POST /api/products
│       │   ├── OrderController.java     GET+POST /api/orders
│       │   └── WeatherController.java   GET /api/weather/{city}
│       └── model/
│           ├── Product.java
│           └── Order.java
│
├── a2a-agent/
│   ├── agent/
│   │   ├── __init__.py
│   │   └── agent.py          ← ADK tools + root_agent definition
│   ├── server.py             ← FastAPI app implementing A2A protocol
│   ├── requirements.txt
│   └── .env.example          ← copy to .env, add GOOGLE_API_KEY
│
├── a2a-client/
│   ├── client.py             ← A2A protocol client (httpx only)
│   └── requirements.txt
│
├── README.md                 ← quick-start
└── GUIDE.md                  ← this file
```
