import autogen
from config import AGENT_CONFIG

class ResearcherAgent:
    def __init__(self):
        self.agent = autogen.AssistantAgent(**AGENT_CONFIG["researcher"])
    
    def get_agent(self):
        return self.agent
    
    def conduct_research(self, topic):
        """Conduct research on a given topic"""
        research_prompt = f"""
        Please conduct comprehensive research on the topic: {topic}
        
        Provide:
        1. Key concepts and definitions
        2. Current trends and developments
        3. Important facts and statistics
        4. Relevant examples or case studies
        5. Summary of findings
        
        Structure your research findings clearly and cite sources where possible.
        """
        return research_prompt