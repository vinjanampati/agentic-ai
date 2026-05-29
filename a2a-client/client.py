"""
A2A Client — demonstrates the Google Agent-to-Agent (A2A) protocol.

How A2A communication works, step by step:

  1. DISCOVERY  — fetch /.well-known/agent.json to learn what the agent can do
  2. TASK SEND  — POST / with JSON-RPC method "tasks/send" and a message
  3. READ RESULT — parse the "artifacts" array from the response

The protocol is transport-agnostic (HTTP here) and model-agnostic — neither
side needs to know the other's LLM or implementation language.

Usage:
  python client.py                  # runs a scripted demo conversation
  python client.py --interactive    # interactive chat mode
  python client.py --show-raw       # prints raw JSON-RPC payloads
"""

import sys
import uuid
import json
import httpx

A2A_URL = "http://localhost:8001"


# ---------------------------------------------------------------------------
# A2A protocol helpers
# ---------------------------------------------------------------------------

def discover_agent(show_raw: bool = False) -> dict:
    """
    Step 1 — Agent discovery.
    Every A2A server exposes its capabilities at this well-known path.
    """
    resp = httpx.get(f"{A2A_URL}/.well-known/agent.json", timeout=10)
    resp.raise_for_status()
    card = resp.json()
    if show_raw:
        print("\n[RAW] Agent Card:")
        print(json.dumps(card, indent=2))
    return card


def send_task(
    message: str,
    session_id: str,
    user_id: str = "demo_user",
    show_raw: bool = False,
) -> str:
    """
    Step 2 & 3 — Send a task and extract the text response.

    The JSON-RPC request structure:
      {
        "jsonrpc": "2.0",
        "method":  "tasks/send",       ← A2A method name
        "id":      "<rpc-request-id>", ← correlates request↔response
        "params":  {
          "id":        "<task-id>",    ← unique ID for this task
          "sessionId": "<session-id>", ← keeps conversation context
          "message":   {
            "role":  "user",
            "parts": [{ "type": "text", "text": "…" }]
          }
        }
      }

    The response result carries the agent's reply in "artifacts":
      {
        "id": "<task-id>",
        "status": { "state": "completed" },
        "artifacts": [
          { "parts": [{ "type": "text", "text": "…" }] }
        ]
      }
    """
    payload = {
        "jsonrpc": "2.0",
        "method": "tasks/send",
        "id": str(uuid.uuid4()),       # JSON-RPC request ID
        "params": {
            "id": str(uuid.uuid4()),   # task ID
            "sessionId": session_id,
            "userId": user_id,
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": message}],
            },
        },
    }

    if show_raw:
        print("\n[RAW] → Request:")
        print(json.dumps(payload, indent=2))

    resp = httpx.post(f"{A2A_URL}/", json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()

    if show_raw:
        print("\n[RAW] ← Response:")
        print(json.dumps(data, indent=2))

    # Extract text from the first text artifact part
    result = data.get("result", {})
    for artifact in result.get("artifacts", []):
        for part in artifact.get("parts", []):
            if part.get("type") == "text":
                return part["text"]

    error = data.get("error")
    if error:
        return f"[Agent error {error['code']}] {error['message']}"

    return "(no text response)"


# ---------------------------------------------------------------------------
# Demo helpers
# ---------------------------------------------------------------------------

def print_separator(label: str = ""):
    line = "─" * 60
    if label:
        pad = (58 - len(label)) // 2
        print(f"┌{'─' * pad} {label} {'─' * pad}┐")
    else:
        print(line)


def chat(user_msg: str, session_id: str, show_raw: bool = False):
    print(f"\n You  ▶  {user_msg}")
    response = send_task(user_msg, session_id, show_raw=show_raw)
    print(f" Agent ◀  {response}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    show_raw = "--show-raw" in sys.argv
    interactive = "--interactive" in sys.argv

    print_separator("A2A Client Demo")
    print()

    # ── Step 1: Discover ────────────────────────────────────────────────────
    print("▶ Discovering agent at", A2A_URL)
    try:
        card = discover_agent(show_raw=show_raw)
    except httpx.ConnectError:
        print(f"\n✗  Cannot reach A2A agent at {A2A_URL}")
        print("   Make sure the agent server is running:  python server.py")
        sys.exit(1)

    print(f"  Name        : {card['name']}")
    print(f"  Description : {card['description']}")
    print(f"  Skills      : {', '.join(s['name'] for s in card.get('skills', []))}")
    print()

    # ── Step 2: Start a session ─────────────────────────────────────────────
    # A session ID lets the agent maintain conversation context across turns.
    session_id = str(uuid.uuid4())
    print(f"▶ Session ID: {session_id[:8]}…")
    print()

    if interactive:
        # ── Interactive mode ─────────────────────────────────────────────────
        print("▶ Interactive mode  (Ctrl+C or empty line to quit)\n")
        while True:
            try:
                user_input = input(" You  ▶  ").strip()
                if not user_input:
                    break
                response = send_task(user_input, session_id, show_raw=show_raw)
                print(f" Agent ◀  {response}\n")
            except KeyboardInterrupt:
                print("\nBye!")
                break
    else:
        # ── Scripted demo ────────────────────────────────────────────────────
        print("▶ Running scripted demo conversation\n")

        print_separator("Turn 1 — List products")
        chat("What products do you have in stock?", session_id, show_raw)

        print_separator("Turn 2 — Filter by category")
        chat("Show me only the Electronics items", session_id, show_raw)

        print_separator("Turn 3 — Product detail")
        chat("Tell me more about product ID 3", session_id, show_raw)

        print_separator("Turn 4 — Place an order")
        chat(
            "Please order 2 units of the Wireless Headphones for customer Alice Smith",
            session_id,
            show_raw,
        )

        print_separator("Turn 5 — Confirm order was recorded")
        chat("Show me all current orders", session_id, show_raw)

        print_separator("Turn 6 — Weather lookup")
        chat("What's the weather like in Tokyo right now?", session_id, show_raw)

        print_separator("Done")


if __name__ == "__main__":
    main()
