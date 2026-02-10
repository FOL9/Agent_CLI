import dns.resolver
from typing import Optional, List
import requests
import socket
from typing import Set, List
from google.genai import types
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

def enumerate_subdomains(
    working_directory: str,
    domain: str,
    method: str = "dns",
    wordlist: Optional[List[str]] = None,
    check_alive: bool = True
) -> str:
    """
    Enumerate subdomains for a target domain using multiple techniques.
    
    Args:
        working_directory: Base working directory
        domain: Target domain (e.g., 'example.com')
        method: Enumeration method ('dns', 'crt', 'brute', 'all')
        wordlist: Custom wordlist for brute force (optional)
        check_alive: Check if discovered subdomains are alive
    
    Returns:
        List of discovered subdomains with status
    """
    
    console.print()
    console.print(Panel(
        f"[cyan]Target: {domain}[/cyan]\n[dim]Method: {method}[/dim]",
        title="[yellow]🔍 Subdomain Enumeration[/yellow]",
        border_style="yellow",
        padding=(0, 2)
    ))
    
    discovered_subdomains: Set[str] = set()
    
    try:
        # Method 1: DNS enumeration
        if method in ['dns', 'all']:
            console.print("\n[cyan]→ DNS Enumeration...[/cyan]")
            dns_subs = _dns_enumeration(domain)
            discovered_subdomains.update(dns_subs)
            console.print(f"[green]Found {len(dns_subs)} via DNS[/green]")
        
        # Method 2: Certificate Transparency
        if method in ['crt', 'all']:
            console.print("\n[cyan]→ Certificate Transparency Logs...[/cyan]")
            crt_subs = _crt_sh_search(domain)
            discovered_subdomains.update(crt_subs)
            console.print(f"[green]Found {len(crt_subs)} via CT logs[/green]")
        
        # Method 3: Brute force
        if method in ['brute', 'all']:
            console.print("\n[cyan]→ Brute Force Enumeration...[/cyan]")
            if not wordlist:
                # Default common subdomains
                wordlist = [
                    'www', 'mail', 'ftp', 'localhost', 'webmail', 'smtp', 'pop', 'ns1', 'webdisk',
                    'ns2', 'cpanel', 'whm', 'autodiscover', 'autoconfig', 'admin', 'api', 'dev',
                    'staging', 'test', 'portal', 'cdn', 'blog', 'shop', 'store', 'news', 'support',
                    'app', 'mobile', 'beta', 'vpn', 'gateway', 'secure', 'login', 'dashboard',
                    'console', 'panel', 'internal', 'private', 'secret', 'hidden'
                ]
            
            brute_subs = _brute_force(domain, wordlist[:50])  # Limit for speed
            discovered_subdomains.update(brute_subs)
            console.print(f"[green]Found {len(brute_subs)} via brute force[/green]")
        
        # Check if subdomains are alive
        alive_subs = []
        if check_alive and discovered_subdomains:
            console.print("\n[cyan]→ Checking subdomain status...[/cyan]")
            console.print("[dim]─" * 88 + "[/dim]")
            
            for subdomain in sorted(discovered_subdomains):
                status = _check_subdomain_alive(subdomain)
                if status:
                    alive_subs.append((subdomain, status))
                    console.print(f"[green]✓[/green] {subdomain:40} [{status}]")
                else:
                    console.print(f"[dim]✗ {subdomain:40} [Not Responding][/dim]")
        
        console.print("[dim]─" * 88 + "[/dim]")
        console.print(f"\n[bold green]Total: {len(discovered_subdomains)} subdomains[/bold green]")
        console.print(f"[bold green]Alive: {len(alive_subs)} subdomains[/bold green]\n")
        
        # Build result
        result = f"""Subdomain Enumeration Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Domain: {domain}
Method: {method}
Total Discovered: {len(discovered_subdomains)}
Alive: {len(alive_subs)}

Discovered Subdomains:
"""
        
        if alive_subs:
            result += "\nAlive Subdomains:\n"
            for sub, status in alive_subs:
                result += f"  ✓ {sub} [{status}]\n"
        
        result += "\nAll Discovered:\n"
        for sub in sorted(discovered_subdomains):
            result += f"  • {sub}\n"
        
        return result
    
    except Exception as e:
        error = f"Error during subdomain enumeration: {str(e)}"
        console.print(f"[red]{error}[/red]\n")
        return error


def _dns_enumeration(domain: str) -> Set[str]:
    """Enumerate subdomains via DNS records"""
    subdomains = set()
    
    try:
        # Check common DNS records
        record_types = ['A', 'AAAA', 'CNAME', 'MX', 'NS', 'TXT']
        
        for record_type in record_types:
            try:
                answers = dns.resolver.resolve(domain, record_type)
                for rdata in answers:
                    value = str(rdata)
                    if domain in value:
                        subdomains.add(value.rstrip('.'))
            except:
                pass
    except:
        pass
    
    return subdomains


def _crt_sh_search(domain: str) -> Set[str]:
    """Search Certificate Transparency logs"""
    subdomains = set()
    
    try:
        url = f"https://crt.sh/?q=%.{domain}&output=json"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            for entry in data:
                name = entry.get('name_value', '')
                if name and domain in name:
                    # Handle wildcard and multiple domains
                    names = name.split('\n')
                    for n in names:
                        n = n.strip().lstrip('*.')
                        if n and domain in n:
                            subdomains.add(n)
    except:
        pass
    
    return subdomains


def _brute_force(domain: str, wordlist: List[str]) -> Set[str]:
    """Brute force subdomains using wordlist"""
    subdomains = set()
    
    for word in wordlist:
        subdomain = f"{word}.{domain}"
        try:
            socket.gethostbyname(subdomain)
            subdomains.add(subdomain)
        except:
            pass
    
    return subdomains


def _check_subdomain_alive(subdomain: str) -> Optional[str]:
    """Check if subdomain is responding"""
    for protocol in ['https', 'http']:
        try:
            url = f"{protocol}://{subdomain}"
            response = requests.get(url, timeout=3, verify=False, allow_redirects=False)
            return f"{protocol.upper()} {response.status_code}"
        except:
            pass
    
    return None


# Schema definition
schema_enumerate_subdomains = types.FunctionDeclaration(
    name="enumerate_subdomains",
    description="""Discover subdomains for a target domain using DNS enumeration, certificate transparency logs, 
    and brute force. Essential for initial reconnaissance and attack surface mapping.""",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "domain": types.Schema(
                type=types.Type.STRING,
                description="Target domain (e.g., 'example.com')",
            ),
            "method": types.Schema(
                type=types.Type.STRING,
                description="Enumeration method: 'dns', 'crt' (certificate transparency), 'brute', or 'all' (default: 'dns')",
            ),
            "wordlist": types.Schema(
                type=types.Type.ARRAY,
                description="Custom wordlist for brute force (optional)",
                items=types.Schema(type=types.Type.STRING),
            ),
            "check_alive": types.Schema(
                type=types.Type.BOOLEAN,
                description="Check if discovered subdomains are responding (default: true)",
            ),
        },
        required=["domain"],
    ),
)