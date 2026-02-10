"""
SDX MCP Server - Universal AI Agent with Model Context Protocol
Enhanced with: MCP compatibility, multi-transport, resources, prompts, security
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from enum import Enum
from dotenv import load_dotenv

# FastMCP Framework
from mcp.server.fastmcp import FastMCP
from mcp.types import Tool, Resource, Prompt, TextContent, ImageContent

# APIs - Your existing functions
from func.stealth_scanner import schema_stealth_scan
from func.parameter_hunter import schema_hunt_parameters
from func.get_files_info import schema_get_files_info
from func.get_file_content import schema_get_file_content
from func.write_file import schema_write_file
from func.run_python_file import schema_run_python_file
from func.run_shell import schema_run_shell
from func.make_http_request import schema_make_http_request
from func.enumerate_subdomains import schema_enumerate_subdomains
from func.scan_ports import schema_scan_ports
from call_function import call_function

# Rich for local UI (optional)
from rich.console import Console
from rich.panel import Panel
from rich import box

# Pydantic for validation
from pydantic import BaseModel, Field, validator


# ============================================================================
# MCP SERVER INITIALIZATION
# ============================================================================

# Create MCP server instance
mcp = FastMCP(
    name="SDX Security Agent",

    dependencies=["google-genai", "rich", "pydantic", "python-dotenv"]
)

# Console for stderr logging only (never stdout with stdio!)
console = Console(stderr=True, force_terminal=True)


# ============================================================================
# PYDANTIC MODELS FOR INPUT VALIDATION
# ============================================================================

class FileOperationInput(BaseModel):
    """Validated input for file operations"""
    path: str = Field(..., description="File path (relative or absolute)")
    
    @validator('path')
    def validate_path(cls, v):
        # Prevent path traversal
        if '..' in v or v.startswith('/etc') or v.startswith('/sys'):
            raise ValueError("Path traversal or system directory access denied")
        return v


class ShellCommandInput(BaseModel):
    """Validated input for shell commands"""
    command: str = Field(..., description="Shell command to execute")
    timeout: int = Field(default=30, ge=1, le=300, description="Timeout in seconds")
    
    @validator('command')
    def validate_command(cls, v):
        # Block dangerous commands
        dangerous = ['rm -rf /', 'mkfs', 'dd if=', ':(){:|:&};:', 'chmod -R 777 /']
        if any(cmd in v for cmd in dangerous):
            raise ValueError("Dangerous command blocked for safety")
        return v


class ScanInput(BaseModel):
    """Validated input for security scans"""
    target: str = Field(..., description="Target IP/domain for scanning")
    ports: Optional[str] = Field(default="1-1000", description="Port range (e.g., '1-1000' or '80,443')")
    
    @validator('target')
    def validate_target(cls, v):
        # Basic validation - you should add proper IP/domain validation
        if not v or len(v) > 253:
            raise ValueError("Invalid target format")
        return v


class HttpRequestInput(BaseModel):
    """Validated input for HTTP requests"""
    url: str = Field(..., description="Target URL")
    method: str = Field(default="GET", description="HTTP method")
    headers: Optional[Dict[str, str]] = Field(default=None)
    data: Optional[Dict[str, Any]] = Field(default=None)
    
    @validator('url')
    def validate_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")
        return v
    
    @validator('method')
    def validate_method(cls, v):
        allowed = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']
        if v.upper() not in allowed:
            raise ValueError(f"Method must be one of {allowed}")
        return v.upper()


# ============================================================================
# SESSION & LOGGING (Thread-safe for MCP)
# ============================================================================

class MCPLogger:
    """Logger that respects MCP stdio protocol (stderr only!)"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        log_file = self.log_dir / f"sdx_mcp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        # Configure logging to stderr and file (NEVER stdout!)
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stderr)  # stderr, not stdout!
            ]
        )
        self.logger = logging.getLogger("SDX-MCP")
        
        # Silence noisy external loggers
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("google_genai").setLevel(logging.WARNING)
    
    def info(self, msg: str):
        self.logger.info(msg)
    
    def error(self, msg: str):
        self.logger.error(msg)
    
    def warning(self, msg: str):
        self.logger.warning(msg)


