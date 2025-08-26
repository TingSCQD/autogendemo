import os
from dotenv import load_dotenv

load_dotenv()

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required")

# AutoGen Configuration
LLM_CONFIG = {
    "config_list": [
        {
            "model": "gpt-4",
            "api_key": OPENAI_API_KEY,
        }
    ],
    "temperature": 0.7,
    "timeout": 120,
}

# Agent Configuration
AGENT_CONFIG = {
    "coordinator": {
        "name": "coordinator",
        "system_message": """You are a Coordinator Agent responsible for managing tasks and coordinating between other agents.
        Your role is to:
        1. Understand the task requirements
        2. Delegate tasks to appropriate agents
        3. Coordinate communication between agents
        4. Ensure task completion and quality
        5. Provide final results to the user
        
        Always be clear in your instructions and maintain professional communication.""",
        "llm_config": LLM_CONFIG,
        "human_input_mode": "NEVER",
    },
    
    "researcher": {
        "name": "researcher",
        "system_message": """You are a Research Agent specialized in gathering and analyzing information.
        Your role is to:
        1. Conduct thorough research on given topics
        2. Analyze and synthesize information
        3. Provide accurate and well-structured research findings
        4. Cite sources when possible
        5. Collaborate with other agents as needed
        
        Focus on providing factual, well-researched content.""",
        "llm_config": LLM_CONFIG,
        "human_input_mode": "NEVER",
    },
    
    "writer": {
        "name": "writer",
        "system_message": """You are a Writer Agent specialized in creating well-structured content.
        Your role is to:
        1. Transform research findings into clear, readable content
        2. Create structured reports and documents
        3. Ensure proper formatting and organization
        4. Maintain consistent tone and style
        5. Collaborate with other agents to refine content
        
        Focus on clarity, structure, and professional presentation.""",
        "llm_config": LLM_CONFIG,
        "human_input_mode": "NEVER",
    }
}