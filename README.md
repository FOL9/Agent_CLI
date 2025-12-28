# 🤖 SDX Agent v2.0

<div align="center">

```
   ▀▄   ▄▀  
   ▄█▀███▀█▄ 
  █▀███████▀█ 
  █ █▀▀▀▀▀█ █ 
```

**An intelligent CLI agent powered by Google's Gemini 2.5 Flash**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Gemini](https://img.shields.io/badge/AI-Gemini%202.5%20Flash-orange.svg)](https://ai.google.dev/)

[Features](#-features) • [Installation](#-installation) • [Usage](#-usage) • [Architecture](#-architecture) • [API Reference](#-api-reference)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Usage Guide](#-usage)
  - [Interactive Mode](#interactive-mode)
  - [Available Commands](#available-commands)
  - [File Operations](#file-operations)
- [Architecture](#-architecture)
  - [Core Components](#core-components)
  - [System Flow](#system-flow)
- [API Reference](#-api-reference)
- [Configuration](#-configuration)
- [Session Management](#-session-management)
- [Logging System](#-logging-system)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🌟 Overview

**SDX Agent** is a sophisticated command-line AI assistant that combines the power of Google's Gemini 2.5 Flash model with local file system operations. It acts as your personal coding companion, capable of understanding natural language requests and executing complex file operations, code analysis, and script execution.

### What Makes SDX Agent Special?

- 🧠 **AI-Powered Intelligence**: Uses Gemini 2.5 Flash for natural language understanding
- 💻 **File System Integration**: Direct access to read, write, and execute files
- 🎨 **Beautiful UI**: Rich terminal interface with animations and styled output
- 📝 **Session Memory**: Maintains conversation history for context-aware responses
- 🔍 **Debug Monitoring**: Optional API request monitoring for developers
- ⚡ **Fast & Efficient**: Optimized for quick responses and minimal latency

---

## ✨ Features

### Core Capabilities

| Feature | Description |
|---------|-------------|
| 📁 **File Management** | List, read, write, and organize files in your project |
| 🐍 **Code Execution** | Run Python scripts directly from the agent |
| 🤖 **AI Assistance** | Get coding help, explanations, and debugging support |
| 💾 **Session Persistence** | Conversation history saved automatically |
| 📊 **Rich Logging** | Detailed logs with configurable monitoring levels |
| 🎯 **Context Awareness** | Agent remembers previous interactions |
| 🎨 **Animated UI** | NPX-style loading animations and styled panels |
| 🔧 **Extensible** | Easy to add new tools and capabilities |

### Supported Operations

```plaintext
┌─────────────────────┬──────────────────────────────────────────┐
│ Operation           │ Description                              │
├─────────────────────┼──────────────────────────────────────────┤
│ get_files_info      │ List files/directories with filters      │
│ get_file_content    │ Read and analyze file contents           │
│ write_file          │ Create or update files                   │
│ run_python_file     │ Execute Python scripts with arguments    │
└─────────────────────┴──────────────────────────────────────────┘
```

---

## 🚀 Installation

### Prerequisites

- **Python 3.8+** installed on your system
- **Google Gemini API Key** (get it from [Google AI Studio](https://makersuite.google.com/app/apikey))
- **Git** (for cloning the repository)

### Step-by-Step Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/your-username/sdx-agent.git
   cd sdx-agent
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure API Key**
   
   Create a `.env` file in the project root:
   ```bash
   touch .env
   ```
   
   Add your API key:
   ```env
   GEMINI_API_KEY=your_api_key_here
   ```

4. **Verify Installation**
   ```bash
   python main.py
   ```

### Dependencies Overview

| Package | Version | Purpose |
|---------|---------|---------|
| `google-generativeai` | Latest | Google Gemini API client |
| `python-dotenv` | Latest | Environment variable management |
| `rich` | Latest | Terminal UI and formatting |
| `Flask` | Latest | Web framework (for extensions) |
| `gunicorn` | Latest | WSGI HTTP server |
| `Werkzeug` | Latest | WSGI utilities |

Install all dependencies:
```bash
pip install google-generativeai python-dotenv rich Flask gunicorn Werkzeug
```

---

## 🎯 Quick Start

### Launch the Agent

```bash
python main.py
```

### First Commands to Try

```bash
# List files in current directory
→ List all Python files in this directory

# Read a file
→ Show me the contents of main.py

# Create a file
→ Create a new file called hello.py that prints "Hello, World!"

# Run code
→ Execute the hello.py script

# Get help
→ /help
```

---

## 📖 Usage

### Interactive Mode

When you launch SDX Agent, you'll see a welcome screen:

```
┌─ SDX Agent v2.0.0 ────────────────────────────────────────────┐
│                                                                │
│  Welcome back Developer!               Tips for Getting Started│
│                                        • Type naturally         │
│     ▀▄   ▄▀                           • Use --verbose for info │
│     ▄█▀███▀█▄                         • Type /help for commands│
│    █▀███████▀█                                                 │
│    █ █▀▀▀▀▀█ █                        Quick Actions           │
│                                        • /status               │
│  Gemini 2.5 Flash · SDX Agent v2.0    • /monitor_on           │
│  Current working directory /path/     • /clear                │
│                                        • /exit                 │
└────────────────────────────────────────────────────────────────┘
```

### Available Commands

#### Session Management

| Command | Alias | Description |
|---------|-------|-------------|
| `/help` | - | Display all available commands |
| `/status` | - | Show current session information |
| `/history` | - | View recent conversation history |
| `/clear` | - | Clear conversation history |
| `/exit` | `/quit`, `/q` | Exit the agent |

#### Monitoring & Debugging

| Command | Description | Use Case |
|---------|-------------|----------|
| `/monitor_on` | Enable API request monitoring | Debug API calls and responses |
| `/monitor_off` | Disable API request monitoring | Clean output for normal use |
| `--verbose` | Show token usage details | Append to any query for stats |

**Example with verbose flag:**
```bash
→ List all Python files --verbose
```

Output will include:
```
┌─ Token Usage ──────────────────────┐
│ Iteration: 1/20                    │
│ Prompt tokens: 1,234               │
│ Candidate tokens: 567              │
│ Total tokens: 1,801                │
└────────────────────────────────────┘
```

### File Operations

#### Listing Files

```bash
# List all files
→ Show me all files in this directory

# List specific file types
→ List all Python files

# List with details
→ Give me detailed information about all JSON files
```

#### Reading Files

```bash
# Read a single file
→ Read the contents of config.py

# Analyze code
→ Analyze main.py and explain what it does

# Find specific content
→ Find all functions in utils.py
```

#### Writing Files

```bash
# Create new file
→ Create a Python script that calculates fibonacci numbers

# Update existing file
→ Add error handling to the existing database.py file

# Refactor code
→ Refactor the User class in models.py to use dataclasses
```

#### Executing Code

```bash
# Run a script
→ Execute the test.py script

# Run with arguments
→ Run data_processor.py with the argument --input data.csv

# Test and debug
→ Run tests.py and show me any errors
```

---

## 🏗️ Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                        SDX Agent                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   UI Layer   │  │  AI Engine   │  │  File System │    │
│  │              │  │              │  │              │    │
│  │  • Rich UI   │  │  • Gemini    │  │  • Read/Write│    │
│  │  • Spinner   │  │  • Tools     │  │  • Execute   │    │
│  │  • Panels    │  │  • Context   │  │  • List      │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│         │                  │                  │            │
│         └──────────────────┴──────────────────┘            │
│                           │                                │
│  ┌────────────────────────┴────────────────────────┐      │
│  │          Session & Logging Manager              │      │
│  │  • History  • Logs  • State  • Persistence     │      │
│  └─────────────────────────────────────────────────┘      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Component Breakdown

#### 1. **UI Components** (`UI` class)

Handles all user interface rendering:

| Component | Purpose |
|-----------|---------|
| `welcome_screen()` | Display startup screen with tips |
| `prompt()` | Show interactive input prompt |
| `success()` | Display success messages in panels |
| `error()` | Show error messages with styling |
| `info()` | Display informational messages |
| `separator()` | Visual separation between sections |
| `code()` | Syntax-highlighted code display |

#### 2. **AI Agent** (`SDXAgent` class)

Core intelligence and request processing:

```python
class SDXAgent:
    - client: genai.Client          # Google AI client
    - ui: UI                         # UI renderer
    - session: SessionManager        # Session state
    - logger: Logger                 # Logging system
    - max_iterations: int = 20       # Max AI thinking loops
```

**Key Methods:**

| Method | Description |
|--------|-------------|
| `get_tools()` | Returns available function declarations |
| `get_config()` | Configures AI model parameters |
| `process_request()` | Main request processing loop |
| `run_interactive()` | Starts interactive session |

#### 3. **Session Manager** (`SessionManager` class)

Manages conversation state and persistence:

```
sessions/
├── session_20241228_143022.json
├── session_20241228_150145.json
└── session_20241228_163512.json
```

**Session File Structure:**
```json
{
  "timestamp": "2024-12-28T14:30:22.123456",
  "role": "user",
  "content": "List all Python files",
  "metadata": {}
}
```

**Methods:**

| Method | Purpose |
|--------|---------|
| `add_message()` | Add message to history |
| `save_history()` | Persist to disk |
| `load_history()` | Load from disk |
| `get_context()` | Get recent messages for AI |
| `clear_history()` | Reset session |

#### 4. **Logger** (`Logger` class)

Advanced logging with monitoring control:

```
logs/
├── sdx_agent_20241228_143022.log
├── sdx_agent_20241228_150145.log
└── sdx_agent_20241228_163512.log
```

**Log Levels:**

| Level | When Used |
|-------|-----------|
| `INFO` | Normal operations, successful requests |
| `WARNING` | Non-critical issues, max iterations |
| `ERROR` | Failures, exceptions, API errors |
| `DEBUG` | Detailed debugging (when monitoring on) |

**Features:**
- Console logging with Rich formatting
- File logging for all sessions
- Toggle monitoring for verbose output
- External library log control

#### 5. **Thinking Spinner** (`ThinkingSpinner` class)

Animated loading indicator:

```python
# Braille patterns for smooth animation
FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']

# Usage
spinner = ThinkingSpinner()
spinner.start()
# ... do work ...
spinner.stop("Complete!")
```

**Animation Example:**
```
⚙  Processing your request ⠋
⚙  Processing your request ⠙
⚙  Processing your request ⠹
✔ Request complete
```

#### 6. **Command Handler** (`CommandHandler` class)

Processes special commands and shortcuts:

```python
COMMANDS = {
    'help': 'Show help information',
    'history': 'Show chat history',
    'clear': 'Clear chat history',
    'status': 'Show agent status',
    'monitor_on': 'Enable monitoring',
    'monitor_off': 'Disable monitoring',
    'exit': 'Exit the agent'
}
```

### System Flow

```
User Input
    ↓
Command Check → [Special Command?] → Yes → Execute Command
    ↓ No                                           ↓
Parse Input                                    Display Result
    ↓
Start Spinner
    ↓
Send to Gemini API
    ↓
[Function Call Needed?] → Yes → Execute Function
    ↓ No                              ↓
Generate Response                  Return Result
    ↓                                   ↓
Stop Spinner ←────────────────────────┘
    ↓
Display Response
    ↓
Save to Session
```

---

## 🔧 API Reference

### Google Gemini API Integration

#### Model Configuration

```python
config = types.GenerateContentConfig(
    tools=[self.get_tools()],
    system_instruction=SYSTEM_PROMPT,
    temperature=0.7,  # Creativity level (0.0-1.0)
)
```

#### System Prompt

The agent uses a comprehensive system prompt that defines:

- **Identity**: Senior software engineer with 10+ years experience
- **Capabilities**: File operations, code execution, analysis
- **Expertise**: Python, JavaScript, databases, algorithms, DevOps
- **Methodology**: Understand → Investigate → Plan → Implement → Validate → Document

### Available Tools (Functions)

#### 1. `get_files_info`

Lists files and directories in the current working directory.

**Schema:**
```python
{
    "name": "get_files_info",
    "description": "List all files and directories...",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory path"
            }
        }
    }
}
```

**Example Request:**
```bash
→ List all Python files in the current directory
```

**Response:**
```
📁 Current Directory Files:
- main.py (12.3 KB)
- utils.py (5.1 KB)
- config.py (2.8 KB)
```

#### 2. `get_file_content`

Reads and returns the contents of a specified file.

**Schema:**
```python
{
    "name": "get_file_content",
    "description": "Read the contents of a file...",
    "parameters": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file"
            }
        },
        "required": ["file_path"]
    }
}
```

**Example Request:**
```bash
→ Show me the contents of config.py
```

#### 3. `write_file`

Creates a new file or updates an existing file with content.

**Schema:**
```python
{
    "name": "write_file",
    "description": "Write content to a file...",
    "parameters": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path where file should be written"
            },
            "content": {
                "type": "string",
                "description": "Content to write to the file"
            }
        },
        "required": ["file_path", "content"]
    }
}
```

**Example Request:**
```bash
→ Create a file called test.py that prints "Hello World"
```

#### 4. `run_python_file`

Executes a Python script with optional command-line arguments.

**Schema:**
```python
{
    "name": "run_python_file",
    "description": "Execute a Python file...",
    "parameters": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to Python file"
            },
            "args": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Command line arguments"
            }
        },
        "required": ["file_path"]
    }
}
```

**Example Request:**
```bash
→ Run test.py with arguments --verbose --output results.txt
```

### API Response Handling

The agent processes responses in iterations:

```python
for iteration in range(max_iterations):
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=messages,
        config=config
    )
    
    if response.function_calls:
        # Execute requested functions
        for function_call in response.function_calls:
            result = call_function(function_call)
            messages.append(result)
    else:
        # Final response received
        display_response(response.text)
        break
```

**Iteration Limits:**
- Maximum: 20 iterations per request
- Prevents infinite loops
- Warning displayed if limit reached

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Required
GEMINI_API_KEY=your_api_key_here

# Optional
LOG_LEVEL=INFO
MAX_ITERATIONS=20
SESSION_DIR=sessions
LOG_DIR=logs
```

### Theme Customization

Edit `Theme` class in `main.py`:

```python
class Theme:
    ORANGE = "#FF8C42"   # Primary accent
    DIM = "#6B7280"      # Secondary text
    TEXT = "#F9FAFB"     # Main text
    GREEN = "#10B981"    # Success messages
    RED = "#EF4444"      # Error messages
    YELLOW = "#F59E0B"   # Warnings
    CYAN = "#06B6D4"     # Info messages
    PURPLE = "#A78BFA"   # Highlights
    BLUE = "#3B82F6"     # Links/references
```

### AI Model Settings

Adjust in `SDXAgent.get_config()`:

```python
types.GenerateContentConfig(
    temperature=0.7,        # Creativity (0.0-1.0)
    top_p=0.95,            # Nucleus sampling
    top_k=40,              # Top-k sampling
    max_output_tokens=2048 # Response length
)
```

---

## 💾 Session Management

### Session Storage

Sessions are automatically saved to `sessions/` directory:

```
sessions/
├── session_20241228_143022.json  (Current)
├── session_20241228_140115.json  (Previous)
└── session_20241227_183045.json  (Older)
```

### Session File Format

```json
[
  {
    "timestamp": "2024-12-28T14:30:22.123456",
    "role": "user",
    "content": "List all Python files",
    "metadata": {}
  },
  {
    "timestamp": "2024-12-28T14:30:25.789012",
    "role": "assistant",
    "content": "Here are the Python files...",
    "metadata": {
      "tokens_used": 1234,
      "model": "gemini-2.5-flash"
    }
  }
]
```

### Context Window

The agent uses the last **5 messages** as context:

```python
def get_context(self, limit: int = 5) -> List[Dict]:
    return self.history[-limit:]
```

This provides:
- Recent conversation context
- Reduced token usage
- Faster responses
- Better relevance

---

## 📊 Logging System

### Log File Structure

```
logs/
├── sdx_agent_20241228_143022.log
│   ├── [INFO] Session started
│   ├── [INFO] Request processed
│   └── [ERROR] Failed to read file
```

### Log Format

```
2024-12-28 14:30:22,123 - SDXAgent - INFO - Request processed successfully
│         │              │           │      │
│         │              │           │      └─ Message
│         │              │           └─ Level
│         │              └─ Logger name
│         └─ Timestamp
```

### Log Levels

| Level | Color | Use Case |
|-------|-------|----------|
| `DEBUG` | Gray | Detailed debugging info |
| `INFO` | Cyan | Normal operations |
| `WARNING` | Yellow | Non-critical issues |
| `ERROR` | Red | Failures and exceptions |
| `CRITICAL` | Bright Red | System failures |

### Monitoring Mode

Enable detailed API logging:

```bash
→ /monitor_on
```

Shows:
- HTTP requests to Gemini API
- Request/response payloads
- Token usage
- Function call details

Disable for cleaner output:

```bash
→ /monitor_off
```

---

## 🐛 Troubleshooting

### Common Issues

#### 1. API Key Error

**Error:**
```
✗ Configuration Error
Please create a .env file with:
  GEMINI_API_KEY=your_api_key_here
```

**Solution:**
1. Create `.env` file in project root
2. Add your API key: `GEMINI_API_KEY=your_key`
3. Restart the agent

#### 2. Import Errors

**Error:**
```
ModuleNotFoundError: No module named 'google.generativeai'
```

**Solution:**
```bash
pip install -r requirements.txt
```

#### 3. Permission Denied

**Error:**
```
PermissionError: [Errno 13] Permission denied: 'test.py'
```

**Solution:**
```bash
chmod +x test.py  # Unix/Linux/Mac
# or run as administrator on Windows
```

#### 4. Max Iterations Reached

**Warning:**
```
⚠ Max Iterations Reached
Reached maximum iterations (20). Task may require more steps.
```

**Solution:**
- Break complex tasks into smaller steps
- Provide more specific instructions
- Check if the task is too ambiguous

### Debug Mode

Enable verbose logging:

```bash
→ /monitor_on
→ Your request --verbose
```

This shows:
- Token usage per iteration
- Function calls made
- API request/response details
- Execution timing

---

## 🤝 Contributing

We welcome contributions! Here's how to get started:

### Development Setup

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/your-username/sdx-agent.git
   ```
3. Create a feature branch:
   ```bash
   git checkout -b feature/amazing-feature
   ```
4. Make your changes
5. Run tests (if available)
6. Commit your changes:
   ```bash
   git commit -m "Add amazing feature"
   ```
7. Push to your fork:
   ```bash
   git push origin feature/amazing-feature
   ```
8. Open a Pull Request

### Contribution Guidelines

- Follow PEP 8 style guide
- Add docstrings to all functions
- Update README for new features
- Test thoroughly before submitting
- Keep commits atomic and descriptive

### Adding New Tools

To add a new function the AI can call:

1. Create function schema in `func/`:
   ```python
   schema_new_tool = types.FunctionDeclaration(
       name="new_tool",
       description="What this tool does",
       parameters={...}
   )
   ```

2. Implement the function:
   ```python
   def new_tool(params):
       # Implementation
       return result
   ```

3. Register in `call_function.py`:
   ```python
   elif function_name == "new_tool":
       result = new_tool(params)
   ```

4. Add to agent's tools:
   ```python
   def get_tools(self):
       return types.Tool(
           function_declarations=[
               ...,
               schema_new_tool,
           ]
       )
   ```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2024 Mohamed Fahfah

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction...
```

---

## 👨‍💻 Author

**Mohamed Fahfah**

- GitHub: [@your-username](https://github.com/your-username)
- Email: your.email@example.com

---

## 🙏 Acknowledgments

- **Google AI** for the Gemini API
- **Rich** library for beautiful terminal UI
- **Python community** for excellent libraries and tools

---

## 📚 Additional Resources

- [Google Gemini API Documentation](https://ai.google.dev/docs)
- [Rich Library Documentation](https://rich.readthedocs.io/)
- [Python Dotenv Guide](https://pypi.org/project/python-dotenv/)

---

## 🗺️ Roadmap

### Planned Features

- [ ] Multi-language support (JavaScript, Java, C++)
- [ ] Web interface option
- [ ] Plugin system for custom tools
- [ ] Cloud storage integration
- [ ] Team collaboration features
- [ ] Voice input support
- [ ] Code generation templates
- [ ] Integrated testing framework

---

<div align="center">

**Made with ❤️ by Mohamed Fahfah**

⭐ Star this repo if you find it helpful!

</div>
