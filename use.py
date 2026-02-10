from flask import Flask, render_template_string, send_file, request, abort
import os
import zipfile
from pathlib import Path
import io

app = Flask(__name__)

# Set the root directory to browse (change this to your desired path)
ROOT_DIR = os.path.expanduser("~")  # Start from home directory

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Directory Browser</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body class="bg-gray-50 min-h-screen">
    <div class="container mx-auto px-4 py-8 max-w-6xl">
        <div class="bg-white rounded-lg shadow-lg overflow-hidden">
            <!-- Header -->
            <div class="bg-gradient-to-r from-blue-600 to-blue-700 text-white p-6">
                <h1 class="text-3xl font-bold mb-2">
                    <i class="fas fa-folder-open mr-3"></i>Directory Browser
                </h1>
                <p class="text-blue-100">Browse and download folders from your system</p>
            </div>

            <!-- Breadcrumb Navigation -->
            <div class="bg-gray-100 px-6 py-4 border-b">
                <div class="flex items-center space-x-2 text-sm">
                    <i class="fas fa-home text-gray-600"></i>
                    {% set parts = current_path.split('/') %}
                    {% for i in range(parts|length) %}
                        {% if i > 0 %}
                            <span class="text-gray-400">/</span>
                            <a href="/?path={{ '/'.join(parts[:i+1]) }}" 
                               class="text-blue-600 hover:text-blue-800 hover:underline">
                                {{ parts[i] or 'root' }}
                            </a>
                        {% endif %}
                    {% endfor %}
                </div>
            </div>

            <!-- Directory Listing -->
            <div class="p-6">
                {% if parent_path %}
                <a href="/?path={{ parent_path }}" 
                   class="flex items-center p-4 mb-2 bg-gray-50 hover:bg-gray-100 rounded-lg transition">
                    <i class="fas fa-arrow-left text-gray-600 mr-3"></i>
                    <span class="text-gray-700 font-medium">Go Up</span>
                </a>
                {% endif %}

                <div class="space-y-2">
                    {% for item in items %}
                    <div class="flex items-center justify-between p-4 bg-white border border-gray-200 rounded-lg hover:border-blue-300 hover:shadow-md transition">
                        <div class="flex items-center flex-1">
                            {% if item.is_dir %}
                                <i class="fas fa-folder text-yellow-500 text-xl mr-4"></i>
                                <a href="/?path={{ item.path }}" 
                                   class="text-gray-800 hover:text-blue-600 font-medium flex-1">
                                    {{ item.name }}
                                </a>
                            {% else %}
                                <i class="fas fa-file text-gray-400 text-xl mr-4"></i>
                                <span class="text-gray-700 flex-1">{{ item.name }}</span>
                            {% endif %}
                        </div>
                        
                        <div class="flex items-center space-x-4">
                            <span class="text-sm text-gray-500">{{ item.size }}</span>
                            {% if item.is_dir %}
                                <a href="/download?path={{ item.path }}" 
                                   class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition flex items-center">
                                    <i class="fas fa-download mr-2"></i>
                                    Download
                                </a>
                            {% endif %}
                        </div>
                    </div>
                    {% endfor %}
                </div>

                {% if not items %}
                <div class="text-center py-12 text-gray-500">
                    <i class="fas fa-inbox text-6xl mb-4"></i>
                    <p class="text-lg">This directory is empty</p>
                </div>
                {% endif %}
            </div>
        </div>
    </div>
</body>
</html>
"""

def get_size_format(size_bytes):
    """Convert bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"

def zipdir(path, ziph):
    """Zip directory recursively"""
    for root, dirs, files in os.walk(path):
        for file in files:
            file_path = os.path.join(root, file)
            arcname = os.path.relpath(file_path, os.path.dirname(path))
            try:
                ziph.write(file_path, arcname)
            except:
                pass  # Skip files that can't be read

@app.route('/')
def index():
    path = request.args.get('path', ROOT_DIR)
    
    # Security: prevent directory traversal
    path = os.path.abspath(path)
    if not path.startswith(os.path.abspath(ROOT_DIR)):
        abort(403)
    
    if not os.path.exists(path):
        abort(404)
    
    items = []
    try:
        for entry in sorted(os.listdir(path)):
            full_path = os.path.join(path, entry)
            try:
                is_dir = os.path.isdir(full_path)
                size = 0 if is_dir else os.path.getsize(full_path)
                items.append({
                    'name': entry,
                    'path': full_path,
                    'is_dir': is_dir,
                    'size': get_size_format(size) if not is_dir else '-'
                })
            except:
                continue  # Skip items we can't access
    except PermissionError:
        abort(403)
    
    # Separate directories and files, then sort
    dirs = [item for item in items if item['is_dir']]
    files = [item for item in items if not item['is_dir']]
    items = dirs + files
    
    parent_path = os.path.dirname(path) if path != ROOT_DIR else None
    
    return render_template_string(
        HTML_TEMPLATE,
        items=items,
        current_path=path,
        parent_path=parent_path
    )

@app.route('/download')
def download():
    path = request.args.get('path')
    
    if not path:
        abort(400)
    
    # Security: prevent directory traversal
    path = os.path.abspath(path)
    if not path.startswith(os.path.abspath(ROOT_DIR)):
        abort(403)
    
    if not os.path.exists(path) or not os.path.isdir(path):
        abort(404)
    
    # Create ZIP file in memory
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipdir(path, zipf)
    
    memory_file.seek(0)
    folder_name = os.path.basename(path)
    
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'{folder_name}.zip'
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
