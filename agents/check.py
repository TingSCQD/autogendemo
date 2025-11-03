import autogen
import sys
import os
from typing import Dict, List, Optional, Tuple
import math

# 添加父目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import AGENT_CONFIG


class CheckAgent:
    """
    检查 Agent，负责综合实际情况的冲突检测和不合常理的规划甄别
    判断方案是否符合实际条件，并提供详细解释
    """
    
    def __init__(self):
        self.agent = autogen.AssistantAgent(**AGENT_CONFIG["check"])
        
        # 合理性阈值
        self.MAX_TAXI_SPEED = 80  # 出租车最大平均速度（km/h）
        self.MIN_TAXI_SPEED = 10  # 出租车最小平均速度（km/h）
        self.MAX_BUS_SPEED = 60  # 公交最大平均速度（km/h）
        self.MIN_BUS_SPEED = 10  # 公交最小平均速度（km/h）
        self.MAX_CITY_DISTANCE = 100  # 城市内最大合理距离（km）
        self.MIN_REALISTIC_TIME = 5  # 最短合理交通时间（分钟）
        self.MAX_DISTANCE_FOR_TIME = {
            'taxi': 0.8,  # 出租车：时间(分钟) * 0.8 = 最大合理距离(km)
            'bus': 0.5   # 公交：时间(分钟) * 0.5 = 最大合理距离(km)
        }
    
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
    
    def _estimate_distance_from_time(self, duration: float, mode: str) -> float:
        """
        根据时间和交通方式估算距离
        
        Args:
            duration: 时间（分钟）
            mode: 交通方式（'taxi' 或 'bus'）
            
        Returns:
            估算的距离（km）
        """
        if mode == 'taxi':
            # 假设平均速度 30-50 km/h，取中值 40 km/h = 0.67 km/min
            avg_speed_km_per_min = self.MAX_TAXI_SPEED / 60 * 0.5  # 取最大速度的一半作为平均
            return duration * avg_speed_km_per_min
        else:  # bus
            # 假设平均速度 20-40 km/h，取中值 30 km/h = 0.5 km/min
            avg_speed_km_per_min = self.MAX_BUS_SPEED / 60 * 0.5
            return duration * avg_speed_km_per_min
    
    def _calculate_speed(self, duration: float, estimated_distance: float) -> float:
        """
        计算实际速度
        
        Args:
            duration: 时间（分钟）
            estimated_distance: 估算距离（km）
            
        Returns:
            速度（km/h），如果无法计算返回0
        """
        if duration <= 0:
            return 0
        return (estimated_distance / duration) * 60  # 转换为 km/h
    
    def check_realistic_transport_time(self, 
                                      solution: Dict, 
                                      travel_days: int, 
                                      intra_city_trans: Dict) -> List[Dict]:
        """
        检查交通时间的合理性
        例如：10分钟跨越100km这种不合常理的情况
        """
        issues = []
        accommodations = solution.get('accommodations', [])
        transport_modes = solution.get('transport_mode', {})
        
        if not accommodations:
            return issues
        
        hotel_id = accommodations[0].get('id')
        
        for day in range(1, travel_days + 1):
            if day not in solution.get('attractions', {}):
                continue
            
            attr_id = solution['attractions'][day].get('id')
            mode = transport_modes.get(day, 'taxi')
            
            if day == travel_days:
                # 最后一天：酒店→景点（单程）
                duration = self._get_transport_params(intra_city_trans, hotel_id, attr_id, 
                                                     'taxi_duration' if mode == 'taxi' else 'bus_duration')
                
                if duration > 0:
                    # 估算距离
                    estimated_distance = self._estimate_distance_from_time(duration, mode)
                    
                    # 检查时间是否过短但可能距离过远
                    if duration < self.MIN_REALISTIC_TIME:
                        max_distance = duration * self.MAX_DISTANCE_FOR_TIME.get(mode, 0.6)
                        if estimated_distance > max_distance:
                            issues.append({
                                'type': 'unrealistic_time_distance',
                                'day': day,
                                'issue': f'第{day}天：{mode}从酒店到景点仅需{duration:.1f}分钟，但可能距离过远（估算{estimated_distance:.2f}km），不合常理',
                                'duration': duration,
                                'estimated_distance': estimated_distance,
                                'max_realistic_distance': max_distance,
                                'severity': 'error',
                                'explanation': f'正常情况下，{duration:.1f}分钟只能行驶约{max_distance:.2f}km，但估算距离为{estimated_distance:.2f}km，存在矛盾'
                            })
                    
                    # 检查速度是否合理
                    speed = self._calculate_speed(duration, estimated_distance)
                    if mode == 'taxi':
                        if speed > self.MAX_TAXI_SPEED:
                            issues.append({
                                'type': 'unrealistic_speed',
                                'day': day,
                                'issue': f'第{day}天：出租车速度{speed:.1f}km/h超过合理范围（最大{self.MAX_TAXI_SPEED}km/h）',
                                'speed': speed,
                                'max_speed': self.MAX_TAXI_SPEED,
                                'severity': 'error',
                                'explanation': f'城市内出租车平均速度通常不超过{self.MAX_TAXI_SPEED}km/h，当前速度为{speed:.1f}km/h不合理'
                            })
                        elif speed < self.MIN_TAXI_SPEED and duration > 5:
                            issues.append({
                                'type': 'too_slow',
                                'day': day,
                                'issue': f'第{day}天：出租车速度{speed:.1f}km/h过低（低于{self.MIN_TAXI_SPEED}km/h），可能交通拥堵或路线不合理',
                                'speed': speed,
                                'min_speed': self.MIN_TAXI_SPEED,
                                'severity': 'warning',
                                'explanation': f'城市内正常行驶速度应不低于{self.MIN_TAXI_SPEED}km/h，当前速度{speed:.1f}km/h可能存在问题'
                            })
                    else:  # bus
                        if speed > self.MAX_BUS_SPEED:
                            issues.append({
                                'type': 'unrealistic_speed',
                                'day': day,
                                'issue': f'第{day}天：公交速度{speed:.1f}km/h超过合理范围（最大{self.MAX_BUS_SPEED}km/h）',
                                'speed': speed,
                                'max_speed': self.MAX_BUS_SPEED,
                                'severity': 'error',
                                'explanation': f'城市内公交平均速度通常不超过{self.MAX_BUS_SPEED}km/h，当前速度为{speed:.1f}km/h不合理'
                            })
            else:
                # 其他天：酒店↔景点（往返）
                duration1 = self._get_transport_params(intra_city_trans, hotel_id, attr_id,
                                                       'taxi_duration' if mode == 'taxi' else 'bus_duration')
                duration2 = self._get_transport_params(intra_city_trans, attr_id, hotel_id,
                                                       'taxi_duration' if mode == 'taxi' else 'bus_duration')
                
                total_duration = duration1 + duration2
                
                if duration1 > 0 and duration2 > 0:
                    # 检查往返时间是否合理
                    estimated_distance = self._estimate_distance_from_time(duration1, mode)
                    
                    # 检查单程时间
                    for i, duration in enumerate([duration1, duration2], 1):
                        if duration < self.MIN_REALISTIC_TIME:
                            max_distance = duration * self.MAX_DISTANCE_FOR_TIME.get(mode, 0.6)
                            if estimated_distance > max_distance:
                                direction = '去程' if i == 1 else '返程'
                                issues.append({
                                    'type': 'unrealistic_time_distance',
                                    'day': day,
                                    'issue': f'第{day}天：{direction}仅需{duration:.1f}分钟但可能距离过远（估算{estimated_distance:.2f}km），不合常理',
                                    'duration': duration,
                                    'estimated_distance': estimated_distance,
                                    'max_realistic_distance': max_distance,
                                    'severity': 'error',
                                    'explanation': f'{direction}时间{duration:.1f}分钟与估算距离{estimated_distance:.2f}km不匹配'
                                })
        
        return issues
    
    def check_activity_sequence(self, solution: Dict, travel_days: int, intra_city_trans: Dict) -> List[Dict]:
        """
        检查活动安排的合理性
        例如：景点和餐厅之间的距离是否合理
        """
        issues = []
        accommodations = solution.get('accommodations', [])
        
        if not accommodations:
            return issues
        
        hotel_id = accommodations[0].get('id')
        
        for day in range(1, travel_days + 1):
            if day not in solution.get('attractions', {}):
                continue
            
            attr_id = solution['attractions'][day].get('id')
            restaurants = solution.get('restaurants', {}).get(day, [])
            
            # 检查景点和酒店距离是否在城市合理范围内
            hotel_to_attr_duration = self._get_transport_params(intra_city_trans, hotel_id, attr_id, 'taxi_duration')
            if hotel_to_attr_duration > 0:
                estimated_distance = self._estimate_distance_from_time(hotel_to_attr_duration, 'taxi')
                if estimated_distance > self.MAX_CITY_DISTANCE:
                    issues.append({
                        'type': 'excessive_distance',
                        'day': day,
                        'issue': f'第{day}天：酒店到景点距离约{estimated_distance:.2f}km，超过城市内合理距离（{self.MAX_CITY_DISTANCE}km）',
                        'distance': estimated_distance,
                        'max_distance': self.MAX_CITY_DISTANCE,
                        'severity': 'error',
                        'explanation': f'同一城市内，酒店到景点的距离通常不超过{self.MAX_CITY_DISTANCE}km，当前距离{estimated_distance:.2f}km可能不合理'
                    })
            
            # 检查餐厅是否都距离景点过远（如果所有餐厅都距离很远，可能不合理）
            if restaurants:
                far_restaurants = []
                for rest in restaurants:
                    rest_id = rest.get('id')
                    if rest_id:
                        # 估算餐厅到景点的时间（如果有数据）
                        # 这里简化处理，实际应该查询餐厅的位置数据
                        pass
        
        return issues
    
    def check_train_schedule_reasonableness(self, solution: Dict) -> List[Dict]:
        """
        检查火车时刻表的合理性
        例如：出发时间是否太早或太晚
        """
        issues = []
        
        train_departure = solution.get('train_departure')
        train_back = solution.get('train_back')
        
        # 检查是否有火车信息
        if not train_departure:
            issues.append({
                'type': 'missing_train',
                'issue': '缺少出发火车信息',
                'severity': 'error',
                'explanation': '方案必须包含第一天的出发火车信息'
            })
        
        if not train_back:
            issues.append({
                'type': 'missing_train',
                'issue': '缺少返程火车信息',
                'severity': 'error',
                'explanation': '方案必须包含最后一天的返程火车信息'
            })
        
        return issues
    
    def check_data_consistency(self, solution: Dict, travel_days: int, intra_city_trans: Dict) -> List[Dict]:
        """
        检查数据一致性
        例如：往返时间是否对称（去程和返程时间应该相近）
        """
        issues = []
        accommodations = solution.get('accommodations', [])
        transport_modes = solution.get('transport_mode', {})
        
        if not accommodations:
            return issues
        
        hotel_id = accommodations[0].get('id')
        
        for day in range(1, travel_days):
            if day not in solution.get('attractions', {}):
                continue
            
            attr_id = solution['attractions'][day].get('id')
            mode = transport_modes.get(day, 'taxi')
            
            duration_type = 'taxi_duration' if mode == 'taxi' else 'bus_duration'
            duration1 = self._get_transport_params(intra_city_trans, hotel_id, attr_id, duration_type)
            duration2 = self._get_transport_params(intra_city_trans, attr_id, hotel_id, duration_type)
            
            if duration1 > 0 and duration2 > 0:
                # 检查往返时间差异是否过大（超过50%认为不合理）
                time_diff_ratio = abs(duration1 - duration2) / max(duration1, duration2)
                if time_diff_ratio > 0.5:
                    issues.append({
                        'type': 'asymmetric_time',
                        'day': day,
                        'issue': f'第{day}天：酒店↔景点往返时间差异过大（去程{duration1:.1f}分钟，返程{duration2:.1f}分钟）',
                        'duration1': duration1,
                        'duration2': duration2,
                        'difference_ratio': time_diff_ratio,
                        'severity': 'warning',
                        'explanation': f'正常情况下往返时间应该相近，但去程{duration1:.1f}分钟与返程{duration2:.1f}分钟差异过大（{time_diff_ratio*100:.1f}%），可能存在数据错误'
                    })
        
        return issues
    
    def comprehensive_check(self,
                           solution: Dict,
                           travel_days: int,
                           peoples: int = 1,
                           budget: Optional[float] = None,
                           feedback_result: Optional[Dict] = None,
                           intra_city_trans: Optional[Dict] = None) -> Dict:
        """
        综合检查行程方案的合理性和实际可行性
        
        Args:
            solution: planner 生成的行程方案
            travel_days: 旅行天数
            peoples: 人数
            budget: 预算（可选）
            feedback_result: FeedbackAgent 的检查结果（通过参数传入，可选）
            intra_city_trans: 市内交通数据（通过参数传入，可选）
            
        Returns:
            包含检查结果的字典，包含是否符合条件的判断和详细解释
        """
        # 如果没有传入 feedback_result，创建一个空的结果
        if feedback_result is None:
            feedback_result = {
                'error_list': [],
                'warning_list': [],
                'is_valid': True
            }
        
        # 使用传入的市内交通数据，如果没有则使用空字典
        if intra_city_trans is None:
            intra_city_trans = {}
        
        # 合理性检查
        realistic_issues = []
        
        # 1. 检查交通时间合理性
        realistic_issues.extend(self.check_realistic_transport_time(solution, travel_days, intra_city_trans))
        
        # 2. 检查活动序列合理性
        realistic_issues.extend(self.check_activity_sequence(solution, travel_days, intra_city_trans))
        
        # 3. 检查火车时刻表合理性
        realistic_issues.extend(self.check_train_schedule_reasonableness(solution))
        
        # 4. 检查数据一致性
        realistic_issues.extend(self.check_data_consistency(solution, travel_days, intra_city_trans))
        
        # 分类问题
        realistic_errors = [i for i in realistic_issues if i.get('severity') == 'error']
        realistic_warnings = [i for i in realistic_issues if i.get('severity') == 'warning']
        
        # 综合判断
        total_errors = len(feedback_result['error_list']) + len(realistic_errors)
        total_warnings = len(feedback_result['warning_list']) + len(realistic_warnings)
        is_valid = (len(feedback_result['error_list']) == 0 and len(realistic_errors) == 0)
        
        # 生成详细解释
        explanations = []
        
        if not is_valid:
            explanations.append("方案不符合条件，原因如下：")
            
            if feedback_result['error_list']:
                explanations.append(f"\n约束条件错误（{len(feedback_result['error_list'])}个）：")
                for error in feedback_result['error_list']:
                    explanations.append(f"  - {error.get('issue', '未知错误')}")
            
            if realistic_errors:
                explanations.append(f"\n合理性错误（{len(realistic_errors)}个）：")
                for error in realistic_errors:
                    explanations.append(f"  - {error.get('issue', '未知错误')}")
                    if 'explanation' in error:
                        explanations.append(f"    说明：{error['explanation']}")
        else:
            explanations.append("方案基本符合条件。")
            if total_warnings > 0:
                explanations.append(f"\n但存在{total_warnings}个警告，建议优化：")
                for warning in feedback_result['warning_list']:
                    explanations.append(f"  - {warning.get('issue', '未知警告')}")
                for warning in realistic_warnings:
                    explanations.append(f"  - {warning.get('issue', '未知警告')}")
                    if 'explanation' in warning:
                        explanations.append(f"    说明：{warning['explanation']}")
        
        return {
            'is_valid': is_valid,
            'status': 'valid' if is_valid else 'invalid',
            'summary': f"检测到 {total_errors} 个错误和 {total_warnings} 个警告",
            'explanation': '\n'.join(explanations),
            'constraint_check': feedback_result,
            'realistic_check': {
                'has_issues': len(realistic_issues) > 0,
                'total_issues': len(realistic_issues),
                'errors': len(realistic_errors),
                'warnings': len(realistic_warnings),
                'issues': realistic_issues,
                'error_list': realistic_errors,
                'warning_list': realistic_warnings
            },
            'total_errors': total_errors,
            'total_warnings': total_warnings
        }
    
    def check_and_explain(self,
                          solution: Dict,
                          travel_days: int,
                          peoples: int = 1,
                          budget: Optional[float] = None,
                          feedback_result: Optional[Dict] = None,
                          intra_city_trans: Optional[Dict] = None) -> Dict:
        """
        检查方案并提供详细解释
        
        Args:
            solution: planner 生成的行程方案
            travel_days: 旅行天数
            peoples: 人数
            budget: 预算（可选）
            feedback_result: FeedbackAgent 的检查结果（通过参数传入，可选）
            intra_city_trans: 市内交通数据（通过参数传入，可选）
            
        Returns:
            包含判断结果和详细解释的字典
        """
        result = self.comprehensive_check(solution, travel_days, peoples, budget, feedback_result, intra_city_trans)
        
        return {
            'is_valid': result['is_valid'],
            'judgment': '符合条件' if result['is_valid'] else '不符合条件',
            'explanation': result['explanation'],
            'details': result
        }

