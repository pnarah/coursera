# Message Passing: The Basic Pattern
# The simplest form of agent interaction is message passing, where one agent sends a request and receives a response.
# This is like sending an email to a colleague - they get your message, do some work, and send back their results. 
# You don’t see how they arrived at their answer; you just get their final response.
@register_tool()
def call_agent(action_context: ActionContext, 
               agent_name: str, 
               task: str) -> dict:
    """Basic message passing between agents."""
    agent_registry = action_context.get_agent_registry()
    agent_run = agent_registry.get_agent(agent_name)
    
    # Create fresh memory for the invoked agent
    invoked_memory = Memory()
    
    # Run agent and get result
    result_memory = agent_run(
        user_input=task,
        memory=invoked_memory
    )
    
    # Return only the final memory item
    return {
        "result": result_memory.items[-1].get("content", "No result")
    }

# Memory Reflection: Learning from the Process
# Sometimes we want the first agent to understand how the second agent reached its conclusion. 
# This is like asking a colleague to not just give you their answer, but to explain their thought process.
# We can achieve this by copying all of the second agent’s memories back to the first agent:
@register_tool()
def call_agent_with_reflection(action_context: ActionContext, 
                             agent_name: str, 
                             task: str) -> dict:
    """Call agent and receive their full thought process."""
    agent_registry = action_context.get_agent_registry()
    agent_run = agent_registry.get_agent(agent_name)
    
    # Create fresh memory for invoked agent
    invoked_memory = Memory()
    
    # Run agent
    result_memory = agent_run(
        user_input=task,
        memory=invoked_memory
    )
    
    # Get the caller's memory
    caller_memory = action_context.get_memory()
    
    # Add all memories from invoked agent to caller
    # although we could leave off the last memory to
    # avoid duplication
    for memory_item in result_memory.items:
        caller_memory.add_memory({
            "type": f"{agent_name}_thought",  # Mark source of memory
            "content": memory_item["content"]
        })
    
    return {
        "result": result_memory.items[-1].get("content", "No result"),
        "memories_added": len(result_memory.items)
    }

# Memory Handoff: Continuing the Conversation
# Sometimes we want the second agent to pick up where the first agent left off, with full context of what’s happened 
# so far. This is like having a colleague step in to take over a project - they need to know everything that’s 
# happened up to that point:
@register_tool()
def hand_off_to_agent(action_context: ActionContext, 
                      agent_name: str, 
                      task: str) -> dict:
    """Transfer control to another agent with shared memory."""
    agent_registry = action_context.get_agent_registry()
    agent_run = agent_registry.get_agent(agent_name)
    
    # Get the current memory to hand off
    current_memory = action_context.get_memory()
    
    # Run agent with existing memory
    result_memory = agent_run(
        user_input=task,
        memory=current_memory  # Pass the existing memory
    )
    
    return {
        "result": result_memory.items[-1].get("content", "No result"),
        "memory_id": id(result_memory)
    }

# Selective Memory Sharing: Using LLM Understanding for Context Selection
@register_tool(description="Delegate a task to another agent with selected context")
def call_agent_with_selected_context(action_context: ActionContext,
                                   agent_name: str,
                                   task: str) -> dict:
    """Call agent with LLM-selected relevant memories."""
    agent_registry = action_context.get_agent_registry()
    agent_run = agent_registry.get_agent(agent_name)
    
    # Get current memory and add IDs
    current_memory = action_context.get_memory()
    memory_with_ids = []
    for idx, item in enumerate(current_memory.items):
        memory_with_ids.append({
            **item,
            "memory_id": f"mem_{idx}"
        })
    
    # Create schema for memory selection
    selection_schema = {
        "type": "object",
        "properties": {
            "selected_memories": {
                "type": "array",
                "items": {
                    "type": "string",
                    "description": "ID of a memory to include"
                }
            },
            "reasoning": {
                "type": "string",
                "description": "Explanation of why these memories were selected"
            }
        },
        "required": ["selected_memories", "reasoning"]
    }
    
    # Format memories for LLM review
    memory_text = "\n".join([
        f"Memory {m['memory_id']}: {m['content']}" 
        for m in memory_with_ids
    ])
    
    # Ask LLM to select relevant memories
    selection_prompt = f"""Review these memories and select the ones relevant for this task:

                        Task: {task}

                        Available Memories:
                        {memory_text}

                        Select memories that provide important context or information for this specific task.
                        Explain your selection process."""

    # Self-prompting magic to find the most relevant memories
    selection = prompt_llm_for_json(
        action_context=action_context,
        schema=selection_schema,
        prompt=selection_prompt
    )
    
    # Create filtered memory from selection
    filtered_memory = Memory()
    selected_ids = set(selection["selected_memories"])
    for item in memory_with_ids:
        if item["memory_id"] in selected_ids:
            # Remove the temporary memory_id before adding
            item_copy = item.copy()
            del item_copy["memory_id"]
            filtered_memory.add_memory(item_copy)
    
    # Run the agent with selected memories
    result_memory = agent_run(
        user_input=task,
        memory=filtered_memory
    )
    
    # Add results and selection reasoning to original memory
    current_memory.add_memory({
        "type": "system",
        "content": f"Memory selection reasoning: {selection['reasoning']}"
    })
    
    for memory_item in result_memory.items:
        current_memory.add_memory(memory_item)
    
    return {
        "result": result_memory.items[-1].get("content", "No result"),
        "shared_memories": len(filtered_memory.items),
        "selection_reasoning": selection["reasoning"]
    }




# # Example memory contents:
# memories = [
#     {"type": "user", "content": "We need to build a new reporting dashboard"},
#     {"type": "assistant", "content": "Initial cost estimate: $50,000"},
#     {"type": "user", "content": "That seems high"},
#     {"type": "assistant", "content": "Breakdown: $20k development, $15k design..."},
#     {"type": "system", "content": "Project deadline updated to Q3"},
#     {"type": "user", "content": "Can we reduce the cost?"}
# ]

# # LLM's selection might return:
# {
#     "selected_memories": ["mem_1", "mem_3", "mem_5"],
#     "reasoning": "Selected memories containing cost information and the request for cost reduction, excluding project timeline and general discussion as they're not directly relevant to the budget review task."
# }