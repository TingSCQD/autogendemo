import autogen
from agents import CoordinatorAgent, ResearcherAgent, PlannerAgent


class GenerateTask:
    """
    Generate Task
    组成：coordinator,researcher,planner
    描述：调用API搜索信息，然后规划出一份行程
    """
    def __init__(self):
        self.coordinator = CoordinatorAgent()
        self.researcher = ResearcherAgent()
        self.planner = PlannerAgent()

    def execute(self, question):
        print(f"\n Starting Generate Task: {question}")
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
                self.planner.get_agent()
            ],
            messages=[],
            max_round=5,
        )

        manager = autogen.GroupChatManager(groupchat=group_chat, llm_config=self.coordinator.agent.llm_config)

        # Start the conversation
        task_message = f"""
        Generate Task: {question}

        Coordinator, please manage this Generate task:
        1. Ask the Researcher to gather information about {question}
        2. Once research is complete, ask the Planner to create a Feasible itinerary planning
        3. Ensure the final output is well-structured and informative
        4. The final output should be a JSON format travel plan with the structure:
           {{
             "answer": {{
               "question_id": "...",
               "question": "...",
               "plan": [...]
             }}
           }}

        Begin the task coordination now.
        """

        chat_result = user_proxy.initiate_chat(manager, message=task_message)
        
        # 尝试从聊天结果中提取生成的行程计划
        # 方法1: 从最后的消息中提取JSON
        import json
        import re
        
        result = None
        
        # 获取所有消息
        messages = group_chat.messages if hasattr(group_chat, 'messages') else []
        if chat_result and hasattr(chat_result, 'chat_history'):
            messages = chat_result.chat_history
        
        # 从后往前查找包含JSON的消息
        for message in reversed(messages):
            content = message.get("content", "") if isinstance(message, dict) else str(message)
            
            # 尝试提取JSON部分（可能在代码块中）
            json_pattern = r'\{[\s\S]*"answer"[\s\S]*\}'
            json_match = re.search(json_pattern, content)
            
            if json_match:
                try:
                    json_str = json_match.group(0)
                    result = json.loads(json_str)
                    if "answer" in result:
                        return result
                except json.JSONDecodeError:
                    continue
            
            # 尝试提取markdown代码块中的JSON
            if "```json" in content or "```" in content:
                json_start = content.find("```json") if "```json" in content else content.find("```")
                if json_start != -1:
                    json_start = content.find("\n", json_start) + 1
                    json_end = content.find("```", json_start)
                    if json_end != -1:
                        try:
                            json_str = content[json_start:json_end].strip()
                            result = json.loads(json_str)
                            if "answer" in result:
                                return result
                        except json.JSONDecodeError:
                            continue
        
        # 如果无法提取JSON，返回一个基本的错误结构
        if result is None:
            return {
                "answer": {
                    "question_id": "",
                    "question": question,
                    "plan": [],
                    "error": "无法从agent对话中提取有效的行程计划JSON"
                }
            }
        
        return result