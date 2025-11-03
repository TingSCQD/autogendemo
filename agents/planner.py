import autogen
import sys
import os
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING
import pyomo.environ as pyo
from pyomo.opt import SolverStatus, TerminationCondition

# 添加父目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import AGENT_CONFIG, TRAVEL_API_BASE_URL, TRAVEL_API_TIMEOUT

if TYPE_CHECKING:
    from agents.researcher import ResearcherAgent


class PlannerAgent:
    """
    行程规划 Agent，负责基于约束条件进行符号化建模并生成初步行程方案
    """
    
    def __init__(self):
        self.agent = autogen.AssistantAgent(**AGENT_CONFIG["planner"])
        self.api_timeout = TRAVEL_API_TIMEOUT
        
        # 约束条件常量
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
    
    def fetch_data(self, researcher, origin_city: str, destination_city: str) -> Tuple[Dict, Dict, Dict, Dict]:
        """
        从 API 获取所需数据
        
        Args:
            researcher: ResearcherAgent 实例（通过参数传入）
            origin_city: 出发城市
            destination_city: 目的地城市
        """
        cross_city_train_departure = researcher.get_cross_city_transport(origin_city, destination_city) or []
        cross_city_train_back = researcher.get_cross_city_transport(destination_city, origin_city) or []
        
        poi_data = {
            'attractions': researcher.get_attractions(destination_city) or [],
            'accommodations': researcher.get_accommodations(destination_city) or [],
            'restaurants': researcher.get_restaurants(destination_city) or []
        }
        
        intra_city_trans = researcher.get_intra_city_transport(destination_city) or {}
        
        return cross_city_train_departure, cross_city_train_back, poi_data, intra_city_trans
    
    def build_model(
        self,
        cross_city_train_departure: List[Dict],
        cross_city_train_back: List[Dict],
        poi_data: Dict,
        intra_city_trans: Dict,
        travel_days: int,
        peoples: int = 1,
        budget: Optional[float] = None,
        prefer_taxi: bool = True
    ) -> pyo.ConcreteModel:
        """
        构建优化模型
        
        约束条件：
        1. 每日应选择一个景点、三个餐饮、一个住宿以及住宿和景点间的交通方式
        2. 每天固定两次市内通勤，即住宿和景点的往返
        3. 最后一天无住宿，最后一天的交通为前一晚酒店与最后一天景点间的交通
        4. 每日活动时间小于等于840分钟
        5. 出发/返程火车乘坐时间不计入每日活动时间
        6. 火车费用计入对应日期
        7. 第一天上午出发，最后一天返程
        8. 房型均为双人间、无额外说明则默认合租
        9. 打车一次可载4人
        10. 忽略出发城市的市内通勤过程
        11. 若未提及预算，则默认不限制预算
        12. 求解器限制为scip求解器
        """
        model = pyo.ConcreteModel()
        
        # 定义集合
        days = list(range(1, travel_days + 1))
        model.days = pyo.Set(initialize=days)
        
        # 最后一天索引
        last_day = travel_days
        
        # 构建数据字典
        attraction_dict = {a['id']: a for a in poi_data['attractions']}
        hotel_dict = {h['id']: h for h in poi_data['accommodations']}
        restaurant_dict = {r['id']: r for r in poi_data['restaurants']}
        train_departure_dict = {t['train_number']: t for t in cross_city_train_departure}
        train_back_dict = {t['train_number']: t for t in cross_city_train_back}
        
        model.attractions = pyo.Set(initialize=attraction_dict.keys())
        model.accommodations = pyo.Set(initialize=hotel_dict.keys())
        model.restaurants = pyo.Set(initialize=restaurant_dict.keys())
        model.train_departure = pyo.Set(initialize=train_departure_dict.keys())
        model.train_back = pyo.Set(initialize=train_back_dict.keys())
        
        # 定义参数
        model.attr_data = pyo.Param(
            model.attractions,
            initialize=lambda m, a: {
                'id': attraction_dict[a]['id'],
                'name': attraction_dict[a]['name'],
                'cost': float(attraction_dict[a].get('cost', 0)),
                'type': attraction_dict[a].get('type', ''),
                'rating': float(attraction_dict[a].get('rating', 0)),
                'duration': float(attraction_dict[a].get('duration', 0))
            }
        )
        
        model.hotel_data = pyo.Param(
            model.accommodations,
            initialize=lambda m, h: {
                'id': hotel_dict[h]['id'],
                'name': hotel_dict[h]['name'],
                'cost': float(hotel_dict[h].get('cost', 0)),
                'type': hotel_dict[h].get('type', ''),
                'rating': float(hotel_dict[h].get('rating', 0)),
                'feature': hotel_dict[h].get('feature', '')
            }
        )
        
        model.rest_data = pyo.Param(
            model.restaurants,
            initialize=lambda m, r: {
                'id': restaurant_dict[r]['id'],
                'name': restaurant_dict[r]['name'],
                'cost': float(restaurant_dict[r].get('cost', 0)),
                'type': restaurant_dict[r].get('type', ''),
                'rating': float(restaurant_dict[r].get('rating', 0)),
                'queue_time': float(restaurant_dict[r].get('queue_time', 0)),
                'duration': float(restaurant_dict[r].get('duration', 0))
            }
        )
        
        model.train_departure_data = pyo.Param(
            model.train_departure,
            initialize=lambda m, t: {
                'train_number': train_departure_dict[t]['train_number'],
                'cost': float(train_departure_dict[t].get('cost', 0)),
                'duration': float(train_departure_dict[t].get('duration', 0)),
                'origin_id': train_departure_dict[t].get('origin_id', ''),
                'origin_station': train_departure_dict[t].get('origin_station', ''),
                'destination_id': train_departure_dict[t].get('destination_id', ''),
                'destination_station': train_departure_dict[t].get('destination_station', '')
            }
        )
        
        model.train_back_data = pyo.Param(
            model.train_back,
            initialize=lambda m, t: {
                'train_number': train_back_dict[t]['train_number'],
                'cost': float(train_back_dict[t].get('cost', 0)),
                'duration': float(train_back_dict[t].get('duration', 0)),
                'origin_id': train_back_dict[t].get('origin_id', ''),
                'origin_station': train_back_dict[t].get('origin_station', ''),
                'destination_id': train_back_dict[t].get('destination_id', ''),
                'destination_station': train_back_dict[t].get('destination_station', '')
            }
        )
        
        # 定义变量
        # 每日选择的景点
        model.select_attr = pyo.Var(model.days, model.attractions, domain=pyo.Binary)
        
        # 住宿选择（不包括最后一天）
        model.select_hotel = pyo.Var(model.accommodations, domain=pyo.Binary)
        
        # 每日选择的餐厅
        model.select_rest = pyo.Var(model.days, model.restaurants, domain=pyo.Binary)
        
        # 交通方式：0=出租车，1=公交
        model.trans_mode = pyo.Var(model.days, domain=pyo.Binary)
        
        # 出发/返程火车选择
        model.select_train_departure = pyo.Var(model.train_departure, domain=pyo.Binary)
        model.select_train_back = pyo.Var(model.train_back, domain=pyo.Binary)
        
        # 景点-酒店关联变量（用于计算交通费用和时间）
        model.attr_hotel = pyo.Var(
            model.days, model.attractions, model.accommodations,
            domain=pyo.Binary
        )
        
        # 约束条件1: 链接景点和酒店
        def link_attr_hotel_rule1(model, d, a, h):
            return model.attr_hotel[d, a, h] <= model.select_attr[d, a]
        
        def link_attr_hotel_rule2(model, d, a, h):
            # 最后一天不需要酒店
            if d == last_day:
                return pyo.Constraint.Skip
            return model.attr_hotel[d, a, h] <= model.select_hotel[h]
        
        def link_attr_hotel_rule3(model, d, a, h):
            if d == last_day:
                return pyo.Constraint.Skip
            return model.attr_hotel[d, a, h] >= model.select_attr[d, a] + model.select_hotel[h] - 1
        
        model.link_attr_hotel1 = pyo.Constraint(
            model.days, model.attractions, model.accommodations,
            rule=link_attr_hotel_rule1
        )
        model.link_attr_hotel2 = pyo.Constraint(
            model.days, model.attractions, model.accommodations,
            rule=link_attr_hotel_rule2
        )
        model.link_attr_hotel3 = pyo.Constraint(
            model.days, model.attractions, model.accommodations,
            rule=link_attr_hotel_rule3
        )
        
        # 约束条件1: 每日选择一个景点
        model.one_attr_per_day = pyo.Constraint(
            model.days,
            rule=lambda m, d: sum(m.select_attr[d, a] for a in m.attractions) == 1
        )
        
        # 约束条件1: 每日三个餐饮
        model.three_meals_per_day = pyo.Constraint(
            model.days,
            rule=lambda m, d: sum(m.select_rest[d, r] for r in m.restaurants) == self.MEALS_PER_DAY
        )
        
        # 约束条件1: 选择一个住宿（不包括最后一天）
        model.one_hotel = pyo.Constraint(
            rule=lambda m: sum(m.select_hotel[h] for h in m.accommodations) == 1
        )
        
        # 约束条件: 每个景点最多被选择一次
        model.unique_attr = pyo.Constraint(
            model.attractions,
            rule=lambda m, a: sum(m.select_attr[d, a] for d in m.days) <= 1
        )
        
        # 约束条件: 每个餐厅最多被选择一次
        model.unique_rest = pyo.Constraint(
            model.restaurants,
            rule=lambda m, r: sum(m.select_rest[d, r] for d in m.days) <= 1
        )
        
        # 约束条件7: 第一天选择出发火车，最后一天选择返程火车
        model.single_train_departure = pyo.Constraint(
            rule=lambda m: sum(m.select_train_departure[t] for t in m.train_departure) == 1
        )
        
        model.single_train_back = pyo.Constraint(
            rule=lambda m: sum(m.select_train_back[t] for t in m.train_back) == 1
        )
        
        # 约束条件4: 每日活动时间 <= 840分钟
        # 活动时间包括：景点时间、餐饮时间（含排队）、市内交通时间（往返）
        # 不包括：出发/返程火车乘坐时间
        def time_rule(model, d):
            # 景点时间
            attr_time = sum(
                model.select_attr[d, a] * model.attr_data[a]['duration']
                for a in model.attractions
            )
            
            # 餐饮时间（含排队）
            rest_time = sum(
                model.select_rest[d, r] * (model.rest_data[r]['duration'] + model.rest_data[r]['queue_time'])
                for r in model.restaurants
            )
            
            # 市内交通时间（住宿-景点往返，最后一天为前一晚酒店-景点）
            # 创建一个辅助函数来获取交通参数
            def get_trans_param(origin_id, dest_id, param_type):
                for key in [f"{origin_id},{dest_id}", f"{dest_id},{origin_id}"]:
                    if key in intra_city_trans:
                        value = float(intra_city_trans[key].get(param_type, 0))
                        return value if value > 0 else 0.0
                return 0.0
            
            if d == last_day:
                # 最后一天：前一晚酒店 -> 景点（单程）
                trans_time = sum(
                    model.attr_hotel[d-1, a, h] * (
                        (1 - model.trans_mode[d]) * get_trans_param(h, a, 'taxi_duration') +
                        model.trans_mode[d] * get_trans_param(h, a, 'bus_duration')
                    )
                    for a in model.attractions
                    for h in model.accommodations
                )
            else:
                # 其他天：酒店 <-> 景点（往返两次通勤）
                trans_time = sum(
                    model.attr_hotel[d, a, h] * (
                        (1 - model.trans_mode[d]) * (
                            get_trans_param(h, a, 'taxi_duration') +
                            get_trans_param(a, h, 'taxi_duration')
                        ) +
                        model.trans_mode[d] * (
                            get_trans_param(h, a, 'bus_duration') +
                            get_trans_param(a, h, 'bus_duration')
                        )
                    )
                    for a in model.attractions
                    for h in model.accommodations
                )
            
            return attr_time + rest_time + trans_time <= self.MAX_DAILY_TIME
        
        model.time_con = pyo.Constraint(model.days, rule=time_rule)
        
        # 约束条件11: 预算约束（如果有预算限制）
        if budget is not None:
            def budget_rule(model):
                # 住宿费用（双人间，合租，不包括最后一天）
                rooms_needed = (peoples + 1) // 2  # 双人间，默认合租
                hotel_cost = sum(
                    model.select_hotel[h] * model.hotel_data[h]['cost'] * (travel_days - 1) * rooms_needed
                    for h in model.accommodations
                )
                
                # 景点费用
                attraction_cost = sum(
                    model.select_attr[d, a] * model.attr_data[a]['cost']
                    for d in model.days
                    for a in model.attractions
                ) * peoples
                
                # 餐饮费用
                restaurant_cost = sum(
                    model.select_rest[d, r] * model.rest_data[r]['cost']
                    for d in model.days
                    for r in model.restaurants
                ) * peoples
                
                # 市内交通费用
                def get_trans_cost(origin_id, dest_id, param_type):
                    for key in [f"{origin_id},{dest_id}", f"{dest_id},{origin_id}"]:
                        if key in intra_city_trans:
                            value = float(intra_city_trans[key].get(param_type, 0))
                            return value if value > 0 else 0.0
                    return 0.0
                
                transport_cost = 0
                for d in model.days:
                    if d == last_day:
                        # 最后一天：前一晚酒店 -> 景点
                        transport_cost += sum(
                            model.attr_hotel[d-1, a, h] * (
                                (1 - model.trans_mode[d]) * (
                                    # 打车：考虑载客数（4人）
                                    (peoples + self.TAXI_CAPACITY - 1) // self.TAXI_CAPACITY * 
                                    get_trans_cost(h, a, 'taxi_cost')
                                ) +
                                model.trans_mode[d] * (
                                    # 公交：按人数
                                    peoples * get_trans_cost(h, a, 'bus_cost')
                                )
                            )
                            for a in model.attractions
                            for h in model.accommodations
                        )
                    else:
                        # 其他天：酒店 <-> 景点（往返）
                        transport_cost += sum(
                            model.attr_hotel[d, a, h] * (
                                (1 - model.trans_mode[d]) * (
                                    # 打车：考虑载客数（往返两次）
                                    (peoples + self.TAXI_CAPACITY - 1) // self.TAXI_CAPACITY * (
                                        get_trans_cost(h, a, 'taxi_cost') +
                                        get_trans_cost(a, h, 'taxi_cost')
                                    )
                                ) +
                                model.trans_mode[d] * (
                                    # 公交：按人数（往返两次）
                                    peoples * (
                                        get_trans_cost(h, a, 'bus_cost') +
                                        get_trans_cost(a, h, 'bus_cost')
                                    )
                                )
                            )
                            for a in model.attractions
                            for h in model.accommodations
                        )
                
                # 火车费用（计入对应日期：第一天计入第一天，最后一天计入最后一天）
                train_departure_cost = sum(
                    model.select_train_departure[t] * model.train_departure_data[t]['cost']
                    for t in model.train_departure
                ) * peoples
                
                train_back_cost = sum(
                    model.select_train_back[t] * model.train_back_data[t]['cost']
                    for t in model.train_back
                ) * peoples
                
                return hotel_cost + attraction_cost + restaurant_cost + transport_cost + train_departure_cost + train_back_cost <= budget
            
            model.budget_con = pyo.Constraint(rule=budget_rule)
        
        # 约束条件9: 交通方式偏好（如果偏好打车，则尽量使用出租车）
        if prefer_taxi:
            # 可以通过目标函数体现偏好，或添加软约束
            pass
        
        # 目标函数：最大化评分（景点、餐厅、住宿的评分总和）
        def obj_rule(model):
            rating = (
                sum(model.select_attr[d, a] * model.attr_data[a]['rating']
                    for d in model.days for a in model.attractions) +
                sum(model.select_rest[d, r] * model.rest_data[r]['rating']
                    for d in model.days for r in model.restaurants) +
                sum(model.select_hotel[h] * model.hotel_data[h]['rating']
                    for h in model.accommodations)
            )
            return rating
        
        model.obj = pyo.Objective(rule=obj_rule, sense=pyo.maximize)
        
        return model
    
    def solve_model(self, model: pyo.ConcreteModel) -> Tuple[Dict, bool]:
        """
        求解模型
        
        约束条件12: 求解器限制为scip求解器
        """
        solver = pyo.SolverFactory('scip')
        
        # SCIP 求解器选项
        solver.options = {
            'limits/time': 300,  # 最大求解时间（秒）
            'limits/gap': 0.01,  # 相对最优性 gap
        }
        
        try:
            results = solver.solve(model, tee=False)
            
            if (results.solver.status == SolverStatus.ok and 
                results.solver.termination_condition == TerminationCondition.optimal):
                return self._extract_solution(model), True
            elif results.solver.termination_condition == TerminationCondition.feasible:
                # 找到可行解但不一定最优
                return self._extract_solution(model), True
            else:
                return {}, False
        except Exception as e:
            print(f"求解器错误: {e}")
            return {}, False
    
    def _extract_solution(self, model: pyo.ConcreteModel) -> Dict:
        """提取解"""
        solution = {
            'attractions': {},
            'accommodations': [],
            'restaurants': {},
            'train_departure': None,
            'train_back': None,
            'transport_mode': {}
        }
        
        # 提取景点
        for d in model.days:
            for a in model.attractions:
                if pyo.value(model.select_attr[d, a]) > 0.9:
                    solution['attractions'][d] = {
                        'id': model.attr_data[a]['id'],
                        'name': model.attr_data[a]['name'],
                        'data': dict(model.attr_data[a])
                    }
        
        # 提取住宿
        for h in model.accommodations:
            if pyo.value(model.select_hotel[h]) > 0.9:
                solution['accommodations'].append({
                    'id': model.hotel_data[h]['id'],
                    'name': model.hotel_data[h]['name'],
                    'data': dict(model.hotel_data[h])
                })
        
        # 提取餐厅
        for d in model.days:
            solution['restaurants'][d] = []
            for r in model.restaurants:
                if pyo.value(model.select_rest[d, r]) > 0.9:
                    solution['restaurants'][d].append({
                        'id': model.rest_data[r]['id'],
                        'name': model.rest_data[r]['name'],
                        'data': dict(model.rest_data[r])
                    })
        
        # 提取出发火车
        for t in model.train_departure:
            if pyo.value(model.select_train_departure[t]) > 0.9:
                solution['train_departure'] = {
                    'train_number': model.train_departure_data[t]['train_number'],
                    'data': dict(model.train_departure_data[t])
                }
        
        # 提取返程火车
        for t in model.train_back:
            if pyo.value(model.select_train_back[t]) > 0.9:
                solution['train_back'] = {
                    'train_number': model.train_back_data[t]['train_number'],
                    'data': dict(model.train_back_data[t])
                }
        
        # 提取交通方式
        for d in model.days:
            mode = 'taxi' if pyo.value(model.trans_mode[d]) < 0.5 else 'bus'
            solution['transport_mode'][d] = mode
        
        return solution
    
    def plan_trip(
        self,
        researcher,
        origin_city: str,
        destination_city: str,
        travel_days: int,
        peoples: int = 1,
        budget: Optional[float] = None,
        prefer_taxi: bool = True
    ) -> Dict:
        """
        规划行程
        
        Args:
            researcher: ResearcherAgent 实例（通过参数传入）
            origin_city: 出发城市
            destination_city: 目的地城市
            travel_days: 旅行天数
            peoples: 人数
            budget: 预算（可选，如果为None则不限制预算）
            prefer_taxi: 是否偏好出租车
            
        Returns:
            包含行程方案的字典
        """
        # 获取数据
        print(f"正在获取 {destination_city} 的 POI 数据和交通信息...")
        cross_city_train_departure, cross_city_train_back, poi_data, intra_city_trans = self.fetch_data(
            researcher, origin_city, destination_city
        )
        
        if not poi_data['attractions'] or not poi_data['accommodations'] or not poi_data['restaurants']:
            return {
                'success': False,
                'error': '数据不足，无法规划行程'
            }
        
        # 构建模型
        print("正在构建优化模型...")
        model = self.build_model(
            cross_city_train_departure,
            cross_city_train_back,
            poi_data,
            intra_city_trans,
            travel_days,
            peoples,
            budget,
            prefer_taxi
        )
        
        # 求解模型
        print("正在求解优化问题...")
        solution, success = self.solve_model(model)
        
        if not success:
            return {
                'success': False,
                'error': '无法找到可行解'
            }
        
        return {
            'success': True,
            'solution': solution,
            'origin_city': origin_city,
            'destination_city': destination_city,
            'travel_days': travel_days,
            'peoples': peoples,
            'budget': budget
        }

