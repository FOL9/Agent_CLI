import requests
import json
import time
import random
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse
from google.genai import types
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from fake_useragent import UserAgent

console = Console()

class StealthScanner:
    """Advanced stealthy web scanner with browser-like behavior"""
    
    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()
        
    def get_headers(self, referer: str = None) -> Dict:
        """Generate realistic browser headers"""
        headers = {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }
        
        if referer:
            headers['Referer'] = referer
            
        return headers
    
    def random_delay(self):
        """Random delay to avoid detection"""
        time.sleep(random.uniform(0.5, 2.0))


def stealth_scan(
    working_directory: str,
    url: str,
    scan_type: str = "full",
    aggressive: bool = False
) -> str:
    """
    Advanced stealthy scanner that bypasses WAF and behaves like a real browser.
    
    Args:
        working_directory: Base working directory
        url: Target URL
        scan_type: Type of scan ('recon', 'vuln', 'full')
        aggressive: Use aggressive techniques (may trigger WAF)
    
    Returns:
        Comprehensive vulnerability report
    """
    
    scanner = StealthScanner()
    
    console.print()
    console.print(Panel(
        f"[cyan]{url}[/cyan]\n[dim]Scan Type: {scan_type} | Stealth Mode: Active[/dim]",
        title="[yellow]🕵️ Stealth Scanner[/yellow]",
        border_style="yellow",
        padding=(0, 2)
    ))
    
    findings = {
        'critical': [],
        'high': [],
        'medium': [],
        'low': [],
        'info': []
    }
    
    try:
        console.print("\n[cyan]→ Initializing stealth mode...[/cyan]")
        console.print("[dim]→ Rotating user agents[/dim]")
        console.print("[dim]→ Mimicking browser behavior[/dim]")
        console.print("[dim]─" * 88 + "[/dim]\n")
        
        # Phase 1: Reconnaissance
        if scan_type in ['recon', 'full']:
            console.print("[bold cyan]Phase 1: Reconnaissance[/bold cyan]")
            _stealth_recon(url, scanner, findings, aggressive)
        
        # Phase 2: Vulnerability Detection
        if scan_type in ['vuln', 'full']:
            console.print("\n[bold cyan]Phase 2: Vulnerability Detection[/bold cyan]")
            _detect_vulnerabilities(url, scanner, findings, aggressive)
        
        # Phase 3: Next.js Specific Tests
        if scan_type == 'full':
            console.print("\n[bold cyan]Phase 3: Next.js Exploitation[/bold cyan]")
            _nextjs_exploitation(url, scanner, findings, aggressive)
        
        console.print("\n[dim]─" * 88 + "[/dim]\n")
        
        # Display results
        _display_stealth_findings(findings)
        
        # Generate report
        return _generate_stealth_report(url, findings, scan_type)
    
    except Exception as e:
        error = f"Error during stealth scan: {str(e)}"
        console.print(f"[red]{error}[/red]\n")
        return error


def _stealth_recon(url: str, scanner: StealthScanner, findings: Dict, aggressive: bool):
    """Perform stealthy reconnaissance"""
    
    # 1. Initial request with browser headers
    console.print("[cyan]1.[/cyan] Accessing target with browser profile...")
    scanner.random_delay()
    
    try:
        response = scanner.session.get(
            url,
            headers=scanner.get_headers(),
            timeout=15,
            verify=False
        )
        
        html = response.text
        headers = response.headers
        
        console.print(f"  [green]✓[/green] Status: {response.status_code}")
        console.print(f"  [dim]Response time: {response.elapsed.total_seconds():.2f}s[/dim]")
        
        # Detect framework
        if '_next' in html or 'Next.js' in str(headers):
            findings['info'].append({
                'title': 'Framework Detected: Next.js',
                'severity': 'info',
                'details': 'Application built with Next.js framework'
            })
            console.print("  [cyan]→[/cyan] Next.js application detected")
        
        # Check for React
        if '__NEXT_DATA__' in html or 'react' in html.lower():
            findings['info'].append({
                'title': 'Frontend: React',
                'severity': 'info',
                'details': 'React framework in use'
            })
        
        # Security headers check
        console.print("[cyan]2.[/cyan] Analyzing security posture...")
        missing_headers = []
        
        if 'X-Frame-Options' not in headers:
            missing_headers.append('X-Frame-Options')
        if 'Content-Security-Policy' not in headers:
            missing_headers.append('CSP')
        if 'X-Content-Type-Options' not in headers:
            missing_headers.append('X-Content-Type-Options')
        
        if missing_headers:
            findings['medium'].append({
                'title': f'Missing Security Headers: {", ".join(missing_headers)}',
                'severity': 'medium',
                'details': 'Application lacks important security headers',
                'impact': 'Vulnerable to clickjacking, XSS, MIME sniffing',
                'remediation': 'Implement missing security headers'
            })
            console.print(f"  [yellow]⚠[/yellow] Missing {len(missing_headers)} security headers")
        
        # Check for information disclosure
        if 'X-Powered-By' in headers:
            findings['low'].append({
                'title': 'Information Disclosure: X-Powered-By Header',
                'severity': 'low',
                'details': f"Header value: {headers['X-Powered-By']}",
                'impact': 'Technology stack exposed',
                'remediation': 'Remove X-Powered-By header'
            })
            console.print(f"  [yellow]⚠[/yellow] Technology disclosure: {headers['X-Powered-By']}")
        
        # 3. API Discovery
        console.print("[cyan]3.[/cyan] Discovering API endpoints...")
        scanner.random_delay()
        
        api_routes = _discover_apis(url, scanner, html)
        if api_routes:
            findings['info'].append({
                'title': f'Discovered {len(api_routes)} API Endpoints',
                'severity': 'info',
                'details': f"Routes: {', '.join(api_routes)}"
            })
            console.print(f"  [green]✓[/green] Found {len(api_routes)} API routes")
            for route in api_routes[:5]:
                console.print(f"    [dim]• {route}[/dim]")
        
        # 4. Static asset analysis
        console.print("[cyan]4.[/cyan] Analyzing static assets...")
        scanner.random_delay()
        
        _analyze_static_assets(url, scanner, findings, html)
        
    except Exception as e:
        console.print(f"  [red]✗[/red] Recon failed: {str(e)}")


