import os
import json
import asyncio
import subprocess
from typing import Optional, Dict, List, Any
from pathlib import Path
from google.genai import types
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

class MCPServer:
    """Represents a single MCP server connection"""
    
    def __init__(self, name: str, command: str, args: List[str], env: Optional[Dict[str, str]] = None):
        self.name = name
        self.command = command
        self.args = args
        self.env = env or {}
        self.process = None
        self.available_tools = []
    
    async def start(self):
        """Start the MCP server process"""
        try:
            env = os.environ.copy()
            env.update(self.env)
            
            self.process = await asyncio.create_subprocess_exec(
                self.command,
                *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            # Initialize connection
            await self._send_initialize()
            return True
        except Exception as e:
            console.print(f"[red]Failed to start MCP server '{self.name}': {e}[/red]")
            return False
    
    async def stop(self):
        """Stop the MCP server process"""
        if self.process:
            self.process.terminate()
            await self.process.wait()
    
    async def _send_initialize(self):
        """Send initialization request to MCP server"""
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "sdx-agent",
                    "version": "3.0.0"
                }
            }
        }
        
        await self._send_request(init_request)
        
        # Request tools list
        await self._list_tools()
    
    async def _list_tools(self):
        """List available tools from the MCP server"""
        list_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        response = await self._send_request(list_request)
        if response and "result" in response:
            self.available_tools = response["result"].get("tools", [])
    
    async def _send_request(self, request: Dict) -> Optional[Dict]:
        """Send JSON-RPC request to MCP server"""
        if not self.process or not self.process.stdin:
            return None
        
        try:
            request_str = json.dumps(request) + "\n"
            self.process.stdin.write(request_str.encode())
            await self.process.stdin.drain()
            
            # Read response
            response_line = await self.process.stdout.readline()
            if response_line:
                return json.loads(response_line.decode())
        except Exception as e:
            console.print(f"[yellow]MCP request error: {e}[/yellow]")
        
        return None
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict]:
        """Call a tool on the MCP server"""
        tool_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        return await self._send_request(tool_request)


class MCPManager:
    """Manages multiple MCP server connections"""
    
    def __init__(self, config_file: str = "config/mcp_config.json"):
        # Ensure config directory exists
        config_dir = os.path.dirname(config_file)
        if config_dir and not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
            console.print(f"[green]Created config directory: {config_dir}[/green]")
        
        self.config_file = config_file
        self.servers: Dict[str, MCPServer] = {}
        self.loop = None
    
    def load_config(self) -> Dict[str, Any]:
        """Load MCP server configuration"""
        if not os.path.exists(self.config_file):
            return self._create_default_config()
        
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            console.print(f"[yellow]Failed to load MCP config: {e}[/yellow]")
            return {"mcpServers": {}}
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create default MCP configuration file"""
        default_config = {
        }
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
            console.print(f"[green]Created default MCP config: {self.config_file}[/green]")
        except Exception as e:
            console.print(f"[yellow]Failed to create default config: {e}[/yellow]")
        
        return default_config
    
    async def start_server(self, server_name: str) -> bool:
        """Start a specific MCP server"""
        config = self.load_config()
        server_config = config.get("mcpServers", {}).get(server_name)
        
        if not server_config:
            console.print(f"[red]MCP server '{server_name}' not found in config[/red]")
            return False
        
        server = MCPServer(
            name=server_name,
            command=server_config["command"],
            args=server_config["args"],
            env=server_config.get("env", {})
        )
        
        if await server.start():
            self.servers[server_name] = server
            console.print(f"[green]✓ MCP server '{server_name}' started[/green]")
            return True
        
        return False
    
    async def stop_server(self, server_name: str):
        """Stop a specific MCP server"""
        if server_name in self.servers:
            await self.servers[server_name].stop()
            del self.servers[server_name]
            console.print(f"[yellow]MCP server '{server_name}' stopped[/yellow]")
    
    async def stop_all_servers(self):
        """Stop all running MCP servers"""
        for server_name in list(self.servers.keys()):
            await self.stop_server(server_name)
    
    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get all available tools from all servers"""
        all_tools = []
        for server_name, server in self.servers.items():
            for tool in server.available_tools:
                tool_copy = tool.copy()
                tool_copy["_server"] = server_name
                all_tools.append(tool_copy)
        return all_tools
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict]:
        """Call a tool on the appropriate MCP server"""
        # Find which server has this tool
        for server_name, server in self.servers.items():
            tool_names = [t["name"] for t in server.available_tools]
            if tool_name in tool_names:
                return await server.call_tool(tool_name, arguments)
        
        console.print(f"[red]Tool '{tool_name}' not found on any MCP server[/red]")
        return None
    
    def display_status(self):
        """Display status of all MCP servers and their tools"""
        console.print()
        console.print(Panel(
            "[cyan]MCP Server Status[/cyan]",
            title="[bold blue]🔌 Model Context Protocol[/bold blue]",
            border_style="blue"
        ))
        
        if not self.servers:
            console.print("[yellow]No MCP servers running[/yellow]\n")
            return
        
        for server_name, server in self.servers.items():
            table = Table(title=f"Server: {server_name}", show_header=True)
            table.add_column("Tool Name", style="cyan")
            table.add_column("Description", style="white")
            
            for tool in server.available_tools:
                table.add_row(
                    tool.get("name", "Unknown"),
                    tool.get("description", "No description")[:60]
                )
            
            console.print(table)
            console.print()


