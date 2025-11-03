"""
评估模块：对生成的旅行计划结果进行评估评分
包括：可执行率(ER)、求解准确率(AR)、实体覆盖率(ECR)、平均推理时间(ART)
"""

import json
import time
import requests
import os
from typing import Dict, List, Optional, Tuple, Any
from dotenv import load_dotenv

load_dotenv()

SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY")
SILICONFLOW_API_BASE_URL = os.getenv("SILICONFLOW_API_BASE_URL", "https://api.siliconflow.cn/v1")
SILICONFLOW_MODEL = os.getenv("SILICONFLOW_MODEL", "Qwen/QwQ-32B")

# 注意：API base_url应该包含完整路径，但chat/completions endpoint需要完整URL
if SILICONFLOW_API_BASE_URL.endswith("/v1"):
    # 已经是正确格式
    pass
elif not SILICONFLOW_API_BASE_URL.endswith("/v1/chat/completions"):
    # 确保有/v1后缀
    if not SILICONFLOW_API_BASE_URL.endswith("/v1"):
        SILICONFLOW_API_BASE_URL = SILICONFLOW_API_BASE_URL.rstrip("/") + "/v1"


class TravelPlanEvaluator:
    """旅行计划评估器"""
    
    # JSON格式要求的标准字段
    REQUIRED_ANSWER_FIELDS = ["question_id", "question", "plan", "total_cost"]
    REQUIRED_PLAN_FIELDS = [
        "date", "breakfast_id", "breakfast", "breakfast_time", "breakfast_cost",
        "lunch_id", "lunch", "lunch_time", "lunch_cost",
        "dinner_id", "dinner", "dinner_time", "dinner_cost",
        "attraction_id", "attraction", "attraction_cost",
        "accommodation_id", "accommodation", "accommodation_cost",
        "path"
    ]
    REQUIRED_PATH_FIELDS = ["ori_id", "des_id", "time", "cost"]
    
    def __init__(self):
        self.api_key = SILICONFLOW_API_KEY
        self.api_base_url = SILICONFLOW_API_BASE_URL
        self.model = SILICONFLOW_MODEL
        
    def evaluate_executability(self, result: Any) -> Tuple[float, str]:
        """
        评估可执行率(ER)
        检查JSON是否可以解析且格式是否符合要求
        
        Returns:
            (ER_score, error_message)
            ER_score: 1.0 如果可执行，0.0 如果不可执行
            error_message: 错误信息（如果有）
        """
        try:
            # 尝试解析JSON
            if isinstance(result, str):
                data = json.loads(result)
            elif isinstance(result, dict):
                data = result
            else:
                return 0.0, f"结果类型错误，期望字符串或字典，得到: {type(result)}"
            
            # 检查是否有answer字段
            if "answer" not in data:
                return 0.0, "缺少'answer'字段"
            
            answer = data["answer"]
            
            # 检查必需字段
            for field in self.REQUIRED_ANSWER_FIELDS:
                if field not in answer:
                    return 0.0, f"answer中缺少必需字段: {field}"
            
            # 检查plan是否为列表
            if not isinstance(answer["plan"], list):
                return 0.0, "plan字段必须是列表"
            
            # 检查每个plan项的必需字段
            for i, plan_item in enumerate(answer["plan"]):
                for field in self.REQUIRED_PLAN_FIELDS:
                    if field not in plan_item:
                        return 0.0, f"plan[{i}]中缺少必需字段: {field}"
                
                # 检查path字段
                if not isinstance(plan_item["path"], list):
                    return 0.0, f"plan[{i}].path必须是列表"
                
                # 检查每个path项的必需字段
                for j, path_item in enumerate(plan_item["path"]):
                    for field in self.REQUIRED_PATH_FIELDS:
                        if field not in path_item:
                            return 0.0, f"plan[{i}].path[{j}]中缺少必需字段: {field}"
            
            # 检查total_cost是否为数字
            if not isinstance(answer.get("total_cost"), (int, float)):
                return 0.0, "total_cost必须是数字"
            
            return 1.0, "JSON格式正确"
            
        except json.JSONDecodeError as e:
            return 0.0, f"JSON解析错误: {str(e)}"
        except Exception as e:
            return 0.0, f"评估可执行率时出错: {str(e)}"
    
    def evaluate_accuracy_rate(self, result: Any, question: str, ground_truth: Optional[Dict] = None) -> Tuple[float, str]:
        """
        评估求解准确率(AR)
        使用LLM评估规划在预算、时间、路线可达性、地点连贯性上的合理性
        取值范围: 0到1
        
        Args:
            result: 生成的旅行计划结果
            question: 原始问题
            ground_truth: 标准答案（可选，用于参考）
        
        Returns:
            (AR_score, explanation)
            AR_score: 0-1之间的分数
            explanation: 评估说明
        """
        try:
            # 解析result
            if isinstance(result, str):
                data = json.loads(result)
            elif isinstance(result, dict):
                data = result
            else:
                return 0.0, "结果格式错误"
            
            if "answer" not in data:
                return 0.0, "缺少answer字段"
            
            answer = data["answer"]
            plan = answer.get("plan", [])
            
            # 构建评估提示词
            prompt = f"""你是一个旅行计划评估专家。请评估以下旅行计划的合理性，从以下维度进行评分（每个维度0-1分，最后取平均）：
1. 预算合理性：计划是否在预算范围内，费用计算是否准确
2. 时间合理性：每日活动时间是否合理，交通时间是否充足
3. 路线可达性：景点、餐厅、酒店之间的交通路线是否可达
4. 地点连贯性：地点安排是否连贯，是否避免不必要的往返

原始问题：{question}

旅行计划：
{json.dumps(plan, ensure_ascii=False, indent=2)}

请给出：
1. 总体评分（0-1之间的浮点数）
2. 每个维度的评分
3. 详细的评估说明（指出存在的问题和改进建议）

请以JSON格式返回，格式如下：
{{
    "overall_score": 0.85,
    "dimension_scores": {{
        "budget": 0.9,
        "time": 0.8,
        "route_accessibility": 0.85,
        "location_coherence": 0.85
    }},
    "explanation": "详细说明..."
}}
"""
            
            # 调用LLM API
            # 确保URL格式正确
            if self.api_base_url.endswith("/v1"):
                url = f"{self.api_base_url}/chat/completions"
            else:
                url = f"{self.api_base_url.rstrip('/')}/v1/chat/completions"
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3
            }
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=120)
            response.raise_for_status()
            
            result_data = response.json()
            content = result_data["choices"][0]["message"]["content"]
            
            # 尝试解析LLM返回的JSON
            try:
                # 提取JSON部分（可能在markdown代码块中）
                if "```json" in content:
                    json_start = content.find("```json") + 7
                    json_end = content.find("```", json_start)
                    content = content[json_start:json_end].strip()
                elif "```" in content:
                    json_start = content.find("```") + 3
                    json_end = content.find("```", json_start)
                    content = content[json_start:json_end].strip()
                
                eval_result = json.loads(content)
                ar_score = float(eval_result.get("overall_score", 0.0))
                explanation = eval_result.get("explanation", "无详细说明")
                
                # 确保分数在0-1范围内
                ar_score = max(0.0, min(1.0, ar_score))
                
                return ar_score, explanation
                
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                # 如果无法解析JSON，尝试从文本中提取数字
                # 简单启发式：查找0-1之间的小数
                import re
                scores = re.findall(r'0?\.\d+|1\.0|1\.00|1', content)
                if scores:
                    try:
                        ar_score = float(scores[0])
                        ar_score = max(0.0, min(1.0, ar_score))
                        return ar_score, f"从响应中提取的评分: {content[:200]}"
                    except:
                        pass
                
                # 如果都失败，返回默认值
                return 0.5, f"无法解析LLM响应，原始内容: {content[:200]}"
            
        except requests.exceptions.RequestException as e:
            return 0.0, f"API请求错误: {str(e)}"
        except Exception as e:
            return 0.0, f"评估求解准确率时出错: {str(e)}"
    
    def evaluate_entity_coverage_rate(
        self, 
        result: Any, 
        correct_entities: Dict[str, List[str]]
    ) -> Tuple[float, Dict[str, Any]]:
        """
        评估实体覆盖率(ECR)
        ECR = N_detect / N_total
        
        Args:
            result: 生成的旅行计划结果
            correct_entities: 正确的实体字典，格式为：
                {
                    "attractions": ["attraction_id1", "attraction_id2", ...],
                    "restaurants": ["restaurant_id1", "restaurant_id2", ...],
                    "accommodations": ["accommodation_id1", "accommodation_id2", ...]
                }
        
        Returns:
            (ECR_score, details)
            ECR_score: 实体覆盖率分数
            details: 详细信息，包括检测到的实体、总数等
        """
        try:
            # 解析result
            if isinstance(result, str):
                data = json.loads(result)
            elif isinstance(result, dict):
                data = result
            else:
                return 0.0, {"error": "结果格式错误"}
            
            if "answer" not in data:
                return 0.0, {"error": "缺少answer字段"}
            
            answer = data["answer"]
            plan = answer.get("plan", [])
            
            # 提取生成的实体ID
            detected_attractions = set()
            detected_restaurants = set()
            detected_accommodations = set()
            
            for day_plan in plan:
                # 景点
                if "attraction_id" in day_plan and day_plan["attraction_id"]:
                    detected_attractions.add(str(day_plan["attraction_id"]))
                
                # 餐厅（早餐、午餐、晚餐）
                for meal_type in ["breakfast_id", "lunch_id", "dinner_id"]:
                    if meal_type in day_plan and day_plan[meal_type]:
                        detected_restaurants.add(str(day_plan[meal_type]))
                
                # 住宿
                if "accommodation_id" in day_plan and day_plan["accommodation_id"]:
                    detected_accommodations.add(str(day_plan["accommodation_id"]))
            
            # 计算各类实体的覆盖率
            total_entities = 0
            detected_entities = 0
            entity_details = {}
            
            for entity_type in ["attractions", "restaurants", "accommodations"]:
                correct_list = [str(eid) for eid in correct_entities.get(entity_type, [])]
                total = len(correct_list)
                total_entities += total
                
                if entity_type == "attractions":
                    detected = len(detected_attractions & set(correct_list))
                    detected_entities += detected
                elif entity_type == "restaurants":
                    detected = len(detected_restaurants & set(correct_list))
                    detected_entities += detected
                elif entity_type == "accommodations":
                    detected = len(detected_accommodations & set(correct_list))
                    detected_entities += detected
                
                entity_details[entity_type] = {
                    "total": total,
                    "detected": detected,
                    "coverage": detected / total if total > 0 else 0.0,
                    "correct_entities": correct_list,
                    "detected_entities": list(detected_attractions if entity_type == "attractions" 
                                              else detected_restaurants if entity_type == "restaurants"
                                              else detected_accommodations)
                }
            
            # 计算总体ECR
            ecr_score = detected_entities / total_entities if total_entities > 0 else 0.0
            
            details = {
                "total_entities": total_entities,
                "detected_entities": detected_entities,
                "ecr_score": ecr_score,
                "entity_details": entity_details
            }
            
            return ecr_score, details
            
        except Exception as e:
            return 0.0, {"error": f"评估实体覆盖率时出错: {str(e)}"}
    
    def calculate_art_star(self, art_minutes: float) -> float:
        """
        根据平均推理时间(ART)计算ART*
        
        ART*分段函数：
        - ART < 1 Min: 1.0
        - 1min <= ART < 5Min: 0.6
        - 5min <= ART < 10min: 0.2
        - 10min <= ART: 0.0
        """
        if art_minutes < 1.0:
            return 1.0
        elif art_minutes < 5.0:
            return 0.6
        elif art_minutes < 10.0:
            return 0.2
        else:
            return 0.0
    
    def calculate_final_score(
        self,
        er: float,
        ar: float,
        ecr: float,
        art_star: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        计算最终分数
        Final Score = ER * (0.7 * AR + 0.3 * ECR)
        
        注意：根据公式，ART*不直接参与最终分数计算，但可以单独报告
        """
        weighted_score = 0.7 * ar + 0.3 * ecr
        final_score = er * weighted_score
        
        return {
            "final_score": final_score,
            "er": er,
            "ar": ar,
            "ecr": ecr,
            "weighted_score": weighted_score,
            "art_star": art_star,
            "formula": "Final Score = ER * (0.7 * AR + 0.3 * ECR)"
        }
    
    def comprehensive_evaluate(
        self,
        result: Any,
        question: str,
        correct_entities: Optional[Dict[str, List[str]]] = None,
        inference_time_seconds: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        综合评估：执行所有评估指标并返回完整结果
        
        Args:
            result: 生成的旅行计划结果
            question: 原始问题
            correct_entities: 正确的实体字典（用于ECR计算）
            inference_time_seconds: 推理时间（秒），如果提供则计算ART*
        
        Returns:
            包含所有评估指标的字典
        """
        evaluation_result = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "question": question
        }
        
        # 1. 评估可执行率(ER)
        er_score, er_message = self.evaluate_executability(result)
        evaluation_result["er"] = {
            "score": er_score,
            "message": er_message
        }
        
        # 2. 评估求解准确率(AR)
        if er_score > 0:  # 只有可执行时才评估AR
            ar_score, ar_explanation = self.evaluate_accuracy_rate(result, question)
            evaluation_result["ar"] = {
                "score": ar_score,
                "explanation": ar_explanation
            }
        else:
            evaluation_result["ar"] = {
                "score": 0.0,
                "explanation": "由于ER=0，跳过AR评估"
            }
            ar_score = 0.0
        
        # 3. 评估实体覆盖率(ECR)
        if correct_entities is not None:
            ecr_score, ecr_details = self.evaluate_entity_coverage_rate(result, correct_entities)
            evaluation_result["ecr"] = {
                "score": ecr_score,
                "details": ecr_details
            }
        else:
            evaluation_result["ecr"] = {
                "score": 0.0,
                "details": {"message": "未提供correct_entities，无法计算ECR"}
            }
            ecr_score = 0.0
        
        # 4. 计算平均推理时间(ART)和ART*
        if inference_time_seconds is not None:
            art_minutes = inference_time_seconds / 60.0
            art_star = self.calculate_art_star(art_minutes)
            evaluation_result["art"] = {
                "seconds": inference_time_seconds,
                "minutes": art_minutes,
                "art_star": art_star
            }
        else:
            evaluation_result["art"] = {
                "message": "未提供推理时间"
            }
            art_star = None
        
        # 5. 计算最终分数
        final_score_result = self.calculate_final_score(er_score, ar_score, ecr_score, art_star)
        evaluation_result["final_score"] = final_score_result
        
        return evaluation_result


