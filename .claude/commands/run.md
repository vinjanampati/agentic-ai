Run the full A2A stack locally.

Remind the user to open 3 terminals and run:

**Terminal 1 — Spring Boot API**
```bash
cd spring-boot-app && mvn spring-boot:run
```

**Terminal 2 — A2A Agent**
```bash
cd a2a-agent && source .env && python server.py
```

**Terminal 3 — Client**
```bash
cd a2a-client && python client.py
# or interactive mode:
python client.py --interactive
# or see raw JSON-RPC:
python client.py --show-raw
```

Check that:
- Spring Boot is healthy: http://localhost:8080/api/products
- Agent card is up: http://localhost:8001/.well-known/agent.json
