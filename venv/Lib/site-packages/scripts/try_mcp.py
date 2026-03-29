# server.py
import asyncio

from fastmcp import FastMCP, Client

# Create an MCP server
mcp = FastMCP("Demo")

# Add an addition tool
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    print(f"{a} + {b}")
    return a + b

# Add a dynamic greeting resource
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    return f"Hello, {name}!"


client = Client(mcp)

async def call_tool(name: str):
    async with client:
        result = await client.call_tool("add", {"a": 3, "b": 4})
        print(result)


asyncio.run(call_tool("Ford"))