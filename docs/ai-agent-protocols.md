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
     ▼
MCP Server (exposes tools, files, APIs)
```

- An MCP server exposes resources (files, DB queries, APIs) in a standard format
- The agent connects to one or many MCP servers
- Complementary to A2A — MCP handles tool access, A2A handles agent-to-agent calls

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
