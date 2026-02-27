import os
import subprocess 
from google.genai import types

def run_python_file(working_directory , file_path: str , args=[]) : 
    abs_working_dir = os.path.abspath(working_directory)
    abs_file_path = os.path.abspath(os.path.join(working_directory ,  file_path) )
    if not abs_file_path.startswith(abs_working_dir):
        return f'Error : {file_path} Access denied'
    if not os.path.isfile(abs_file_path) : 
        return f'Error : file {file_path} not found '
    if not file_path.endswith('.py') :
        return f'Error : {file_path} is not python file '
    try :
        final_args = ['python3' , file_path ]
        final_args.extend(args) 
        output = subprocess.run(
            final_args,
            timeout=30 ,
            capture_output=True,
            cwd=abs_working_dir
            )
        final_string = f'''
        STDOUT : {output.stdout}
        STDERR : {output.stderr}
        '''
        if output.stdout == "" and output.stderr == "": 
            final_string = "No output produced "
        if output.returncode != 0:
            final_string += f'process_exited with the code {output.returncode}'
        return final_string
    except Exception as e:
        return f'Error : excuting python file  {file_path}  '        

schema_run_python_file = types.FunctionDeclaration(
    name="run_python_file",
    description="runs a python file with python3 interpreter. accepts additional cli args as an onpptional array.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "file_path": types.Schema(
                type=types.Type.STRING,
                description="the file to run  , relative to the working directory.",
            ),
            "args": types.Schema(
                type=types.Type.ARRAY,    
                description="An optional array of strings to be used as the CLI args for the python file .",
                items=types.Schema(
                    type=types.Type.STRING,        
                ),
                
            ),
        },
    ),
)