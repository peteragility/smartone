# Testing for Smartone Agentic Use Cases

A simple agent implementation using the strands library.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```python
from strands import Agent, tool
from strands_tools import calculator

# Define your custom tools
@tool
def word_count(text: str) -> int:
    """Count words in text."""
    return len(text.split())

# Create an agent with your tools
agent = Agent(tools=[word_count, calculator])

# Use the agent
response = agent("pls answer the square root of 1764? and how many words are in this question?")
print(response)
```

## Dependencies

- strands
- strands_tools
