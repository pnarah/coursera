from typing import Callable, List
from commonlib.Goal import Goal
from commonlib.Environment import Environment

from commonlib.AgentLanguage import AgentLanguage
from commonlib.ActionRegistry import ActionRegistry
from commonlib.Environment import PythonEnvironment
from commonlib.Prompt import Prompt
from Capabilities.Capability import Capability
from Capabilities.TimeAwareCapability import TimeAwareCapability
from Capabilities.PlanFirstCapability import PlanFirstCapability


class Agent:
    def __init__(self,
                 goals: List[Goal],
                 agent_language: AgentLanguage,
                 action_registry: ActionRegistry,
                 generate_response: Callable[[Prompt], str],
                 environment: Environment,
                 capabilities: List[Capability] = [],
                 max_iterations: int = 10,
                 max_duration_seconds: int = 180):
        """
        Initialize an agent with its core GAME components and capabilities.
        
        Goals, Actions, Memory, and Environment (GAME) form the core of the agent,
        while capabilities provide ways to extend and modify the agent's behavior.
        
        Args:
            goals: What the agent aims to achieve
            agent_language: How the agent formats and parses LLM interactions
            action_registry: Available tools the agent can use
            generate_response: Function to call the LLM
            environment: Manages tool execution and results
            capabilities: List of capabilities that extend agent behavior
            max_iterations: Maximum number of action loops
            max_duration_seconds: Maximum runtime in seconds
        """
        self.goals = goals
        self.generate_response = generate_response
        self.agent_language = agent_language
        self.actions = action_registry
        self.environment = environment
        self.capabilities = capabilities or []
        self.max_iterations = max_iterations
        self.max_duration_seconds = max_duration_seconds

    def run(self, user_input: str, memory=None, action_context_props=None):

        ... existing code ...
        
        # Initialize capabilities
        for capability in self.capabilities:
            capability.init(self, action_context)
            
        while True:
            # Start of loop capabilities
            can_start_loop = reduce(lambda a, c: c.start_agent_loop(self, action_context),
                                self.capabilities, False)

            ... existing code ...
            
            # Construct prompt with capability modifications
            prompt = reduce(lambda p, c: c.process_prompt(self, action_context, p),
                        self.capabilities, base_prompt)

            ... existing code ...
            
            # Process response with capabilities
            response = reduce(lambda r, c: c.process_response(self, action_context, r),
                            self.capabilities, response)

            ... existing code ...
            
            # Process action with capabilities
            action = reduce(lambda a, c: c.process_action(self, action_context, a),
                        self.capabilities, action)
            
            ... existing code ...
            
            # Process result with capabilities
            result = reduce(lambda r, c: c.process_result(self, action_context, response,
                                                        action_def, action, r),
                        self.capabilities, result)

            ... existing code ...
            
            # End of loop capabilities
            for capability in self.capabilities:
                capability.end_agent_loop(self, action_context)



agent = Agent(
    goals=[
        Goal(name="scheduling",
             description="Schedule meetings considering current time and availability")
    ],
    agent_language=JSONAgentLanguage(),
    action_registry=registry,
    generate_response=llm.generate,
    environment=PythonEnvironment(),
    capabilities=[
        TimeAwareCapability(),
        LoggingCapability(log_level="INFO"),
        MetricsCapability(metrics_server="prometheus:9090")
    ]
)

agent = Agent(
    goals=[Goal(name="task", description="Complete the assigned task")],
    agent_language=JSONAgentLanguage(),
    action_registry=registry,
    generate_response=llm.generate,
    environment=PythonEnvironment(),
    capabilities=[
        TimeAwareCapability()
    ]
)

# Example conversation
agent.run("Schedule a team meeting for today")

# Agent response might include:
# "Since it's already 5:30 PM on Friday, I recommend scheduling the meeting  for Monday morning instead. Would you like me to look for available times  on Monday?"


agent = Agent(
    goals=[
        Goal(name="analysis",
             description="Analyze sales data and create a report")
    ],
    capabilities=[
        PlanFirstCapability(track_progress=True)
    ],
    # ... other agent configuration
)

result = agent.run("Analyze our Q4 sales data and create a report")


# Create an agent with progress tracking
agent = Agent(
    goals=[
        Goal(
            name="data_processing",
            description="Process and analyze customer feedback data"
        )
    ],
    capabilities=[
        ProgressTrackingCapability(track_frequency=2)  # Track every 2nd iteration
    ],
    # ... other agent configuration
)

# Example execution flow
memory = agent.run("Analyze customer feedback from Q4 and identify top issues")