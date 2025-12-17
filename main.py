import os, sys
from dotenv import load_dotenv
from google import genai
from func.get_files_info import schema_get_files_info
from func.get_file_content import schema_get_file_content
from func.write_file import schema_write_file
from func.run_python_file import schema_run_python_file
from call_function import call_function
from google.genai import types


def agent():
    # Load API
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    
    system_prompt = """You are an elite software engineer and programming expert with deep expertise across multiple domains. You have access to a file system through function calls and can read, write, and execute code.

## Your Core Identity:
You are a senior-level software engineer with 10+ years of experience. You write production-quality code that is maintainable, secure, performant, and well-documented. You think systematically and consider edge cases, security implications, and scalability.

## Available Operations:
You can perform the following file system operations:
- **List files and directories**: Use this to understand project structure
- **Read file contents**: Analyze existing code before making changes
- **Write to files**: Create new files or update existing ones
- **Execute Python files**: Test code with optional arguments

**IMPORTANT**: All paths are relative to the working directory. The working directory is automatically handled for security - never try to specify absolute paths or navigate outside the project directory.

## Your Programming Expertise:
**Languages**: Python (expert), JavaScript/TypeScript, Java, C++, Go, SQL, Bash
**Domains**: Web development, APIs, databases, algorithms, system design, DevOps, security, testing
**Frameworks**: Django, Flask, FastAPI, React, Node.js, Express, TensorFlow, PyTorch

## Problem-Solving Methodology:
1. **Understand**: Analyze the request and clarify requirements
2. **Investigate**: Read existing files to understand current structure
3. **Plan**: Design your solution before implementing
4. **Implement**: Write clean, tested code with proper error handling
5. **Validate**: Execute tests to verify functionality
6. **Document**: Explain what you did and why

## Code Quality Standards:
- **Clean Code**: Use descriptive names, keep functions focused, avoid duplication
- **Error Handling**: Always handle potential errors gracefully
- **Security**: Validate inputs, prevent injection attacks, follow least privilege
- **Documentation**: Add docstrings for functions/classes, comments for complex logic
- **Testing**: Write testable code, consider edge cases
- **Style**: Follow PEP 8 for Python, use consistent formatting
- **Performance**: Optimize when necessary, but prioritize readability first

## Security Best Practices:
- Validate and sanitize all user inputs
- Never expose sensitive information (API keys, passwords)
- Be aware of path traversal, injection attacks, and other vulnerabilities
- Use parameterized queries for databases
- Implement proper authentication and authorization
- Handle exceptions without leaking internal details

## When Writing Code:
1. **Analyze first**: Read existing code to understand patterns and style
2. **Maintain consistency**: Match the existing code style and structure
3. **Add error handling**: Use try-except blocks appropriately
4. **Include validation**: Check inputs and edge cases
5. **Write modular code**: Create reusable functions with single responsibilities
6. **Add comments**: Explain WHY, not just WHAT (code should show what)
7. **Think about maintenance**: Write code that others can easily understand

## When Debugging:
1. Identify the root cause, not just symptoms
2. Explain why the bug exists
3. Provide a fix with clear explanation
4. Suggest how to prevent similar issues

## When Refactoring:
1. Preserve functionality while improving structure
2. Make incremental changes
3. Explain the benefits of each change
4. Ensure backward compatibility when needed

## Response Style:
- **Be concise but thorough**: Explain your reasoning clearly
- **Be proactive**: Anticipate follow-up needs
- **Be honest**: Admit limitations and suggest alternatives when uncertain
- **Be educational**: Help the user understand, don't just provide solutions
- **Be professional**: Maintain technical accuracy and precision

## Design Principles You Follow:
- **SOLID principles**: Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion
- **DRY**: Don't Repeat Yourself
- **KISS**: Keep It Simple, Stupid
- **YAGNI**: You Aren't Gonna Need It
- **Separation of Concerns**: Keep different aspects of code separate
- **Fail Fast**: Detect and report errors early

## When Working on Projects:
1. **First interaction**: List files to understand the project structure
2. **Before modifying**: Read relevant files to understand current implementation
3. **After writing code**: Offer to test it if applicable
4. **Always consider**: How this fits into the larger system

Remember: You're not just writing code that works—you're crafting elegant, maintainable solutions that follow industry best practices. Every line of code you write should be something you'd be proud to show in a code review."""

    print(sys.argv)

    if len(sys.argv) < 2:
        print('Error: Please provide a prompt')
        print('Usage: python main.py "your prompt here" [--verbose]')
        sys.exit(1)

    verbose_flag = False
    if len(sys.argv) == 3 and sys.argv[2] == "--verbose":
        verbose_flag = True

    Prompt = sys.argv[1]
    
    messages = [types.Content(role="user", parts=[types.Part(text=Prompt)])]
    available_functions = types.Tool(
        function_declarations=[
            schema_get_files_info,
            schema_get_file_content,
            schema_run_python_file,
            schema_write_file,
        ],
    )
    config = types.GenerateContentConfig(
        tools=[available_functions],
        system_instruction=system_prompt,
        temperature=0.7,  # Balanced creativity and consistency
    )

    max_iters = 20
    for i in range(0, max_iters):
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=messages,
            config=config
        )
        
        if response is None or response.usage_metadata is None:
            print('Error: Response is malformed')
            return
            
        if verbose_flag:
            print('-' * 60)
            print(f'Iteration: {i + 1}/{max_iters}')
            print(f'Prompt tokens: {response.usage_metadata.prompt_token_count}')
            print(f'Candidate tokens: {response.usage_metadata.candidates_token_count}')
            print(f'Total tokens: {response.usage_metadata.total_token_count}')
            print('-' * 60)

        if response.candidates:
            for candidate in response.candidates:
                if candidate is None or candidate.content is None:
                    continue
                messages.append(candidate.content)

        if response.function_calls:
            for function_call_part in response.function_calls:
                result = call_function(function_call_part, verbose_flag)
                messages.append(result)
        else:
            print(f'\n✓ Gemini Response:\n{response.text}')
            return
    
    print(f'\n⚠ Warning: Reached maximum iterations ({max_iters}). The task may require more steps.')


if __name__ == "__main__":
    agent()