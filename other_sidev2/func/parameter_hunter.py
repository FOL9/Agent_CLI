import requests
from typing import Optional, List

import json
import time
import random
from typing import List, Dict
from urllib.parse import urljoin, urlparse, parse_qs
from google.genai import types
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn
from fake_useragent import UserAgent

console = Console()

def hunt_parameters(
    working_directory: str,
    url: str,
    method: str = "GET",
    wordlist: Optional[List[str]] = None,
    techniques: str = "all"
) -> str:
    """
    Advanced parameter discovery and fuzzing with stealth mode.
    
    Args:
        working_directory: Base working directory
        url: Target URL
        method: HTTP method (GET, POST)
        wordlist: Custom parameter wordlist
        techniques: Discovery techniques ('basic', 'advanced', 'all')
    
    Returns:
        Discovered parameters and potential vulnerabilities
    """
    
    ua = UserAgent()
    
    console.print()
    console.print(Panel(
        f"[cyan]{url}[/cyan]\n[dim]Method: {method} | Technique: {techniques}[/dim]",
        title="[yellow]🔎 Parameter Hunter[/yellow]",
        border_style="yellow",
        padding=(0, 2)
    ))
    
    findings = {
        'parameters': [],
        'vulnerabilities': []
    }
    
    try:
        console.print("\n[cyan]→ Initializing parameter discovery...[/cyan]")
        console.print("[dim]─" * 88 + "[/dim]\n")
        
        # Default parameter wordlist
        if not wordlist:
            wordlist = [
                # Common parameters
                'id', 'user', 'page', 'limit', 'offset', 'query', 'search', 'q',
                'token', 'key', 'api_key', 'apikey', 'auth', 'access_token',
                'redirect', 'url', 'next', 'return', 'callback', 'continue',
                'file', 'path', 'filename', 'upload', 'download',
                'email', 'username', 'password', 'pwd', 'pass',
                'admin', 'debug', 'test', 'dev', 'mode',
                'format', 'type', 'action', 'method', 'function',
                'data', 'json', 'xml', 'body', 'content',
                'sort', 'order', 'orderby', 'sortby',
                'filter', 'where', 'field', 'column',
                'start', 'end', 'from', 'to', 'date', 'time',
                'count', 'total', 'size', 'length',
                'version', 'v', 'api', 'endpoint',
                # Next.js specific
                '__nextDataReq', '__flight__', '__props__',
                'buildId', 'pageProps', 'rsc',
            ]
        
        # Technique 1: Basic parameter detection
        if techniques in ['basic', 'all']:
            console.print("[bold cyan]Technique 1: Basic Parameter Fuzzing[/bold cyan]")
            _basic_fuzzing(url, method, wordlist, ua, findings)
        
        # Technique 2: Reflection analysis
        if techniques in ['advanced', 'all']:
            console.print("\n[bold cyan]Technique 2: Reflection Analysis[/bold cyan]")
            _reflection_analysis(url, method, wordlist, ua, findings)
        
        # Technique 3: Error-based discovery
        if techniques in ['advanced', 'all']:
            console.print("\n[bold cyan]Technique 3: Error-Based Discovery[/bold cyan]")
            _error_based_discovery(url, method, ua, findings)
        
        # Technique 4: Timing analysis
        if techniques == 'all':
            console.print("\n[bold cyan]Technique 4: Timing Analysis[/bold cyan]")
            _timing_analysis(url, method, wordlist, ua, findings)
        
        console.print("\n[dim]─" * 88 + "[/dim]\n")
        
        # Display results
        _display_param_findings(findings)
        
        # Generate report
        return _generate_param_report(url, findings, method)
    
    except Exception as e:
        error = f"Error during parameter hunting: {str(e)}"
        console.print(f"[red]{error}[/red]\n")
        return error


