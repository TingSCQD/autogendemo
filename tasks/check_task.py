import autogen
from agents import CoordinatorAgent, ResearcherAgent, CheckAgent, WriterAgent, FeedbackAgent


class CheckTask:
    def __init__(self):
        self.coordinator = CoordinatorAgent()
        self.check = CheckAgent()
        self.feedback = FeedbackAgent()


    def execute(self, Itinerary):
        print(f"\n Starting Check Task")
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
                self.check.get_agent(),
                self.feedback.get_agent(),
            ],
            messages=[],
            max_round=3,
        )

        manager = autogen.GroupChatManager(groupchat=group_chat, llm_config=self.coordinator.agent.llm_config)

        # Start the conversation
        task_message = f"""
        Check Task: 

        Coordinator, please manage this check task:
        1. Ask the check and feedback to Check the rationality of the following itinerary: {Itinerary}
        2. If either check or feedback thinks this journey is unreasonable, record the parts they think are unreasonable
        3. Make sure to obtain check and feedback's common approval before outputting the results
        4. Return true if the final result is reasonable; otherwise, return false
        5. The result should be clearly stated as a boolean value (true/false) or in JSON format:
           {{"is_valid": true/false, "errors": [...], "warnings": [...]}}
        Begin the task coordination now.
        """

        chat_result = user_proxy.initiate_chat(manager, message=task_message)
        
        # 尝试从聊天结果中提取检查结果
        import json
        import re
        
        result = None
        is_valid = False
        
        # 获取所有消息
        messages = group_chat.messages if hasattr(group_chat, 'messages') else []
        if chat_result and hasattr(chat_result, 'chat_history'):
            messages = chat_result.chat_history
        
        # 从后往前查找包含检查结果的消息
        for message in reversed(messages):
            content = message.get("content", "") if isinstance(message, dict) else str(message)
            
            # 尝试提取JSON格式的检查结果（包含 is_valid 字段）
            json_pattern = r'\{[\s\S]*"is_valid"[\s\S]*\}'
            json_match = re.search(json_pattern, content, re.IGNORECASE)
            
            if json_match:
                try:
                    json_str = json_match.group(0)
                    result = json.loads(json_str)
                    if "is_valid" in result:
                        is_valid = bool(result.get("is_valid", False))
                        # 返回完整的检查结果字典
                        return {
                            "is_valid": is_valid,
                            "errors": result.get("errors", []),
                            "warnings": result.get("warnings", [])
                        }
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
                            if "is_valid" in result:
                                is_valid = bool(result.get("is_valid", False))
                                return {
                                    "is_valid": is_valid,
                                    "errors": result.get("errors", []),
                                    "warnings": result.get("warnings", [])
                                }
                        except json.JSONDecodeError:
                            continue
            
            # 尝试从文本中提取布尔值和错误信息
            # 如果找到 true，但还没有提取到完整结果，继续查找
            if re.search(r'\btrue\b', content, re.IGNORECASE):
                if result is None:  # 如果没有找到JSON，使用简单的文本提取
                    is_valid = True
                    # 尝试提取错误或警告信息
                    errors = []
                    warnings = []
                    # 查找错误相关的文本
                    if re.search(r'\berror', content, re.IGNORECASE):
                        error_matches = re.findall(r'(?:error|问题|不合理)[:\s]+([^\n]+)', content, re.IGNORECASE)
                        errors = error_matches[:5]  # 最多保留5条
                    if re.search(r'\bwarning', content, re.IGNORECASE):
                        warning_matches = re.findall(r'(?:warning|警告|建议)[:\s]+([^\n]+)', content, re.IGNORECASE)
                        warnings = warning_matches[:5]
                    return {
                        "is_valid": True,
                        "errors": errors,
                        "warnings": warnings
                    }
            
            # 如果找到 false，更关注错误信息
            if re.search(r'\bfalse\b', content, re.IGNORECASE):
                is_valid = False
                # 提取错误和警告信息（false时更重要）
                errors = []
                warnings = []
                # 提取错误信息
                error_patterns = [
                    r'(?:error|错误|问题|不合理)[:\s]+([^\n\.]+)',
                    r'(?:不符合|违反|缺失)[:\s]+([^\n\.]+)',
                ]
                for pattern in error_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    errors.extend(matches)  # false时多保留一些错误信息
                # 去重但保持顺序
                seen = set()
                errors = [e.strip() for e in errors if e.strip() and (e.strip() not in seen or seen.add(e.strip()) is None)]
                
                # 提取警告信息
                warning_matches = re.findall(r'(?:warning|警告|建议|注意)[:\s]+([^\n\.]+)', content, re.IGNORECASE)
                warnings = [w.strip() for w in warning_matches]
                
                return {
                    "is_valid": False,
                    "errors": errors,
                    "warnings": warnings
                }
        
        # 如果无法提取，默认返回False（认为检查未通过）
        return {
            "is_valid": False,
            "errors": ["无法从agent对话中提取有效的检查结果"],
            "warnings": [],
            "details": "无法解析检查结果，默认认为检查未通过"
        }