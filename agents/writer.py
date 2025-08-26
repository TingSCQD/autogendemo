import autogen
from config import AGENT_CONFIG

class WriterAgent:
    def __init__(self):
        self.agent = autogen.AssistantAgent(**AGENT_CONFIG["writer"])
    
    def get_agent(self):
        return self.agent
    
    def create_report(self, research_data, report_type="summary"):
        """Create a structured report based on research data"""
        writing_prompt = f"""
        Based on the research data provided, create a well-structured {report_type}.
        
        Research Data:
        {research_data}
        
        Please format the report with:
        1. Executive Summary
        2. Main Content (organized in logical sections)
        3. Key Findings
        4. Conclusion
        5. Recommendations (if applicable)
        
        Ensure the report is professional, clear, and well-organized.
        """
        return writing_prompt