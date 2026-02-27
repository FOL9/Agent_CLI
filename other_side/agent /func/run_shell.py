import os
import subprocess
import shlex
from google.genai import types

def run_shell(working_directory, command: str, timeout: int = 30):
    """
    Execute shell commands securely for cybersecurity operations.
    
    Args:
        working_directory: The directory to execute the command in
        command: The shell command to execute
        timeout: Maximum execution time in seconds (default: 30)
    
    Returns:
        String containing stdout, stderr, and exit code information
    """
    abs_working_dir = os.path.abspath(working_directory)
    
    # Security checks
    if not os.path.isdir(abs_working_dir):
        return f'Error: Working directory {working_directory} does not exist'
    
    # Blacklist dangerous commands for safety
    dangerous_commands = ['rm -rf /', 'mkfs', 'dd if=/dev/zero', ':(){:|:&};:', 'chmod -R 777 /']
    if any(dangerous in command.lower() for dangerous in dangerous_commands):
        return 'Error: Command contains potentially dangerous operations and is blocked'
    
    try:
        # Parse command safely
        cmd_parts = shlex.split(command)
        
        if not cmd_parts:
            return 'Error: Empty command provided'
        
        # Execute the command
        process = subprocess.run(
            cmd_parts,
            timeout=timeout,
            capture_output=True,
            text=True,
            cwd=abs_working_dir,
            shell=False  # Avoid shell injection
        )
        
        # Format output
        stdout_output = process.stdout.strip() if process.stdout else ""
        stderr_output = process.stderr.strip() if process.stderr else ""
        
        final_string = f'''Command: {command}
Working Directory: {abs_working_dir}

STDOUT:
{stdout_output if stdout_output else "(empty)"}

STDERR:
{stderr_output if stderr_output else "(empty)"}

Exit Code: {process.returncode}
'''
        
        if process.returncode != 0:
            final_string += f'\n⚠ Process exited with non-zero code: {process.returncode}'
        
        return final_string
    
    except subprocess.TimeoutExpired:
        return f'Error: Command execution timed out after {timeout} seconds'
    
    except FileNotFoundError:
        return f'Error: Command not found - {cmd_parts[0]}'
    
    except PermissionError:
        return f'Error: Permission denied to execute command'
    
    except Exception as e:
        return f'Error executing shell command: {str(e)}'


# Schema definition for the AI agent
schema_run_shell = types.FunctionDeclaration(
    name="run_shell",
    description="""Execute shell commands for cybersecurity operations and daily working , penetration testing, and system administration. 
    Supports tools like nmap, netcat, curl, wget, ping, traceroute, and other security utilities.
    Commands are executed securely with timeout protection.""",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "command": types.Schema(
                type=types.Type.STRING,
                description="The shell command to execute (e.g., 'nmap -sV 192.168.1.1', 'curl -I https://example.com')",
            ),
            "timeout": types.Schema(
                type=types.Type.INTEGER,
                description="Maximum execution time in seconds (default: 30, max: 300)",
            ),
        },
        required=["command"],
    ),
)