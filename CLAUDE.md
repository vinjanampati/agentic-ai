# Project: agentic-ai (A2A Protocol Demo)

## What this is
A learning project for Google's Agent-to-Agent (A2A) protocol.
Three components work together: a Spring Boot REST API, a Python A2A agent powered by Google ADK + Gemini, and a Python A2A client.

## Architecture (IMPORTANT)
The agent is a **semantic proxy**, not a discovery-only provider.
The client NEVER talks to Spring Boot directly — all requests go through the agent.

```
Client (client.py)
  → A2A JSON-RPC → Agent (server.py + agent.py)
                     → Gemini decides which tool to call
                     → Tool calls Spring Boot REST API (:8080)
                     ← Returns natural language response
  ← artifacts
```

## Key files
| File | Role |
|------|------|
| `a2a-agent/agent/agent.py` | ADK tools + root_agent definition |
| `a2a-agent/server.py` | FastAPI A2A server (JSON-RPC, agent card) |
| `a2a-client/client.py` | A2A client (discovery + tasks/send) |
| `spring-boot-app/src/.../controller/` | REST endpoints (:8080) |

## Ports
- Spring Boot: `:8080`
- A2A Agent: `:8001`

## Running
```bash
# Terminal 1
cd spring-boot-app && mvn spring-boot:run

# Terminal 2
cd a2a-agent && source .env && python server.py

# Terminal 3
cd a2a-client && python client.py
```

## Conventions
- Python agents: tools are plain functions; docstring = LLM description; type hints = JSON schema
- Return `{"success": bool, ...}` from all tool functions, never raise exceptions
- One tool per action — no combined operations
- Agent model: `gemini-2.0-flash` (configured via `GOOGLE_API_KEY` in `.env`)

## GitHub
Repository: https://github.com/vinjanampati/agentic-ai
