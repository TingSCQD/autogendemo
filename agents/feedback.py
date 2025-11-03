import autogen
import sys
import os
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

# 添加父目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import AGENT_CONFIG


class FeedbackAgent:
    """
    反馈 Agent，负责检测初步行程方案中的冲突
    检查与 planner 相同的约束条件
    """
    
    def __init__(self):
        self.agent = autogen.AssistantAgent(**AGENT_CONFIG["feedback"])
        
        # 约束条件常量（与 planner 保持一致）
        self.MAX_DAILY_TIME = 840  # 每日最大活动时间（分钟）
        self.MEALS_PER_DAY = 3  # 每日餐饮数量
        self.ATTRACTIONS_PER_DAY = 1  # 每日景点数量
        self.TAXI_CAPACITY = 4  # 出租车载客数
        self.ROOM_TYPE = "双人间"  # 房型
    
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
    
    def check_constraint_1(self, solution: Dict, travel_days: int) -> List[Dict]:
        """
        约束1: 每日应选择一个景点、三个餐饮、一个住宿（最后一天无住宿）
        """
        conflicts = []
        
        for day in range(1, travel_days + 1):
            # 检查景点数量
            if day not in solution.get('attractions', {}):
                conflicts.append({
                    'constraint': '每日选择一个景点',
                    'day': day,
                    'issue': f'第{day}天缺少景点选择',
                    'severity': 'error'
                })
            elif solution['attractions'][day] is None:
                conflicts.append({
                    'constraint': '每日选择一个景点',
                    'day': day,
                    'issue': f'第{day}天景点选择为空',
                    'severity': 'error'
                })
            
            # 检查餐饮数量
            restaurants = solution.get('restaurants', {}).get(day, [])
            if len(restaurants) != self.MEALS_PER_DAY:
                conflicts.append({
                    'constraint': '每日三个餐饮',
                    'day': day,
                    'issue': f'第{day}天餐饮数量为{len(restaurants)}，应为{self.MEALS_PER_DAY}',
                    'severity': 'error'
                })
            
        # 检查住宿（全局选择，不包括最后一天）
        accommodations = solution.get('accommodations', [])
        if not accommodations or len(accommodations) == 0:
            conflicts.append({
                'constraint': '住宿选择',
                'issue': '缺少住宿选择（前几晚需要住宿）',
                'severity': 'error'
            })
        
        return conflicts
    
    def check_constraint_2_3(self, solution: Dict, travel_days: int, intra_city_trans: Dict) -> List[Dict]:
        """
        约束2&3: 每天固定两次市内通勤（住宿↔景点往返），最后一天为前一晚酒店→景点
        """
        conflicts = []
        accommodations = solution.get('accommodations', [])
        
        if not accommodations:
            conflicts.append({
                'constraint': '市内通勤',
                'issue': '缺少住宿信息，无法检查交通安排',
                'severity': 'warning'
            })
            return conflicts
        
        hotel_id = accommodations[0].get('id') if accommodations else None
        
        for day in range(1, travel_days + 1):
            if day not in solution.get('attractions', {}):
                continue
            
            attr_id = solution['attractions'][day].get('id')
            if not attr_id or not hotel_id:
                continue
            
            # 检查交通数据是否存在
            if day == travel_days:
                # 最后一天：酒店→景点（单程）
                key1 = f"{hotel_id},{attr_id}"
                key2 = f"{attr_id},{hotel_id}"
                if key1 not in intra_city_trans and key2 not in intra_city_trans:
                    conflicts.append({
                        'constraint': '最后一天交通',
                        'day': day,
                        'issue': f'第{day}天缺少从酒店到景点的交通数据',
                        'severity': 'warning'
                    })
            else:
                # 其他天：酒店↔景点（往返）
                key1 = f"{hotel_id},{attr_id}"
                key2 = f"{attr_id},{hotel_id}"
                if key1 not in intra_city_trans or key2 not in intra_city_trans:
                    conflicts.append({
                        'constraint': '每日两次市内通勤',
                        'day': day,
                        'issue': f'第{day}天缺少酒店与景点间的往返交通数据',
                        'severity': 'warning'
                    })
        
        return conflicts
    
    def check_constraint_4(self, solution: Dict, travel_days: int, intra_city_trans: Dict) -> List[Dict]:
        """
        约束4: 每日活动时间 <= 840分钟
        包括：景点时间、餐饮时间（含排队）、市内交通时间（不包括火车时间）
        """
        conflicts = []
        accommodations = solution.get('accommodations', [])
        hotel_id = accommodations[0].get('id') if accommodations else None
        transport_modes = solution.get('transport_mode', {})
        
        for day in range(1, travel_days + 1):
            total_time = 0
            
            # 景点时间
            if day in solution.get('attractions', {}):
                attr_data = solution['attractions'][day].get('data', {})
                total_time += float(attr_data.get('duration', 0))
            
            # 餐饮时间（含排队）
            restaurants = solution.get('restaurants', {}).get(day, [])
            for rest in restaurants:
                rest_data = rest.get('data', {})
                total_time += float(rest_data.get('duration', 0)) + float(rest_data.get('queue_time', 0))
            
            # 市内交通时间
            if day in solution.get('attractions', {}) and hotel_id:
                attr_id = solution['attractions'][day].get('id')
                mode = transport_modes.get(day, 'taxi')
                
                if day == travel_days:
                    # 最后一天：酒店→景点（单程）
                    duration_type = 'taxi_duration' if mode == 'taxi' else 'bus_duration'
                    trans_time = self._get_transport_params(intra_city_trans, hotel_id, attr_id, duration_type)
                    total_time += trans_time
                else:
                    # 其他天：酒店↔景点（往返）
                    duration_type = 'taxi_duration' if mode == 'taxi' else 'bus_duration'
                    trans_time1 = self._get_transport_params(intra_city_trans, hotel_id, attr_id, duration_type)
                    trans_time2 = self._get_transport_params(intra_city_trans, attr_id, hotel_id, duration_type)
                    total_time += trans_time1 + trans_time2
            
            if total_time > self.MAX_DAILY_TIME:
                conflicts.append({
                    'constraint': '每日活动时间限制',
                    'day': day,
                    'issue': f'第{day}天活动时间为{total_time:.1f}分钟，超过{self.MAX_DAILY_TIME}分钟限制',
                    'actual_time': total_time,
                    'max_time': self.MAX_DAILY_TIME,
                    'severity': 'error'
                })
        
        return conflicts
    
    def check_constraint_5_6(self, solution: Dict, travel_days: int) -> List[Dict]:
        """
        约束5&6: 出发/返程火车乘坐时间不计入每日活动时间，火车费用计入对应日期
        """
        conflicts = []
        
        # 检查是否有出发火车（第一天）
        if not solution.get('train_departure'):
            conflicts.append({
                'constraint': '第一天出发火车',
                'day': 1,
                'issue': '缺少第一天出发的火车信息',
                'severity': 'error'
            })
        
        # 检查是否有返程火车（最后一天）
        if not solution.get('train_back'):
            conflicts.append({
                'constraint': '最后一天返程火车',
                'day': travel_days,
                'issue': f'缺少第{travel_days}天返程的火车信息',
                'severity': 'error'
            })
        
        # 验证火车时间不计入活动时间（这个在 check_constraint_4 中已经处理）
        
        return conflicts
    
    def check_constraint_8_9(self, solution: Dict, peoples: int, intra_city_trans: Dict) -> List[Dict]:
        """
        约束8&9: 房型均为双人间默认合租，打车一次可载4人
        """
        conflicts = []
        accommodations = solution.get('accommodations', [])
        
        if not accommodations:
            return conflicts
        
        hotel_data = accommodations[0].get('data', {})
        hotel_cost = float(hotel_data.get('cost', 0))
        rooms_needed = (peoples + 1) // 2  # 双人间，默认合租
        
        # 检查交通费用计算是否正确（出租车载客4人）
        transport_modes = solution.get('transport_mode', {})
        travel_days = len(solution.get('attractions', {}))
        hotel_id = accommodations[0].get('id')
        
        for day in range(1, travel_days + 1):
            if day not in solution.get('attractions', {}):
                continue
            
            attr_id = solution['attractions'][day].get('id')
            mode = transport_modes.get(day, 'taxi')
            
            if mode == 'taxi':
                # 检查是否需要多辆出租车
                if peoples > self.TAXI_CAPACITY:
                    # 这个在预算检查中会处理，这里只做警告
                    conflicts.append({
                        'constraint': '出租车载客数',
                        'day': day,
                        'issue': f'第{day}天人数({peoples}人)超过出租车载客数({self.TAXI_CAPACITY}人)，需要多辆车',
                        'severity': 'warning'
                    })
        
        return conflicts
    
    def check_budget(self, solution: Dict, travel_days: int, peoples: int, budget: Optional[float], intra_city_trans: Dict) -> List[Dict]:
        """
        约束11: 预算约束检查（如果提供了预算）
        """
        if budget is None:
            return []  # 无预算限制
        
        conflicts = []
        total_cost = 0
        
        # 住宿费用（双人间，合租，不包括最后一天）
        accommodations = solution.get('accommodations', [])
        if accommodations:
            hotel_data = accommodations[0].get('data', {})
            hotel_cost = float(hotel_data.get('cost', 0))
            rooms_needed = (peoples + 1) // 2
            hotel_total = hotel_cost * (travel_days - 1) * rooms_needed
            total_cost += hotel_total
        
        # 景点费用
        for day in range(1, travel_days + 1):
            if day in solution.get('attractions', {}):
                attr_data = solution['attractions'][day].get('data', {})
                total_cost += float(attr_data.get('cost', 0)) * peoples
        
        # 餐饮费用
        for day in range(1, travel_days + 1):
            restaurants = solution.get('restaurants', {}).get(day, [])
            for rest in restaurants:
                rest_data = rest.get('data', {})
                total_cost += float(rest_data.get('cost', 0)) * peoples
        
        # 市内交通费用
        if accommodations:
            hotel_id = accommodations[0].get('id')
            transport_modes = solution.get('transport_mode', {})
            
            for day in range(1, travel_days + 1):
                if day not in solution.get('attractions', {}):
                    continue
                
                attr_id = solution['attractions'][day].get('id')
                mode = transport_modes.get(day, 'taxi')
                
                if day == travel_days:
                    # 最后一天：酒店→景点
                    if mode == 'taxi':
                        taxi_trips = (peoples + self.TAXI_CAPACITY - 1) // self.TAXI_CAPACITY
                        cost = self._get_transport_params(intra_city_trans, hotel_id, attr_id, 'taxi_cost')
                        total_cost += taxi_trips * cost
                    else:
                        cost = self._get_transport_params(intra_city_trans, hotel_id, attr_id, 'bus_cost')
                        total_cost += peoples * cost
                else:
                    # 其他天：酒店↔景点（往返）
                    if mode == 'taxi':
                        taxi_trips = (peoples + self.TAXI_CAPACITY - 1) // self.TAXI_CAPACITY
                        cost1 = self._get_transport_params(intra_city_trans, hotel_id, attr_id, 'taxi_cost')
                        cost2 = self._get_transport_params(intra_city_trans, attr_id, hotel_id, 'taxi_cost')
                        total_cost += taxi_trips * (cost1 + cost2)
                    else:
                        cost1 = self._get_transport_params(intra_city_trans, hotel_id, attr_id, 'bus_cost')
                        cost2 = self._get_transport_params(intra_city_trans, attr_id, hotel_id, 'bus_cost')
                        total_cost += peoples * (cost1 + cost2)
        
        # 火车费用
        if solution.get('train_departure'):
            train_data = solution['train_departure'].get('data', {})
            total_cost += float(train_data.get('cost', 0)) * peoples
        
        if solution.get('train_back'):
            train_data = solution['train_back'].get('data', {})
            total_cost += float(train_data.get('cost', 0)) * peoples
        
        if total_cost > budget:
            conflicts.append({
                'constraint': '预算约束',
                'issue': f'总费用{total_cost:.2f}元超过预算{budget:.2f}元',
                'actual_cost': total_cost,
                'budget': budget,
                'severity': 'error'
            })
        
        return conflicts
    
    def check_solution(self, 
                      solution: Dict, 
                      travel_days: int, 
                      peoples: int = 1,
                      budget: Optional[float] = None,
                      intra_city_trans: Optional[Dict] = None) -> Dict:
        """
        检查行程方案的所有约束条件
        
        Args:
            solution: planner 生成的行程方案
            travel_days: 旅行天数
            peoples: 人数
            budget: 预算（可选）
            intra_city_trans: 市内交通数据（通过参数传入，可选）
            
        Returns:
            包含冲突检测结果的字典
        """
        conflicts = []
        
        # 使用传入的市内交通数据，如果没有则使用空字典
        if intra_city_trans is None:
            intra_city_trans = {}
        
        # 约束1: 每日景点、餐饮、住宿数量
        conflicts.extend(self.check_constraint_1(solution, travel_days))
        
        # 约束2&3: 市内通勤安排
        conflicts.extend(self.check_constraint_2_3(solution, travel_days, intra_city_trans))
        
        # 约束4: 每日活动时间限制
        conflicts.extend(self.check_constraint_4(solution, travel_days, intra_city_trans))
        
        # 约束5&6: 火车时间和费用
        conflicts.extend(self.check_constraint_5_6(solution, travel_days))
        
        # 约束8&9: 房型和出租车载客
        conflicts.extend(self.check_constraint_8_9(solution, peoples, intra_city_trans))
        
        # 约束11: 预算约束
        conflicts.extend(self.check_budget(solution, travel_days, peoples, budget, intra_city_trans))
        
        # 分类冲突
        errors = [c for c in conflicts if c.get('severity') == 'error']
        warnings = [c for c in conflicts if c.get('severity') == 'warning']
        
        return {
            'has_conflicts': len(conflicts) > 0,
            'total_conflicts': len(conflicts),
            'errors': len(errors),
            'warnings': len(warnings),
            'conflicts': conflicts,
            'error_list': errors,
            'warning_list': warnings,
            'is_valid': len(errors) == 0  # 只有当没有错误时才认为方案有效
        }
    
    def provide_feedback(self, 
                        solution: Dict,
                        travel_days: int,
                        peoples: int = 1,
                        budget: Optional[float] = None,
                        intra_city_trans: Optional[Dict] = None) -> Dict:
        """
        提供反馈信息
        
        Args:
            solution: planner 生成的行程方案
            travel_days: 旅行天数
            peoples: 人数
            budget: 预算（可选）
            intra_city_trans: 市内交通数据（通过参数传入，可选）
            
        Returns:
            包含反馈信息的字典
        """
        check_result = self.check_solution(solution, travel_days, peoples, budget, intra_city_trans)
        
        feedback = {
            'status': 'valid' if check_result['is_valid'] else 'invalid',
            'summary': f"检测到 {check_result['errors']} 个错误和 {check_result['warnings']} 个警告",
            'check_result': check_result,
            'recommendations': []
        }
        
        # 生成改进建议
        if check_result['errors'] > 0:
            feedback['recommendations'].append("请修复所有错误以确保方案可行")
        
        if check_result['warnings'] > 0:
            feedback['recommendations'].append("请检查警告信息，优化方案质量")
        
        # 针对具体冲突的建议
        for conflict in check_result['error_list']:
            if 'day' in conflict:
                feedback['recommendations'].append(
                    f"第{conflict['day']}天: {conflict['issue']}"
                )
        
        return feedback

