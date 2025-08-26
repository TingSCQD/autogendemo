import autogen
from config import AGENT_CONFIG

class CoordinatorAgent:
    def __init__(self):
        self.agent = autogen.AssistantAgent(**AGENT_CONFIG["coordinator"])
    
    def get_agent(self):
        return self.agent
    
    def initiate_task(self, task_description, agents):
        """Initiate a task and coordinate between agents"""
        message = f"""
        Task Description: {task_description}
        
        Please coordinate with the available agents to complete this task:
        - Research Agent: For gathering and analyzing information
        - Writer Agent: For creating structured content and reports
        
        Start by delegating the research phase, then move to content creation.
        """
        
        return message