"""
Tools and Agent implementation for the Virtual TA system.
"""

from langchain.tools import StructuredTool
from typing import Optional, List
from langchain.schema.language_model import BaseLanguageModel
from pydantic import BaseModel, Field

# Tool argument schemas
class RagArgs(BaseModel):
    query: str = Field(..., description="The query to get course information for")

class ExplainArgs(BaseModel):
    query: str = Field(..., description="The query to explain")
    previous_query: Optional[str] = Field(default="", description="Previous query for context")

class ExerciseArgs(BaseModel):
    query: str = Field(..., description="The query to generate exercise for")
    previous_query: str = Field(default="", description="Previous query for context")
    skill_level: str = Field(default="beginner", description="Student's skill level")
    previous_exercise: str = Field(default="", description="Previous exercise for context")

class AnalyticsArgs(BaseModel):
    query: str = Field(..., description="The query about data analytics")
    chat_history: str = Field(default="", description="Previous chat history for context")

class DebugArgs(BaseModel):
    query: str = Field(..., description="The code or error to debug")
    chat_history: str = Field(default="", description="Previous chat history for context")

class ChatArgs(BaseModel):
    query: str = Field(..., description="The message to respond to")
    chat_history: str = Field(default="", description="Previous chat history for context")

# Tool definitions
def rag_tool(chain):
    """Tool for retrieving course-related information."""
    def _run(args: RagArgs) -> str:
        return chain.invoke(args.query)
    
    return StructuredTool(
        name="course_information",
        description="Use this tool when the query is about course-specific information, instructor, syllabus, or assignments.",
        func=_run,
        args_schema=RagArgs
    )

def explain_tool(chain):
    """Tool for explaining technical concepts."""
    def _run(args: ExplainArgs) -> str:
        return chain.invoke({"query": args.query, "chat_history": args.previous_query})
    
    return StructuredTool(
        name="explain_concept",
        description="Use this tool when the query asks for explanation of Python, SQL, or other concepts.",
        func=_run,
        args_schema=ExplainArgs
    )

def exercise_tool(chain):
    """Tool for generating exercise questions."""
    def _run(args: ExerciseArgs) -> str:
        return chain.invoke({
            "current_query": args.query,
            "previous_query": args.previous_query,
            "skill_level": args.skill_level,
            "previous_exercise": args.previous_exercise
        })
    
    return StructuredTool(
        name="generate_exercise",
        description="Use this tool when the query asks for Python or SQL practice exercises.",
        func=_run,
        args_schema=ExerciseArgs
    )

def analytics_tool(chain):
    """Tool for data analytics explanations."""
    def _run(args: AnalyticsArgs) -> str:
        return chain.invoke({
            "query": args.query,
            "chat_history": args.chat_history
        })
    
    return StructuredTool(
        name="explain_analytics",
        description="Use this tool when the query is about data analysis with pandas, matplotlib, seaborn, or statistics.",
        func=_run,
        args_schema=AnalyticsArgs
    )

def debug_tool(chain):
    """Tool for debugging assistance."""
    def _run(args: DebugArgs) -> str:
        return chain.invoke({
            "query": args.query,
            "chat_history": args.chat_history
        })
    
    return StructuredTool(
        name="debug_code",
        description="Use this tool when the query is about code errors or debugging help.",
        func=_run,
        args_schema=DebugArgs
    )

def chat_tool(chain):
    """Tool for general conversation."""
    def _run(args: ChatArgs) -> str:
        return chain.invoke({
            "query": args.query,
            "chat_history": args.chat_history
        })
    
    return StructuredTool(
        name="general_chat",
        description="Use this tool for general conversation or when no other tools are appropriate.",
        func=_run,
        args_schema=ChatArgs
    )

def create_tool_chain(llm: BaseLanguageModel, chain_dict: dict):
    """Create a tool-enabled LLM chain."""
    tools = [
        rag_tool(chain_dict['rag']),
        explain_tool(chain_dict['explain']),
        exercise_tool(chain_dict['exercise']),
        analytics_tool(chain_dict['analytics']),
        debug_tool(chain_dict['debug']),
        chat_tool(chain_dict['chat'])
    ]
    
    # Bind tools to LLM with system message
    return llm.bind_tools(tools, tool_choice="any")
#     return llm.bind(
#         system_message="""You are a Virtual Teaching Assistant for an undergraduate data analytics course.
# Your role is to help students by choosing the most appropriate tool based on their query.

# The input will be formatted as:
# Query: [user's question]
# Previous conversation: [chat history]

# For each input, analyze:
# 1. Extract the actual query from the "Query:" section
# 2. Use the previous conversation as context when needed
# 3. Choose the most relevant tool based on the query's intent

# When using tools:
# 1. For the query parameter, use ONLY the text after "Query:" (without the "Query:" prefix)
# 2. For tools that accept chat_history or previous_query, use the text after "Previous conversation:"
# 3. For the exercise tool, always use "beginner" as the skill level unless explicitly stated

# ALWAYS use the most appropriate tool for the query. If unsure, use general_chat.
# Remember to extract ONLY the actual query text without the "Query:" prefix when passing to tools."""
#     ).bind_tools(tools)
