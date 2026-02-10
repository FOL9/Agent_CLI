import os
from google.genai import types

def get_file_content(working_directory: str, file_path: str) -> str:
    """
    Read and return the contents of a file.
    
    Args:
        working_directory: The base working directory
        file_path: Relative path to the file to read
    
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
            content = f.read()
        
        # Add file info header
        size = os.path.getsize(abs_file_path)
        header = f"File: {file_path}\nSize: {size} bytes\n{'-' * 60}\n"
        
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
    description="Read and return the complete contents of a text file. Essential for understanding existing code before making changes.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "file_path": types.Schema(
                type=types.Type.STRING,
                description="The relative path to the file to read (e.g., 'main.py', 'src/utils.py')",
            ),
        },
        required=["file_path"],
    ),
)