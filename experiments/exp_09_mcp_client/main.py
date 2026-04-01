"""
Experiment 09 — MCP Client Integration

Replicates the MCP client pattern from src/services/mcp/client.ts.

Key concepts demonstrated:
  1. MCP server (stdio transport) exposing tools
  2. MCP client connecting via subprocess stdin/stdout
  3. Tool discovery (list_tools) and integration
  4. Tool naming convention: mcp__server__tool
  5. Tool pool merging (built-ins win on collision)

Since the real MCP SDK requires a running server, this experiment simulates
the MCP protocol with a lightweight JSON-RPC implementation over stdio.

Run:
    python -m exp_09_mcp_client.main --mock
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from dataclasses import dataclass, field
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.utils import header, section, step, info, warn, colored, setup_argparser


# ---------------------------------------------------------------------------
# JSON-RPC message types (simplified MCP protocol)
# ---------------------------------------------------------------------------

def make_request(method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4())[:8],
        "method": method,
        "params": params or {},
    }


def make_response(req_id: str, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def make_error(req_id: str, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


# ---------------------------------------------------------------------------
# MCP Server (simulated in-process)
# ---------------------------------------------------------------------------

class MockMCPServer:
    """Simulates an MCP server that exposes tools via JSON-RPC."""

    def __init__(self, name: str, tools: list[dict[str, Any]]):
        self.name = name
        self._tools = {t["name"]: t for t in tools}

    async def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        method = request.get("method", "")
        req_id = request.get("id", "")
        params = request.get("params", {})

        if method == "initialize":
            return make_response(req_id, {
                "protocolVersion": "2025-03-26",
                "serverInfo": {"name": self.name, "version": "1.0.0"},
                "capabilities": {"tools": {}},
            })
        elif method == "tools/list":
            tool_list = [
                {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "inputSchema": t.get("input_schema", {"type": "object", "properties": {}}),
                }
                for t in self._tools.values()
            ]
            return make_response(req_id, {"tools": tool_list})
        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            tool = self._tools.get(tool_name)
            if not tool:
                return make_error(req_id, -32602, f"Unknown tool: {tool_name}")
            handler = tool.get("handler")
            if handler:
                result = await handler(arguments)
            else:
                result = {"mock": True, "tool": tool_name, "args": arguments}
            return make_response(req_id, {
                "content": [{"type": "text", "text": json.dumps(result)}],
                "isError": False,
            })
        else:
            return make_error(req_id, -32601, f"Unknown method: {method}")


# ---------------------------------------------------------------------------
# MCP Client
# ---------------------------------------------------------------------------

@dataclass
class MCPToolDef:
    server_name: str
    name: str
    qualified_name: str
    description: str
    input_schema: dict[str, Any]


class MCPClient:
    """Client that connects to an MCP server and discovers tools."""

    def __init__(self, server_name: str, server: MockMCPServer):
        self.server_name = server_name
        self._server = server
        self._connected = False
        self._tools: list[MCPToolDef] = []

    async def connect(self) -> dict[str, Any]:
        """Initialize connection to the MCP server."""
        request = make_request("initialize", {
            "protocolVersion": "2025-03-26",
            "clientInfo": {"name": "experiment-client", "version": "1.0.0"},
        })
        response = await self._server.handle_request(request)
        self._connected = True
        return response.get("result", {})

    async def list_tools(self) -> list[MCPToolDef]:
        """Discover tools exposed by the server."""
        if not self._connected:
            await self.connect()

        request = make_request("tools/list")
        response = await self._server.handle_request(request)
        result = response.get("result", {})

        self._tools = []
        for tool in result.get("tools", []):
            qualified = f"mcp__{self.server_name}__{tool['name']}"
            self._tools.append(MCPToolDef(
                server_name=self.server_name,
                name=tool["name"],
                qualified_name=qualified,
                description=tool.get("description", ""),
                input_schema=tool.get("inputSchema", {}),
            ))
        return self._tools

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """Call a tool on the server with timeout."""
        if not self._connected:
            await self.connect()

        request = make_request("tools/call", {"name": tool_name, "arguments": arguments})
        try:
            response = await asyncio.wait_for(
                self._server.handle_request(request),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            return {"error": f"Tool call timed out after {timeout}s"}

        if "error" in response:
            return {"error": response["error"]["message"]}

        result = response.get("result", {})
        contents = result.get("content", [])
        text_parts = [c.get("text", "") for c in contents if c.get("type") == "text"]
        return {"result": "\n".join(text_parts), "is_error": result.get("isError", False)}


# ---------------------------------------------------------------------------
# Tool pool merging
# ---------------------------------------------------------------------------

@dataclass
class UnifiedTool:
    name: str
    description: str
    source: str  # "built-in" or "mcp"
    mcp_client: MCPClient | None = None
    mcp_tool_name: str | None = None


def assemble_tool_pool(
    built_ins: list[UnifiedTool],
    mcp_tools: list[UnifiedTool],
) -> list[UnifiedTool]:
    """Merge built-in and MCP tools. Built-ins win on name collision."""
    by_name: dict[str, UnifiedTool] = {}
    for t in sorted(built_ins, key=lambda x: x.name):
        by_name.setdefault(t.name, t)
    for t in sorted(mcp_tools, key=lambda x: x.name):
        by_name.setdefault(t.name, t)
    return list(by_name.values())


# ---------------------------------------------------------------------------
# Sample tool handlers
# ---------------------------------------------------------------------------

async def weather_handler(args: dict[str, Any]) -> dict[str, Any]:
    city = args.get("city", "Unknown")
    forecasts = {
        "tokyo": {"temp": 22, "condition": "Sunny", "humidity": 45},
        "london": {"temp": 15, "condition": "Cloudy", "humidity": 78},
        "new york": {"temp": 28, "condition": "Clear", "humidity": 55},
    }
    return forecasts.get(city.lower(), {"temp": 20, "condition": "Unknown", "humidity": 50})


async def translate_handler(args: dict[str, Any]) -> dict[str, Any]:
    text = args.get("text", "")
    target = args.get("target_language", "en")
    return {"translated": f"[{target}] {text}", "source_language": "auto"}


async def db_query_handler(args: dict[str, Any]) -> dict[str, Any]:
    query = args.get("query", "")
    return {"rows": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}], "query": query}


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

async def main() -> None:
    parser = setup_argparser("Experiment 09: MCP Client Integration")
    parser.parse_args()

    header("Experiment 09: MCP Client Integration")

    # Create mock MCP servers
    weather_server = MockMCPServer("weather", [
        {
            "name": "get_forecast",
            "description": "Get weather forecast for a city",
            "input_schema": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
            "handler": weather_handler,
        },
        {
            "name": "get_alerts",
            "description": "Get weather alerts for a region",
            "input_schema": {
                "type": "object",
                "properties": {"region": {"type": "string"}},
            },
            "handler": None,
        },
    ])

    db_server = MockMCPServer("database", [
        {
            "name": "query",
            "description": "Execute a database query",
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            "handler": db_query_handler,
        },
    ])

    # --- Connect and discover ---
    section("1. Server Connection (Initialize)")
    weather_client = MCPClient("weather", weather_server)
    server_info = await weather_client.connect()
    step(1, f"Connected to: {server_info.get('serverInfo', {}).get('name')}")
    info(f"Protocol: {server_info.get('protocolVersion')}")

    section("2. Tool Discovery (tools/list)")
    weather_tools = await weather_client.list_tools()
    step(2, f"Discovered {len(weather_tools)} tools from 'weather' server:")
    for t in weather_tools:
        print(f"    {colored(t.qualified_name, 'cyan')}: {t.description}")

    db_client = MCPClient("database", db_server)
    db_tools = await db_client.list_tools()
    step(3, f"Discovered {len(db_tools)} tools from 'database' server:")
    for t in db_tools:
        print(f"    {colored(t.qualified_name, 'cyan')}: {t.description}")

    # --- Call tools ---
    section("3. Tool Execution (tools/call)")
    step(4, "Calling weather/get_forecast for Tokyo:")
    result = await weather_client.call_tool("get_forecast", {"city": "Tokyo"})
    print(f"    Result: {colored(result['result'], 'green')}")

    step(5, "Calling database/query:")
    result = await db_client.call_tool("query", {"query": "SELECT * FROM users"})
    print(f"    Result: {colored(result['result'], 'green')}")

    step(6, "Calling unknown tool (error handling):")
    result = await weather_client.call_tool("nonexistent", {})
    print(f"    Error: {colored(str(result.get('error')), 'red')}")

    # --- Pool merging ---
    section("4. Tool Pool Merging (Built-in + MCP)")
    built_ins = [
        UnifiedTool(name="read_file", description="Read a file", source="built-in"),
        UnifiedTool(name="write_file", description="Write a file", source="built-in"),
        UnifiedTool(name="bash", description="Run shell command", source="built-in"),
    ]
    mcp_unified = [
        UnifiedTool(
            name=t.qualified_name,
            description=t.description,
            source="mcp",
            mcp_client=weather_client,
            mcp_tool_name=t.name,
        )
        for t in weather_tools
    ] + [
        UnifiedTool(
            name=t.qualified_name,
            description=t.description,
            source="mcp",
            mcp_client=db_client,
            mcp_tool_name=t.name,
        )
        for t in db_tools
    ]

    collision_tool = UnifiedTool(name="read_file", description="MCP read_file (should lose)", source="mcp")
    mcp_unified.append(collision_tool)

    merged = assemble_tool_pool(built_ins, mcp_unified)
    step(7, f"Merged pool: {len(merged)} tools")
    for t in merged:
        source_color = "green" if t.source == "built-in" else "magenta"
        print(f"    {t.name:40s} [{colored(t.source, source_color)}] {t.description}")

    info("Note: built-in 'read_file' wins over MCP 'read_file' (first-seen wins)")


if __name__ == "__main__":
    asyncio.run(main())
