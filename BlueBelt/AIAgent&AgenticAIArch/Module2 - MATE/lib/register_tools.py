# Model Efficiency: Choose Your Pieces Wisely
@register_tool(description="Extract basic contact information from text")
def extract_contact_info(action_context: ActionContext, text: str) -> dict:
    """Extract name, email, and phone from text using a smaller, faster model."""
    # Use a smaller model for simple extraction
    response = action_context.get("fast_llm")(Prompt(messages=[
        {"role": "system", "content": "Extract contact information in JSON format."},
        {"role": "user", "content": text}
    ]))
    return json.loads(response)

@register_tool(description="Analyze complex technical documentation")
def analyze_technical_doc(action_context: ActionContext, document: str) -> dict:
    """Perform deep analysis of technical documentation."""
    # Use a more capable model for complex analysis
    response = action_context.get("powerful_llm")(Prompt(messages=[
        {"role": "system", "content": "Analyze technical this documentation thoroughly to identify potential contradictions in process that could lead to unexpected problems."},
        {"role": "user", "content": document}
    ]))
    return json.loads(response)

# Action Specificity: Control the Board
# Too generic - opens up possibilities for misuse
@register_tool(description="Modify calendar events")
def update_calendar(action_context: ActionContext, 
                   event_id: str,
                   updates: dict) -> dict:
    """Update any aspect of a calendar event."""
    return calendar.update_event(event_id, updates)

# More specific - clear purpose and limited scope
@register_tool(description="Reschedule a meeting you own to a new time")
def reschedule_my_meeting(action_context: ActionContext,
                         event_id: str,
                         new_start_time: str,
                         new_duration_minutes: int) -> dict:
    """
    Reschedule a meeting you own to a new time.
    Only works for meetings where you are the organizer.
    """
    # Verify ownership
    event = calendar.get_event(event_id)
    if event.organizer != action_context.get("user_email"):
        raise ValueError("Can only reschedule meetings you organize")
        
    # Validate new time is in the future
    new_start = datetime.fromisoformat(new_start_time)
    if new_start < datetime.now():
        raise ValueError("Cannot schedule meetings in the past")
        
    return calendar.update_event_time(
        event_id,
        new_start_time=new_start_time,
        duration_minutes=new_duration_minutes
    )

# Token Efficiency: Maximize Every Move
# Token inefficient - includes unnecessary context
@register_tool(description="Analyze sales data to identify trends and patterns...")
def analyze_sales(action_context: ActionContext, data: str) -> str:
    """
    This function will analyze sales data to identify trends and patterns.
    It looks at various aspects including:
    - Monthly trends
    - Seasonal patterns
    - Year-over-year growth
    - Product category performance
    - Regional variations
    - Customer segments
    
    The analysis will be thorough and consider multiple factors...
    [More verbose documentation]
    """
    
    # This prompt asks for unneeded analysis, leading to both a waste of input and output tokens
    return prompt_llm(action_context, f"""
        Analyze this sales data thoroughly. Consider monthly trends,
        seasonal patterns, year-over-year growth, product categories,
        regional variations, and customer segments. Provide detailed
        insights about all these aspects.
        
        Data: {data}
        
        Please give a comprehensive analysis...
    """)

# Token efficient - focused and precise
@register_tool(description="Analyze sales data for key trends")
def analyze_sales(action_context: ActionContext, data: str) -> str:
    """Calculate key sales metrics and identify significant trends."""
    
    # This prompt is focused and precise, using tokens efficiently
    return prompt_llm(action_context, f"""
        Sales Data: {data}
        1. Calculate YoY growth
        2. Identify top 3 trends
        3. Flag significant anomalies
    """)
