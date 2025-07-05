import streamlit as st
import os
import logging
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState, StateGraph, START
from langgraph.prebuilt import tools_condition, ToolNode
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import MemorySaver

# Load environment variables
load_dotenv()

# Import tools
from tools.neo import get_near_earth_objects
from tools.apod import get_apod
from tools.weather import get_weather
from tools.iss_locator import get_iss_location
from tools.astronauts_in_space import get_astronauts

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ✅ Load API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

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

@st.cache_resource
def initialize_graph():
    """Initialize the LangGraph with caching"""
    
    # Define Available Tools
    tools = [
        get_iss_location,
        get_astronauts,
        get_weather,
        get_apod,
        get_near_earth_objects,
        get_stock_price,
        buy_stocks
    ]

    # Initialize LLM with Azure OpenAI proxy
    llm = ChatOpenAI(model="gpt-4o", api_key=OPENAI_API_KEY)

    # Bind Tools to LLM
    # llm_with_tools = llm.bind_tools(tools, parallel_tool_calls=False)
    llm = AzureChatOpenAI(
        azure_endpoint="https://",
        api_version="2024-10-21",
        api_key=os.getenv("AZURE_API_KEY"),  # Set this in your .env file
        model="gpt-4o",
        default_headers={"x-c-app": "my-app"},
    )

    # System Message
    sys_msg = SystemMessage(content="You are a helpful assistant providing space-related information and stock trading services.")

    # Define Assistant Node
    def assistant(state: MessagesState):
        return {"messages": [llm.invoke([sys_msg] + state["messages"])]}

    # Build the LangGraph
    builder = StateGraph(MessagesState)

    # Add Nodes
    builder.add_node("assistant", assistant)
    builder.add_node("tools", ToolNode(tools))

    # Define Edges
    builder.add_edge(START, "assistant")
    builder.add_conditional_edges(
        "assistant",
        tools_condition,
    )
    builder.add_edge("tools", "assistant")

    # Compile the Graph
    memory = MemorySaver()
    compiled_graph = builder.compile(checkpointer=memory)
    
    return compiled_graph

