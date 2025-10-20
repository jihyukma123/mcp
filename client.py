"""
Run from the repository root:
    uv run examples/snippets/clients/streamable_basic.py
"""

import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def main():
    # Connect to a streamable HTTP server
    async with streamablehttp_client("https://f1b4166ba41569.lhr.life/mcp") as (
        read_stream,
        write_stream,
        _,
    ):
        # Create a session using the client streams
        async with ClientSession(read_stream, write_stream) as session:
            # Initialize the connection
            await session.initialize()
            # List available tools
            tools = await session.list_tools()
            resources = await session.list_resources()
            resource_templates = await session.list_resource_templates()
            prompts = await session.list_prompts()
            print(f"Available tools: {[tool.name for tool in tools.tools]}")
            print(f"Available resources: {[resource.name for resource in resources.resources]}")
            print(f"Available resource templates: {[resource_template.name for resource_template in resource_templates.resourceTemplates]}")
            print(f"Available prompts: {[prompt.name for prompt in prompts.prompts]}")


if __name__ == "__main__":
    asyncio.run(main())