def _basic_fuzzing(url: str, method: str, wordlist: List[str], ua: UserAgent, findings: Dict):
    """Basic parameter fuzzing"""
    
    console.print("[cyan]→ Fuzzing parameters...[/cyan]")
    
    discovered = []
    
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:
        
        task = progress.add_task("[cyan]Testing parameters...", total=len(wordlist))
        
        for param in wordlist:
            try:
                headers = {
                    'User-Agent': ua.random,
                    'Accept': 'application/json,text/html,*/*'
                }
                
                if method == "GET":
                    test_url = f"{url}?{param}=test"
                    response = requests.get(
                        test_url,
                        headers=headers,
                        timeout=5,
                        verify=False
                    )
                else:
                    response = requests.post(
                        url,
                        data={param: 'test'},
                        headers=headers,
                        timeout=5,
                        verify=False
                    )
                
                # Check if parameter is reflected
                if 'test' in response.text and param not in discovered:
                    discovered.append(param)
                    findings['parameters'].append({
                        'name': param,
                        'method': method,
                        'reflected': True,
                        'type': 'discovered'
                    })
                    console.print(f"  [green]✓[/green] Found: {param} (reflected)")
                
                # Check for different response (parameter exists)
                elif len(response.text) != len(requests.get(url, headers=headers, timeout=5, verify=False).text):
                    if param not in discovered:
                        discovered.append(param)
                        findings['parameters'].append({
                            'name': param,
                            'method': method,
                            'reflected': False,
                            'type': 'discovered'
                        })
                        console.print(f"  [cyan]•[/cyan] Found: {param} (affects response)")
                
                time.sleep(random.uniform(0.1, 0.3))
                
            except:
                pass
            
            progress.update(task, advance=1)
    
    console.print(f"  [bold green]Discovered {len(discovered)} parameters[/bold green]")


def _reflection_analysis(url: str, method: str, wordlist: List[str], ua: UserAgent, findings: Dict):
    """Advanced reflection analysis"""
    
    console.print("[cyan]→ Analyzing parameter reflection...[/cyan]")
    
    # Test with unique markers
    marker = f"xss{random.randint(10000, 99999)}"
    
    for param in wordlist[:30]:  # Test top parameters
        try:
            headers = {'User-Agent': ua.random}
            
            if method == "GET":
                test_url = f"{url}?{param}={marker}"
                response = requests.get(test_url, headers=headers, timeout=5, verify=False)
            else:
                response = requests.post(
                    url,
                    data={param: marker},
                    headers=headers,
                    timeout=5,
                    verify=False
                )
            
            if marker in response.text:
                # Check if it's in script context (XSS potential)
                if f'<script>' in response.text or f'javascript:' in response.text:
                    findings['vulnerabilities'].append({
                        'type': 'XSS',
                        'severity': 'high',
                        'parameter': param,
                        'description': f'Parameter {param} reflected in dangerous context',
                        'impact': 'Potential XSS vulnerability'
                    })
                    console.print(f"  [red]✗ XSS potential: {param}[/red]")
                else:
                    console.print(f"  [yellow]⚠ Reflected: {param}[/yellow]")
            
            time.sleep(random.uniform(0.2, 0.5))
            
        except:
            pass


def _error_based_discovery(url: str, method: str, ua: UserAgent, findings: Dict):
    """Error-based parameter discovery"""
    
    console.print("[cyan]→ Testing error responses...[/cyan]")
    
    # SQL injection markers
    sqli_payloads = ["'", "\"", "1=1", "' OR '1'='1"]
    
    for payload in sqli_payloads:
        try:
            headers = {'User-Agent': ua.random}
            
            if method == "GET":
                test_url = f"{url}?id={payload}"
                response = requests.get(test_url, headers=headers, timeout=5, verify=False)
            else:
                response = requests.post(
                    url,
                    data={'id': payload},
                    headers=headers,
                    timeout=5,
                    verify=False
                )
            
            # Check for SQL errors
            sql_errors = [
                'sql syntax',
                'mysql',
                'postgresql',
                'sqlite',
                'ora-',
                'syntax error',
                'unclosed quotation'
            ]
            
            response_lower = response.text.lower()
            if any(error in response_lower for error in sql_errors):
                findings['vulnerabilities'].append({
                    'type': 'SQLi',
                    'severity': 'critical',
                    'parameter': 'id',
                    'description': 'SQL injection vulnerability detected',
                    'impact': 'Database compromise possible',
                    'payload': payload
                })
                console.print(f"  [red]✗ CRITICAL: SQL injection found! (payload: {payload})[/red]")
                break
            
            time.sleep(random.uniform(0.3, 0.6))
            
        except:
            pass
    
    console.print("  [green]✓[/green] Error analysis complete")


