import os
from google.genai import types

def get_file_content(working_directory: str, file_path: str, start_line: int = None, end_line: int = None) -> str:
    """
    Read and return the contents of a file, optionally from specific line range.
    
    Args:
        working_directory: The base working directory
        file_path: Relative path to the file to read
        start_line: Optional starting line number (1-indexed)
        end_line: Optional ending line number (1-indexed, inclusive)
    
    Returns:
        String containing file contents or error message
    """
    abs_working_dir = os.path.abspath(working_directory)
    abs_file_path = os.path.abspath(os.path.join(working_directory, file_path))
    
    # Security check: prevent directory traversal
    if not abs_file_path.startswith(abs_working_dir):
        return f'Error: Access denied - {file_path} is outside working directory'
    
    if not os.path.exists(abs_file_path):
        return f'Error: File {file_path} does not exist'
    
    if not os.path.isfile(abs_file_path):
        return f'Error: {file_path} is not a file'
    
    try:
        # Try to read as text
        with open(abs_file_path, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        
        total_lines = len(all_lines)
        
        # Validate line range
        if start_line is not None or end_line is not None:
            # Set defaults
            start = start_line if start_line is not None else 1
            end = end_line if end_line is not None else total_lines
            
            # Validate range
            if start < 1:
                return f'Error: start_line must be >= 1 (got {start})'
            if end < start:
                return f'Error: end_line ({end}) must be >= start_line ({start})'
            if start > total_lines:
                return f'Error: start_line ({start}) exceeds file length ({total_lines} lines)'
            
            # Clamp end_line to file length
            end = min(end, total_lines)
            
            # Extract the requested lines (convert to 0-indexed)
            selected_lines = all_lines[start - 1:end]
            content = ''.join(selected_lines)
            
            # Return formatted content with line numbers and metadata
            result = f"RANGE:{start}-{end}:{total_lines}\n"
            for i, line in enumerate(selected_lines):
                line_num = start + i
                result += f"{line_num:4d} | {line}"
            
            return result
        else:
            # Read entire file
            content = ''.join(all_lines)
            size = os.path.getsize(abs_file_path)
            
            # Add simple header for full file
            header = f"File: {file_path}\nSize: {size} bytes | Lines: {total_lines}\n{'-' * 60}\n"
            return header + content
    
    except UnicodeDecodeError:
        # Binary file
        size = os.path.getsize(abs_file_path)
        return f'Error: {file_path} is a binary file ({size} bytes) - cannot display as text'
    
    except PermissionError:
        return f'Error: Permission denied reading {file_path}'
    
    except Exception as e:
        return f'Error reading file {file_path}: {str(e)}'


# Schema definition for the AI agent
schema_get_file_content = types.FunctionDeclaration(
    name="get_file_content",
    description=(
        "Read and return the contents of a text file. "
        "Can read the entire file or a specific line range (useful when error messages show line numbers). "
        "Examples: Read full file, read lines 20-60 for debugging, read around error line 145."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "file_path": types.Schema(
                type=types.Type.STRING,
                description="The relative path to the file to read (e.g., 'main.py', 'src/utils.py')",
            ),
            "start_line": types.Schema(
                type=types.Type.INTEGER,
                description="Optional: Starting line number to read from (1-indexed). If omitted, reads from beginning.",
            ),
            "end_line": types.Schema(
                type=types.Type.INTEGER,
                description="Optional: Ending line number to read to (1-indexed, inclusive). If omitted, reads to end.",
            ),
        },
        required=["file_path"],
    ),
)