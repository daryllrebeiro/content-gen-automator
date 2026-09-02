import json
from contextlib import asynccontextmanager

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
import mcp.types as types

from app.database import get_db
from app.domain.project import Project
from sqlalchemy.orm import Session

mcp_app = Server("content-gen-mcp")

@mcp_app.list_resources()
async def list_resources() -> list[types.Resource]:
    # In a real setup, we would dynamically list active projects
    return [
        types.Resource(
            uri="project://active",
            name="Active Projects",
            mimeType="application/json",
            description="List of currently active project states and continuity locks",
        )
    ]

@mcp_app.read_resource()
async def read_resource(uri: str) -> str:
    if uri == "project://active":
        # Simplified example: fetch active projects
        # In a real implementation this would query the DB
        return json.dumps([{"id": "mock_id", "state": "AWAITING_NEXT", "topic": "Example topic"}])
    raise ValueError(f"Unknown resource URI: {uri}")

@mcp_app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_project_state",
            description="Get the full state of a project including continuity locks and approved facts.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "description": "The UUID of the project"}
                },
                "required": ["project_id"]
            }
        ),
        types.Tool(
            name="update_fact_status",
            description="Update the status of a specific factual claim.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "fact_id": {"type": "string"},
                    "status": {"type": "string", "enum": ["verified", "partially_verified", "uncertain", "contradicted"]}
                },
                "required": ["project_id", "fact_id", "status"]
            }
        )
    ]

@mcp_app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "get_project_state":
        project_id = arguments.get("project_id")
        return [types.TextContent(type="text", text=f"State for {project_id}: (Mocked DB response)")]
    elif name == "update_fact_status":
        project_id = arguments.get("project_id")
        fact_id = arguments.get("fact_id")
        status = arguments.get("status")
        return [types.TextContent(type="text", text=f"Updated fact {fact_id} to {status}")]
    raise ValueError(f"Unknown tool: {name}")

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await mcp_app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="content-gen-mcp",
                server_version="0.1.0",
                capabilities=mcp_app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            )
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
