def run(self, user_input: str, memory=None, action_context_props=None):
    """Execute the agent loop."""
    memory = memory or Memory()
    
    # Create context with all necessary resources
    action_context = ActionContext({
        'memory': memory,
        'llm': self.generate_response,
        # Request-specific auth
        **action_context_props
    })
    
    while True:
        prompt = self.construct_prompt(action_context, self.goals, memory)
        response = self.prompt_llm_for_action(action_context, prompt)
        result = self.handle_agent_response(action_context, response)
        
        if self.should_terminate(action_context, response):
            break

...
# Run the agent and create custom context for the action to 
# pass to tools that need it
some_agent.run("Update the project status...", 
               memory=..., 
               # Pass request-specific auth token
               action_context_props={"auth_token": "my_auth_token"})


# By using ActionContext, we’ve solved several key challenges:

# Tools can access conversation history without being coupled to the agent implementation
# Authentication and other request-specific information can be injected where needed
# Tools remain independent and testable since their dependencies are explicitly declared
# The agent can provide different contexts for different execution environments (development, production, testing)


def handle_agent_response(self, action_context: ActionContext, response: str) -> dict:
    """Handle action without dependency management."""
    action_def, action = self.get_action(response)
    result = self.environment.execute_action(self, action_context, action_def, action["args"])
    return result