def main():
    st.set_page_config(
        page_title="🚀 Space & Stock Assistant",
        page_icon="🌌",
        layout="wide"
    )
    
    st.title("🚀 Space & Stock Assistant")
    st.write("Ask me about space information and stock trading! I provide ISS location, astronauts, weather, astronomy pictures, near-Earth objects, stock prices, and stock purchases with approval.")

    # Initialize the graph
    if "graph" not in st.session_state:
        with st.spinner("Initializing Graph..."):
            st.session_state.graph = initialize_graph()
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = "streamlit_thread"
    
    if "pending_approval" not in st.session_state:
        st.session_state.pending_approval = None
    
    if "approval_details" not in st.session_state:
        st.session_state.approval_details = None

    # Sidebar
    with st.sidebar:
        st.header("🛠️ Available Tools")
        
        # Space Tools
        st.subheader("🌌 Space Tools")
        space_tools = {
            "🛰️ ISS Location": "Get current International Space Station location",
            "👨‍🚀 Astronauts": "Find out who's currently in space",
            "🌦️ Weather": "Get weather information for any location",
            "🌌 APOD": "NASA's Astronomy Picture of the Day",
            "☄️ Near Earth Objects": "Information about asteroids and comets"
        }
        
        for tool, description in space_tools.items():
            st.write(f"**{tool}**")
            st.write(f"_{description}_")
            st.write("---")
        
        # Stock Tools
        st.subheader("📈 Stock Tools")
        st.write("**💰 Stock Prices**: Get current stock prices")
        st.write("**🛒 Buy Stocks**: Purchase stocks with approval process")
        st.write("---")
        
        # Available Stocks
        st.subheader("📊 Available Stocks")
        stocks = {"MSFT": 200.3, "AAPL": 100.4, "AMZN": 150.0, "RIL": 87.6}
        for symbol, price in stocks.items():
            st.write(f"**{symbol}**: ${price}")
        
        st.header("💡 Example Questions")
        examples = [
            "Where is the ISS right now?",
            "Who are the astronauts in space?",
            "What's the weather in Tokyo?",
            "Show me today's astronomy picture",
            "What's the price of MSFT stock?",
            "Buy 10 shares of AAPL",
            "Any asteroids approaching Earth?"
        ]
        
        for example in examples:
            if st.button(example, key=f"ex_{example}"):
                st.session_state.messages.append({"role": "user", "content": example})
                st.rerun()
        
        st.header("🔧 Controls")
        if st.button("🗑️ Clear Chat"):
            st.session_state.messages = []
            st.session_state.pending_approval = None
            st.session_state.approval_details = None
            st.rerun()

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
    # Handle pending stock purchase approval
    if st.session_state.pending_approval:
        st.warning("⚠️ Stock Purchase Approval Required")
        st.info(st.session_state.approval_details)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Approve Purchase", key="approve_btn"):
                config = {"configurable": {"thread_id": st.session_state.thread_id}}
                try:
                    # Resume with approval
                    resume_events = list(st.session_state.graph.stream(
                        Command(resume="yes"), 
                        config
                    ))
                    
                    for event in resume_events:
                        for value in event.values():
                            if "messages" in value and value["messages"]:
                                latest_message = value["messages"][-1]
                                if hasattr(latest_message, 'content') and latest_message.content:
                                    st.session_state.messages.append({
                                        "role": "assistant", 
                                        "content": latest_message.content
                                    })
                    
                    st.session_state.pending_approval = None
                    st.session_state.approval_details = None
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error processing approval: {str(e)}")
        
        with col2:
            if st.button("❌ Decline Purchase", key="decline_btn"):
                config = {"configurable": {"thread_id": st.session_state.thread_id}}
                try:
                    # Resume with decline
                    resume_events = list(st.session_state.graph.stream(
                        Command(resume="no"), 
                        config
                    ))
                    
                    for event in resume_events:
                        for value in event.values():
                            if "messages" in value and value["messages"]:
                                latest_message = value["messages"][-1]
                                if hasattr(latest_message, 'content') and latest_message.content:
                                    st.session_state.messages.append({
                                        "role": "assistant", 
                                        "content": latest_message.content
                                    })
                    
                    st.session_state.pending_approval = None
                    st.session_state.approval_details = None
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error processing decline: {str(e)}")



    # Chat input
    if prompt := st.chat_input("Ask me about space or stocks..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Process with graph
        with st.chat_message("assistant"):
            with st.spinner("Processing..."):
                config = {"configurable": {"thread_id": st.session_state.thread_id}}
                
                try:
                    # Use streaming to handle tool calls properly
                    events = list(st.session_state.graph.stream(
                        {"messages": [HumanMessage(content=prompt)]}, 
                        config
                    ))
                    
                    # Process events
                    response_content = ""
                    for event in events:
                        for value in event.values():
                            if "messages" in value and value["messages"]:
                                latest_message = value["messages"][-1]
                                if hasattr(latest_message, 'content') and latest_message.content:
                                    response_content = latest_message.content
                    
                    # Check if graph is interrupted (waiting for approval)
                    state = st.session_state.graph.get_state(config)
                    if state.next:
                        st.session_state.pending_approval = True
                        st.session_state.approval_details = f"Stock purchase approval needed for: {prompt}"
                        st.rerun()
                    else:
                        # Display response
                        if response_content:
                            st.markdown(response_content)
                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": response_content
                            })
                        else:
                            st.markdown("I processed your request.")
                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": "I processed your request."
                            })
                
                except Exception as e:
                    # Check if it's an interrupt
                    try:
                        state = st.session_state.graph.get_state(config)
                        if state.next:
                            st.session_state.pending_approval = True
                            st.session_state.approval_details = f"Stock purchase approval needed for: {prompt}"
                            st.rerun()
                        else:
                            error_msg = f"Sorry, I encountered an error: {str(e)}"
                            st.error(error_msg)
                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": error_msg
                            })
                    except Exception as state_error:
                        error_msg = f"Sorry, I encountered an error: {str(e)}"
                        st.error(error_msg)
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": error_msg
                        })

    # Graph visualization
    with st.expander("🔍 View Graph Structure"):
        if st.button("Generate Graph Visualization"):
            try:
                graph_image = st.session_state.graph.get_graph().draw_mermaid_png()
                st.image(graph_image, caption="Graph Structure")
            except Exception as e:
                st.warning(f"Could not generate graph visualization: {str(e)}")
                st.info("Install graphviz for visualization: `pip install graphviz`")

if __name__ == "__main__":
    main()