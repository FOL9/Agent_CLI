import os 
from google.genai import types

schema_get_files_info = types.FunctionDeclaration(
    name="get_files_info",
    description="Lists files in the specified directory along with their sizes, constrained to the working directory.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "directory": types.Schema(
                type=types.Type.STRING,
                description="The directory to list files from, relative to the working directory. If not provided, lists files in the working directory itself.",
            ),
        },
    ),
)

def get_files_info(working_directory :str , directory=".") :
    abs_working_dir = os.path.abspath(working_directory)
    abs_directory = os.path.abspath(os.path.join(working_directory ,  directory) )
    if not abs_directory.startswith(abs_working_dir):
        return f'Error : {directory} Access denied'
    
    final_responce  = ""
    contents = os.listdir(abs_directory)
    for content in contents :
        content_path = os.path.join(abs_directory, content)
        isdir = os.path.isdir(content_path)
        size = os.path.getsize(content_path)
        final_responce += f'- {content:<15} size: {size} bytes  is_dir: {isdir}\n'
    return final_responce 


