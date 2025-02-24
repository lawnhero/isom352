import streamlit as st
from langchain_community.vectorstores import FAISS
from langchain.globals import set_verbose
from langchain_core.messages import HumanMessage, AIMessage

import utils.chains_lcel as chains
from utils.sidebar import sidebar
import utils.llm_models as llms

import langchain
langchain.debug = False
# Enable verbose logging
# set_verbose(True)

# Set the page_title
st.set_page_config(
        page_title="🦜 ISOM 352 Virtual TA - Beta 2", 
        page_icon="🔍",
        layout="wide")

from utils.utils import load_db, query_db_connection, process_and_store_query
from datetime import datetime

# 1. Load the Vectorised database
retriever = load_db().as_retriever()

# 2. MongoDB Atlas connection
mongo_db = query_db_connection()
collection = mongo_db['ISOM 352']

# 3. Setup LLM and chains
gpt4o_mini = llms.openai_gpt4o_mini
gpt4o_mini_json = llms.openai_4o_mini_json
claude_sonnet = llms.claude_sonnet
claude_haiku = llms.claude_haiku
gpt4o = llms.openai_gpt4o

# 3a. Setup query router
router_chain = chains.router_chain(gpt4o_mini_json) 
# 3b. Setup LLMChain & prompts for RAG answer generation
rag_chain = chains.rag_chain(claude_sonnet, retriever)
# 3c. Setup openai_chain for explain concepts
explain_chain = chains.explain_chain(gpt4o)
# 3d. Setup openai exercise chain
exercise_chain = chains.exercise_chain(claude_sonnet)
# 3e. Setup openai chat chain
chat_chain = chains.chat_chain(gpt4o_mini)
# 3f. Setup openai analytics chain
analytics_chain = chains.analytics_chain(claude_sonnet)
# 3g. Setup debug chain
debug_chain = chains.debug_chain(claude_haiku)
# midterm chain
midterm_chain = chains.exam_chain(claude_sonnet)

# 4. generate response based on router choice and new query
def generate_response(query:str, router_choice:str, history:dict):

    if "course" in router_choice:
        # only pass the str as a Runnable parameter
        response = rag_chain.stream(input={
            'query': query,
            "chat_history": [history['previous_response']],}) 
    
    elif "exercise" in router_choice:
        response = exercise_chain.stream(input={
            'query': query, 
            'chat_history': [
                history['previous_query'],
                history['previous_response']]} )
    
    elif "explain" in router_choice:
        response = explain_chain.stream(input={'query': query, 
            'chat_history': [history['previous_response']],})
        
    elif 'analytics' in router_choice: # invoke to chat model
        response = analytics_chain.stream(input={'query': query, 
            'chat_history': [history['previous_response']],})
        
    elif 'debug' in router_choice: # invoke to debug model
        response = debug_chain.stream(input={'query': query, 
            'chat_history': [history['previous_response']],})
    
    else: # invoke to chat model
        response = chat_chain.stream(input={'query': query, 
            'chat_history': st.session_state.chat_history,})
    
    return response
        
# 5. Build an app with streamlit
def main():

    st.header("ISOM 352 Virtual TA - Beta 🔍")
    # st.write("Currently support queries on syllabus and coding request.")
    sidebar()
    current_time = datetime.now()
    end_date = datetime(2025, 2, 22, 10, 00, 00)

    if current_time < end_date:
        is_midterm = True
    # Initialize chat history in session state
    if "chat_history" not in st.session_state:
        # initialize chat history for display only
        st.session_state.chat_history = []
        st.session_state.chat_history.append(
            # AIMessage("Hello! I'm your virtual TA. Ask me about the course📚, Python🐍, SQL🛢️ and Analytics📊...")
            AIMessage(f"Hello! The time now is {current_time.strftime('%Y-%m-%d %H:%M')} and midterm will ends at {end_date.strftime('%Y-%m-%d %H:%M')}... Good luck!" )
            )
        
        # initialize activity history to feed into chains as history context
        st.session_state.history = {}
        st.session_state.history['previous_query'] = ""
        st.session_state.history['previous_classification'] = ""
        st.session_state.history['previous_response'] = ""

    # display the chat history
    for message in st.session_state.chat_history:
        if isinstance(message, HumanMessage):
            st.chat_message("Human").markdown(message.content)
        elif isinstance(message, AIMessage):
            st.chat_message("AI", avatar="🦜").markdown(message.content)

    # truncate chat history to last 5 messages
    max_num_messages = 5
    if len(st.session_state.chat_history) > max_num_messages:
        st.session_state.chat_history = st.session_state.chat_history[-max_num_messages:]


    # get user query as chat input
    user_query = st.chat_input(placeholder="Enter your query here ", 
                           max_chars=200)

    if user_query:
        # display user query
        with st.chat_message("Human"):
            st.markdown(user_query)
        
        st.session_state.chat_history.append(HumanMessage(user_query))

        # check if midterm time period and set is_midterm
        # is_midterm = False
        # check the time and compare to 10/13/2024
        if is_midterm:
            response = midterm_chain.stream(user_query,)
        else:
            # first decide course of action with router chain
            choice = router_chain.invoke(input={
                'current_query': user_query, 
                'previous_query': st.session_state.history['previous_query'],
                "previous_classification": st.session_state.history["previous_classification"]})
            
            # store data in MongoDB
            process_and_store_query(collection, query=user_query, label=choice.label)

            # update the new query except for debug mode
            if "debug" not in choice.label:
                user_query = choice.query

            print(f"router: {choice.label}, query: {user_query}")
            # with st.spinner("Great question..."):
            # get proper response
            response = generate_response(query=user_query,
                                         router_choice=choice.label, 
                                        history=st.session_state.history)
        
        with st.chat_message("AI", avatar="🦜"):
            ai_response = st.write_stream(response)
        
        # append the chat history
        
        st.session_state.chat_history.append(AIMessage(ai_response))

        # update history states for customization 
        # st.session_state.history['previous_query'] += "Query:" + user_query + "\n"
        st.session_state.history['previous_query'] = HumanMessage(user_query)
        if not is_midterm:
            st.session_state.history['previous_classification'] = choice
        st.session_state.history['previous_response'] = AIMessage(ai_response)

if __name__ == '__main__':
    main()
