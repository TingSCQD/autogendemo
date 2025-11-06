import autogen
from config import AGENT_CONFIG


class CoordinatorAgent:
    """协调器 Agent，负责统筹安排各个 agents 完成任务"""
    
    def __init__(self):
        self.agent = autogen.AssistantAgent(**AGENT_CONFIG["coordinator"])
    
    def get_agent(self):
        return self.agent
    
    def initiate_task(self, task_description, agents):
        """Initiate a task and coordinate between agents"""
        message = f"""
        任务描述: {task_description}
        
        请协调合适的agent完成此任务。
        """
        
        return message