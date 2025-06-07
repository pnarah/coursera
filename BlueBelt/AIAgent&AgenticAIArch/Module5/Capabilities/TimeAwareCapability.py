from datetime import datetime
from zoneinfo import ZoneInfo
from Capabilities.Capability import Capability
from commonlib.ActionContext import ActionContext
from commonlib.Prompt import Prompt
from commonlib.ActionRegistry import Action

class TimeAwareCapability(Capability):
    def __init__(self):
        super().__init__(
            name="Time Awareness",
            description="Allows the agent to be aware of time"
        )
        
    def init(self, agent, action_context: ActionContext) -> dict:
        """Set up time awareness at the start of agent execution."""
        # Get timezone from context or use default
        time_zone_name = action_context.get("time_zone", "America/Chicago")
        timezone = ZoneInfo(time_zone_name)
        
        # Get current time in specified timezone
        current_time = datetime.now(timezone)
        
        # Format time in both machine and human-readable formats
        iso_time = current_time.strftime("%Y-%m-%dT%H:%M:%S%z")
        human_time = current_time.strftime("%H:%M %A, %B %d, %Y")
        
        # Store time information in memory
        memory = action_context.get_memory()
        memory.add_memory({
            "type": "system",
            "content": f"""Right now, it is {human_time} (ISO: {iso_time}).
            You are in the {time_zone_name} timezone.
            Please consider the day/time, if relevant, when responding."""
        })
        
    def process_prompt(self, agent, action_context: ActionContext, 
                      prompt: Prompt) -> Prompt:
        """Update time information in each prompt."""
        time_zone_name = action_context.get("time_zone", "America/Chicago")
        current_time = datetime.now(ZoneInfo(time_zone_name))
        
        # Add current time to system message
        system_msg = (f"Current time: "
                     f"{current_time.strftime('%H:%M %A, %B %d, %Y')} "
                     f"({time_zone_name})\n\n")
        
        # Add to existing system message or create new one
        messages = prompt.messages
        if messages and messages[0]["role"] == "system":
            messages[0]["content"] = system_msg + messages[0]["content"]
        else:
            messages.insert(0, {
                "role": "system",
                "content": system_msg
            })
            
        return Prompt(messages=messages)
    
class EnhancedTimeAwareCapability(TimeAwareCapability):
    def process_action(self, agent, action_context: ActionContext, 
                      action: dict) -> dict:
        """Add timing information to action results."""
        # Add execution time to action metadata
        action["execution_time"] = datetime.now(
            ZoneInfo(action_context.get("time_zone", "America/Chicago"))
        ).isoformat()
        return action
        
    def process_result(self, agent, action_context: ActionContext,
                      response: str, action_def: Action,
                      action: dict, result: any) -> any:
        """Add duration information to results."""
        if isinstance(result, dict):
            result["action_duration"] = (
                datetime.now(ZoneInfo(action_context.get("time_zone"))) -
                datetime.fromisoformat(action["execution_time"])
            ).total_seconds()
        return result