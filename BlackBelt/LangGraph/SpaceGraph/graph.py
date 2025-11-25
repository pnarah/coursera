import os
import logging
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain_openai import ChatOpenAI  # ✅ FIXED: Use LangChain's OpenAI wrapper
from langgraph.graph import MessagesState, StateGraph, START
from langgraph.prebuilt import tools_condition, ToolNode
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.types import interrupt, Command

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
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Stock trading tools
@tool
def get_stock_price(symbol: str) -> float:
    '''Return the current price of a stock given the stock symbol'''
    return {"MSFT": 200.3, "AAPL": 100.4, "AMZN": 150.0, "RIL": 87.6}.get(symbol, 0.0)

@tool
def buy_stocks(symbol: str, quantity: int, total_price: float) -> str:
    '''Buy stocks given the stock symbol and quantity'''
    decision = interrupt(f"Approve buying {quantity} {symbol} stocks for ${total_price:.2f}?")

    if decision == "yes":
        return f"You bought {quantity} shares of {symbol} for a total price of {total_price}"
    else:
        return "Buying declined."

# ✅ Define Available Tools (including stock trading tools)
tools = [
    get_iss_location,
    get_astronauts,
    get_weather,
    get_apod,
    get_near_earth_objects,
    get_stock_price,
    buy_stocks
]

# ✅ Use ChatOpenAI (Now Supports `.bind_tools`)gpt-4o gpt-4.1-mini
# llm = ChatOpenAI(model="gpt-4o", api_key=OPENAI_API_KEY)
llm = AzureChatOpenAI(
        azure_endpoint="https://1",
        api_version="2024-10-21",
        api_key=os.getenv("AZURE_API_KEY"),  # Set this in your .env file
        model="gpt-4o",
        default_headers={"x-c-app": "my-app"},
    )

# ✅ Bind Tools to LLM
llm_with_tools = llm.bind_tools(tools, parallel_tool_calls=False)

# ✅ System Message (Updated to include stock trading)
sys_msg = SystemMessage(content="You are a helpful assistant providing space-related information and stock trading services.")

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
    
    try:
        for event in compiled_graph.stream({"messages": [{"role": "user", "content": user_input}]}, config):
            for value in event.values():
                if "messages" in value and value["messages"]:
                    print("Assistant:", value["messages"][-1].content)
                    
        # Check for interrupts (stock purchase approvals)
        state = compiled_graph.get_state(config)
        if state.next and "__interrupt__" in str(state.next):
            # Handle interrupt for stock purchase approval
            decision = input("Enter your decision (yes/no): ")
            compiled_graph.update_state(config, None, as_node="__interrupt__")
            
            # Resume with the decision
            for event in compiled_graph.stream(Command(resume=decision), config):
                for value in event.values():
                    if "messages" in value and value["messages"]:
                        print("Assistant:", value["messages"][-1].content)
                        
    except Exception as e:
        print(f"Error: {str(e)}")
        # Check if it's an interrupt
        try:
            state = compiled_graph.get_state(config)
            if hasattr(state, 'tasks') and state.tasks:
                # This is likely an interrupt
                print("Stock purchase approval needed.")
                decision = input("Approve purchase? (yes/no): ")
                
                # Resume the graph with the decision
                for event in compiled_graph.stream(Command(resume=decision), config):
                    for value in event.values():
                        if "messages" in value and value["messages"]:
                            print("Assistant:", value["messages"][-1].content)
        except Exception as resume_error:
            print(f"Resume error: {str(resume_error)}")

def handle_stock_purchase_interactive():
    """Enhanced interactive handler for stock purchases"""
    config = {"configurable": {"thread_id": "stock_thread"}}
    
    print("🚀 Space & Stock Assistant")
    print("Ask me about space or stock information!")
    print("Examples:")
    print("- Where is the ISS?")
    print("- What's the price of MSFT stock?")
    print("- Buy 10 shares of AAPL")
    print("Type 'quit' to exit.\n")
    
    while True:
        try:
            user_input = input("User: ")
            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break
            
            # Check if this is a stock purchase request
            if "buy" in user_input.lower() and any(stock in user_input.upper() for stock in ["MSFT", "AAPL", "AMZN", "RIL"]):
                # This might trigger an interrupt
                try:
                    state = compiled_graph.invoke(
                        {"messages": [HumanMessage(content=user_input)]}, 
                        config
                    )
                    
                    # Check for interrupt
                    if "__interrupt__" in str(state):
                        print("⚠️  Stock purchase approval required!")
                        decision = input("Approve this purchase? (yes/no): ")
                        
                        # Resume with decision
                        state = compiled_graph.invoke(Command(resume=decision), config)
                        if "messages" in state and state["messages"]:
                            print("Assistant:", state["messages"][-1].content)
                    else:
                        # Normal response
                        if "messages" in state and state["messages"]:
                            print("Assistant:", state["messages"][-1].content)
                            
                except Exception as e:
                    print(f"Error processing stock purchase: {str(e)}")
                    
            else:
                # Regular space or stock price queries
                stream_graph_updates(user_input)
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {str(e)}")
            continue

# ✅ Run the interactive session
if __name__ == "__main__":
    handle_stock_purchase_interactive()