def _timing_analysis(url: str, method: str, wordlist: List[str], ua: UserAgent, findings: Dict):
    """Timing-based parameter detection"""
    
    console.print("[cyan]→ Performing timing analysis...[/cyan]")
    
    # Get baseline timing
    headers = {'User-Agent': ua.random}
    baseline_times = []
    
    for _ in range(3):
        try:
            start = time.time()
            requests.get(url, headers=headers, timeout=10, verify=False)
            baseline_times.append(time.time() - start)
            time.sleep(0.5)
        except:
            pass
    
    if not baseline_times:
        console.print("  [dim]• Unable to establish baseline[/dim]")
        return
    
    avg_baseline = sum(baseline_times) / len(baseline_times)
    
    # Test for blind SQLi with timing
    test_params = ['id', 'user', 'page']
    
    for param in test_params:
        try:
            # Time-based payload (sleep)
            test_url = f"{url}?{param}=1' AND SLEEP(5)--"
            
            start = time.time()
            response = requests.get(
                test_url,
                headers=headers,
                timeout=10,
                verify=False
            )
            elapsed = time.time() - start
            
            # If response took significantly longer
            if elapsed > avg_baseline + 4:
                findings['vulnerabilities'].append({
                    'type': 'Blind SQLi',
                    'severity': 'critical',
                    'parameter': param,
                    'description': f'Time-based blind SQL injection in {param}',
                    'impact': 'Database can be extracted via timing attacks'
                })
                console.print(f"  [red]✗ CRITICAL: Blind SQLi in {param}![/red]")
            
            time.sleep(1)
            
        except:
            pass
    
    console.print("  [green]✓[/green] Timing analysis complete")


def _display_param_findings(findings: Dict):
    """Display findings"""
    
    console.print("[bold cyan]📋 Discovery Summary[/bold cyan]\n")
    
    # Parameters table
    if findings['parameters']:
        param_table = Table(title="Discovered Parameters", show_lines=True)
        param_table.add_column("Parameter", style="cyan")
        param_table.add_column("Method", style="yellow")
        param_table.add_column("Reflected", style="green")
        param_table.add_column("Type", style="dim")
        
        for param in findings['parameters']:
            param_table.add_row(
                param['name'],
                param['method'],
                "Yes" if param['reflected'] else "No",
                param['type']
            )
        
        console.print(param_table)
        console.print()
    
    # Vulnerabilities
    if findings['vulnerabilities']:
        console.print("[bold red]🚨 Vulnerabilities Detected[/bold red]\n")
        
        vuln_table = Table(show_lines=True)
        vuln_table.add_column("Type", style="red")
        vuln_table.add_column("Severity", style="yellow")
        vuln_table.add_column("Parameter", style="cyan")
        vuln_table.add_column("Description", style="dim")
        
        for vuln in findings['vulnerabilities']:
            vuln_table.add_row(
                vuln['type'],
                vuln['severity'].upper(),
                vuln['parameter'],
                vuln['description']
            )
        
        console.print(vuln_table)
        console.print()


def _generate_param_report(url: str, findings: Dict, method: str) -> str:
    """Generate parameter discovery report"""
    
    report = f"""Parameter Discovery Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Target: {url}
Method: {method}
Parameters Found: {len(findings['parameters'])}
Vulnerabilities: {len(findings['vulnerabilities'])}

"""
    
    if findings['parameters']:
        report += "\nDISCOVERED PARAMETERS:\n"
        report += "=" * 60 + "\n\n"
        
        for param in findings['parameters']:
            report += f"• {param['name']}\n"
            report += f"  Method: {param['method']}\n"
            report += f"  Reflected: {param['reflected']}\n"
            report += f"  Type: {param['type']}\n\n"
    
    if findings['vulnerabilities']:
        report += "\nVULNERABILITIES:\n"
        report += "=" * 60 + "\n\n"
        
        for vuln in findings['vulnerabilities']:
            report += f"⚠ {vuln['type']} - {vuln['severity'].upper()}\n"
            report += f"  Parameter: {vuln['parameter']}\n"
            report += f"  Description: {vuln['description']}\n"
            report += f"  Impact: {vuln['impact']}\n"
            if 'payload' in vuln:
                report += f"  Payload: {vuln['payload']}\n"
            report += "\n"
    
    return report


# Schema definition
schema_hunt_parameters = types.FunctionDeclaration(
    name="hunt_parameters",
    description="""Advanced parameter discovery tool with stealth capabilities. Uses multiple techniques including 
    basic fuzzing, reflection analysis, error-based discovery, and timing attacks to find hidden parameters and 
    vulnerabilities like SQLi, XSS, and blind SQLi. Essential for API testing and bug hunting.""",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "url": types.Schema(
                type=types.Type.STRING,
                description="Target URL to test",
            ),
            "method": types.Schema(
                type=types.Type.STRING,
                description="HTTP method: GET or POST (default: GET)",
            ),
            "wordlist": types.Schema(
                type=types.Type.ARRAY,
                description="Custom parameter wordlist (optional)",
                items=types.Schema(type=types.Type.STRING),
            ),
            "techniques": types.Schema(
                type=types.Type.STRING,
                description="Discovery techniques: 'basic', 'advanced', or 'all' (default: all)",
            ),
        },
        required=["url"],
    ),
)