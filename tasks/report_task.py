import autogen
from agents import CoordinatorAgent, ResearcherAgent, WriterAgent

class ReportTask:
    def __init__(self):
        self.coordinator = CoordinatorAgent()
        self.researcher = ResearcherAgent()
        self.writer = WriterAgent()
    
    def execute(self, topic, report_type="comprehensive"):
        """Execute a report generation task with agent collaboration"""
        print(f"\n📊 Starting Report Task: {topic} ({report_type} report)")
        print("=" * 50)
        
        # Create user proxy for interaction
        user_proxy = autogen.UserProxyAgent(
            name="user_proxy",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=15,
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
            max_round=20,
        )
        
        manager = autogen.GroupChatManager(groupchat=group_chat, llm_config=self.coordinator.agent.llm_config)
        
        # Start the conversation
        task_message = f"""
        Report Generation Task: {topic}
        
        Coordinator, please manage this {report_type} report generation:
        1. Direct the Researcher to conduct in-depth research on {topic}
        2. Ask the Researcher to analyze trends, challenges, and opportunities
        3. Have the Writer create a comprehensive business report with:
           - Executive Summary
           - Market Analysis
           - Key Findings
           - Strategic Recommendations
           - Conclusion
        4. Ensure the report is professional and actionable
        
        Begin the coordinated report generation now.
        """
        
        user_proxy.initiate_chat(manager, message=task_message)
        
        return "Report generation task completed"