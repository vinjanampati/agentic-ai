"""
A2A Server — implements the Google Agent-to-Agent (A2A) protocol over HTTP.

The A2A protocol uses JSON-RPC 2.0. The two key endpoints are:

  GET  /.well-known/agent.json   → Agent Card  (who am I, what can I do?)
  POST /                          → JSON-RPC    (tasks/send, tasks/get, …)

Flow of a tasks/send call:
  Client → POST /  { method: "tasks/send", params: { message: { parts: [{text: "…"}] } } }
  Server → runs the ADK agent with the message text
  Server → returns { result: { artifacts: [{ parts: [{type:"text", text:"…"}] }] } }

Run this file directly:
  python server.py

Or use the ADK CLI (it discovers root_agent automatically):
  adk api_server agent --port 8001
"""

import asyncio
import uuid
import logging

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agent.agent import root_agent

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ADK runtime setup
# Each unique (user_id, session_id) pair gets its own conversation history.
# ---------------------------------------------------------------------------
session_service = InMemorySessionService()
runner = Runner(
    agent=root_agent,
    app_name="store_assistant",
    session_service=session_service,
)

# ---------------------------------------------------------------------------
# Agent Card — the A2A "business card" that clients discover first.
# Clients fetch this to know what skills/capabilities the agent has before
# they start sending tasks.
# ---------------------------------------------------------------------------
AGENT_CARD = {
    "name": "store_assistant",
    "description": "Store assistant: browse products, place orders, check weather",
    "version": "1.0.0",
    "url": "http://localhost:8001",
    "capabilities": {
        "streaming": False,         # we respond synchronously in this demo
        "pushNotifications": False,
    },
    "defaultInputModes": ["text/plain"],
    "defaultOutputModes": ["text/plain"],
    "skills": [
        {
            "id": "product-catalog",
            "name": "Product Catalog",
            "description": "List all products, filter by category, or look up a specific product by ID",
            "examples": [
                "Show me all products",
                "What electronics do you have?",
                "Tell me about product 3",
            ],
        },
        {
            "id": "order-management",
            "name": "Order Management",
            "description": "Place new orders and view existing ones",
            "examples": [
                "Order 2 units of product 1 for Alice",
                "Show all current orders",
            ],
        },
        {
            "id": "weather",
            "name": "Weather Lookup",
            "description": "Get current weather for major cities",
            "examples": ["What's the weather in Tokyo?"],
        },
    ],
}

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="A2A Agent Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/.well-known/agent.json", summary="A2A Agent Card")
async def agent_card():
    """
    A2A Discovery endpoint.
    Clients call this first to learn what the agent can do.
    """
    return JSONResponse(AGENT_CARD)


@app.post("/", summary="A2A JSON-RPC endpoint")
async def jsonrpc_handler(request: Request):
    """
    A2A task endpoint (JSON-RPC 2.0).
    Currently supports: tasks/send
    """
    body = await request.json()
    rpc_id = body.get("id")
    method = body.get("method")
    params = body.get("params", {})

    log.info("← %s  (rpc_id=%s)", method, rpc_id)

    if method == "tasks/send":
        return await _handle_tasks_send(rpc_id, params)

    # Unknown method
    return _rpc_error(rpc_id, -32601, f"Method not supported: {method}")


# ---------------------------------------------------------------------------
# tasks/send handler
# ---------------------------------------------------------------------------
async def _handle_tasks_send(rpc_id: str, params: dict) -> JSONResponse:
    task_id = params.get("id") or str(uuid.uuid4())
    message = params.get("message", {})
    session_id = params.get("sessionId") or str(uuid.uuid4())
    user_id = params.get("userId", "anonymous")

    # Extract plain text from the A2A message parts array
    user_text = ""
    for part in message.get("parts", []):
        if part.get("type") == "text":
            user_text = part["text"]
            break

    if not user_text:
        return _rpc_error(rpc_id, -32602, "Message must contain at least one text part")

    log.info("  user_text=%r  session=%s", user_text[:80], session_id)

    # Ensure session exists in ADK's session service
    session = await session_service.get_session(
        app_name="store_assistant", user_id=user_id, session_id=session_id
    )
    if session is None:
        session = await session_service.create_session(
            app_name="store_assistant", user_id=user_id, session_id=session_id
        )

    # Run the ADK agent and collect the final text response
    adk_message = types.Content(role="user", parts=[types.Part(text=user_text)])
    response_text = ""

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=adk_message,
    ):
        # ADK emits many events (tool calls, intermediate steps).
        # We only care about the final text response.
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    response_text += part.text

    log.info("  → response length=%d chars", len(response_text))

    # Wrap in A2A response envelope
    return JSONResponse(
        {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "result": {
                "id": task_id,
                "status": {"state": "completed"},
                # artifacts carry the actual output — can be text, data, files, etc.
                "artifacts": [
                    {
                        "parts": [{"type": "text", "text": response_text}]
                    }
                ],
            },
        }
    )


def _rpc_error(rpc_id, code: int, message: str) -> JSONResponse:
    return JSONResponse(
        {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": code, "message": message}}
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Starting A2A agent server on http://localhost:8001")
    print("  Agent card : http://localhost:8001/.well-known/agent.json")
    print("  RPC endpoint: http://localhost:8001/\n")
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="warning")
