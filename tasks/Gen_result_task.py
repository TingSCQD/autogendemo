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
            max_consecutive_auto_reply=5,
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
            max_round=5,
        )

        manager = autogen.GroupChatManager(groupchat=group_chat, llm_config=self.coordinator.agent.llm_config)

        # Start the conversation
        task_message = f"""
        Generate Result Task: {question}

        Coordinator, please manage this task:
        1. Ask the Researcher to gather comprehensive information about {question}
        2. Once research is complete, ask the Writer to create the final travel plan
        3. Ensure the final output is a JSON format travel plan with the following structure:
           {{
             "answer": {{
               "question_id": "...",
               "question": "...",
               "plan": [
                 {{
                   "date": "YYYY-MM-DD",
                   "breakfast_id": "...",
                   "breakfast": "...",
                   "breakfast_time": "...",
                   "breakfast_cost": 0.0,
                   "lunch_id": "...",
                   "lunch": "...",
                   "lunch_time": "...",
                   "lunch_cost": 0.0,
                   "dinner_id": "...",
                   "dinner": "...",
                   "dinner_time": "...",
                   "dinner_cost": 0.0,
                   "attraction_id": "...",
                   "attraction": "...",
                   "attraction_cost": 0.0,
                   "accommodation_id": "...",
                   "accommodation": "...",
                   "accommodation_cost": 0.0,
                   "path": [
                     {{
                       "ori_id": "...",
                       "des_id": "...",
                       "time": 0,
                       "cost": 0.0
                     }}
                   ]
                 }}
               ],
               "total_cost": 0.0,
               "budget": 0.0,
               "budget_remaining": 0.0,
               "budget_utilization": 0.0
             }}
           }}
           
        Important notes:
        - Each day in "plan" should include breakfast, lunch, dinner, attraction, accommodation (except last day), and path information
        - The "path" array should contain transportation routes between locations
        - All costs should be numeric values (floats)
        - Dates should be in "YYYY-MM-DD" format
        - Times should be in "HH:MM" format or minutes (integer)

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
                            # 只要存在 "answer" 字段且可解析，就返回
                            if isinstance(result, dict) and "answer" in result:
                                return result
                        except json.JSONDecodeError:
                            continue
            
            # 方法2: 尝试从文本中提取包含 "answer" 字段的JSON
            json_pattern = r'\{[\s\S]*"answer"[\s\S]*\}'
            json_match = re.search(json_pattern, content)
            
            if json_match:
                try:
                    json_str = json_match.group(0)
                    result = json.loads(json_str)
                    # 只要存在 "answer" 字段且可解析，就返回
                    if isinstance(result, dict) and "answer" in result:
                        return result
                except json.JSONDecodeError:
                    continue
        
        # 如果无法提取包含 "answer" 字段的JSON，返回一个基本的错误结构
        return {
            "answer": {
                "question_id": "",
                "question": question,
                "plan": [],
                "total_cost": 0.0,
                "error": "无法从agent对话中提取有效的行程计划JSON"
            }
        }