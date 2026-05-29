# Architecture: A2A Agent as a Semantic Proxy

## The Core Question

> Does the client call Spring Boot directly after discovering services, or does everything go through the agent?

**Answer: Everything goes through the agent. It is a proxy, not just a discovery provider.**

---

## Request Flow

```
┌──────────────┐    A2A (JSON-RPC)    ┌────────────────────────────┐
│   Client     │ ──────────────────▶  │  A2A Agent (Python)        │
│  client.py   │                      │  ─────────────────────────  │
│              │                      │  1. Receives natural lang.  │
│              │                      │  2. Sends to Gemini LLM     │
│              │                      │  3. Gemini picks a tool     │
│              │                      │  4. Tool calls Spring Boot  │
│              │                      │  5. Result → Gemini         │
│              │                      │  6. Gemini writes response  │
│              │ ◀──────────────────  │  7. Wraps in A2A artifact   │
└──────────────┘    A2A (JSON-RPC)    └────────────┬───────────────┘
                                                   │ HTTP (REST)
                                      ┌────────────▼───────────────┐
                                      │  Spring Boot API            │
                                      │  :8080                      │
                                      │  /api/products              │
                                      │  /api/orders                │
                                      │  /api/weather               │
                                      └─────────────────────────────┘
```

---

## What the Client Does

### Step 1 — Discovery (metadata only, no Spring Boot)
```
GET /.well-known/agent.json
```
Returns the Agent Card: name, description, skills. This tells the client what the agent can do — it does **not** reveal Spring Boot or any backend detail.

### Step 2 — Send a natural language task
```
POST /
{
  "jsonrpc": "2.0",
  "method": "tasks/send",
  "params": {
    "sessionId": "abc-123",
    "message": {
      "parts": [{ "type": "text", "text": "Order 2 Wireless Headphones for Alice" }]
    }
  }
}
```

### Step 3 — Read the response
```json
{
  "result": {
    "status": { "state": "completed" },
    "artifacts": [
      { "parts": [{ "type": "text", "text": "Order placed! Total: $59.98" }] }
    ]
  }
}
```

The client only speaks A2A. It has no knowledge of REST endpoints, Spring Boot, or Gemini.

---

## What the Agent Does (the proxy layer)

Inside `agent.py`, each Spring Boot endpoint is wrapped as an ADK tool:

```python
def create_order(product_id: str, quantity: int, customer_name: str) -> dict:
    """Place an order for a product."""
    # 1. Look up product price
    product = httpx.get(f"{SPRING_BOOT_URL}/api/products/{product_id}").json()
    # 2. Submit order
    order = httpx.post(f"{SPRING_BOOT_URL}/api/orders", json={...}).json()
    return {"success": True, "order": order}
```

Gemini reads the docstring to decide when to call this tool. The agent handles:
- Natural language → tool selection (Gemini)
- Tool execution → Spring Boot HTTP calls (Python)
- Spring Boot response → natural language (Gemini)
- Natural language → A2A artifact (server.py)

---

## Why This Design

| Concern | Handled by |
|---------|-----------|
| Protocol translation (NL ↔ REST) | Agent (Gemini + tools) |
| Backend encapsulation | Agent hides Spring Boot from client |
| Multi-turn conversation memory | Agent session (`sessionId`) |
| Client simplicity | Client only needs JSON-RPC over HTTP |
| Backend flexibility | Swap Spring Boot for any REST API without changing client |

---

## Comparison: Proxy vs Discovery-Only

| Mode | What client does after discovery |
|------|----------------------------------|
| **This project (proxy)** | Sends ALL requests to agent; agent calls backend |
| Discovery-only | Gets backend URLs from agent, then calls backend directly |

This project uses the **proxy model**, which is the standard A2A pattern. The agent card is a capability advertisement, not a service registry.