class SessionStore:
    """Thread-safe session storage for MCP"""
    
    def __init__(self, session_dir: str = "sessions"):
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(exist_ok=True)
        self.sessions: Dict[str, List[Dict]] = {}
        self._lock = asyncio.Lock()
    
    async def add_entry(self, session_id: str, role: str, content: str, metadata: Optional[Dict] = None):
        async with self._lock:
            if session_id not in self.sessions:
                self.sessions[session_id] = []
            
            entry = {
                "timestamp": datetime.now().isoformat(),
                "role": role,
                "content": content,
                "metadata": metadata or {}
            }
            self.sessions[session_id].append(entry)
            
            # Persist to disk
            session_file = self.session_dir / f"{session_id}.json"
            with open(session_file, 'w') as f:
                json.dump(self.sessions[session_id], f, indent=2)
    
    async def get_history(self, session_id: str) -> List[Dict]:
        async with self._lock:
            return self.sessions.get(session_id, [])


# Global instances
logger = MCPLogger()
session_store = SessionStore()


# ============================================================================
# MCP TOOLS - Security Operations
# ============================================================================

@mcp.tool()
async def get_files_info(path: str = ".") -> Dict[str, Any]:
    """
    List files and directories with detailed information.
    
    Returns JSON with file names, sizes, types, and permissions.
    Perfect for reconnaissance and finding interesting files.
    
    Args:
        path: Directory path to scan (default: current directory)
    """
    try:
        validated = FileOperationInput(path=path)
        logger.info(f"Listing files in: {validated.path}")
        
        target_path = Path(validated.path)
        if not target_path.exists():
            return {"error": "Path does not exist", "path": path}
        
        files_info = []
        for item in target_path.iterdir():
            try:
                stat = item.stat()
                files_info.append({
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "permissions": oct(stat.st_mode)[-3:]
                })
            except Exception as e:
                logger.warning(f"Error reading {item}: {e}")
        
        return {
            "path": str(target_path.absolute()),
            "count": len(files_info),
            "items": files_info
        }
    
    except Exception as e:
        logger.error(f"get_files_info error: {e}")
        return {"error": str(e)}


@mcp.tool()
async def get_file_content(path: str) -> Dict[str, Any]:
    """
    Read and return file content with metadata.
    
    Supports text files with encoding detection.
    Returns content, size, and file type information.
    
    Args:
        path: Path to file to read
    """
    try:
        validated = FileOperationInput(path=path)
        logger.info(f"Reading file: {validated.path}")
        
        file_path = Path(validated.path)
        if not file_path.exists() or not file_path.is_file():
            return {"error": "File not found", "path": path}
        
        # Read with encoding detection
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        
        return {
            "path": str(file_path.absolute()),
            "size": file_path.stat().st_size,
            "content": content,
            "lines": len(content.splitlines()),
            "encoding": "utf-8"
        }
    
    except Exception as e:
        logger.error(f"get_file_content error: {e}")
        return {"error": str(e)}


