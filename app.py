import streamlit as st
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.globals import set_verbose
from langchain_core.messages import HumanMessage, AIMessage

import utils.chains_lcel as chains
from utils.sidebar import sidebar
import utils.llm_models as llms

# Enable verbose logging
set_verbose(True)

# Enable Langchain logging
LANGCHAIN_TRACING_V2="true"
LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"
# LANGCHAIN_API_KEY="<your-api-key>"
LANGCHAIN_PROJECT="streamlit-demo"

# Set the page_title
st.set_page_config(
        page_title="🦜 ISOM 352 Virtual TA - Beta", 
        page_icon="🔍",
        layout="wide")

from utils.utils import load_db
from datetime import datetime

# 1. Load the Vectorised database
db = load_db()

# 2. Function for similarity search
retriever = db.as_retriever()

# 3. Setup LLM and chains
gpt35 = llms.openai_gpt35
claude_sonnet = llms.claude_sonnet
claude_haiku = llms.claude_haiku
gpt4o = llms.openai_gpt4o

# 3a. Setup query router
router_chain = chains.router_chain(claude_sonnet)
# 3b. Setup LLMChain & prompts for RAG answer generation
rag_chain = chains.rag_chain(claude_haiku, retriever)
# 3c. Setup openai_chain for explain concepts
explain_chain = chains.explain_chain(claude_haiku)
# 3d. Setup openai exercise chain
exercise_chain = chains.exercise_chain(claude_sonnet)
# 3e. Setup openai chat chain
chat_chain = chains.chat_chain(gpt35)
# 3f. Setup openai analytics chain
analytics_chain = chains.analytics_chain(claude_haiku)
# 3g. Setup debug chain
debug_chain = chains.debug_chain(gpt35)
# midterm chain
midterm_chain = chains.exam_chain(claude_sonnet)

# 4. generate response based on router choice and new query
def generate_response(query:str, router_choice:str, history:dict):

    if "course" in router_choice:
        # only pass the str as a Runnable parameter
        response = rag_chain.stream(query) 
    
    elif "exercise" in router_choice:
        response = exercise_chain.stream(input={
            'current_query': query, 
            'previous_query': history["previous_query"],
            "skill_level": "beginner" ,
            "previous_exercise": history["previous_response"]} )
    
    elif "explain" in router_choice:
        response = explain_chain.stream(input={'query': query, 
            'previous_query': history['previous_query'],})
        
    elif 'analytics' in router_choice: # invoke to chat model
        response = analytics_chain.stream(input={'query': query, 
            'chat_history': history['previous_response'],})
        
    elif 'debug' in router_choice: # invoke to debug model
        response = debug_chain.stream(input={'query': query, 
            'chat_history': history['previous_response'],})
    
    else: # invoke to chat model
        response = chat_chain.stream(input={'query': query, 
            'chat_history': history['previous_response'],})
    
    return response
        
# 5. Build an app with streamlit
def main():

    st.header("ISOM 352 Virtual TA - Beta 🔍")
    # st.write("Currently support queries on syllabus and coding request.")
    sidebar()
    current_time = datetime.now()
    end_date = datetime(2024, 10, 13, 23, 59, 59)

    if current_time < end_date:
        is_midterm = True
    # Initialize chat history in session state
    if "chat_history" not in st.session_state:
        # initialize chat history
        st.session_state.chat_history = []
        st.session_state.chat_history.append(
            # AIMessage("Hello! I'm your virtual TA. Ask me about the course📚, Python🐍, SQL🛢️ and Analytics📊...")
            AIMessage(f"Hello! The time now is {current_time.strftime('%Y-%m-%d %H:%M')} and midterm will ends at {end_date.strftime('%Y-%m-%d %H:%M')}... Good luck!" )
            )
        # initialize activity history as dict
        st.session_state.history = {}
        st.session_state.history['previous_query'] = ""
        st.session_state.history['previous_classification'] = ""
        st.session_state.history['previous_response'] = ""

    # display the chat history
    for message in st.session_state.chat_history:
        if isinstance(message, HumanMessage):
            with st.chat_message("Human"):
                st.markdown(message.content)
        elif isinstance(message, AIMessage):
            with st.chat_message("AI", avatar="🦜"):
                st.markdown(message.content)

    # truncate chat history to last 5 messages
    max_num_messages = 3
    if len(st.session_state.chat_history) > max_num_messages:
        st.session_state.chat_history = st.session_state.chat_history[-max_num_messages:]


    # get user query as chat input
    user_query = st.chat_input(placeholder="Enter your query here ", 
                           max_chars=200)

    if user_query:
        # display user query
        with st.chat_message("Human"):
            st.markdown(user_query)


        # check the time and compare to 10/13/2024
        if is_midterm:
            response = midterm_chain.stream(user_query,)
        else:
            # first decide course of action with router chain
            choice = router_chain.invoke(input={
                'current_query': user_query, 
                'previous_query': st.session_state.history['previous_query'],
                "previous_classification": st.session_state.history["previous_classification"]})
            
            # define the new query
            if "debug" not in choice.label:
                user_query = choice.query

            print(f"router: {choice.label}, query: {user_query}")
            # with st.spinner("Great question..."):
            # get proper response
            response = generate_response(query=user_query,router_choice=choice.label, 
                                        history=st.session_state.history)
        # generate 
        # with st.spinner():
        with st.chat_message("AI", avatar="🦜"):
            ai_response = st.write_stream(response)
        
        # append the chat history
        st.session_state.chat_history.append(HumanMessage(user_query))
        st.session_state.chat_history.append(AIMessage(ai_response))

        # update history states for customization 
        st.session_state.history['previous_query'] += "Query:" + user_query + "\n"
        if not is_midterm:
            st.session_state.history['previous_classification'] = choice
        st.session_state.history['previous_response'] = ai_response

if __name__ == '__main__':
    main()