def evaluate_multiple_samples(
    results: List[Any],
    questions: List[str],
    correct_entities_list: Optional[List[Dict[str, List[str]]]] = None,
    inference_times: Optional[List[float]] = None
) -> Dict[str, Any]:
    """
    批量评估多个样本
    
    Args:
        results: 多个生成结果的列表
        questions: 对应的问题列表
        correct_entities_list: 对应的正确实体列表（可选）
        inference_times: 对应的推理时间列表（可选）
    
    Returns:
        包含平均分数和每个样本详细结果的字典
    """
    evaluator = TravelPlanEvaluator()
    
    evaluations = []
    total_er = 0.0
    total_ar = 0.0
    total_ecr = 0.0
    total_art_seconds = 0.0
    
    for i, (result, question) in enumerate(zip(results, questions)):
        correct_entities = correct_entities_list[i] if correct_entities_list else None
        inference_time = inference_times[i] if inference_times else None
        
        eval_result = evaluator.comprehensive_evaluate(
            result, question, correct_entities, inference_time
        )
        evaluations.append(eval_result)
        
        total_er += eval_result["er"]["score"]
        total_ar += eval_result["ar"]["score"]
        total_ecr += eval_result["ecr"]["score"]
        if inference_time:
            total_art_seconds += inference_time
    
    n = len(results)
    avg_er = total_er / n if n > 0 else 0.0
    avg_ar = total_ar / n if n > 0 else 0.0
    avg_ecr = total_ecr / n if n > 0 else 0.0
    avg_art_minutes = (total_art_seconds / n / 60.0) if n > 0 and total_art_seconds > 0 else None
    
    # 计算平均最终分数
    avg_final_score = avg_er * (0.7 * avg_ar + 0.3 * avg_ecr)
    
    return {
        "sample_count": n,
        "average_scores": {
            "er": avg_er,
            "ar": avg_ar,
            "ecr": avg_ecr,
            "art_minutes": avg_art_minutes,
            "art_star": evaluator.calculate_art_star(avg_art_minutes) if avg_art_minutes else None,
            "final_score": avg_final_score
        },
        "individual_evaluations": evaluations
    }