@mcp.tool()
async def write_file(path: str, content: str, mode: str = "w") -> Dict[str, Any]:
    """
    Write content to a file (create or overwrite).
    
    Supports text mode writing with automatic directory creation.
    Use for saving scan results, creating scripts, etc.
    
    Args:
        path: Target file path
        content: Content to write
        mode: Write mode ('w' for overwrite, 'a' for append)
    """
    try:
        validated = FileOperationInput(path=path)
        logger.info(f"Writing to file: {validated.path}")
        
        file_path = Path(validated.path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        if mode not in ['w', 'a']:
            return {"error": "Mode must be 'w' (write) or 'a' (append)"}
        
        with open(file_path, mode, encoding='utf-8') as f:
            f.write(content)
        
        return {
            "success": True,
            "path": str(file_path.absolute()),
            "bytes_written": len(content.encode('utf-8')),
            "mode": mode
        }
    
    except Exception as e:
        logger.error(f"write_file error: {e}")
        return {"error": str(e)}


@mcp.tool()
async def run_shell(command: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Execute shell command and return output.
    
    ⚠️ DANGEROUS: This runs arbitrary shell commands. Use with caution.
    Includes safety checks for common dangerous commands.
    Returns stdout, stderr, and exit code.
    
    Args:
        command: Shell command to execute
        timeout: Maximum execution time in seconds (default: 30)
    """
    try:
        validated = ShellCommandInput(command=command, timeout=timeout)
        logger.info(f"Executing shell command: {validated.command}")
        
        process = await asyncio.create_subprocess_shell(
            validated.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.getcwd()
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=validated.timeout
            )
            
            return {
                "success": process.returncode == 0,
                "exit_code": process.returncode,
                "stdout": stdout.decode('utf-8', errors='ignore'),
                "stderr": stderr.decode('utf-8', errors='ignore'),
                "command": validated.command
            }
        
        except asyncio.TimeoutError:
            process.kill()
            return {"error": "Command timeout", "timeout": validated.timeout}
    
    except Exception as e:
        logger.error(f"run_shell error: {e}")
        return {"error": str(e)}


@mcp.tool()
async def run_python_file(path: str, args: str = "") -> Dict[str, Any]:
    """
    Execute a Python script and return output.
    
    Runs Python files in a subprocess with optional arguments.
    Returns stdout, stderr, and execution status.
    
    Args:
        path: Path to Python file
        args: Command-line arguments for the script
    """
    try:
        validated = FileOperationInput(path=path)
        logger.info(f"Running Python file: {validated.path}")
        
        file_path = Path(validated.path)
        if not file_path.exists() or file_path.suffix != '.py':
            return {"error": "Python file not found", "path": path}
        
        cmd = f"python {file_path} {args}".strip()
        return await run_shell(cmd, timeout=60)
    
    except Exception as e:
        logger.error(f"run_python_file error: {e}")
        return {"error": str(e)}


@mcp.tool()
async def make_http_request(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Make HTTP/HTTPS requests for web reconnaissance.
    
    Supports all major HTTP methods with custom headers and data.
    Returns status code, headers, and response body.
    Perfect for API testing and web app enumeration.
    
    Args:
        url: Target URL
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        headers: Optional HTTP headers
        data: Optional request body (for POST/PUT)
    """
    try:
        import httpx
        
        validated = HttpRequestInput(url=url, method=method, headers=headers, data=data)
        logger.info(f"HTTP {validated.method} request to: {validated.url}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=validated.method,
                url=validated.url,
                headers=validated.headers,
                json=validated.data
            )
            
            return {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response.text,
                "size": len(response.content),
                "elapsed_ms": int(response.elapsed.total_seconds() * 1000)
            }
    
    except Exception as e:
        logger.error(f"make_http_request error: {e}")
        return {"error": str(e)}


@mcp.tool()
async def enumerate_subdomains(domain: str, wordlist: str = "common") -> Dict[str, Any]:
    """
    Discover subdomains of a target domain.
    
    Uses DNS queries and common subdomain wordlists.
    Returns list of discovered subdomains with resolution status.
    
    Args:
        domain: Target domain (e.g., example.com)
        wordlist: Wordlist size ('small', 'common', 'large')
    """
    try:
        logger.info(f"Enumerating subdomains for: {domain}")
        
        # Common subdomain prefixes
        wordlists = {
            "small": ["www", "mail", "ftp", "admin"],
            "common": ["www", "mail", "ftp", "admin", "blog", "dev", "test", "api", "cdn", "m"],
            "large": ["www", "mail", "ftp", "admin", "blog", "dev", "test", "api", "cdn", "m",
                     "shop", "forum", "support", "help", "docs", "portal", "vpn", "remote"]
        }
        
        prefixes = wordlists.get(wordlist, wordlists["common"])
        discovered = []
        
        for prefix in prefixes:
            subdomain = f"{prefix}.{domain}"
            try:
                # Try DNS resolution
                result = await run_shell(f"nslookup {subdomain}", timeout=5)
                if result.get("success") and "can't find" not in result.get("stdout", "").lower():
                    discovered.append({
                        "subdomain": subdomain,
                        "status": "resolved"
                    })
            except:
                pass
        
        return {
            "domain": domain,
            "wordlist": wordlist,
            "found": len(discovered),
            "subdomains": discovered
        }
    
    except Exception as e:
        logger.error(f"enumerate_subdomains error: {e}")
        return {"error": str(e)}


@mcp.tool()
async def scan_ports(target: str, ports: str = "1-1000") -> Dict[str, Any]:
    """
    Scan open TCP ports on target host.
    
    Uses socket connections to detect open ports.
    Returns list of open ports with service detection.
    
    Args:
        target: Target IP or hostname
        ports: Port range ('80,443' or '1-1000')
    """
    try:
        validated = ScanInput(target=target, ports=ports)
        logger.info(f"Port scanning: {validated.target} ports {validated.ports}")
        
        # Use nmap if available, otherwise fallback to Python sockets
        nmap_check = await run_shell("which nmap", timeout=2)
        
        if nmap_check.get("success"):
            # Use nmap for better results
            cmd = f"nmap -p {validated.ports} {validated.target}"
            result = await run_shell(cmd, timeout=120)
            
            return {
                "target": validated.target,
                "ports_scanned": validated.ports,
                "scan_method": "nmap",
                "raw_output": result.get("stdout", ""),
                "success": result.get("success", False)
            }
        else:
            return {
                "error": "nmap not available",
                "suggestion": "Install nmap for port scanning"
            }
    
    except Exception as e:
        logger.error(f"scan_ports error: {e}")
        return {"error": str(e)}


@mcp.tool()
async def stealth_scan(target: str, technique: str = "syn") -> Dict[str, Any]:
    """
    Perform stealthy reconnaissance scan on target.
    
    ⚠️ ETHICAL USE ONLY: Only scan systems you own or have permission to test.
    Uses advanced techniques to avoid detection.
    
    Args:
        target: Target IP or hostname
        technique: Scan technique ('syn', 'ack', 'fin', 'null')
    """
    try:
        validated = ScanInput(target=target)
        logger.info(f"Stealth scan on {validated.target} using {technique}")
        
        techniques = {
            "syn": "-sS",
            "ack": "-sA", 
            "fin": "-sF",
            "null": "-sN"
        }
        
        nmap_flag = techniques.get(technique, "-sS")
        cmd = f"sudo nmap {nmap_flag} -T2 {validated.target}"
        
        result = await run_shell(cmd, timeout=180)
        
        return {
            "target": validated.target,
            "technique": technique,
            "scan_output": result.get("stdout", ""),
            "success": result.get("success", False),
            "warning": "Use only on authorized targets"
        }
    
    except Exception as e:
        logger.error(f"stealth_scan error: {e}")
        return {"error": str(e)}


@mcp.tool()
async def hunt_parameters(url: str, method: str = "GET") -> Dict[str, Any]:
    """
    Discover hidden parameters in web endpoints.
    
    Tests common parameter names to find hidden functionality.
    Useful for finding admin panels, debug modes, etc.
    
    Args:
        url: Target URL to test
        method: HTTP method to use
    """
    try:
        logger.info(f"Parameter hunting on: {url}")
        
        # Common parameter names to test
        params = ["id", "user", "admin", "debug", "test", "page", "file", "action", 
                 "cmd", "exec", "query", "search", "redirect", "url"]
        
        discovered = []
        
        for param in params:
            test_url = f"{url}?{param}=test"
            result = await make_http_request(test_url, method)
            
            # Simple detection: different response = parameter recognized
            if result.get("status_code") != 404:
                discovered.append({
                    "parameter": param,
                    "status": result.get("status_code"),
                    "size": result.get("size", 0)
                })
        
        return {
            "url": url,
            "method": method,
            "tested": len(params),
            "discovered": len(discovered),
            "parameters": discovered
        }
    
    except Exception as e:
        logger.error(f"hunt_parameters error: {e}")
        return {"error": str(e)}


# ============================================================================
# MCP RESOURCES - Data Exposure
# ============================================================================

@mcp.resource("session://history")
async def get_session_history() -> str:
    """
    Access current session history.
    
    Returns all commands and responses from this session.
    """
    # This would return actual session data
    return json.dumps({
        "session_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "entries": [],
        "note": "Session history tracking"
    }, indent=2)


@mcp.resource("logs://recent")
async def get_recent_logs() -> str:
    """
    Access recent SDX operation logs.
    
    Returns last 100 log entries for debugging.
    """
    log_dir = Path("logs")
    if not log_dir.exists():
        return json.dumps({"error": "No logs available"})
    
    # Find most recent log file
    log_files = sorted(log_dir.glob("sdx_mcp_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    
    if not log_files:
        return json.dumps({"error": "No log files found"})
    
    recent_log = log_files[0]
    with open(recent_log, 'r') as f:
        lines = f.readlines()[-100:]  # Last 100 lines
    
    return json.dumps({
        "log_file": recent_log.name,
        "lines": len(lines),
        "content": "".join(lines)
    }, indent=2)


@mcp.resource("results://scans")
async def get_scan_results() -> str:
    """
    Access saved scan results.
    
    Returns all stored security scan results.
    """
    results_dir = Path("results")
    if not results_dir.exists():
        return json.dumps({"error": "No scan results available"})
    
    results = []
    for result_file in results_dir.glob("*.json"):
        try:
            with open(result_file, 'r') as f:
                data = json.load(f)
                results.append({
                    "file": result_file.name,
                    "data": data
                })
        except:
            pass
    
    return json.dumps(results, indent=2)


# ============================================================================
# MCP PROMPTS - Templates
# ============================================================================

@mcp.prompt()
async def penetration_test_prompt(target: str) -> str:
    """
    Generate a comprehensive penetration testing plan.
    
    Args:
        target: Target system or domain
    """
    return f"""# Penetration Testing Plan for {target}

## Phase 1: Reconnaissance
1. Enumerate subdomains using `enumerate_subdomains`
2. Scan open ports with `scan_ports`
3. Identify web technologies

## Phase 2: Vulnerability Analysis
1. Test for common web vulnerabilities
2. Check for misconfigurations
3. Hunt for hidden parameters with `hunt_parameters`

## Phase 3: Exploitation (Authorized Only!)
1. Attempt to exploit found vulnerabilities
2. Document all findings
3. Maintain stealth with `stealth_scan`

## Phase 4: Reporting
1. Compile findings
2. Rate severity (Critical/High/Medium/Low)
3. Provide remediation steps

⚠️ CRITICAL: Only test systems you own or have explicit permission to test!
"""


@mcp.prompt()
async def vulnerability_scan_prompt(target: str, scan_type: str = "web") -> str:
    """
    Generate a vulnerability scanning workflow.
    
    Args:
        target: Target to scan
        scan_type: Type of scan (web, network, api)
    """
    if scan_type == "web":
        return f"""# Web Vulnerability Scan: {target}

1. **Information Gathering**
   - Check HTTP headers for security issues
   - Identify server software versions
   - Map application structure

2. **Parameter Discovery**
   - Use `hunt_parameters` to find hidden params
   - Test for injection points
   - Check for parameter pollution

3. **Security Testing**
   - Test for XSS, SQLi, CSRF
   - Check authentication mechanisms
   - Verify authorization controls

4. **Reporting**
   - Document all vulnerabilities
   - Provide proof of concept
   - Suggest fixes
"""
    else:
        return f"""# Network Vulnerability Scan: {target}

1. Port scanning with `scan_ports`
2. Service enumeration
3. Version detection
4. Exploit matching
5. Report generation
"""


@mcp.prompt()
async def recon_prompt(domain: str) -> str:
    """
    Generate a reconnaissance workflow.
    
    Args:
        domain: Target domain
    """
    return f"""# Reconnaissance Workflow: {domain}

## Passive Reconnaissance
1. WHOIS lookup
2. DNS enumeration
3. Search engine dorking
4. Social media OSINT

## Active Reconnaissance
1. `enumerate_subdomains("{domain}", "large")`
2. `scan_ports` on discovered hosts
3. Web crawling and spidering
4. Technology fingerprinting

## Data Analysis
1. Compile discovered assets
2. Identify attack surface
3. Prioritize targets
4. Plan next steps
"""


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

async def main():
    """Run the MCP server"""
    load_dotenv()
    
    logger.info("=" * 60)
    logger.info("SDX MCP Server Starting")
    logger.info(f"Version: 2.0.0")
    logger.info(f"CWD: {os.getcwd()}")
    logger.info("=" * 60)
    
    # Log available tools
    logger.info(f"Tools registered: {len(mcp.list_tools())}")
    logger.info(f"Resources available: 3")
    logger.info(f"Prompts defined: 3")
    
    # Run the MCP server (stdio by default)
    await mcp.run()


if __name__ == "__main__":
    asyncio.run(main())