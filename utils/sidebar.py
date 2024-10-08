import streamlit as st
import os

def sidebar():
    with st.sidebar:
        st.markdown("# Disclaimer")
        st.markdown(
            '''📖 Virtual TA is a work in progress. It is designed to assist students with their queries. Please make sure DO NOT include any personal information in your queries. '''
        )
        st.markdown("Made by Dr.Wenjun Gu (wenjun.gu@emory.edu)")
        st.markdown("---")
        st.markdown(
            "## Example use cases\n"
            "1. What's the TAs office hours?\n" 
            "2. Compare `list` and `dict` in Python\n"
            "3. Give me 3 practice questions on functions in Python\n"
            "4. How to fix the error in my code? \n"
            "5. How to implement loops with `dict`? \n"
        )
        # st.markdown("---")
        st.markdown(
            "## General advice\n"
            "1. Provide detailed context.\n" 
            "2. Try your questions in different ways.\n"
            "3. Query about specific task.\n"
        )
        st.markdown("---")
        # st.markdown("# About")
        # st.markdown(
        #     '''📖 Virtual TA allows you to ask questions about course, 
        #     lecture contents and assignments. It also helps you to write Python codes and SQL queries.
        #     And generate practice exercises for you to practice coding skills.'''
        # )
        # st.markdown(
        #     "This tool is a work in progress. "
        # )
        # st.markdown("Made by Dr.Wenjun Gu (wenjun.gu@emory.edu)")
       

        # api_key_input = st.text_input(
        #     "OpenAI API Key",
        #     type="password",
        #     placeholder="Paste your OpenAI API key here (sk-...)",
        #     help="You can get your API key from https://platform.openai.com/account/api-keys.",  # noqa: E501
        #     value=os.environ.get("OPENAI_API_KEY", None)
        #     or st.session_state.get("OPENAI_API_KEY", ""),
        # )

        # user_name = st.text_input(
        #     "Enter your name ",
        #     # type="password",
        #     placeholder="Your prefered name here...",
        #     help="This information will be deleted after each session",  # noqa: E501
        #     value='ISOM 352 Coder',
        # )

        # st.session_state["user_name"] = user_name

#         st.markdown("---")


#         st.markdown(
#         """
# # FAQ
# ## Best practice for interacting with virtual TA?
# Your query should provide as much information as possible to help identify the correct knowledge.  
# """
#         )
