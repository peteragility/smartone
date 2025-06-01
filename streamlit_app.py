from strands import Agent, tool
from strands_tools import calculator, current_time, generate_image
import streamlit as st
import asyncio
import requests
import threading
from queue import Queue

@tool
def word_count(text: str) -> int:
    """Count words in text."""
    return len(text.split())

# Define the agent with tools
agent = Agent(tools=[word_count, calculator, current_time, generate_image])

# New sample queries (more complicated calculations, only 2)
sample_queries = [
    "What is the result of (1234 * 56) + (789 - 432) / 3, and how many words are in this question?",
    "Calculate (9876 / 12) * (34 + 56) - 123, and count the words in this sentence.",
    "What is the current time in New York?",
    "Generate an image of a cat playing chess."
]

def process_query_in_thread(query, result_queue):
    """Process query in a separate thread and put results in queue."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def process():
        async for event in agent.stream_async(query):
            result_queue.put(event)
        result_queue.put(None)  # Signal completion
    
    try:
        loop.run_until_complete(process())
    finally:
        loop.close()

def main():
    st.set_page_config(page_title="AI Assistant with Tools", layout="wide")
    
    # Custom CSS for the entire app
    st.markdown("""
    <style>
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    .main-header {
        text-align: center;
        margin-bottom: 2rem;
    }
    .main-header h1 {
        color: #1E88E5;
        font-size: 2.5rem !important;
    }
    .main-header p {
        font-size: 1.2rem !important;
        color: #555;
    }
    /* Fix for text wrapping in agent responses */
    .stMarkdown p {
        white-space: normal !important;
        word-wrap: break-word !important;
    }
    /* Ensure proper line breaks */
    .agent-response {
        white-space: normal !important;
        word-wrap: break-word !important;
        line-height: 1.5 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header with improved styling
    st.markdown("""
    <div class="main-header">
        <h1>🤖 AI Assistant with Tools</h1>
        <p>This demo showcases an AI agent that can use tools to answer your questions.
        Try asking questions that involve calculations, word counting, or web searches!</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []  # Full conversation history
    if "processing" not in st.session_state:
        st.session_state.processing = False
    if "result_queue" not in st.session_state:
        st.session_state.result_queue = Queue()
    if "thread" not in st.session_state:
        st.session_state.thread = None
    if "current_response" not in st.session_state:
        st.session_state.current_response = {"events": [], "final": ""}
    
    # Function to handle query submission
    def handle_submit():
        if st.session_state.query and not st.session_state.processing:
            st.session_state.submitted_query = st.session_state.query
            st.session_state.processing = True
    
    # Clear input after processing completes
    if not st.session_state.processing and "submitted_query" in st.session_state:
        if st.session_state.query == st.session_state.submitted_query:
            st.session_state.query = ""
    
    # Sample queries section
    st.subheader("💡 Sample Questions")
    cols = st.columns(2)
    for i, sample in enumerate(sample_queries):
        if cols[i % 2].button(sample, key=f"sample_{i}"):
            st.session_state.query = sample
    
    # Custom CSS for the input area
    st.markdown("""
    <style>
    .stTextInput > div > div > input {
        border-radius: 10px 0 0 10px !important;
        border-right: none !important;
        padding: 15px !important;
        font-size: 16px !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1) !important;
    }
    .ask-button {
        border-radius: 0 10px 10px 0 !important;
        padding: 15px !important;
        font-size: 16px !important;
        font-weight: bold !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1) !important;
        margin-left: -10px !important;
    }
    .input-container {
        display: flex !important;
        margin-bottom: 20px !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Query input with button in same row
    col1, col2 = st.columns([5, 1])
    with col1:
        query = st.text_input("Your Question", key="query", placeholder="Ask me anything...", 
                             label_visibility="collapsed")
    with col2:
        submit = st.button("Ask", type="primary", disabled=st.session_state.processing,
                          key="ask_button", use_container_width=True)
    
    # Display previous messages (latest Q/A at the top)
    for message in reversed(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"], unsafe_allow_html=True)
    
    # Process query when submitted
    if submit and query and not st.session_state.processing:
        # Store the submitted query
        st.session_state.submitted_query = query
        # Add the user message to history (at the beginning)
        st.session_state.messages.insert(0, {"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)
        # Reset current response
        st.session_state.current_response = {"events": [], "final": ""}
        # Start processing in thread
        st.session_state.processing = True
        st.session_state.result_queue = Queue()
        st.session_state.thread = threading.Thread(
            target=process_query_in_thread,
            args=(query, st.session_state.result_queue)
        )
        st.session_state.thread.start()
        st.rerun()
    
    # Check for results from the processing thread
    if st.session_state.processing:
        # Create or get the assistant message container
        with st.chat_message("assistant"):
            response_container = st.container()
        
        # Process any available results
        updated = False
        while not st.session_state.result_queue.empty():
            updated = True
            event = st.session_state.result_queue.get()
            
            if event is None:  # Processing complete
                st.session_state.processing = False
                full_response = _format_current_response()
                # Insert assistant message at the beginning
                if len(st.session_state.messages) == 1:  # Only user message exists
                    st.session_state.messages.insert(1, {"role": "assistant", "content": full_response})
                else:
                    st.session_state.messages[1] = {"role": "assistant", "content": full_response}
                break
            
            # Store events in chronological order
            if event.get("reasoningText"):
                st.session_state.current_response["events"].append({
                    "type": "reasoning",
                    "content": event["reasoningText"]
                })
            
            if event.get("current_tool_use") and event["current_tool_use"].get("name"):
                tool_name = event["current_tool_use"]["name"]
                # Only add if it's not the same as the last tool
                if not st.session_state.current_response["events"] or \
                   not (st.session_state.current_response["events"][-1].get("type") == "tool" and \
                        st.session_state.current_response["events"][-1].get("content") == tool_name):
                    st.session_state.current_response["events"].append({
                        "type": "tool",
                        "content": tool_name
                    })
            
            if event.get("data"):
                st.session_state.current_response["events"].append({
                    "type": "output",
                    "content": event["data"]
                })
            
            if event.get("message") and event["message"].get("role") == "assistant":
                st.session_state.current_response["final"] = event["message"]["content"]
        
        # Display the current state of the response
        if updated or st.session_state.processing:
            for block in _format_current_response():
                if block["type"] == "text":
                    st.markdown(block["content"], unsafe_allow_html=True)
                elif block["type"] == "image":
                    st.image(block["content"])
        
        # If still processing, rerun to check for more results
        if st.session_state.processing:
            st.rerun()

def _format_current_response():
    """Format the current response for display in chronological order, returning a list of output elements (text or image)."""
    response = st.session_state.current_response
    formatted_blocks = []

    output_buffer = []
    image_urls = []
    last_tool = None
    for event in response["events"]:
        if event["type"] == "reasoning":
            formatted_blocks.append({"type": "text", "content": f"🤔 **Reasoning:** {event['content']}"})
        elif event["type"] == "tool":
            last_tool = event["content"]
            formatted_blocks.append({"type": "text", "content": f"🔧 **Using tool:** {event['content']}"})
        elif event["type"] == "output":
            content = event['content']
            if isinstance(content, str):
                content = content.replace("\n", " ")
            # If the last tool is generate_image and content looks like an image URL/path, treat as image
            if last_tool == "generate_image" and isinstance(content, str) and (content.startswith("http://") or content.startswith("https://") or content.endswith(".png") or content.endswith(".jpg") or content.endswith(".jpeg")):
                image_urls.append(content)
            else:
                output_buffer.append(content)

    # Show the current buffer as a single paragraph (streaming style)
    if output_buffer:
        formatted_blocks.append({"type": "text", "content": ' '.join(output_buffer)})
    for img_url in image_urls:
        formatted_blocks.append({"type": "image", "content": img_url})

    # Add final answer if available
    if response["final"]:
        final_answer = response["final"]
        if isinstance(final_answer, str):
            final_answer = final_answer.replace("\n", " ")
        formatted_blocks.append({"type": "text", "content": f"✅ **Final Answer:** {final_answer}"})

    return formatted_blocks

if __name__ == "__main__":
    main()