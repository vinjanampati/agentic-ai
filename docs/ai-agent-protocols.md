# AI Agent Communication: Industry Landscape

## The Core Concept: Tool Calling

All modern LLMs support **tool calling** (also called function calling) — the ability for the model to decide to invoke a function rather than just return text.

```
User message
     │
     ▼
LLM sees message + tool definitions (JSON schema)
     │
     ▼
LLM decides which tool to call and with what args
     │
     ▼
App executes the tool, feeds result back to LLM
     │
     ▼
LLM writes final response
```

This is the engine **inside** every AI agent. What differs between platforms is how that agent is exposed to the outside world.

---

## OpenAI — Everything Inside One App

With OpenAI function calling, the entire flow lives inside your application:

```
REST request (string)
     │
     ▼
Your app → OpenAI API (tools defined inline in the request)
                │
                ▼
           LLM picks tool → your app executes it
                │
                ▼
           LLM writes response
     │
     ▼
REST response (string)
```

- Tools are defined **inline** in every API request as JSON schema
- Your app both defines and executes the tools
- The client sending the REST request has no visibility into tools
- Everything is **one black box** — one app, one LLM, one conversation
- No standard way for another agent to discover or call your agent

**OpenAI's related offerings:**

| Product | What it adds |
|---------|-------------|
| Function calling | Internal tool use within one API call |
| Assistants API | Adds persistent threads + memory, still within OpenAI |
| GPT Actions | Lets a ChatGPT plugin call external REST APIs — ChatGPT-specific |

None of these define an open standard for **agent-to-agent** communication.

---

## Google A2A — Agents as Standalone Services

A2A (Agent-to-Agent) treats each agent as a **published service** with a standard interface. Any client — another agent, a CLI, a web app — can discover and call it without knowing the internals.

```
Client (any language, any framework)
     │  A2A JSON-RPC
     ▼
Agent (owns its tools internally)
     │  HTTP / any protocol
     ▼
Backend (REST API, database, third-party service…)
```

- The agent advertises its capabilities via an **Agent Card** (`/.well-known/agent.json`)
- Clients send natural language; the agent handles all tool orchestration internally
- Client never knows which LLM, tools, or backend the agent uses
- Agents can call **other agents** — enabling multi-agent pipelines

---

## Anthropic MCP — Connecting Agents to Data Sources

MCP (Model Context Protocol) is a different layer — it standardizes how an agent connects to **tools and data sources**, not how agents talk to each other.

```
Agent (Claude)
     │  MCP
     ├── File system server
     ├── Database server
     └── GitHub server
```

- An MCP server exposes resources (files, DB queries, APIs) in a standard format
- The agent connects to one or many MCP servers
- Complementary to A2A — MCP handles tool access, A2A handles agent-to-agent calls

---

## MCP vs A2A — Are They the Same?

They look similar on the surface (both are protocols over HTTP) but solve **different problems at different layers**.

| | MCP | A2A |
|---|---|---|
| **What's on the other end** | A data source or tool | Another agent (with its own LLM) |
| **Who does the reasoning** | Your agent | The remote agent |
| **Result you get back** | Raw data | Reasoned natural language response |
| **Analogy** | Plugin / API client | Contractor you delegate to |

**MCP** = how an agent gets its tools and data ("what can I access?")

**A2A** = how agents delegate work to each other ("who can I ask to do this?")

They are **complementary**, not competing. A production system would use both:

```
Orchestrator Agent
  │ MCP         ← gets its own tools (files, DBs, APIs)
  │ A2A         ← delegates to specialist agents
  ▼
Store Agent
  │ MCP         ← store agent also has its own MCP tools
  ▼
Spring Boot API
```

---

## Side-by-Side Comparison

| | OpenAI Function Calling | Google A2A | Anthropic MCP |
|---|---|---|---|
| **Purpose** | Internal LLM tool use | Agent-to-agent communication | Agent-to-tool/data connection |
| **Scope** | Inside one app | Across separate services | Inside one agent's toolchain |
| **Client knows about tools** | Yes (defines them) | No | No |
| **Standard discovery** | No | Yes (Agent Card) | Yes (MCP server manifest) |
| **Multi-agent** | Hard | Built-in | Not the focus |
| **LLM agnostic** | No — OpenAI only | Yes | Yes |
| **Open standard** | No | Yes | Yes |

---

## How This Project Fits

This project uses **both** OpenAI-style tool calling and A2A:

```
Client
  │ A2A JSON-RPC          ← standard agent interface (Google A2A)
  ▼
Agent (Gemini + ADK tools) ← tool calling internally (same concept as OpenAI)
  │ HTTP REST
  ▼
Spring Boot API
```

- **Internally**: Gemini uses tool calling to decide which Spring Boot endpoint to hit
- **Externally**: The agent is exposed as an A2A service any client can discover and call

The function calling is the **engine**. A2A is the **interface the engine presents to the world**.

---

## How MCP Could Fit Into This Project

Currently the agent calls Spring Boot directly via `httpx` inside each tool function.
With MCP, the Spring Boot API would instead be wrapped as an **MCP server**, and the
agent would connect to it via the MCP protocol rather than raw HTTP.

**Current architecture (no MCP):**
```
Agent (agent.py)
  │ httpx (raw HTTP)
  ▼
Spring Boot :8080
```

**With MCP:**
```
Agent (agent.py)
  │ MCP protocol
  ▼
Spring Boot MCP Server   ← new layer wrapping :8080
  │ HTTP REST
  ▼
Spring Boot :8080
```

**What changes in `agent.py`:**

Instead of each tool making a raw `httpx` call:
```python
# Current — raw HTTP inside the tool
def get_all_products() -> dict:
    resp = httpx.get("http://localhost:8080/api/products")
    return {"products": resp.json()}
```

The tool would call the MCP server and let MCP handle the HTTP:
```python
# With MCP — agent reads from MCP resource
def get_all_products() -> dict:
    result = mcp_client.read_resource("store://products")
    return {"products": result}
```

**Why you'd do this:**

| Reason | Explanation |
|--------|-------------|
| Reusability | Any MCP-compatible agent can use the same Spring Boot MCP server |
| Standardization | No custom HTTP logic per tool — MCP handles transport |
| Composability | Plug in other MCP servers (database, file system) without changing agent code |
| Swappability | Swap Spring Boot for a different backend without touching the agent |

**Why you might not bother for this project:**

The current approach (raw `httpx` in each tool) is simpler and works fine for a single agent
talking to a single backend. MCP adds value when **multiple agents** need to share the same
tools, or when you want to plug in many different data sources using one standard interface.
