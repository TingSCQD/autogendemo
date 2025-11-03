import autogen
import json
import sys
import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta

# 添加父目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import AGENT_CONFIG


class WriterAgent:
    """
    Writer Agent，负责整合多方结果，生成满足预算且兼顾体验的 JSON 格式行程信息
    """
    
    def __init__(self):
        self.agent = autogen.AssistantAgent(**AGENT_CONFIG["writer"])
        
        # 约束条件常量
        self.TAXI_CAPACITY = 4  # 出租车载客数
    
    def get_agent(self):
        return self.agent
    
    def _get_transport_params(self, intra_city_trans: Dict, origin_id: str, destination_id: str, param_type: str) -> float:
        """获取两点间交通参数"""
        for key in [f"{origin_id},{destination_id}", f"{destination_id},{origin_id}"]:
            if key in intra_city_trans:
                data = intra_city_trans[key]
                value = float(data.get(param_type, 0))
                return value if value > 0 else 0.0
        return 0.0
    
    def _format_date(self, start_date: str, day_offset: int) -> str:
        """
        格式化日期
        
        Args:
            start_date: 开始日期，格式如 "2025年6月10日"
            day_offset: 天数偏移（0表示第一天）
            
        Returns:
            格式化后的日期字符串
        """
        try:
            # 解析日期格式 "2025年6月10日"
            date_str = start_date.replace('年', '-').replace('月', '-').replace('日', '')
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            target_date = dt + timedelta(days=day_offset)
            return target_date.strftime('%Y-%m-%d')
        except:
            # 如果解析失败，尝试其他格式
            try:
                dt = datetime.strptime(start_date, '%Y-%m-%d')
                target_date = dt + timedelta(days=day_offset)
                return target_date.strftime('%Y-%m-%d')
            except:
                return start_date
    
    def _calculate_transport_cost(self, 
                                  origin_id: str, 
                                  destination_id: str,
                                  mode: str,
                                  peoples: int,
                                  intra_city_trans: Dict) -> float:
        """计算交通费用"""
        if mode == 'taxi':
            cost_per_trip = self._get_transport_params(intra_city_trans, origin_id, destination_id, 'taxi_cost')
            trips_needed = (peoples + self.TAXI_CAPACITY - 1) // self.TAXI_CAPACITY
            return trips_needed * cost_per_trip
        else:  # bus
            cost_per_person = self._get_transport_params(intra_city_trans, origin_id, destination_id, 'bus_cost')
            return peoples * cost_per_person
    
    def _generate_path(self,
                      origin_id: str,
                      destination_id: str,
                      mode: str,
                      peoples: int,
                      intra_city_trans: Dict) -> Dict:
        """生成路径信息"""
        if mode == 'taxi':
            time = self._get_transport_params(intra_city_trans, origin_id, destination_id, 'taxi_duration')
            cost = self._calculate_transport_cost(origin_id, destination_id, mode, peoples, intra_city_trans)
        else:  # bus
            time = self._get_transport_params(intra_city_trans, origin_id, destination_id, 'bus_duration')
            cost = self._calculate_transport_cost(origin_id, destination_id, mode, peoples, intra_city_trans)
        
        return {
            "ori_id": origin_id,
            "des_id": destination_id,
            "time": str(int(time)) if time > 0 else "0",
            "cost": f"{cost:.2f}" if cost > 0 else "0.00"
        }
    
    def _assign_meals(self, restaurants: List[Dict]) -> Dict:
        """
        将3个餐厅分配为早餐、午餐、晚餐
        默认：第一个为早餐，第二个为午餐，第三个为晚餐
        """
        meal_assignments = {
            'breakfast': restaurants[0] if len(restaurants) > 0 else None,
            'lunch': restaurants[1] if len(restaurants) > 1 else None,
            'dinner': restaurants[2] if len(restaurants) > 2 else None
        }
        return meal_assignments
    
    def generate_travel_plan_json(
        self,
        solution: Dict,
        travel_days: int,
        peoples: int,
        start_date: str,
        question_id: str = "",
        question: str = "",
        intra_city_trans: Optional[Dict] = None,
        budget: Optional[float] = None
    ) -> Dict:
        """
        生成 JSON 格式的行程信息
        
        Args:
            solution: planner 生成的行程方案
            travel_days: 旅行天数
            peoples: 人数
            start_date: 开始日期（格式：2025年6月10日）
            question_id: 问题ID
            question: 问题描述
            intra_city_trans: 市内交通数据（通过参数传入，可选）
            budget: 预算（可选）
            
        Returns:
            符合要求的 JSON 格式字典
        """
        # 使用传入的市内交通数据，如果没有则使用空字典
        if intra_city_trans is None:
            intra_city_trans = {}
        
        plan = []
        total_cost = 0.0
        
        accommodations = solution.get('accommodations', [])
        transport_modes = solution.get('transport_mode', {})
        hotel_id = accommodations[0].get('id') if accommodations else None
        
        # 计算住宿费用（不包括最后一天）
        if accommodations:
            hotel_data = accommodations[0].get('data', {})
            hotel_cost_per_night = float(hotel_data.get('cost', 0))
            rooms_needed = (peoples + 1) // 2  # 双人间，默认合租
            hotel_total = hotel_cost_per_night * (travel_days - 1) * rooms_needed
            total_cost += hotel_total
        
        # 处理每一天的行程
        for day in range(1, travel_days + 1):
            date = self._format_date(start_date, day - 1)
            day_plan = {
                "date": date
            }
            
            # 景点信息
            if day in solution.get('attractions', {}):
                attraction = solution['attractions'][day]
                attraction_id = attraction.get('id', '')
                attraction_name = attraction.get('name', '')
                attraction_data = attraction.get('data', {})
                attraction_cost = float(attraction_data.get('cost', 0)) * peoples
                
                day_plan["attraction_id"] = attraction_id
                day_plan["attraction"] = attraction_name
                day_plan["attraction_cost"] = f"{attraction_cost:.2f}"
                
                total_cost += attraction_cost
            else:
                day_plan["attraction_id"] = ""
                day_plan["attraction"] = ""
                day_plan["attraction_cost"] = "0.00"
            
            # 餐饮信息（3个：早餐、午餐、晚餐）
            restaurants = solution.get('restaurants', {}).get(day, [])
            meals = self._assign_meals(restaurants)
            
            # 早餐
            if meals['breakfast']:
                breakfast_data = meals['breakfast']
                breakfast_id = breakfast_data.get('id', '')
                breakfast_name = breakfast_data.get('name', '')
                breakfast_data_dict = breakfast_data.get('data', {})
                breakfast_cost = float(breakfast_data_dict.get('cost', 0)) * peoples
                breakfast_duration = float(breakfast_data_dict.get('duration', 0))
                breakfast_queue_time = float(breakfast_data_dict.get('queue_time', 0))
                breakfast_time = breakfast_duration + breakfast_queue_time
                
                day_plan["breakfast_id"] = breakfast_id
                day_plan["breakfast"] = breakfast_name
                day_plan["breakfast_time"] = str(int(breakfast_time))
                day_plan["breakfast_cost"] = f"{breakfast_cost:.2f}"
                
                total_cost += breakfast_cost
            else:
                day_plan["breakfast_id"] = ""
                day_plan["breakfast"] = ""
                day_plan["breakfast_time"] = "0"
                day_plan["breakfast_cost"] = "0.00"
            
            # 午餐
            if meals['lunch']:
                lunch_data = meals['lunch']
                lunch_id = lunch_data.get('id', '')
                lunch_name = lunch_data.get('name', '')
                lunch_data_dict = lunch_data.get('data', {})
                lunch_cost = float(lunch_data_dict.get('cost', 0)) * peoples
                lunch_duration = float(lunch_data_dict.get('duration', 0))
                lunch_queue_time = float(lunch_data_dict.get('queue_time', 0))
                lunch_time = lunch_duration + lunch_queue_time
                
                day_plan["lunch_id"] = lunch_id
                day_plan["lunch"] = lunch_name
                day_plan["lunch_time"] = str(int(lunch_time))
                day_plan["lunch_cost"] = f"{lunch_cost:.2f}"
                
                total_cost += lunch_cost
            else:
                day_plan["lunch_id"] = ""
                day_plan["lunch"] = ""
                day_plan["lunch_time"] = "0"
                day_plan["lunch_cost"] = "0.00"
            
            # 晚餐
            if meals['dinner']:
                dinner_data = meals['dinner']
                dinner_id = dinner_data.get('id', '')
                dinner_name = dinner_data.get('name', '')
                dinner_data_dict = dinner_data.get('data', {})
                dinner_cost = float(dinner_data_dict.get('cost', 0)) * peoples
                dinner_duration = float(dinner_data_dict.get('duration', 0))
                dinner_queue_time = float(dinner_data_dict.get('queue_time', 0))
                dinner_time = dinner_duration + dinner_queue_time
                
                day_plan["dinner_id"] = dinner_id
                day_plan["dinner"] = dinner_name
                day_plan["dinner_time"] = str(int(dinner_time))
                day_plan["dinner_cost"] = f"{dinner_cost:.2f}"
                
                total_cost += dinner_cost
            else:
                day_plan["dinner_id"] = ""
                day_plan["dinner"] = ""
                day_plan["dinner_time"] = "0"
                day_plan["dinner_cost"] = "0.00"
            
            # 住宿信息（不包括最后一天）
            if day < travel_days and accommodations:
                hotel_data = accommodations[0]
                hotel_id_day = hotel_data.get('id', '')
                hotel_name = hotel_data.get('name', '')
                hotel_data_dict = hotel_data.get('data', {})
                hotel_cost = float(hotel_data_dict.get('cost', 0)) * rooms_needed
                
                day_plan["accommodation_id"] = hotel_id_day
                day_plan["accommodation"] = hotel_name
                day_plan["accommodation_cost"] = f"{hotel_cost:.2f}"
            else:
                day_plan["accommodation_id"] = ""
                day_plan["accommodation"] = ""
                day_plan["accommodation_cost"] = "0.00"
            
            # 路径信息（path）
            path = []
            
            if day == 1:
                # 第一天：可能包含出发火车
                train_departure = solution.get('train_departure')
                if train_departure:
                    train_data = train_departure.get('data', {})
                    origin_id = train_data.get('origin_id', '')
                    destination_id = train_data.get('destination_id', '')
                    train_duration = float(train_data.get('duration', 0))
                    train_cost = float(train_data.get('cost', 0)) * peoples
                    
                    path.append({
                        "ori_id": origin_id,
                        "des_id": destination_id,
                        "time": str(int(train_duration)),
                        "cost": f"{train_cost:.2f}"
                    })
                    total_cost += train_cost
            
            # 市内交通路径
            if day in solution.get('attractions', {}) and hotel_id:
                attr_id = solution['attractions'][day].get('id')
                mode = transport_modes.get(day, 'taxi')
                
                if day == travel_days:
                    # 最后一天：酒店→景点（单程）
                    path.append(self._generate_path(hotel_id, attr_id, mode, peoples, intra_city_trans))
                    path_cost = self._calculate_transport_cost(hotel_id, attr_id, mode, peoples, intra_city_trans)
                    total_cost += path_cost
                    
                    # 最后一天可能包含返程火车
                    train_back = solution.get('train_back')
                    if train_back:
                        train_data = train_back.get('data', {})
                        origin_id = train_data.get('origin_id', '')
                        destination_id = train_data.get('destination_id', '')
                        train_duration = float(train_data.get('duration', 0))
                        train_cost = float(train_data.get('cost', 0)) * peoples
                        
                        path.append({
                            "ori_id": origin_id,
                            "des_id": destination_id,
                            "time": str(int(train_duration)),
                            "cost": f"{train_cost:.2f}"
                        })
                        total_cost += train_cost
                else:
                    # 其他天：酒店↔景点（往返）
                    # 去程：酒店→景点
                    path.append(self._generate_path(hotel_id, attr_id, mode, peoples, intra_city_trans))
                    path_cost1 = self._calculate_transport_cost(hotel_id, attr_id, mode, peoples, intra_city_trans)
                    total_cost += path_cost1
                    
                    # 返程：景点→酒店
                    path.append(self._generate_path(attr_id, hotel_id, mode, peoples, intra_city_trans))
                    path_cost2 = self._calculate_transport_cost(attr_id, hotel_id, mode, peoples, intra_city_trans)
                    total_cost += path_cost2
            
            day_plan["path"] = path
            plan.append(day_plan)
        
        # 构建最终答案
        answer = {
            "question_id": question_id,
            "question": question,
            "plan": plan,
            "total_cost": f"{total_cost:.2f}"
        }
        
        # 如果有预算，添加预算相关信息
        if budget is not None:
            answer["budget"] = f"{budget:.2f}"
            answer["budget_remaining"] = f"{budget - total_cost:.2f}"
            answer["budget_utilization"] = f"{(total_cost / budget * 100):.2f}%"
        
        return {
            "answer": answer
        }
    
    def integrate_and_generate(
        self,
        planner_result: Dict,
        feedback_result: Optional[Dict] = None,
        check_result: Optional[Dict] = None,
        question_id: str = "",
        question: str = "",
        start_date: str = "",
        intra_city_trans: Optional[Dict] = None
    ) -> Dict:
        """
        整合多方结果，生成最终 JSON 格式行程信息
        
        Args:
            planner_result: planner 生成的方案结果
            feedback_result: feedback agent 的检查结果（可选）
            check_result: check agent 的检查结果（可选）
            question_id: 问题ID
            question: 问题描述
            start_date: 开始日期
            intra_city_trans: 市内交通数据（通过参数传入，可选）
            
        Returns:
            完整的 JSON 格式行程信息
        """
        if not planner_result.get('success'):
            return {
                "answer": {
                    "question_id": question_id,
                    "question": question,
                    "plan": [],
                    "total_cost": "0.00",
                    "error": planner_result.get('error', '规划失败')
                }
            }
        
        solution = planner_result['solution']
        travel_days = planner_result.get('travel_days', 0)
        peoples = planner_result.get('peoples', 1)
        budget = planner_result.get('budget')
        
        # 生成 JSON 格式的行程
        travel_plan = self.generate_travel_plan_json(
            solution=solution,
            travel_days=travel_days,
            peoples=peoples,
            start_date=start_date,
            question_id=question_id,
            question=question,
            intra_city_trans=intra_city_trans,
            budget=budget
        )
        
        # 如果有 feedback 和 check 结果，可以添加验证信息
        if feedback_result:
            travel_plan['answer']['feedback'] = {
                'is_valid': feedback_result.get('is_valid', False),
                'errors': len(feedback_result.get('error_list', [])),
                'warnings': len(feedback_result.get('warning_list', []))
            }
        
        if check_result:
            travel_plan['answer']['check'] = {
                'is_valid': check_result.get('is_valid', False),
                'total_errors': check_result.get('total_errors', 0),
                'total_warnings': check_result.get('total_warnings', 0)
            }
        
        return travel_plan
    
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
