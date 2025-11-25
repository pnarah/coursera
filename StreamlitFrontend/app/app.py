import os
import streamlit as st
from dotenv import load_dotenv
load_dotenv()

from langchain_openai import AzureChatOpenAI
from langchain.chat_models import init_chat_model
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command
from langchain_core.messages import HumanMessage, AIMessage

class State(TypedDict):
    messages: Annotated[list, add_messages]

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

# Initialize the graph
@st.cache_resource
def initialize_graph():
    tools = [get_stock_price, buy_stocks]
    # llm = init_chat_model("google_genai:gemini-2.0-flash")
    # llm = init_chat_model("openai:gpt-4.1-mini")
    # Initialize LLM using Azure OpenAI proxy
    llm = AzureChatOpenAI(
        azure_endpoint="https://xxx/v1",
        api_version="2024-10-21",
        api_key=os.getenv("AZURE_API_KEY"),  # Set this in your .env file
        model="gpt-4o",
        default_headers={"app": "my-app"},
    )

    llm_with_tools = llm.bind_tools(tools)

    def chatbot_node(state: State):
        msg = llm_with_tools.invoke(state["messages"])
        return {"messages": [msg]}

    memory = MemorySaver()
    builder = StateGraph(State)
    builder.add_node("chatbot", chatbot_node)
    builder.add_node("tools", ToolNode(tools))
    builder.add_edge(START, "chatbot")
    builder.add_conditional_edges("chatbot", tools_condition)
    builder.add_edge("tools", "chatbot")
    builder.add_edge("chatbot", END)
    
    return builder.compile(checkpointer=memory)

def main():
    st.title("🤖 Stock Trading Assistant with Human-in-the-Loop")
    st.write("Ask about stock prices and approve/decline stock purchases!")

    # Initialize session state
    if "graph" not in st.session_state:
        st.session_state.graph = initialize_graph()
    
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = "streamlit_thread"
    
    if "conversation" not in st.session_state:
        st.session_state.conversation = []
    
    if "pending_approval" not in st.session_state:
        st.session_state.pending_approval = None
    
    if "approval_state" not in st.session_state:
        st.session_state.approval_state = None

    # Display conversation history
    if st.session_state.conversation:
        st.subheader("💬 Conversation History")
        for msg in st.session_state.conversation:
            if msg["role"] == "user":
                st.chat_message("user").write(msg["content"])
            else:
                st.chat_message("assistant").write(msg["content"])

    # Handle pending approval
    if st.session_state.pending_approval:
        st.warning("⚠️ Approval Required")
        st.write(st.session_state.pending_approval)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Approve", key="approve"):
                # Resume with approval
                config = {"configurable": {"thread_id": st.session_state.thread_id}}
                state = st.session_state.graph.invoke(Command(resume="yes"), config=config)
                
                # Add response to conversation
                response = state["messages"][-1].content
                st.session_state.conversation.append({"role": "assistant", "content": response})
                
                # Clear pending approval
                st.session_state.pending_approval = None
                st.session_state.approval_state = None
                st.rerun()
        
        with col2:
            if st.button("❌ Decline", key="decline"):
                # Resume with decline
                config = {"configurable": {"thread_id": st.session_state.thread_id}}
                state = st.session_state.graph.invoke(Command(resume="no"), config=config)
                
                # Add response to conversation
                response = state["messages"][-1].content
                st.session_state.conversation.append({"role": "assistant", "content": response})
                
                # Clear pending approval
                st.session_state.pending_approval = None
                st.session_state.approval_state = None
                st.rerun()

    # Chat input
    user_input = st.chat_input("Ask about stock prices or request to buy stocks...")

    if user_input:
        # Add user message to conversation
        st.session_state.conversation.append({"role": "user", "content": user_input})
        
        # Process with graph
        config = {"configurable": {"thread_id": st.session_state.thread_id}}
        
        try:
            state = st.session_state.graph.invoke(
                {"messages": [HumanMessage(content=user_input)]}, 
                config=config
            )
            
            # Check if there's an interrupt (approval needed)
            if "__interrupt__" in state and state["__interrupt__"]:
                interrupt_info = state["__interrupt__"]
                st.session_state.pending_approval = interrupt_info
                st.session_state.approval_state = state
            else:
                # Normal response
                response = state["messages"][-1].content
                st.session_state.conversation.append({"role": "assistant", "content": response})
            
        except Exception as e:
            st.error(f"Error: {str(e)}")
        
        st.rerun()

    # Sidebar with available stocks
    with st.sidebar:
        st.subheader("📈 Available Stocks")
        stocks = {"MSFT": 200.3, "AAPL": 100.4, "AMZN": 150.0, "RIL": 87.6}
        for symbol, price in stocks.items():
            st.write(f"{symbol}: ${price}")
        
        st.subheader("🔧 Controls")
        if st.button("🗑️ Clear Conversation"):
            st.session_state.conversation = []
            st.session_state.pending_approval = None
            st.session_state.approval_state = None
            st.rerun()

if __name__ == "__main__":
    main()


# Install required dependencies (if not already installed):
# pip install streamlit langchain langgraph google-generativeai    
# Run the Streamlit app:
# streamlit run app.py
