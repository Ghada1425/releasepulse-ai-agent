import asyncio
import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def retrieve_mcp(query: str, limit: int = 3) -> list[dict]:
    async with asyncio.timeout(90):
        params = StdioServerParameters(
            command=sys.executable, args=["-m", "releasepulse.mcp_server"]
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "retrieve_qa_guidelines", {"query": query, "limit": limit}
                )
                if result.isError:
                    raise RuntimeError("MCP retrieval failed")
                # SDK v1 returns one JSON text block per list item.
                values = [json.loads(c.text) for c in result.content if c.type == "text"]
                return values[0] if len(values) == 1 and isinstance(values[0], list) else values
