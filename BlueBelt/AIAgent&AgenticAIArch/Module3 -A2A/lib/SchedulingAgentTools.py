@register_tool()
def check_availability(
    action_context: ActionContext,
    attendees: List[str],
    start_date: str,
    end_date: str,
    duration_minutes: int,
    _calendar_api_key: str
) -> List[Dict]:
    """Find available time slots for all attendees."""
    return calendar_service.find_available_slots(...)

@register_tool()
def create_calendar_invite(
    action_context: ActionContext,
    title: str,
    description: str,
    start_time: str,
    duration_minutes: int,
    attendees: List[str],
    _calendar_api_key: str
) -> Dict:
    """Create and send a calendar invitation."""
    return calendar_service.create_event(...)