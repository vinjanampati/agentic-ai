"""
ADK Agent — wraps the Spring Boot REST API as LLM-callable tools.

The agent is defined as `root_agent` which is the conventional name the
ADK CLI (`adk api_server`) looks for when you point it at this module.
"""

import os
import httpx
from google.adk.agents import Agent

# Spring Boot API base URL — override via env var when running in Docker/cloud
SPRING_BOOT_URL = os.getenv("SPRING_BOOT_URL", "http://localhost:8080")


# ---------------------------------------------------------------------------
# Tool functions — each becomes a tool the LLM can call.
# The docstring is sent to the model as the tool description, so keep it
# precise. The type annotations become the JSON schema for the parameters.
# ---------------------------------------------------------------------------

def get_all_products() -> dict:
    """Get the full list of products available in the store catalog."""
    try:
        resp = httpx.get(f"{SPRING_BOOT_URL}/api/products", timeout=10)
        resp.raise_for_status()
        return {"success": True, "products": resp.json()}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_product_by_id(product_id: str) -> dict:
    """Get detailed information about a single product by its ID.

    Args:
        product_id: The numeric ID of the product (e.g. "1", "2").
    """
    try:
        resp = httpx.get(f"{SPRING_BOOT_URL}/api/products/{product_id}", timeout=10)
        if resp.status_code == 404:
            return {"success": False, "error": f"Product '{product_id}' not found"}
        resp.raise_for_status()
        return {"success": True, "product": resp.json()}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_products_by_category(category: str) -> dict:
    """Get all products that belong to a given category.

    Args:
        category: Category name (e.g. "Electronics", "Furniture", "Kitchen").
    """
    try:
        resp = httpx.get(f"{SPRING_BOOT_URL}/api/products/category/{category}", timeout=10)
        resp.raise_for_status()
        return {"success": True, "products": resp.json()}
    except Exception as e:
        return {"success": False, "error": str(e)}


def create_order(product_id: str, quantity: int, customer_name: str) -> dict:
    """Place an order for a product.

    Automatically looks up the product price before submitting the order.

    Args:
        product_id:    ID of the product to order.
        quantity:      Number of units to order (must be >= 1).
        customer_name: Full name of the customer placing the order.
    """
    try:
        # Look up current price so the order total is accurate
        product_resp = httpx.get(f"{SPRING_BOOT_URL}/api/products/{product_id}", timeout=10)
        if product_resp.status_code == 404:
            return {"success": False, "error": f"Product '{product_id}' not found"}
        product = product_resp.json()

        order_resp = httpx.post(
            f"{SPRING_BOOT_URL}/api/orders",
            json={
                "productId": product_id,
                "quantity": quantity,
                "customerName": customer_name,
                "pricePerUnit": product["price"],
            },
            timeout=10,
        )
        order_resp.raise_for_status()
        return {"success": True, "order": order_resp.json()}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_all_orders() -> dict:
    """Get the list of all orders that have been placed."""
    try:
        resp = httpx.get(f"{SPRING_BOOT_URL}/api/orders", timeout=10)
        resp.raise_for_status()
        return {"success": True, "orders": resp.json()}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_weather(city: str) -> dict:
    """Get current weather conditions for a city.

    Args:
        city: City name (e.g. "London", "Tokyo", "New York").
    """
    try:
        resp = httpx.get(f"{SPRING_BOOT_URL}/api/weather/{city}", timeout=10)
        resp.raise_for_status()
        return {"success": True, "weather": resp.json()}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Root agent — the entry-point the ADK runtime discovers
# ---------------------------------------------------------------------------

root_agent = Agent(
    name="store_assistant",
    model="gemini-2.0-flash",
    description=(
        "A store assistant that can browse the product catalog, place orders, "
        "and check weather in cities."
    ),
    instruction="""You are a helpful store assistant.

You have access to a live product catalog and order system backed by a Spring Boot API.
Use the tools available to you to answer questions accurately.

Guidelines:
- When listing products, format them as a readable table or numbered list.
- When placing an order, confirm the details (product name, quantity, total price) before responding.
- For weather, mention temperature, condition, and humidity.
- Be concise but complete in your answers.
""",
    tools=[
        get_all_products,
        get_product_by_id,
        get_products_by_category,
        create_order,
        get_all_orders,
        get_weather,
    ],
)
