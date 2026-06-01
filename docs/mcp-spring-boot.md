# Exposing Spring Boot as an MCP Server

## Does the MCP Server Have to Be a Separate Python Service?

No — neither requirement is true.

**Language:** The MCP server can be written in any language with an official SDK:

| Language | SDK | Maturity |
|---|---|---|
| Python | `mcp[cli]` | Most mature, most examples |
| TypeScript / Node | `@modelcontextprotocol/sdk` | Also very mature |
| **Java / Kotlin** | `io.modelcontextprotocol:sdk` | Official SDK, works with Spring Boot |

**Separate service:** You have two options:

| Option | Description | Tradeoff |
|---|---|---|
| **A — Separate MCP server** | A new process wrapping Spring Boot | Spring Boot unchanged, but extra hop |
| **B — Embed MCP in Spring Boot** | Spring Boot exposes both REST and MCP | One less service, MCP lives next to business logic |

**Option B is the cleaner approach for this project.** You add the MCP SDK to
`pom.xml` and annotate your existing Spring controllers or services. The same
Spring Boot app serves both REST (`:8080`) and MCP on the same port.

```
Option A:  Agent → MCP Server (new process) → Spring Boot
Option B:  Agent → Spring Boot (which IS the MCP server)
```

---

## What is an MCP Server?

An MCP server is a lightweight service that exposes **resources** and **tools** in a
standard format any MCP-compatible agent can connect to.

| MCP Concept | Maps to | Example |
|-------------|---------|---------|
| **Resource** | Read-only data (GET) | Product list, order history |
| **Tool** | Action with side effects (POST/PATCH) | Place order, cancel order |
| **Prompt** | Reusable prompt template | (not used here) |

The Spring Boot API has both — read endpoints (products, weather) and write endpoints
(create order, cancel order). These map cleanly onto MCP resources and tools.

---

## Current Spring Boot Endpoints

```
GET  /api/products                        → list all products
GET  /api/products/{id}                   → get product by ID
GET  /api/products/category/{category}    → filter by category
POST /api/products                        → create product

GET  /api/orders                          → list all orders
GET  /api/orders/{id}                     → get order by ID
POST /api/orders                          → place an order
PATCH /api/orders/{id}/cancel             → cancel an order

GET  /api/weather/{city}                  → get weather for city
```

---

## MCP Mapping

```
Spring Boot endpoint                      MCP type    MCP name
─────────────────────────────────────────────────────────────────
GET  /api/products                    →  resource    store://products
GET  /api/products/{id}               →  resource    store://products/{id}
GET  /api/products/category/{cat}     →  resource    store://products/category/{cat}
GET  /api/orders                      →  resource    store://orders
GET  /api/orders/{id}                 →  resource    store://orders/{id}
GET  /api/weather/{city}              →  resource    store://weather/{city}
POST /api/orders                      →  tool        create_order
PATCH /api/orders/{id}/cancel         →  tool        cancel_order
POST /api/products                    →  tool        create_product
```

Rule of thumb: **GETs become resources, POST/PATCH become tools**.

---

## MCP Server Implementation (Python)

The MCP Python SDK (`mcp`) is the standard way to build an MCP server.
This server wraps the Spring Boot API and exposes it via MCP.

