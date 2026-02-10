import requests
import json
from typing import Optional, Dict, Any
from google.genai import types
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

console = Console()

def make_http_request(
    working_directory: str,
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    data: Optional[str] = None,
    params: Optional[Dict[str, str]] = None,
    cookies: Optional[Dict[str, str]] = None,
    timeout: int = 10,
    verify_ssl: bool = True,
    follow_redirects: bool = True,
    proxy: Optional[str] = None
) -> str:
    """
    Make advanced HTTP requests for bug hunting and security testing.
    
    Args:
        working_directory: Base working directory
        url: Target URL
        method: HTTP method (GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD)
        headers: Custom headers dict
        data: Request body (string or JSON)
        params: URL parameters
        cookies: Cookies dict
        timeout: Request timeout in seconds
        verify_ssl: Verify SSL certificates
        follow_redirects: Follow HTTP redirects
        proxy: Proxy URL (e.g., 'http://127.0.0.1:8080' for Burp)
    
    Returns:
        Detailed response information
    """
    
    # Display request info
    console.print()
    console.print(Panel(
        f"[cyan]{method} {url}[/cyan]",
        title="[yellow]🌐 HTTP Request[/yellow]",
        border_style="yellow",
        padding=(0, 2)
    ))
    
    try:
        # Prepare request arguments
        req_args = {
            'method': method.upper(),
            'url': url,
            'timeout': timeout,
            'verify': verify_ssl,
            'allow_redirects': follow_redirects
        }
        
        if headers:
            req_args['headers'] = headers
        
        if params:
            req_args['params'] = params
        
        if cookies:
            req_args['cookies'] = cookies
        
        if data:
            # Try to parse as JSON first
            try:
                req_args['json'] = json.loads(data)
            except:
                req_args['data'] = data
        
        if proxy:
            req_args['proxies'] = {
                'http': proxy,
                'https': proxy
            }
        
        # Make request
        console.print("[dim]─" * 88 + "[/dim]")
        console.print("[cyan]→ Sending request...[/cyan]")
        
        response = requests.request(**req_args)
        
        # Display response
        console.print(f"[green]← Status: {response.status_code} {response.reason}[/green]")
        console.print(f"[dim]Response Time: {response.elapsed.total_seconds():.3f}s[/dim]")
        console.print("[dim]─" * 88 + "[/dim]")
        
        # Show response headers
        if response.headers:
            console.print("\n[bold cyan]Response Headers:[/bold cyan]")
            headers_table = Table(show_header=False, box=None, padding=(0, 2))
            headers_table.add_column(style="yellow")
            headers_table.add_column(style="dim")
            
            for key, value in list(response.headers.items())[:10]:
                headers_table.add_row(key, value[:80] if len(value) > 80 else value)
            
            console.print(headers_table)
        
        # Show response body preview
        if response.text:
            console.print("\n[bold cyan]Response Body:[/bold cyan]")
            body_preview = response.text[:500]
            if len(response.text) > 500:
                body_preview += "\n... (truncated)"
            
            try:
                # Try to format as JSON
                json_data = response.json()
                syntax = Syntax(json.dumps(json_data, indent=2)[:500], "json", theme="monokai")
                console.print(syntax)
            except:
                console.print(f"[dim]{body_preview}[/dim]")
        
        console.print()
        
        # Build detailed result
        result = f"""HTTP Request Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Request:
  Method: {method.upper()}
  URL: {url}
  Status: {response.status_code} {response.reason}
  Time: {response.elapsed.total_seconds():.3f}s

Response Headers:
{json.dumps(dict(response.headers), indent=2)}

Response Body Length: {len(response.text)} bytes

Response Body:
{response.text[:1000]}{"... (truncated)" if len(response.text) > 1000 else ""}

Security Headers Check:
  - X-Frame-Options: {"✓" if "X-Frame-Options" in response.headers else "✗ Missing"}
  - X-Content-Type-Options: {"✓" if "X-Content-Type-Options" in response.headers else "✗ Missing"}
  - Strict-Transport-Security: {"✓" if "Strict-Transport-Security" in response.headers else "✗ Missing"}
  - Content-Security-Policy: {"✓" if "Content-Security-Policy" in response.headers else "✗ Missing"}
  - X-XSS-Protection: {"✓" if "X-XSS-Protection" in response.headers else "✗ Missing"}
"""
        
        return result
    
    except requests.exceptions.Timeout:
        error = f"Error: Request timed out after {timeout} seconds"
        console.print(f"[red]{error}[/red]\n")
        return error
    
    except requests.exceptions.SSLError as e:
        error = f"Error: SSL certificate verification failed - {str(e)}"
        console.print(f"[red]{error}[/red]\n")
        return error
    
    except requests.exceptions.ConnectionError as e:
        error = f"Error: Connection failed - {str(e)}"
        console.print(f"[red]{error}[/red]\n")
        return error
    
    except Exception as e:
        error = f"Error: {str(e)}"
        console.print(f"[red]{error}[/red]\n")
        return error


# Schema definition
schema_make_http_request = types.FunctionDeclaration(
    name="make_http_request",
    description="""Make advanced HTTP requests for security testing and bug hunting. Supports custom headers, 
    methods, proxies, and detailed response analysis. Essential for testing APIs, SSRF, XXE, and authentication.""",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "url": types.Schema(
                type=types.Type.STRING,
                description="Target URL (e.g., 'https://example.com/api/users')",
            ),
            "method": types.Schema(
                type=types.Type.STRING,
                description="HTTP method: GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD (default: GET)",
            ),
            "headers": types.Schema(
                type=types.Type.OBJECT,
                description="Custom headers as key-value pairs (e.g., {'Authorization': 'Bearer token'})",
            ),
            "data": types.Schema(
                type=types.Type.STRING,
                description="Request body as string or JSON",
            ),
            "params": types.Schema(
                type=types.Type.OBJECT,
                description="URL parameters as key-value pairs",
            ),
            "cookies": types.Schema(
                type=types.Type.OBJECT,
                description="Cookies as key-value pairs",
            ),
            "timeout": types.Schema(
                type=types.Type.INTEGER,
                description="Timeout in seconds (default: 10)",
            ),
            "verify_ssl": types.Schema(
                type=types.Type.BOOLEAN,
                description="Verify SSL certificates (default: true)",
            ),
            "follow_redirects": types.Schema(
                type=types.Type.BOOLEAN,
                description="Follow HTTP redirects (default: true)",
            ),
            "proxy": types.Schema(
                type=types.Type.STRING,
                description="Proxy URL (e.g., 'http://127.0.0.1:8080' for Burp Suite)",
            ),
        },
        required=["url"],
    ),
)