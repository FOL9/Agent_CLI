# SDX Agent

This project is a command-line interface (CLI) tool that acts as an AI agent. It uses the Google Generative AI API to interact with the user, allowing it to perform a variety of tasks, including:

*   Listing files and directories
*   Reading and writing files
*   Executing Python code

The application is built with Python and features a rich, user-friendly interface powered by the `rich` library.

## How it Works

The SDX Agent is designed with a modular architecture that separates concerns and makes it easy to extend. Here's a high-level overview of the key components:

*   **`main.py`**: The main entry point of the application. It handles user input, orchestrates the AI's response, and manages the interactive session.
*   **AI Agent**: The core of the application, powered by the Google Generative AI API. It interprets user requests, determines the appropriate action, and generates responses.
*   **Function Callbacks**: A set of functions that the AI can call to interact with the local file system and execute code. These functions are located in the `func/` directory and include:
    *   `get_files_info`: Lists files in the current directory.
    *   `get_file_content`: Reads the contents of a file.
    *   `write_file`: Writes content to a file.
    *   `run_python_file`: Executes a Python script.
*   **UI Components**: The user interface is built with the `rich` library, providing a polished and interactive experience. This includes features like styled text, progress spinners, and formatted tables.
*   **Session Management**: The agent maintains a session history, allowing it to keep track of the conversation and use previous interactions as context for future requests.

## Getting Started

To get started with the SDX Agent, you'll need to have Python 3 installed on your system. You'll also need to obtain an API key for the Google Generative AI API.

### Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/your-username/sdx-agent.git
    ```

2.  **Install the dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up your API key:**

    Create a `.env` file in the root of the project and add the following line:

    ```
    GEMINI_API_KEY=your_api_key_here
    ```

### Running the Application

Once you've installed the dependencies and set up your API key, you can run the application with the following command:

```bash
python main.py
```

## Usage

The SDX Agent is designed to be intuitive and easy to use. Simply type your requests in natural language, and the agent will do its best to understand and respond.

For example, you can ask the agent to:

*   "List all the files in the current directory."
*   "Read the contents of `main.py`."
*   "Write a new file called `hello.py` that prints 'Hello, world!'"
*   "Run the `hello.py` script."

### Available Commands

The agent also supports a number of special commands that you can use to manage the session and control the application's behavior:

*   `/help`: Show help information.
*   `/history`: Show chat history.
*   `/clear`: Clear chat history.
*   `/status`: Show agent status.
*   `/monitor_on`: Enable request monitoring (show API calls).
*   `/monitor_off`: Disable request monitoring (hide API calls).
*   `/exit`: Exit the agent.

## Dependencies

The SDX Agent relies on the following Python libraries:

*   `google-generativeai`: The official Python library for the Google Generative AI API.
*   `python-dotenv`: For managing environment variables.
*   `rich`: For creating a rich, interactive user interface.
*   `Flask`: A lightweight web framework for Python.
*   `gunicorn`: A Python WSGI HTTP server for UNIX.
*   `Werkzeug`: A comprehensive WSGI web application library.

You can install all of these dependencies at once by running:

```bash
pip install -r requirements.txt
```

## Developper

This project was created by Mohamed Fahfah.
