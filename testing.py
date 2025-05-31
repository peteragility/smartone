from strands import Agent, tool
from strands_tools import calculator

@tool
def word_count(text: str) -> int:
    """Count words in text.

    This docstring is used by the LLM to understand the tool's purpose.
    """
    return len(text.split())

# define the agent with word_count and calculator tools
agent = Agent(tools=[word_count, calculator])

# use the agent, the question need to leverage multiple tools
response = agent("pls answer the sqaure root of 1764? and how many words are in this question?")
print(response)
