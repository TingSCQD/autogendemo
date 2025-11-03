import autogen
from agents import CoordinatorAgent, ResearcherAgent, CheckAgent, WriterAgent, FeedbackAgent


class CheckTask:
    def __init__(self):
        self.coordinator = CoordinatorAgent()
        self.check = CheckAgent()
        self.feedback = FeedbackAgent()


    def execute(self, Itinerary):
        print(f"\n Starting Check Task")
        print("=" * 50)

        # Create user proxy for interaction
        user_proxy = autogen.UserProxyAgent(
            name="user_proxy",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=5,
            is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
            code_execution_config={"work_dir": "workspace"},
        )

        # Create group chat
        group_chat = autogen.GroupChat(
            agents=[
                user_proxy,
                self.coordinator.get_agent(),
                self.check.get_agent(),
                self.feedback.get_agent(),
            ],
            messages=[],
            max_round=5,
        )

        manager = autogen.GroupChatManager(groupchat=group_chat, llm_config=self.coordinator.agent.llm_config)

        # Start the conversation
        task_message = f"""
        Check Task: 

        Coordinator, please manage this check task:
        1. Ask the check and feedback to  Check the rationality of the following itinerary: {Itinerary}
        2. If either check or feedback thinks this journey is unreasonable,record the parts they think are unreasonable
        3. Make sure to obtain check and feedback's common approval before outputting the results
        4. Return true if the final result is reasonable; otherwise, return false
        Begin the task coordination now.
        """

        user_proxy.initiate_chat(manager, message=task_message)

        return "Check task completed"