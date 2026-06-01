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
| **Prompt** | Reusable prompt template | Summarise orders, recommend products |

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

## MCP Prompts

Prompts are reusable message templates the MCP server pre-defines. The agent (or any
MCP client like Claude Desktop) can request them by name, optionally passing arguments,
and the server fills in the template and returns ready-to-use messages.

**When are they useful?**
- You have a complex, multi-step query you want to standardise
- You want consistent phrasing for recurring tasks (daily reports, summaries)
- You want to guide the LLM with curated context without repeating it in every request

**Three examples for this project:**

### 1. Summarise all orders for a customer

The agent needs to fetch all orders, filter by customer, and format a summary.
Rather than leaving the LLM to figure out the phrasing each time, a prompt
packages this as a standard request.

```python
from mcp.server.fastmcp import FastMCP
from mcp.types import PromptMessage, TextContent
import httpx

mcp = FastMCP("store-mcp-server")

@mcp.prompt()
def customer_order_summary(customer_name: str) -> list[PromptMessage]:
    """Generate a prompt asking the agent to summarise orders for a customer."""
    orders = httpx.get("http://localhost:8080/api/orders").json()
    customer_orders = [o for o in orders if o["customerName"] == customer_name]

    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=(
                    f"Here are all orders placed by {customer_name}:\n\n"
                    f"{customer_orders}\n\n"
                    f"Please summarise: total orders, total spend, and most recent order."
                ),
            ),
        )
    ]
```

When invoked, the server fetches the live order data and injects it into the prompt
before handing it to the LLM — the LLM receives a fully populated message, not a
template with blanks.

---

### 2. Product recommendation by category

Fetches the current product list and asks the LLM to recommend the best product
in a given category based on price.

```python
@mcp.prompt()
def recommend_product(category: str, budget: float) -> list[PromptMessage]:
    """Recommend the best product in a category within a budget."""
    products = httpx.get(
        f"http://localhost:8080/api/products/category/{category}"
    ).json()

    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=(
                    f"Available {category} products:\n\n{products}\n\n"
                    f"The customer has a budget of ${budget:.2f}. "
                    f"Recommend the best option and explain why."
                ),
            ),
        )
    ]
```

---

### 3. Daily store report

No arguments — fetches all live data and asks the LLM to produce a full store summary.

```python
@mcp.prompt()
def daily_store_report() -> list[PromptMessage]:
    """Generate a daily report prompt with live products and orders."""
    products = httpx.get("http://localhost:8080/api/products").json()
    orders = httpx.get("http://localhost:8080/api/orders").json()

    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=(
                    f"Store snapshot as of today:\n\n"
                    f"Products ({len(products)} total):\n{products}\n\n"
                    f"Orders ({len(orders)} total):\n{orders}\n\n"
                    f"Please produce a daily report covering: total revenue, "
                    f"best-selling product, and any low-stock items (quantity < 5)."
                ),
            ),
        )
    ]
```

---

### Key difference: Prompt vs Tool vs Resource

| | Resource | Tool | Prompt |
|---|---|---|---|
| **Returns** | Raw data | Action result | Ready-to-send LLM message |
| **LLM involvement** | LLM reads data and decides what to do | LLM decides to call it | LLM receives a pre-built message |
| **Use case** | "Give me the products list" | "Place this order" | "Give me a filled-in question I can send to the LLM" |
| **Who fills in data** | MCP client reads it | Tool executes it | MCP server injects live data into the template |

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
