
import os
from dotenv import load_dotenv

load_dotenv()


SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY")
if not SILICONFLOW_API_KEY:
    raise ValueError("SILICONFLOW_API_KEY environment variable is required")
SILICONFLOW_MODEL = os.getenv("SILICONFLOW_MODEL", "Qwen/Qwen3-32B")
SILICONFLOW_TEMPERATURE = float(os.getenv("SILICONFLOW_TEMPERATURE", "0.7"))
SILICONFLOW_API_BASE_URL = os.getenv("SILICONFLOW_API_BASE_URL", "https://api.siliconflow.cn/v1")

# 旅行规划 API 服务器配置
TRAVEL_API_BASE_URL = os.getenv("TRAVEL_API_BASE_URL", "http://localhost:12457")
TRAVEL_API_TIMEOUT = int(os.getenv("TRAVEL_API_TIMEOUT", "10"))


LLM_CONFIG = {
    "config_list": [
        {
            "model": SILICONFLOW_MODEL,
            "api_key": SILICONFLOW_API_KEY,
            "base_url": SILICONFLOW_API_BASE_URL,
        }
    ],
    "temperature": SILICONFLOW_TEMPERATURE,
    "timeout": 120,
}

from autogen import AssistantAgent
def get_agent():
    return AssistantAgent(
        name="siliconflow",
        llm_config=LLM_CONFIG
    )

# Agent Configuration
AGENT_CONFIG = {
    "coordinator": {
        "name": "coordinator",
        "system_message": """You are a Coordinator Agent responsible for managing tasks and coordinating between other agents.
        Your role is to:
        1. Understand the task requirements
        2. Delegate tasks to appropriate agents based on the task description
        3. Coordinate communication between agents
        4. Ensure task completion and quality
        5. Provide final results to the user
        
        Always be clear in your instructions and maintain professional communication.""",
        "llm_config": LLM_CONFIG,
        "human_input_mode": "NEVER",
    },
    
    "researcher": {
        "name": "researcher",
        "system_message": """You are a Research Agent specialized in gathering travel planning information from POI and path planning databases.
        Your role is to:
        1. Query transportation data (cross-city and intra-city transport)
        2. Retrieve hotel/accommodation information
        3. Gather attraction/POI data
        4. Fetch restaurant information
        5. Get city information and lists
        6. Provide accurate and well-structured data findings
        
        You have access to various API endpoints to query the travel planning database.
        Always provide factual, structured information based on the API responses.
        When querying data, use the appropriate API methods available in the ResearcherAgent class.""",
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
    },
    
    "planner": {
        "name": "planner",
        "system_message": """You are a Travel Planner Agent specialized in creating optimal travel itineraries using constraint-based optimization.
        Your role is to:
        1. Build symbolic models for travel planning constraints
        2. Generate initial travel itinerary proposals
        3. Ensure all constraints are satisfied:
           - Daily: one attraction, three meals, one accommodation (except last day)
           - Daily: two intra-city commutes (hotel-attraction round trip)
           - Last day: no accommodation, transport from previous night's hotel to last day's attraction
           - Daily activity time <= 840 minutes
           - Train travel time not counted in daily activity time
           - Train costs counted in corresponding dates
           - Departure on first day morning, return on last day
           - All rooms are double rooms, default to sharing if not specified
           - Taxi can carry 4 people
           - Ignore intra-city commute in departure city
           - If budget not mentioned, ignore budget constraint
        4. Use SCIP solver for optimization
        5. Maximize ratings while satisfying all constraints
        
        You have access to ResearcherAgent to fetch travel data and use optimization models to generate travel plans.""",
        "llm_config": LLM_CONFIG,
        "human_input_mode": "NEVER",
    }
}