import os
from pathlib import Path
from google.genai import types

def get_files_info(working_directory: str, path: str = ".", recursive: bool = False) -> str:
    """
    Get information about files and directories in the specified path.
    
    Args:
        working_directory: The base working directory
        path: Relative path to list (default: current directory)
        recursive: Whether to list files recursively
    
    Returns:
        String containing file and directory information
    """
    abs_working_dir = os.path.abspath(working_directory)
    abs_path = os.path.abspath(os.path.join(working_directory, path))
    
    # Security check: prevent directory traversal
    if not abs_path.startswith(abs_working_dir):
        return f'Error: Access denied - {path} is outside working directory'
    
    if not os.path.exists(abs_path):
        return f'Error: Path {path} does not exist'
    
    try:
        result = []
        result.append(f"Listing: {path}")
        result.append(f"Absolute path: {abs_path}")
        result.append("-" * 60)
        
        if os.path.isfile(abs_path):
            # Single file info
            stat = os.stat(abs_path)
            result.append(f"Type: File")
            result.append(f"Size: {stat.st_size} bytes")
            result.append(f"Modified: {stat.st_mtime}")
            return "\n".join(result)
        
        # Directory listing
        if recursive:
            result.append("Recursive listing:\n")
            for root, dirs, files in os.walk(abs_path):
                level = root.replace(abs_path, '').count(os.sep)
                indent = '  ' * level
                rel_root = os.path.relpath(root, abs_working_dir)
                result.append(f'{indent}📁 {os.path.basename(root)}/ ({rel_root})')
                
                sub_indent = '  ' * (level + 1)
                for file in sorted(files):
                    file_path = os.path.join(root, file)
                    size = os.path.getsize(file_path)
                    result.append(f'{sub_indent}📄 {file} ({size} bytes)')
        else:
            items = sorted(os.listdir(abs_path))
            dirs = [item for item in items if os.path.isdir(os.path.join(abs_path, item))]
            files = [item for item in items if os.path.isfile(os.path.join(abs_path, item))]
            
            if dirs:
                result.append("\nDirectories:")
                for dir_name in dirs:
                    result.append(f"  📁 {dir_name}/")
            
            if files:
                result.append("\nFiles:")
                for file_name in files:
                    file_path = os.path.join(abs_path, file_name)
                    size = os.path.getsize(file_path)
                    result.append(f"  📄 {file_name} ({size} bytes)")
            
            if not dirs and not files:
                result.append("(empty directory)")
        
        return "\n".join(result)
    
    except PermissionError:
        return f'Error: Permission denied accessing {path}'
    except Exception as e:
        return f'Error listing files: {str(e)}'


# Schema definition for the AI agent
schema_get_files_info = types.FunctionDeclaration(
    name="get_files_info",
    description="List files and directories in a specified path. Can list recursively to see entire directory structure.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "path": types.Schema(
                type=types.Type.STRING,
                description="The relative path to list (e.g., '.', 'src', '../'). Defaults to current directory.",
            ),
            "recursive": types.Schema(
                type=types.Type.BOOLEAN,
                description="Whether to list files recursively through subdirectories (default: false)",
            ),
        },
    ),
)