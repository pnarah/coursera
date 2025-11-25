
@register_tool()
def get_project_status(
    action_context: ActionContext,
    project_id: str,
    _project_api_token: str
) -> Dict:
    """Retrieve current project status information."""
    return project_service.get_status(...)

@register_tool()
def update_project_log(
    action_context: ActionContext,
    entry_type: str,
    description: str,
    _project_api_token: str
) -> Dict:
    """Record an update in the project log."""
    return project_service.log_update(...)

@register_tool()
def call_agent(
    action_context: ActionContext,
    agent_name: str,
    task: str
) -> Dict:
    """Delegate to a specialist agent."""
    # Implementation as shown in previous tutorial