def main():
    """测试评估器功能"""
    print("=" * 60)
    print("旅行计划评估器测试")
    print("=" * 60)
    
    evaluator = TravelPlanEvaluator()
    
    # 测试样例1：完整的、格式正确的旅行计划
    print("\n\n【测试样例1】完整的、格式正确的旅行计划")
    print("-" * 60)
    test_result_1 = {
        "answer": {
            "question_id": "1",
            "question": "我和朋友打算从深圳坐高铁去上海玩三天两晚，预算7000元",
            "plan": [
                {
                    "date": "2025-06-10",
                    "breakfast_id": "rest_001",
                    "breakfast": "上海小笼包店",
                    "breakfast_time": "08:00",
                    "breakfast_cost": 50.0,
                    "lunch_id": "rest_002",
                    "lunch": "上海本帮菜",
                    "lunch_time": "12:00",
                    "lunch_cost": 150.0,
                    "dinner_id": "rest_003",
                    "dinner": "上海火锅店",
                    "dinner_time": "18:00",
                    "dinner_cost": 200.0,
                    "attraction_id": "attr_001",
                    "attraction": "外滩",
                    "attraction_cost": 0.0,
                    "accommodation_id": "hotel_001",
                    "accommodation": "上海酒店",
                    "accommodation_cost": 500.0,
                    "path": [
                        {"ori_id": "station_001", "des_id": "hotel_001", "time": 30, "cost": 50.0},
                        {"ori_id": "hotel_001", "des_id": "attr_001", "time": 20, "cost": 25.0}
                    ]
                },
                {
                    "date": "2025-06-11",
                    "breakfast_id": "rest_004",
                    "breakfast": "上海早餐店",
                    "breakfast_time": "08:00",
                    "breakfast_cost": 40.0,
                    "lunch_id": "rest_005",
                    "lunch": "上海特色餐厅",
                    "lunch_time": "12:30",
                    "lunch_cost": 120.0,
                    "dinner_id": "rest_006",
                    "dinner": "上海海鲜店",
                    "dinner_time": "19:00",
                    "dinner_cost": 250.0,
                    "attraction_id": "attr_002",
                    "attraction": "东方明珠",
                    "attraction_cost": 180.0,
                    "accommodation_id": "hotel_001",
                    "accommodation": "上海酒店",
                    "accommodation_cost": 500.0,
                    "path": [
                        {"ori_id": "hotel_001", "des_id": "attr_002", "time": 25, "cost": 30.0},
                        {"ori_id": "attr_002", "des_id": "hotel_001", "time": 25, "cost": 30.0}
                    ]
                },
                {
                    "date": "2025-06-12",
                    "breakfast_id": "rest_007",
                    "breakfast": "上海早点铺",
                    "breakfast_time": "07:30",
                    "breakfast_cost": 35.0,
                    "lunch_id": "rest_008",
                    "lunch": "上海面馆",
                    "lunch_time": "12:00",
                    "lunch_cost": 80.0,
                    "dinner_id": "rest_009",
                    "dinner": "上海茶餐厅",
                    "dinner_time": "18:30",
                    "dinner_cost": 150.0,
                    "attraction_id": "attr_003",
                    "attraction": "城隍庙",
                    "attraction_cost": 50.0,
                    "accommodation_id": None,
                    "accommodation": None,
                    "accommodation_cost": 0.0,
                    "path": [
                        {"ori_id": "hotel_001", "des_id": "attr_003", "time": 15, "cost": 20.0}
                    ]
                }
            ],
            "total_cost": 3500.0,
            "budget": 7000.0,
            "budget_remaining": 3500.0,
            "budget_utilization": 0.5
        }
    }
    
    correct_entities_1 = {
        "attractions": ["attr_001", "attr_002", "attr_003"],
        "restaurants": ["rest_001", "rest_002", "rest_003", "rest_004", "rest_005", "rest_006", "rest_007", "rest_008", "rest_009"],
        "accommodations": ["hotel_001"]
    }
    
    eval_result_1 = evaluator.comprehensive_evaluate(
        result=test_result_1,
        question="我和朋友打算从深圳坐高铁去上海玩三天两晚，预算7000元",
        correct_entities=correct_entities_1,
        inference_time_seconds=180.5
    )
    
    print(f"ER (可执行率): {eval_result_1['er']['score']:.2f} - {eval_result_1['er']['message']}")
    print(f"AR (求解准确率): {eval_result_1['ar']['score']:.2f}")
    print(f"ECR (实体覆盖率): {eval_result_1['ecr']['score']:.2f}")
    print(f"ART: {eval_result_1['art']['minutes']:.2f} 分钟, ART*: {eval_result_1['art']['art_star']:.2f}")
    print(f"最终分数: {eval_result_1['final_score']['final_score']:.4f}")
    
    # 测试样例2：格式错误（缺少必需字段）
    print("\n\n【测试样例2】格式错误（缺少必需字段）")
    print("-" * 60)
    test_result_2 = {
        "answer": {
            "question_id": "2",
            "question": "测试问题",
            "plan": [
                {
                    "date": "2025-06-10",
                    "breakfast_id": "rest_001",
                    # 缺少其他必需字段
                }
            ]
            # 缺少 total_cost
        }
    }
    
    eval_result_2 = evaluator.comprehensive_evaluate(
        result=test_result_2,
        question="测试问题",
        inference_time_seconds=120.0
    )
    
    print(f"ER (可执行率): {eval_result_2['er']['score']:.2f} - {eval_result_2['er']['message']}")
    print(f"AR (求解准确率): {eval_result_2['ar']['score']:.2f} - {eval_result_2['ar']['explanation']}")
    
    # 测试样例3：JSON字符串格式
    print("\n\n【测试样例3】JSON字符串格式输入")
    print("-" * 60)
    test_result_3_str = json.dumps({
        "answer": {
            "question_id": "3",
            "question": "JSON字符串测试",
            "plan": [
                {
                    "date": "2025-06-10",
                    "breakfast_id": "rest_001",
                    "breakfast": "早餐店",
                    "breakfast_time": "08:00",
                    "breakfast_cost": 50.0,
                    "lunch_id": "rest_002",
                    "lunch": "午餐店",
                    "lunch_time": "12:00",
                    "lunch_cost": 100.0,
                    "dinner_id": "rest_003",
                    "dinner": "晚餐店",
                    "dinner_time": "18:00",
                    "dinner_cost": 150.0,
                    "attraction_id": "attr_001",
                    "attraction": "景点1",
                    "attraction_cost": 100.0,
                    "accommodation_id": "hotel_001",
                    "accommodation": "酒店1",
                    "accommodation_cost": 400.0,
                    "path": [
                        {"ori_id": "ori_001", "des_id": "des_001", "time": 30, "cost": 50.0}
                    ]
                }
            ],
            "total_cost": 850.0
        }
    })
    
    eval_result_3 = evaluator.comprehensive_evaluate(
        result=test_result_3_str,
        question="JSON字符串测试",
        inference_time_seconds=90.0
    )
    
    print(f"ER (可执行率): {eval_result_3['er']['score']:.2f} - {eval_result_3['er']['message']}")
    
    # 测试样例4：实体覆盖率测试（部分实体不匹配）
    print("\n\n【测试样例4】实体覆盖率测试（部分匹配）")
    print("-" * 60)
    test_result_4 = {
        "answer": {
            "question_id": "4",
            "question": "实体覆盖率测试",
            "plan": [
                {
                    "date": "2025-06-10",
                    "breakfast_id": "rest_001",  # 在正确列表中
                    "breakfast": "早餐店1",
                    "breakfast_time": "08:00",
                    "breakfast_cost": 50.0,
                    "lunch_id": "rest_002",  # 在正确列表中
                    "lunch": "午餐店1",
                    "lunch_time": "12:00",
                    "lunch_cost": 100.0,
                    "dinner_id": "rest_wrong",  # 不在正确列表中
                    "dinner": "晚餐店",
                    "dinner_time": "18:00",
                    "dinner_cost": 150.0,
                    "attraction_id": "attr_001",  # 在正确列表中
                    "attraction": "景点1",
                    "attraction_cost": 100.0,
                    "accommodation_id": "hotel_wrong",  # 不在正确列表中
                    "accommodation": "酒店1",
                    "accommodation_cost": 400.0,
                    "path": [
                        {"ori_id": "ori_001", "des_id": "des_001", "time": 30, "cost": 50.0}
                    ]
                }
            ],
            "total_cost": 850.0
        }
    }
    
    correct_entities_4 = {
        "attractions": ["attr_001", "attr_002", "attr_003"],
        "restaurants": ["rest_001", "rest_002", "rest_003", "rest_004"],
        "accommodations": ["hotel_001", "hotel_002"]
    }
    
    eval_result_4 = evaluator.comprehensive_evaluate(
        result=test_result_4,
        question="实体覆盖率测试",
        correct_entities=correct_entities_4,
        inference_time_seconds=60.0
    )
    
    print(f"ER (可执行率): {eval_result_4['er']['score']:.2f}")
    print(f"ECR (实体覆盖率): {eval_result_4['ecr']['score']:.2f}")
    ecr_details = eval_result_4['ecr']['details']
    if isinstance(ecr_details, dict) and 'entity_details' in ecr_details:
        for entity_type, details in ecr_details['entity_details'].items():
            print(f"  {entity_type}: {details['detected']}/{details['total']} ({details['coverage']:.2%})")
    
    # 测试样例5：ART*分段函数测试
    print("\n\n【测试样例5】ART*分段函数测试")
    print("-" * 60)
    test_times = [0.5, 2.0, 7.0, 15.0]  # 分钟
    for art_minutes in test_times:
        art_star = evaluator.calculate_art_star(art_minutes)
        print(f"ART = {art_minutes:.1f} 分钟 -> ART* = {art_star:.2f}")
    
    # 测试批量评估
    print("\n\n【测试样例6】批量评估")
    print("-" * 60)
    batch_results = [test_result_1, test_result_3_str, test_result_4]
    batch_questions = [
        "我和朋友打算从深圳坐高铁去上海玩三天两晚，预算7000元",
        "JSON字符串测试",
        "实体覆盖率测试"
    ]
    batch_correct_entities = [correct_entities_1, None, correct_entities_4]
    batch_times = [180.5, 90.0, 60.0]
    
    batch_eval_result = evaluate_multiple_samples(
        results=batch_results,
        questions=batch_questions,
        correct_entities_list=batch_correct_entities,
        inference_times=batch_times
    )
    
    print(f"样本数量: {batch_eval_result['sample_count']}")
    avg_scores = batch_eval_result['average_scores']
    print(f"平均ER: {avg_scores['er']:.4f}")
    print(f"平均AR: {avg_scores['ar']:.4f}")
    print(f"平均ECR: {avg_scores['ecr']:.4f}")
    print(f"平均ART: {avg_scores['art_minutes']:.2f} 分钟")
    print(f"平均ART*: {avg_scores['art_star']:.2f}")
    print(f"平均最终分数: {avg_scores['final_score']:.4f}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
