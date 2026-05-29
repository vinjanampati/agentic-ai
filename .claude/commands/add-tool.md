Add a new tool to the A2A agent.

Ask the user:
1. What Spring Boot endpoint should this tool call? (method, path, params)
2. What should the tool be named?
3. What description should the LLM see?

Then edit `a2a-agent/agent/agent.py` to:
- Add the tool function following this pattern:
  ```python
  def tool_name(param: str) -> dict:
      """Clear description of what this does and when to use it.

      Args:
          param: Description of the parameter.
      """
      try:
          resp = httpx.get(f"{SPRING_BOOT_URL}/api/endpoint/{param}", timeout=10)
          resp.raise_for_status()
          return {"success": True, "data": resp.json()}
      except Exception as e:
          return {"success": False, "error": str(e)}
  ```
- Add the function to the `tools=[...]` list in `root_agent`

Rules:
- Always return a dict
- Always wrap in try/except, return {"success": False, "error": str(e)} on failure
- Docstring is what Gemini reads — make it precise
- Type-annotate every parameter
