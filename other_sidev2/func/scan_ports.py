import socket
import concurrent.futures
from typing import List, Tuple, Optional
from google.genai import types
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn

console = Console()

def scan_ports(
    working_directory: str,
    target: str,
    ports: Optional[str] = "1-1000",
    scan_type: str = "tcp",
    threads: int = 100,
    timeout: float = 1.0,
    banner_grab: bool = True
) -> str:
    """
    Scan ports on a target host for open services.
    
    Args:
        working_directory: Base working directory
        target: Target IP or hostname
        ports: Port range (e.g., '1-1000', '80,443,8080' or 'top100')
        scan_type: Scan type ('tcp' or 'udp')
        threads: Number of concurrent threads
        timeout: Connection timeout in seconds
        banner_grab: Attempt to grab service banners
    
    Returns:
        List of open ports with service information
    """
    
    console.print()
    console.print(Panel(
        f"[cyan]Target: {target}[/cyan]\n[dim]Ports: {ports} | Type: {scan_type.upper()}[/dim]",
        title="[yellow]🔍 Port Scanning[/yellow]",
        border_style="yellow",
        padding=(0, 2)
    ))
    
    try:
        # Parse port range
        port_list = _parse_ports(ports)
        
        console.print(f"\n[cyan]→ Scanning {len(port_list)} ports...[/cyan]")
        console.print("[dim]─" * 88 + "[/dim]\n")
        
        # Scan ports with progress bar
        open_ports = []
        
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task("[cyan]Scanning...", total=len(port_list))
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
                futures = {
                    executor.submit(_scan_port, target, port, scan_type, timeout): port 
                    for port in port_list
                }
                
                for future in concurrent.futures.as_completed(futures):
                    port = futures[future]
                    try:
                        is_open, service = future.result()
                        if is_open:
                            # Banner grab if enabled
                            banner = ""
                            if banner_grab and scan_type == "tcp":
                                banner = _grab_banner(target, port, timeout)
                            
                            open_ports.append((port, service, banner))
                            console.print(
                                f"[green]✓[/green] Port {port:5} "
                                f"[yellow]{service:15}[/yellow] "
                                f"[dim]{banner[:50] if banner else 'Open'}[/dim]"
                            )
                    except Exception as e:
                        pass
                    
                    progress.update(task, advance=1)
        
        console.print("\n[dim]─" * 88 + "[/dim]")
        console.print(f"[bold green]Found {len(open_ports)} open ports[/bold green]\n")
        
        # Display results table
        if open_ports:
            table = Table(title="Open Ports Summary", show_lines=True)
            table.add_column("Port", style="cyan", justify="right")
            table.add_column("Service", style="yellow")
            table.add_column("Banner", style="dim")
            
            for port, service, banner in open_ports:
                table.add_row(
                    str(port),
                    service,
                    banner[:60] if banner else "N/A"
                )
            
            console.print(table)
            console.print()
        
        # Build result
        result = f"""Port Scan Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Target: {target}
Ports Scanned: {len(port_list)}
Open Ports: {len(open_ports)}
Scan Type: {scan_type.upper()}

Open Ports:
"""
        
        for port, service, banner in open_ports:
            result += f"\n{port}/{scan_type.upper()} - {service}"
            if banner:
                result += f"\n  Banner: {banner}"
        
        # Security recommendations
        result += "\n\nSecurity Notes:\n"
        
        critical_ports = [21, 23, 445, 3389, 5900]  # FTP, Telnet, SMB, RDP, VNC
        for port, service, _ in open_ports:
            if port in critical_ports:
                result += f"  ⚠ Port {port} ({service}) - High-risk service exposed\n"
        
        return result
    
    except Exception as e:
        error = f"Error during port scan: {str(e)}"
        console.print(f"[red]{error}[/red]\n")
        return error


def _parse_ports(ports_str: str) -> List[int]:
    """Parse port specification into list"""
    if ports_str == "top100":
        # Top 100 most common ports
        return [
            21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445, 993, 995,
            1723, 3306, 3389, 5900, 8080, 8443, 8888
        ]
    
    port_list = []
    
    for part in ports_str.split(','):
        if '-' in part:
            start, end = map(int, part.split('-'))
            port_list.extend(range(start, end + 1))
        else:
            port_list.append(int(part))
    
    return sorted(set(port_list))


def _scan_port(target: str, port: int, scan_type: str, timeout: float) -> Tuple[bool, str]:
    """Scan a single port"""
    service = _get_service_name(port)
    
    try:
        if scan_type == "tcp":
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((target, port))
            sock.close()
            return (result == 0, service)
        else:  # UDP
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(timeout)
            sock.sendto(b'', (target, port))
            try:
                sock.recvfrom(1024)
                sock.close()
                return (True, service)
            except socket.timeout:
                sock.close()
                return (True, service)  # UDP: timeout often means open
    except:
        return (False, service)


def _get_service_name(port: int) -> str:
    """Get common service name for port"""
    services = {
        20: "FTP-DATA", 21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP",
        53: "DNS", 80: "HTTP", 110: "POP3", 143: "IMAP", 443: "HTTPS",
        445: "SMB", 993: "IMAPS", 995: "POP3S", 1433: "MSSQL", 3306: "MySQL",
        3389: "RDP", 5432: "PostgreSQL", 5900: "VNC", 6379: "Redis",
        8080: "HTTP-Proxy", 8443: "HTTPS-Alt", 27017: "MongoDB"
    }
    return services.get(port, "Unknown")


def _grab_banner(target: str, port: int, timeout: float) -> str:
    """Attempt to grab service banner"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((target, port))
        
        # Try to receive banner
        sock.send(b'\r\n')
        banner = sock.recv(1024).decode('utf-8', errors='ignore').strip()
        sock.close()
        
        return banner
    except:
        return ""


# Schema definition
schema_scan_ports = types.FunctionDeclaration(
    name="scan_ports",
    description="""Scan ports on a target to discover open services. Supports TCP/UDP scanning, banner grabbing, 
    and concurrent scanning for speed. Essential for network reconnaissance and service discovery.""",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "target": types.Schema(
                type=types.Type.STRING,
                description="Target IP address or hostname (e.g., '192.168.1.1' or 'example.com')",
            ),
            "ports": types.Schema(
                type=types.Type.STRING,
                description="Port range: '1-1000', '80,443,8080', or 'top100' (default: '1-1000')",
            ),
            "scan_type": types.Schema(
                type=types.Type.STRING,
                description="Scan type: 'tcp' or 'udp' (default: 'tcp')",
            ),
            "threads": types.Schema(
                type=types.Type.INTEGER,
                description="Number of concurrent threads (default: 100)",
            ),
            "timeout": types.Schema(
                type=types.Type.NUMBER,
                description="Connection timeout in seconds (default: 1.0)",
            ),
            "banner_grab": types.Schema(
                type=types.Type.BOOLEAN,
                description="Attempt to grab service banners (default: true)",
            ),
        },
        required=["target"],
    ),
)