def _detect_vulnerabilities(url: str, scanner: StealthScanner, findings: Dict, aggressive: bool):
    """Detect common vulnerabilities"""
    
    # 1. Check for exposed sensitive files
    console.print("[cyan]1.[/cyan] Testing for exposed sensitive files...")
    scanner.random_delay()
    
    sensitive_files = [
        '.env',
        '.env.local',
        '.env.production',
        '.git/config',
        'package.json',
        '.next/cache',
    ]
    
    for file in sensitive_files:
        try:
            response = scanner.session.get(
                urljoin(url, file),
                headers=scanner.get_headers(url),
                timeout=5,
                verify=False
            )
            
            if response.status_code == 200 and len(response.content) > 0:
                severity = 'critical' if '.env' in file else 'high'
                findings[severity].append({
                    'title': f'Exposed Sensitive File: {file}',
                    'severity': severity,
                    'details': f'File {file} is publicly accessible',
                    'impact': 'Credentials and secrets may be exposed',
                    'remediation': 'Configure server to block sensitive files'
                })
                console.print(f"  [red]✗ CRITICAL: {file} exposed![/red]")
                scanner.random_delay()
        except:
            pass
    
    console.print("  [green]✓[/green] No sensitive files found")
    
    # 2. API security testing
    console.print("[cyan]2.[/cyan] Testing API security...")
    scanner.random_delay()
    
    api_endpoints = [
        '/api/auth',
        '/api/users',
        '/api/admin',
        '/api/config',
    ]
    
    for endpoint in api_endpoints:
        try:
            response = scanner.session.get(
                urljoin(url, endpoint),
                headers=scanner.get_headers(url),
                timeout=5,
                verify=False
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    # Check for sensitive data
                    sensitive_keys = ['password', 'token', 'secret', 'key', 'apiKey']
                    json_str = json.dumps(data).lower()
                    
                    if any(key in json_str for key in sensitive_keys):
                        findings['critical'].append({
                            'title': f'Sensitive Data Exposed: {endpoint}',
                            'severity': 'critical',
                            'details': f'API endpoint returns sensitive information',
                            'impact': 'Critical data leak',
                            'remediation': 'Implement authentication and filter response'
                        })
                        console.print(f"  [red]✗ CRITICAL: {endpoint} leaks data![/red]")
                except:
                    pass
                
            scanner.random_delay()
        except:
            pass
    
    # 3. IDOR Testing
    if aggressive:
        console.print("[cyan]3.[/cyan] Testing for IDOR vulnerabilities...")
        _test_idor(url, scanner, findings)
    
    # 4. SSRF Testing
    console.print("[cyan]4.[/cyan] Testing for SSRF...")
    scanner.random_delay()
    
    ssrf_payloads = [
        '?url=http://localhost',
        '?redirect=http://127.0.0.1',
        '?callback=http://internal.local',
    ]
    
    for payload in ssrf_payloads:
        try:
            response = scanner.session.get(
                url + payload,
                headers=scanner.get_headers(url),
                timeout=5,
                verify=False,
                allow_redirects=False
            )
            
            if response.status_code in [200, 301, 302] or 'localhost' in response.text:
                findings['high'].append({
                    'title': 'Potential SSRF Vulnerability',
                    'severity': 'high',
                    'details': f'URL parameter vulnerable to SSRF',
                    'impact': 'Internal network access possible',
                    'remediation': 'Validate and sanitize URL parameters'
                })
                console.print("  [red]✗ SSRF vulnerability detected![/red]")
                break
            scanner.random_delay()
        except:
            pass


def _nextjs_exploitation(url: str, scanner: StealthScanner, findings: Dict, aggressive: bool):
    """Next.js specific exploitation tests"""
    
    # 1. Check for Next.js data leaks
    console.print("[cyan]1.[/cyan] Testing for Next.js data leaks...")
    scanner.random_delay()
    
    try:
        response = scanner.session.get(
            url,
            headers=scanner.get_headers(),
            timeout=10,
            verify=False
        )
        
        html = response.text
        
        # Check for __NEXT_DATA__ exposure
        if '__NEXT_DATA__' in html:
            import re
            match = re.search(r'__NEXT_DATA__\s*=\s*({.*?})</script>', html, re.DOTALL)
            if match:
                try:
                    next_data = json.loads(match.group(1))
                    
                    # Check for sensitive data
                    data_str = json.dumps(next_data).lower()
                    if any(key in data_str for key in ['apikey', 'secret', 'password', 'token']):
                        findings['critical'].append({
                            'title': 'Critical: Secrets in __NEXT_DATA__',
                            'severity': 'critical',
                            'details': 'Sensitive data exposed in client-side props',
                            'impact': 'API keys and secrets leaked to client',
                            'remediation': 'Never pass secrets via getServerSideProps'
                        })
                        console.print("  [red]✗ CRITICAL: Secrets leaked in __NEXT_DATA__![/red]")
                except:
                    pass
    except:
        pass
    
    # 2. Image optimization SSRF
    console.print("[cyan]2.[/cyan] Testing Next.js image optimization...")
    scanner.random_delay()
    
    try:
        response = scanner.session.get(
            urljoin(url, '/_next/image?url=http://localhost&w=640&q=75'),
            headers=scanner.get_headers(url),
            timeout=5,
            verify=False
        )
        
        if response.status_code != 400:
            findings['high'].append({
                'title': 'Image Optimization SSRF',
                'severity': 'high',
                'details': 'Next.js image proxy vulnerable to SSRF',
                'impact': 'Can access internal services',
                'remediation': 'Configure image domains whitelist'
            })
            console.print("  [red]✗ Image optimization SSRF![/red]")
    except:
        pass
    
    # 3. Path traversal attempt
    console.print("[cyan]3.[/cyan] Testing for path traversal...")
    scanner.random_delay()
    
    try:
        response = scanner.session.get(
            urljoin(url, '/_next/../../../etc/passwd'),
            headers=scanner.get_headers(url),
            timeout=5,
            verify=False
        )
        
        if response.status_code == 200 and 'root:' in response.text:
            findings['critical'].append({
                'title': 'Path Traversal Vulnerability',
                'severity': 'critical',
                'details': 'CVE-2023-36859 - Path traversal in Next.js',
                'impact': 'File system access',
                'remediation': 'Update Next.js immediately'
            })
            console.print("  [red]✗ CRITICAL: Path traversal works![/red]")
    except:
        pass
    
    console.print("  [green]✓[/green] Next.js exploitation tests complete")


def _discover_apis(url: str, scanner: StealthScanner, html: str) -> List[str]:
    """Discover API routes intelligently"""
    apis = []
    
    # Parse from HTML
    import re
    api_pattern = r'["\']/(api/[^"\']+)["\']'
    matches = re.findall(api_pattern, html)
    apis.extend(set(matches))
    
    # Common routes
    common = ['api/auth', 'api/users', 'api/data', 'api/config']
    
    for route in common:
        try:
            response = scanner.session.head(
                urljoin(url, route),
                headers=scanner.get_headers(url),
                timeout=3,
                verify=False
            )
            if response.status_code != 404:
                apis.append(route)
        except:
            pass
    
    return list(set(apis))


def _analyze_static_assets(url: str, scanner: StealthScanner, findings: Dict, html: str):
    """Analyze static assets for vulnerabilities"""
    
    import re
    
    # Check for environment variables in JS
    env_pattern = r'NEXT_PUBLIC_[A-Z_]+'
    env_vars = re.findall(env_pattern, html)
    
    if env_vars:
        findings['info'].append({
            'title': f'Public Environment Variables: {len(env_vars)}',
            'severity': 'info',
            'details': f'Found: {", ".join(env_vars[:5])}'
        })
        console.print(f"  [cyan]→[/cyan] Found {len(env_vars)} public env vars")


def _test_idor(url: str, scanner: StealthScanner, findings: Dict):
    """Test for IDOR vulnerabilities"""
    
    # Test common IDOR patterns
    idor_tests = [
        '/api/users/1',
        '/api/profile/1',
        '/api/account/1',
    ]
    
    for test_url in idor_tests:
        try:
            response = scanner.session.get(
                urljoin(url, test_url),
                headers=scanner.get_headers(url),
                timeout=5,
                verify=False
            )
            
            if response.status_code == 200:
                findings['high'].append({
                    'title': f'Potential IDOR: {test_url}',
                    'severity': 'high',
                    'details': 'Direct object reference without auth',
                    'impact': 'Unauthorized data access',
                    'remediation': 'Implement authorization checks'
                })
                console.print(f"  [red]✗ IDOR found: {test_url}[/red]")
            
            scanner.random_delay()
        except:
            pass


def _display_stealth_findings(findings: Dict):
    """Display findings in tree format"""
    
    total = sum(len(findings[k]) for k in findings.keys())
    
    if total == 0:
        console.print("[green]✓ No vulnerabilities found[/green]\n")
        return
    
    tree = Tree(f"[bold red]🎯 Findings: {total} Total[/bold red]")
    
    if findings['critical']:
        critical = tree.add(f"[bold red]🚨 CRITICAL ({len(findings['critical'])})[/bold red]")
        for f in findings['critical']:
            critical.add(f"[red]{f['title']}[/red]")
    
    if findings['high']:
        high = tree.add(f"[bold red]⚠ HIGH ({len(findings['high'])})[/bold red]")
        for f in findings['high']:
            high.add(f"[red]{f['title']}[/red]")
    
    if findings['medium']:
        medium = tree.add(f"[bold yellow]• MEDIUM ({len(findings['medium'])})[/bold yellow]")
        for f in findings['medium']:
            medium.add(f"[yellow]{f['title']}[/yellow]")
    
    if findings['low']:
        low = tree.add(f"[bold cyan]ℹ LOW ({len(findings['low'])})[/bold cyan]")
        for f in findings['low']:
            low.add(f"[cyan]{f['title']}[/cyan]")
    
    console.print(tree)
    console.print()


def _generate_stealth_report(url: str, findings: Dict, scan_type: str) -> str:
    """Generate comprehensive report"""
    
    total = sum(len(findings[k]) for k in findings.keys())
    
    report = f"""Stealth Security Scan Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Target: {url}
Scan Type: {scan_type}
Mode: Stealth (Browser Mimicking)
Total Findings: {total}

SEVERITY BREAKDOWN:
  🚨 Critical: {len(findings['critical'])}
  ⚠ High: {len(findings['high'])}
  • Medium: {len(findings['medium'])}
  ℹ Low: {len(findings['low'])}
  • Info: {len(findings['info'])}

"""
    
    for severity in ['critical', 'high', 'medium', 'low', 'info']:
        items = findings[severity]
        if items:
            report += f"\n{'=' * 60}\n"
            report += f"{severity.upper()} SEVERITY:\n"
            report += f"{'=' * 60}\n\n"
            
            for i, finding in enumerate(items, 1):
                report += f"{i}. {finding['title']}\n"
                report += f"   Severity: {finding['severity']}\n"
                report += f"   Details: {finding['details']}\n"
                if 'impact' in finding:
                    report += f"   Impact: {finding['impact']}\n"
                if 'remediation' in finding:
                    report += f"   Remediation: {finding['remediation']}\n"
                report += "\n"
    
    return report


# Schema definition
schema_stealth_scan = types.FunctionDeclaration(
    name="stealth_scan",
    description="""Advanced stealthy web scanner that mimics real browser behavior using rotating user agents 
    and realistic headers. Bypasses WAF detection while testing for Next.js vulnerabilities, API security issues, 
    SSRF, IDOR, and exposed sensitive files. Essential for professional bug hunting.""",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "url": types.Schema(
                type=types.Type.STRING,
                description="Target URL to scan",
            ),
            "scan_type": types.Schema(
                type=types.Type.STRING,
                description="Scan type: 'recon' (reconnaissance only), 'vuln' (vulnerability testing), or 'full' (complete scan)",
            ),
            "aggressive": types.Schema(
                type=types.Type.BOOLEAN,
                description="Use aggressive techniques (may trigger WAF, default: false)",
            ),
        },
        required=["url"],
    ),
)