# Global MCP manager instance
_mcp_manager = None

def get_mcp_manager() -> MCPManager:
    """Get or create the global MCP manager instance"""
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPManager()
    return _mcp_manager


# ============================================================================
# SYNCHRONOUS WRAPPER FUNCTIONS FOR MAIN AGENT
# ============================================================================

def mcp_start_server(working_directory: str, server_name: str) -> str:
    """Start an MCP server (synchronous wrapper)"""
    os.chdir(working_directory)
    
    manager = get_mcp_manager()
    
    # Create event loop if needed
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    success = loop.run_until_complete(manager.start_server(server_name))
    
    if success:
        tools = manager.servers[server_name].available_tools
        tool_list = "\n".join([f"  - {t['name']}: {t.get('description', 'No description')}" for t in tools])
        return f"MCP server '{server_name}' started successfully.\n\nAvailable tools:\n{tool_list}"
    else:
        return f"Failed to start MCP server '{server_name}'"


def mcp_stop_server(working_directory: str, server_name: str) -> str:
    """Stop an MCP server (synchronous wrapper)"""
    manager = get_mcp_manager()
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    loop.run_until_complete(manager.stop_server(server_name))
    return f"MCP server '{server_name}' stopped"


def mcp_list_tools(working_directory: str) -> str:
    """List all available MCP tools (synchronous wrapper)"""
    manager = get_mcp_manager()
    tools = manager.get_all_tools()
    
    if not tools:
        return "No MCP servers running or no tools available"
    
    result = "Available MCP Tools:\n\n"
    for tool in tools:
        server = tool.get("_server", "unknown")
        name = tool.get("name", "unknown")
        desc = tool.get("description", "No description")
        result += f"[{server}] {name}\n  {desc}\n\n"
    
    return result


def mcp_call_tool(working_directory: str, tool_name: str, arguments: Dict[str, Any]) -> str:
    """Call an MCP tool (synchronous wrapper)"""
    manager = get_mcp_manager()
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    result = loop.run_until_complete(manager.call_tool(tool_name, arguments))
    
    if result:
        return json.dumps(result, indent=2)
    else:
        return f"Failed to call tool '{tool_name}'"


def mcp_status(working_directory: str) -> str:
    """Get MCP status (synchronous wrapper)"""
    manager = get_mcp_manager()
    manager.display_status()
    return "MCP status displayed above"


# ============================================================================
# FUNCTION SCHEMAS FOR AI AGENT
# ============================================================================

schema_mcp_start_server = types.FunctionDeclaration(
    name="mcp_start_server",
    description="""Start an MCP (Model Context Protocol) server to access additional tools.
    
    Available servers:
    - 'chrome-devtools': Chrome browser automation and DevTools access
    - 'vercel-skills': Vercel deployment and project management tools
    
    Once started, the server's tools become available for use.""",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "working_directory": types.Schema(
                type=types.Type.STRING,
                description="Current working directory",
            ),
            "server_name": types.Schema(
                type=types.Type.STRING,
                description="Name of the MCP server to start (e.g., 'chrome-devtools', 'vercel-skills')",
            ),
        },
        required=["working_directory", "server_name"],
    ),
)

schema_mcp_stop_server = types.FunctionDeclaration(
    name="mcp_stop_server",
    description="Stop a running MCP server and clean up its resources.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "working_directory": types.Schema(
                type=types.Type.STRING,
                description="Current working directory",
            ),
            "server_name": types.Schema(
                type=types.Type.STRING,
                description="Name of the MCP server to stop",
            ),
        },
        required=["working_directory", "server_name"],
    ),
)

schema_mcp_list_tools = types.FunctionDeclaration(
    name="mcp_list_tools",
    description="List all available tools from all running MCP servers.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "working_directory": types.Schema(
                type=types.Type.STRING,
                description="Current working directory",
            ),
        },
        required=["working_directory"],
    ),
)

schema_mcp_call_tool = types.FunctionDeclaration(
    name="mcp_call_tool",
    description="""Call a tool from a running MCP server.
    
    First use mcp_list_tools to see available tools and their parameters.
    Then call the specific tool with the required arguments.""",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "working_directory": types.Schema(
                type=types.Type.STRING,
                description="Current working directory",
            ),
            "tool_name": types.Schema(
                type=types.Type.STRING,
                description="Name of the MCP tool to call",
            ),
            "arguments": types.Schema(
                type=types.Type.OBJECT,
                description="Arguments to pass to the tool (as a dictionary)",
            ),
        },
        required=["working_directory", "tool_name", "arguments"],
    ),
)

schema_mcp_status = types.FunctionDeclaration(
    name="mcp_status",
    description="Display status of all MCP servers and their available tools.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "working_directory": types.Schema(
                type=types.Type.STRING,
                description="Current working directory",
            ),
        },
        required=["working_directory"],
    ),
)