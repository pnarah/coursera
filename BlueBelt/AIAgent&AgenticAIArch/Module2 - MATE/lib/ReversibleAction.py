class ReversibleAction:
    def __init__(self, execute_func, reverse_func):
        self.execute = execute_func
        self.reverse = reverse_func
        self.execution_record = None

    def run(self, **args):
        """Execute action and record how to reverse it."""
        result = self.execute(**args)
        self.execution_record = {
            "args": args,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        return result

    def undo(self):
        """Reverse the action using recorded information."""
        if not self.execution_record:
            raise ValueError("No action to reverse")
        return self.reverse(**self.execution_record)

# Example using reversible actions
create_event = ReversibleAction(
    execute_func=calendar.create_event,
    reverse_func=lambda **record: calendar.delete_event(record["result"]["event_id"])
)

send_invite = ReversibleAction(
    execute_func=calendar.send_invite,
    reverse_func=lambda **record: calendar.cancel_invite(record["result"]["invite_id"])
)