import autogen
from agents import CoordinatorAgent, ResearcherAgent, WriterAgent


class GenResultTask:
    """
    Generate Result Task
    组成：coordinator, researcher, writer
    描述：整合信息，生成最终的行程计划JSON
    """
    def __init__(self):
        self.coordinator = CoordinatorAgent()
        self.researcher = ResearcherAgent()
        self.writer = WriterAgent()

    def execute(self, question):
        print(f"\n Starting Generate Result Task: {question}")
        print("=" * 50)

        # Create user proxy for interaction
        user_proxy = autogen.UserProxyAgent(
            name="user_proxy",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=3,
            is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
            code_execution_config={"work_dir": "workspace"},
        )

        # Create group chat
        group_chat = autogen.GroupChat(
            agents=[
                user_proxy,
                self.coordinator.get_agent(),
                self.researcher.get_agent(),
                self.writer.get_agent(),
            ],
            messages=[],
            max_round=3,
        )

        manager = autogen.GroupChatManager(groupchat=group_chat, llm_config=self.coordinator.agent.llm_config)

        # Start the conversation
        task_message = f"""
        Generate Result Task: {question}

        Coordinator, please manage this task:
        1. Based on the comprehensive information, and if necessarily, ask the Researcher to gather more comprehensive information about {question}
        2. Once research is complete, ask the Writer to create the final travel plan
        3. Ensure the final output is a JSON format travel plan with the following structure:
           {{
             "budget": 0.0,
             "peoples": 0,
             "travel_days": 0,
             "origin_city": "...",
             "destination_city": "...",
             "start_date": "...",
             "end_date": "...",
             "daily_plans": [
               {{
                 "date": "YYYY年MM月DD日",
                 "cost": 0.0,
                 "cost_time": 0.0,
                 "hotel": {{
                   "cost": 0.0,
                   "feature": "...",
                   "id": "...",
                   "name": "...",
                   "rating": 0.0,
                   "type": "..."
                 }},
                 "attractions": {{
                   "cost": 0.0,
                   "duration": 0.0,
                   "id": "...",
                   "name": "...",
                   "rating": 0.0,
                   "type": "..."
                 }},
                 "restaurants": [
                   {{
                     "type": "breakfast",
                     "restaurant": {{
                       "cost": 0.0,
                       "duration": 0.0,
                       "id": "...",
                       "name": "...",
                       "queue_time": 0.0,
                       "rating": 0.0,
                       "recommended_food": "...",
                       "type": "..."
                     }}
                   }},
                   {{
                     "type": "lunch",
                     "restaurant": {{ ... }}
                   }},
                   {{
                     "type": "dinner",
                     "restaurant": {{ ... }}
                   }}
                 ],
                 "transport": {{
                   "mode": "public_transport",
                   "cost": 0.0,
                   "duration": 0.0
                 }}
               }}
             ],
             "departure_trains": {{
               "cost": "0.0",
               "destination_id": "...",
               "destination_station": "...",
               "duration": "0",
               "origin_id": "...",
               "origin_station": "...",
               "train_number": "..."
             }},
             "back_trains": {{
               "cost": "0.0",
               "destination_id": "...",
               "destination_station": "...",
               "duration": "0",
               "origin_id": "...",
               "origin_station": "...",
               "train_number": "..."
             }},
             "total_cost": 0.0
           }}
           
        Important notes:
        - The output should be a direct JSON object (NOT wrapped in an "answer" field)
        - Each day in "daily_plans" should include hotel (except last day which should be "null"), attractions, restaurants (breakfast, lunch, dinner), and transport information
        - Hotel on the last day should be the string "null" (not a JSON null)
        - Dates should be in "YYYY年MM月DD日" format (e.g., "2025年06月10日")
        - All costs should be numeric values (floats)
        - Train costs and durations should be strings
        - Restaurant type should be one of: "breakfast", "lunch", "dinner"
        - Transport mode should be "public_transport" or "taxi"

        Begin the task coordination now.
        """

        chat_result = user_proxy.initiate_chat(manager, message=task_message)
        
        # 尝试从聊天结果中提取生成的行程计划
        import json
        import re
        
        # 获取所有消息
        messages = group_chat.messages if hasattr(group_chat, 'messages') else []
        if chat_result and hasattr(chat_result, 'chat_history'):
            messages = chat_result.chat_history
        
        # 从后往前查找包含JSON的消息
        for message in reversed(messages):
            content = message.get("content", "") if isinstance(message, dict) else str(message)
            
            # 方法1: 尝试提取markdown代码块中的JSON（优先级高，通常格式更标准）
            if "```json" in content or "```" in content:
                json_start = content.find("```json") if "```json" in content else content.find("```")
                if json_start != -1:
                    json_start = content.find("\n", json_start) + 1
                    json_end = content.find("```", json_start)
                    if json_end != -1:
                        try:
                            json_str = content[json_start:json_end].strip()
                            result = json.loads(json_str)
                            # 检查是否包含期望的字段（budget, peoples, travel_days, daily_plans等）
                            if isinstance(result, dict) and ("daily_plans" in result or "budget" in result):
                                return result
                        except json.JSONDecodeError:
                            continue
            
            # 方法2: 尝试从文本中提取包含 "daily_plans" 或 "budget" 字段的JSON
            json_pattern = r'\{[\s\S]*"(?:daily_plans|budget)"[\s\S]*\}'
            json_match = re.search(json_pattern, content)
            
            if json_match:
                try:
                    json_str = json_match.group(0)
                    result = json.loads(json_str)
                    # 检查是否包含期望的字段
                    if isinstance(result, dict) and ("daily_plans" in result or "budget" in result):
                        return result
                except json.JSONDecodeError:
                    continue
        
        # 如果无法提取有效的JSON，返回一个基本的错误结构
        return {
            "budget": 0.0,
            "peoples": 0,
            "travel_days": 0,
            "origin_city": "",
            "destination_city": "",
            "start_date": "",
            "end_date": "",
            "daily_plans": [],
            "departure_trains": {},
            "back_trains": {},
            "total_cost": 0.0,
            "error": "无法从agent对话中提取有效的行程计划JSON"
        }