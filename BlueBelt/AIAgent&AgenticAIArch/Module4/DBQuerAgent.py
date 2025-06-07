
@register_tool()
def query_database(action_context: ActionContext, 
                query: str, 
                _db_connection: DatabaseConnection, 
                _config: dict) -> dict:
    """Process data using external dependencies."""
    # Tool automatically receives db_connection and config
    ... use the database connection ...
    return query_results


# Agent only knows about and provides the data parameter
# action = {
#     "tool": "query_database",
#     "args": {
#         "query": "some SQL query"
#     }
# }

def get_tool_metadata(func, tool_name=None, description=None, 
                     parameters_override=None, terminal=False, 
                     tags=None):
    """Extract metadata while ignoring special parameters."""
    signature = inspect.signature(func)
    type_hints = get_type_hints(func)

    args_schema = {
        "type": "object",
        "properties": {},
        "required": []
    }

    for param_name, param in signature.parameters.items():
        # Skip special parameters - agent doesn't need to know about these
        if param_name in ["action_context", "action_agent"] or \
           param_name.startswith("_"):
            continue

        # Add regular parameters to the schema
        param_type = type_hints.get(param_name, str)
        args_schema["properties"][param_name] = {
            "type": "string"  # Simplified for example
        }

        if param.default == param.empty:
            args_schema["required"].append(param_name)

    return {
        "name": tool_name or func.__name__,
        "description": description or func.__doc__,
        "parameters": args_schema,
        "tags": tags or [],
        "terminal": terminal,
        "function": func
    }

@register_tool(description="Update user settings in the system")
def update_settings(action_context: ActionContext, 
                   setting_name: str,
                   new_value: str,
                   _auth_token: str,
                   _user_config: dict) -> dict:
    """Update a user setting in the external system."""
    # Tool automatically receives auth_token and user_config
    headers = {"Authorization": f"Bearer {_auth_token}"}
    
    if setting_name not in _user_config["allowed_settings"]:
        raise ValueError(f"Setting {setting_name} not allowed")
        
    response = requests.post(
        "https://api.example.com/settings",
        headers=headers,
        json={"setting": setting_name, "value": new_value}
    )
    
    return {"updated": True, "setting": setting_name}

# Agent's view of the tool
# action = {
#     "tool": "update_settings",
#     "args": {
#         "setting_name": "theme",
#         "new_value": "dark"
#     }
# }


# This system gives us a clean separation of concerns:

# The agent focuses on deciding what actions to take
# Tools declare what dependencies they need
# The environment handles dependency injection and result management
# ActionContext provides a flexible container for shared resources