# The scheduling specialist is focused entirely on finding times and creating meetings:
scheduler_agent = Agent(
    goals=[
        Goal(
            name="schedule_meetings",
            description="""Schedule meetings efficiently by:
            1. Finding times that work for all attendees
            2. Creating and sending calendar invites
            3. Handling any scheduling conflicts"""
        )
    ],
...
)