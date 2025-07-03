import os
import logging
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI  # ✅ FIXED: Use LangChain's OpenAI wrapper
from langgraph.graph import MessagesState, StateGraph, START
from langgraph.prebuilt import tools_condition, ToolNode
from langchain_core.messages import HumanMessage, SystemMessage

# ✅ Load environment variables from .env file
load_dotenv()

# Tools (Assume they are implemented elsewhere)
from tools.neo import get_near_earth_objects
from tools.apod import get_apod
from tools.weather import get_weather
from tools.iss_locator import get_iss_location
from tools.astronauts_in_space import get_astronauts

# ✅ Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ✅ Load API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ✅ Define Available Tools
tools = [
    get_iss_location,
    get_astronauts,
    get_weather,
    get_apod,
    get_near_earth_objects
]

# ✅ Use ChatOpenAI (Now Supports `.bind_tools`)gpt-4o gpt-4.1-mini
llm = ChatOpenAI(model="gpt-4o", api_key=OPENAI_API_KEY)

# ✅ Bind Tools to LLM
llm_with_tools = llm.bind_tools(tools, parallel_tool_calls=False)

# ✅ System Message
sys_msg = SystemMessage(content="You are a helpful assistant providing space-related information.")

# ✅ Define Assistant Node (Now Matches LangGraph Docs)
def assistant(state: MessagesState):
    return {"messages": [llm_with_tools.invoke([sys_msg] + state["messages"])]}

# ✅ Build the LangGraph
builder = StateGraph(MessagesState)

# ✅ Add Nodes
builder.add_node("assistant", assistant)
builder.add_node("tools", ToolNode(tools))

# ✅ Define Edges (Matches Docs)
builder.add_edge(START, "assistant")
builder.add_conditional_edges(
    "assistant",
    tools_condition,  # Routes to "tools" if tools are needed, else to END
)


builder.add_edge("tools", "assistant")  # ✅ Tools always return to assistant




# ✅ Compile the Graph
# compiled_graph = builder.compile()
from langgraph.checkpoint.memory import MemorySaver
memory = MemorySaver()

compiled_graph = builder.compile(checkpointer=memory)

# ✅ Visualize the Graph 
# from IPython.display import Image, display

# try:
#     display(Image(compiled_graph.get_graph().draw_mermaid_png()))
# except Exception:
#     # This requires some extra dependencies and is optional
#     pass


def stream_graph_updates(user_input: str):
    config = {"configurable": {"thread_id": "1"}}
    for event in compiled_graph.stream({"messages": [{"role": "user", "content": user_input}]}, config,):
        for value in event.values():
            print("Assistant:", value["messages"][-1].content)

while True:
    try:
        user_input = input("User: ")
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break

        stream_graph_updates(user_input)
    except:
        # fallback if input() is not available
        user_input = "What do you know about LangGraph?"
        print("User: " + user_input)
        stream_graph_updates(user_input)
        break