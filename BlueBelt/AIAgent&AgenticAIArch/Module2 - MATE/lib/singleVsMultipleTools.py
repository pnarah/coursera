# Approach 1: Multiple loosely constrained tools
@register_tool(description="Create a calendar event")
def create_calendar_event(action_context: ActionContext,
                         title: str,
                         time: str,
                         attendees: List[str]) -> dict:
    """Create a calendar event."""
    return calendar.create_event(title=title,
                               time=time,
                               attendees=attendees)

@register_tool(description="Send email to attendees")
def send_email(action_context: ActionContext,
               to: List[str],
               subject: str,
               body: str) -> dict:
    """Send an email."""
    return email.send(to=to, subject=subject, body=body)

@register_tool(description="Update calendar event")
def update_event(action_context: ActionContext,
                 event_id: str,
                 updates: dict) -> dict:
    """Update any aspect of a calendar event."""
    return calendar.update_event(event_id, updates)

# Approach 2: Single comprehensive safe tool
@register_tool(description="Schedule a team meeting safely")
def schedule_team_meeting(action_context: ActionContext,
                         title: str,
                         description: str,
                         attendees: List[str],
                         duration_minutes: int,
                         timeframe: str = "next_week") -> dict:
    """
    Safely schedule a team meeting with all necessary coordination.
    
    This tool:
    1. Verifies all attendees are valid
    2. Checks calendar availability
    3. Creates the event at the best available time
    4. Sends appropriate notifications
    5. Handles all error cases
    """
    # Input validation
    if not 15 <= duration_minutes <= 120:
        raise ValueError("Meeting duration must be between 15 and 120 minutes")
    
    if len(attendees) > 10:
        raise ValueError("Cannot schedule meetings with more than 10 attendees")
        
    # Verify attendees
    valid_attendees = validate_attendees(attendees)
    if len(valid_attendees) != len(attendees):
        raise ValueError("Some attendees are invalid")
        
    # Find available times
    available_slots = find_available_times(
        attendees=valid_attendees,
        duration=duration_minutes,
        timeframe=timeframe
    )
    
    if not available_slots:
        return {
            "status": "no_availability",
            "message": "No suitable time slots found"
        }
    
    # Create event at best time
    event = calendar.create_event(
        title=title,
        description=description,
        time=available_slots[0],
        duration=duration_minutes,
        attendees=valid_attendees
    )
    
    # Send notifications
    notifications.send_meeting_scheduled(
        event_id=event.id,
        attendees=valid_attendees
    )
    
    return {
        "status": "scheduled",
        "event_id": event.id,
        "scheduled_time": available_slots[0]
    }