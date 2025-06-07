# The project management agent uses these tools to monitor progress and arrange meetings when needed:

project_manager = Agent(
    goals=[
        Goal(
            name="project_oversight",
            description="""Manage project progress by:
            1. Getting the current project status
            2. Identifying when meetings are needed if there are issues in the project status log
            3. Delegating meeting scheduling to the "scheduler_agent" to arrange the meeting
            4. Recording project updates and decisions"""
        )
    ],
    ...
)