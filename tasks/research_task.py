import autogen
from agents import CoordinatorAgent, ResearcherAgent, WriterAgent

class ResearchTask:
    def __init__(self):
        self.coordinator = CoordinatorAgent()
        self.researcher = ResearcherAgent()
        self.writer = WriterAgent()
    
    def execute(self, topic):
        """Execute a research task with agent collaboration"""
        print(f"\n🔍 Starting Research Task: {topic}")
        print("=" * 50)
        
        # Create user proxy for interaction
        user_proxy = autogen.UserProxyAgent(
            name="user_proxy",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=10,
            is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
            code_execution_config={"work_dir": "workspace"},
        )
        
        # Create group chat
        group_chat = autogen.GroupChat(
            agents=[
                user_proxy,
                self.coordinator.get_agent(),
                self.researcher.get_agent(),
                self.writer.get_agent()
            ],
            messages=[],
            max_round=15,
        )
        
        manager = autogen.GroupChatManager(groupchat=group_chat, llm_config=self.coordinator.agent.llm_config)
        
        # Start the conversation
        task_message = f"""
        Research Task: {topic}
        
        Coordinator, please manage this research task:
        1. Ask the Researcher to gather comprehensive information about {topic}
        2. Once research is complete, ask the Writer to create a summary report
        3. Ensure the final output is well-structured and informative
        
        Begin the task coordination now.
        """
        
        user_proxy.initiate_chat(manager, message=task_message)
        
        return "Research task completed"