```python
# mcp-server/server.py

import httpx
from mcp.server.fastmcp import FastMCP

SPRING_BOOT_URL = "http://localhost:8080"

mcp = FastMCP("store-mcp-server")


# ── Resources (read-only, GET endpoints) ────────────────────────────────────

@mcp.resource("store://products")
def list_products() -> str:
    """Full product catalog."""
    resp = httpx.get(f"{SPRING_BOOT_URL}/api/products")
    return resp.text  # MCP resources return strings (JSON text is fine)


@mcp.resource("store://products/{product_id}")
def get_product(product_id: str) -> str:
    """Single product by ID."""
    resp = httpx.get(f"{SPRING_BOOT_URL}/api/products/{product_id}")
    return resp.text


@mcp.resource("store://products/category/{category}")
def get_products_by_category(category: str) -> str:
    """Products filtered by category."""
    resp = httpx.get(f"{SPRING_BOOT_URL}/api/products/category/{category}")
    return resp.text


@mcp.resource("store://orders")
def list_orders() -> str:
    """All orders placed."""
    resp = httpx.get(f"{SPRING_BOOT_URL}/api/orders")
    return resp.text


@mcp.resource("store://orders/{order_id}")
def get_order(order_id: str) -> str:
    """Single order by ID."""
    resp = httpx.get(f"{SPRING_BOOT_URL}/api/orders/{order_id}")
    return resp.text


@mcp.resource("store://weather/{city}")
def get_weather(city: str) -> str:
    """Current weather for a city."""
    resp = httpx.get(f"{SPRING_BOOT_URL}/api/weather/{city}")
    return resp.text


# ── Tools (actions with side effects, POST/PATCH endpoints) ─────────────────

@mcp.tool()
def create_order(product_id: str, quantity: int, customer_name: str) -> dict:
    """Place a new order for a product.

    Args:
        product_id:    ID of the product to order.
        quantity:      Number of units (must be >= 1).
        customer_name: Full name of the customer.
    """
    # Look up price first
    product = httpx.get(f"{SPRING_BOOT_URL}/api/products/{product_id}").json()
    resp = httpx.post(
        f"{SPRING_BOOT_URL}/api/orders",
        json={
            "productId": product_id,
            "quantity": quantity,
            "customerName": customer_name,
            "pricePerUnit": product["price"],
        },
    )
    return resp.json()


@mcp.tool()
def cancel_order(order_id: str) -> dict:
    """Cancel an existing order by ID.

    Args:
        order_id: ID of the order to cancel.
    """
    resp = httpx.patch(f"{SPRING_BOOT_URL}/api/orders/{order_id}/cancel")
    return resp.json()


@mcp.tool()
def create_product(name: str, price: float, category: str) -> dict:
    """Add a new product to the catalog.

    Args:
        name:     Product name.
        price:    Price in USD.
        category: Category (e.g. Electronics, Furniture, Kitchen).
    """
    resp = httpx.post(
        f"{SPRING_BOOT_URL}/api/products",
        json={"name": name, "price": price, "category": category},
    )
    return resp.json()


if __name__ == "__main__":
    mcp.run()
```

---

## How the Agent Connects to the MCP Server

With MCP in place, `agent.py` no longer calls Spring Boot directly. Instead it
connects to the MCP server at startup and uses its tools and resources.

```python
# a2a-agent/agent/agent.py  (with MCP)

from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

root_agent = Agent(
    name="store_assistant",
    model="gemini-2.0-flash",
    instruction="You are a helpful store assistant. Use tools to answer accurately.",
    tools=[
        MCPToolset(
            connection_params=StdioServerParameters(
                command="python",
                args=["../mcp-server/server.py"],
            )
        )
    ],
)
```

The ADK `MCPToolset` automatically discovers all tools and resources exposed by the
MCP server and makes them available to Gemini — no manual tool registration needed.

---

## Architecture With MCP

```
Client
  │ A2A JSON-RPC
  ▼
A2A Agent (server.py + agent.py)
  │ MCP protocol
  ▼
Spring Boot MCP Server (mcp-server/server.py)
  │ HTTP REST
  ▼
Spring Boot API :8080
```

The A2A layer (client ↔ agent) is **unchanged**. MCP only replaces the internal
wiring between the agent and Spring Boot.

---

## What Changes, What Stays the Same

| Component | Without MCP | With MCP |
|-----------|-------------|----------|
| `client.py` | Unchanged | Unchanged |
| `server.py` | Unchanged | Unchanged |
| `agent.py` | Defines tools with `httpx` calls | Uses `MCPToolset` — no manual tools |
| Spring Boot | Called directly by agent | Called by MCP server |
| New file needed | No | `mcp-server/server.py` |

---

## When to Add MCP

| Situation | Use MCP? |
|-----------|----------|
| One agent, one backend | No — current `httpx` approach is simpler |
| Multiple agents sharing the same Spring Boot API | Yes — all agents connect to one MCP server |
| Want to add other data sources (DB, files, GitHub) alongside Spring Boot | Yes — plug in more MCP servers without changing the agent |
| Want to reuse Spring Boot tools in Claude Desktop or other MCP clients | Yes — MCP server is immediately compatible |

---

## Project Structure With MCP Added

```
a2a/
├── spring-boot-app/       ← unchanged
├── mcp-server/            ← new
│   ├── server.py          ← MCP server wrapping Spring Boot
│   └── requirements.txt   ← mcp[cli], httpx
├── a2a-agent/             ← agent.py simplified, uses MCPToolset
├── a2a-client/            ← unchanged
└── docs/
```
