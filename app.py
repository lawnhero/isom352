import streamlit as st
from langchain_community.vectorstores import FAISS
from langchain.globals import set_verbose
from langchain_core.messages import HumanMessage, AIMessage
import traceback

import utils.chains_lcel as chains
from utils.sidebar import sidebar
import utils.llm_models as llms
from utils.utils import load_db
from utils.tools import create_tool_chain
from datetime import datetime

# Constants
MAX_CHAT_HISTORY = 10  # Increased for better context retention
PAGE_TITLE = "🦜 ISOM 352 Virtual TA - Beta 2"
COLLECTION_NAME = "ISOM 352"
MIDTERM_END_DATE = datetime(2024, 10, 13, 23, 59, 59)

@st.cache_resource
def initialize_chains():
    """Initialize all LLM models and chains with caching."""
    try:
        # Load database and setup retriever
        retriever = load_db().as_retriever()
        
        # Setup LLM models
        gpt4o_mini = llms.openai_gpt4o_mini
        gpt4o_mini_json = llms.openai_4o_mini_json
        claude_sonnet = llms.claude_sonnet
        claude_haiku = llms.claude_haiku
        gpt4o = llms.openai_gpt4o
        
        # Create base chains
        chains_dict = {
            'rag': chains.rag_chain(claude_haiku, retriever),
            'explain': chains.explain_chain(gpt4o_mini),
            'exercise': chains.exercise_chain(claude_sonnet),
            'chat': chains.chat_chain(gpt4o_mini),
            'analytics': chains.analytics_chain(claude_sonnet),
            'debug': chains.debug_chain(claude_haiku),
            'midterm': chains.exam_chain(claude_sonnet)
        }
        
        # Create tool chain
        tool_chain = create_tool_chain(gpt4o_mini, chains_dict)
        
        # Return chains dictionary with tool chain
        return tool_chain, chains_dict
    
    except Exception as e:
        st.error(f"Failed to initialize chains: {str(e)}")
        raise e

def setup_session_state():
    """Initialize or reset session state variables."""
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            AIMessage("Hello! I'm your virtual TA. Ask me about the course📚, Python🐍, SQL🛢️ and Analytics📊...")
        ]
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []

def manage_chat_history():
    """Display and manage chat history."""
    # Add clear history button
    if st.sidebar.button("Clear Chat History"):
        st.session_state.chat_history = [
            AIMessage("Hello! I'm your virtual TA. Ask me about the course📚, Python🐍, SQL🛢️ and Analytics📊...")
        ]
        st.session_state.conversation_history = []
        st.rerun()
    
    # Truncate history before displaying if needed
    if len(st.session_state.chat_history) > MAX_CHAT_HISTORY:
        st.session_state.chat_history = st.session_state.chat_history[-MAX_CHAT_HISTORY:]
    
    # Display messages
    for message in st.session_state.chat_history:
        with st.chat_message("Human" if isinstance(message, HumanMessage) else "AI", 
                           avatar="🦜" if isinstance(message, AIMessage) else None):
            st.markdown(message.content)
        
def call_function(name, args, chains_dict):
    """Invoke the appropriate tool based on the name and arguments."""
    if name == "course_information":
        return chains_dict['rag'].stream(args['query'])     # input must be a string rather than a dict for retriever
    if name == "explain_concept":
        return chains_dict['explain'].stream(input=args)
    if name == "generate_exercise":
        return chains_dict['exercise'].stream(input=args)
    if name == "explain_analytics":
        return chains_dict['analytics'].stream(input=args)
    if name == "debug_code":
        return chains_dict['debug'].stream(input=args)
    if name == "general_chat":
        return chains_dict['chat'].stream(input=args)


def main():
    """Main application function with improved error handling and user experience."""
    try:
        # Enable verbose logging and setup page config
        set_verbose(True)
        st.set_page_config(page_title=PAGE_TITLE, page_icon="🔍", layout="wide")
        
        st.header("ISOM 352 Virtual TA - Beta 🔍")
        sidebar()
        
        # Initialize chains with caching
        agent, chain_dict = initialize_chains()
        
        # Initialize session state
        setup_session_state()
        
        # Display chat history
        manage_chat_history()
        
        # Handle user input
        user_query = st.chat_input(
            placeholder="Enter your query here ",
            max_chars=200
        )
        
        if user_query:
            with st.chat_message("Human"):
                st.markdown(user_query)
            
            # Check if in midterm period
            is_midterm = datetime.now() < MIDTERM_END_DATE
            
            with st.spinner("Processing your question..."):
                if is_midterm:
                    response = chain_dict['midterm'].stream(user_query)
                else:
                    # Use tool chain to handle the query with chat history
                    conversation_context = "\n".join([
                        f"{'User' if isinstance(msg, HumanMessage) else 'Assistant'}: {msg.content}"
                        for msg in st.session_state.conversation_history[-3:]  # Last 3 exchanges for context
                    ])
                    
                    tool_call = agent.invoke(
                        f"""Query: {user_query}
                            Previous conversation: {conversation_context}""")
                    print(tool_call.tool_calls)

                    response = call_function(
                        name=tool_call.tool_calls[0]["name"],
                        args=tool_call.tool_calls[0]['args'],
                        chains_dict=chain_dict
                    )
            
            # Display AI response
            with st.chat_message("AI", avatar="🦜"):
                ai_response = st.write_stream(response)
            
            # Update chat history
            st.session_state.chat_history.extend([
                HumanMessage(user_query),
                AIMessage(ai_response)
            ])
            
            # Update conversation history for context
            st.session_state.conversation_history.extend([
                HumanMessage(user_query),
                AIMessage(ai_response)
            ])
            
            # Keep conversation history manageable
            if len(st.session_state.conversation_history) > MAX_CHAT_HISTORY * 2:
                st.session_state.conversation_history = st.session_state.conversation_history[-(MAX_CHAT_HISTORY * 2):]
            
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.error(f"Stack trace: {traceback.format_exc()}")

if __name__ == '__main__':
    main()
