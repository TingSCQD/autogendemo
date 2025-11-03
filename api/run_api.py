from flask import Flask, jsonify, request
from datetime import datetime
import pandas as pd
import json
import os
from pathlib import Path

app = Flask(__name__)

# 数据存储
data = {
    'attractions': None,
    'accommodations': None,
    'restaurants': None,
    'transport': None,
    'path_in_city': None,
    'path_cross_city': None,
    'city_info': None
}

# 数据文件路径
CSV_DIR = Path(__file__).parent / 'data'


def load_data():
    """加载所有CSV数据"""
    try:
        print("正在加载数据...")
        
        # 加载景点数据
        data['attractions'] = pd.read_csv(CSV_DIR / 'poi_attraction.csv')
        print(f"已加载 {len(data['attractions'])} 条景点数据")
        
        # 加载住宿数据
        data['accommodations'] = pd.read_csv(CSV_DIR / 'poi_accommodation.csv')
        print(f"已加载 {len(data['accommodations'])} 条住宿数据")
        
        # 加载餐饮数据
        data['restaurants'] = pd.read_csv(CSV_DIR / 'poi_restaurant.csv')
        print(f"已加载 {len(data['restaurants'])} 条餐饮数据")
        
        # 加载交通站点数据
        data['transport'] = pd.read_csv(CSV_DIR / 'poi_transport.csv')
        print(f"已加载 {len(data['transport'])} 条交通站点数据")
        
        # 加载市内路径规划数据
        data['path_in_city'] = pd.read_csv(CSV_DIR / 'path_planning_in_city.csv')
        print(f"已加载 {len(data['path_in_city'])} 条市内路径数据")
        
        # 加载跨城路径规划数据
        data['path_cross_city'] = pd.read_csv(CSV_DIR / 'path_planning_cross_city.csv')
        print(f"已加载 {len(data['path_cross_city'])} 条跨城路径数据")
        
        # 加载城市信息数据
        data['city_info'] = pd.read_csv(CSV_DIR / 'city_info.csv')
        print(f"已加载 {len(data['city_info'])} 条城市信息数据")
        
        print("所有数据加载完成!")
        return True
    except Exception as e:
        print(f"加载数据失败: {str(e)}")
        return False


def error_response(error, message, path, status_code, details=None):
    """统一的错误响应格式"""
    response = {
        "error": error,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "path": path
    }
    if details:
        response["details"] = details
    return jsonify(response), status_code


@app.route('/cross-city-transport/', methods=['GET'])
def get_cross_city_transport():
    """获取跨城市交通数据"""
    try:
        origin_city = request.args.get('origin_city', '').strip()
        destination_city = request.args.get('destination_city', '').strip()
        
        # 参数验证
        if not origin_city or not destination_city:
            return error_response(
                "Invalid Parameter",
                "出发城市和目的地城市不能为空",
                request.path,
                400
            )
        
        if origin_city == destination_city:
            return error_response(
                "Invalid Parameter",
                "出发城市和目的地城市不能相同",
                request.path,
                400
            )
        
        # 查找起点城市的交通站点
        origin_stations = data['transport'][data['transport']['city_name'] == origin_city]
        if origin_stations.empty:
            return error_response(
                "Data Not Found",
                f"未找到城市'{origin_city}'的交通站点",
                request.path,
                404
            )
        
        # 查找终点城市的交通站点
        dest_stations = data['transport'][data['transport']['city_name'] == destination_city]
        if dest_stations.empty:
            return error_response(
                "Data Not Found",
                f"未找到城市'{destination_city}'的交通站点",
                request.path,
                404
            )
        
        # 查找跨城市路径
        result = []
        for _, origin_row in origin_stations.iterrows():
            origin_id = origin_row['transport_id']
            for _, dest_row in dest_stations.iterrows():
                dest_id = dest_row['transport_id']
                
                # 查找路径记录
                path_records = data['path_cross_city'][
                    (data['path_cross_city']['origin_id'] == origin_id) &
                    (data['path_cross_city']['destination_id'] == dest_id)
                ]
                
                for _, path in path_records.iterrows():
                    train_info = {
                        "origin_id": origin_id,
                        "destination_id": dest_id,
                        "train_number": str(path['train_plan_train_number']),
                        "duration": str(int(path['train_plan_duration'])) if pd.notna(path['train_plan_duration']) else "0",
                        "cost": str(path['train_plan_cost']) if pd.notna(path['train_plan_cost']) else "0",
                        "origin_station": path['train_plan_origin_station'],
                        "destination_station": path['train_plan_destination_station']
                    }
                    result.append(train_info)
        
        if not result:
            return error_response(
                "Data Not Found",
                f"未找到从{origin_city}到{destination_city}的交通方案",
                request.path,
                404
            )
        
        return jsonify(result)
    
    except Exception as e:
        return error_response(
            "Internal Server Error",
            "服务器内部错误",
            request.path,
            500,
            str(e)
        )


@app.route('/attractions/<city_name>', methods=['GET'])
def get_attractions(city_name):
    """获取城市所有景点数据"""
    try:
        city_name = city_name.strip()
        
        if not city_name:
            return error_response(
                "Invalid Parameter",
                "城市名称不能为空",
                request.path,
                400
            )
        
        # 查询景点
        attractions = data['attractions'][data['attractions']['city_name'] == city_name]
        
        if attractions.empty:
            return error_response(
                "Data Not Found",
                f"未找到城市'{city_name}'的景点数据",
                request.path,
                404
            )
        
        result = []
        for _, row in attractions.iterrows():
            attraction = {
                "id": row['attraction_id'],
                "name": row['attraction_name'],
                "cost": float(row['avg_consumption']) if pd.notna(row['avg_consumption']) else 0.0,
                "type": row['attraction_type'] if pd.notna(row['attraction_type']) else "",
                "rating": float(row['rating']) if pd.notna(row['rating']) else 0.0,
                "duration": float(row['suggested_duration']) if pd.notna(row['suggested_duration']) else 0.0
            }
            result.append(attraction)
        
        return jsonify(result)
    
    except Exception as e:
        return error_response(
            "Internal Server Error",
            "服务器内部错误",
            request.path,
            500,
            str(e)
        )


@app.route('/accommodations/<city_name>', methods=['GET'])
def get_accommodations(city_name):
    """获取城市所有住宿数据"""
    try:
        city_name = city_name.strip()
        
        if not city_name:
            return error_response(
                "Invalid Parameter",
                "城市名称不能为空",
                request.path,
                400
            )
        
        # 查询住宿
        accommodations = data['accommodations'][data['accommodations']['city_name'] == city_name]
        
        if accommodations.empty:
            return error_response(
                "Data Not Found",
                f"未找到城市'{city_name}'的酒店数据",
                request.path,
                404
            )
        
        result = []
        for _, row in accommodations.iterrows():
            accommodation = {
                "id": row['accommodation_id'],
                "name": row['accommodation_name'],
                "cost": float(row['avg_price']) if pd.notna(row['avg_price']) else 0.0,
                "type": row['accommodation_type'] if pd.notna(row['accommodation_type']) else "",
                "rating": float(row['rating']) if pd.notna(row['rating']) else 0.0,
                "feature": row['feature_hotel_type'] if pd.notna(row['feature_hotel_type']) else ""
            }
            result.append(accommodation)
        
        return jsonify(result)
    
    except Exception as e:
        return error_response(
            "Internal Server Error",
            "服务器内部错误",
            request.path,
            500,
            str(e)
        )


@app.route('/restaurants/<city_name>', methods=['GET'])
def get_restaurants(city_name):
    """获取城市所有餐厅数据"""
    try:
        city_name = city_name.strip()
        
        if not city_name:
            return error_response(
                "Invalid Parameter",
                "城市名称不能为空",
                request.path,
                400
            )
        
        # 查询餐厅
        restaurants = data['restaurants'][data['restaurants']['city_name'] == city_name]
        
        if restaurants.empty:
            return error_response(
                "Data Not Found",
                f"未找到城市'{city_name}'的餐厅数据",
                request.path,
                404
            )
        
        result = []
        for _, row in restaurants.iterrows():
            restaurant = {
                "id": row['restaurant_id'],
                "name": row['restaurant_name'],
                "cost": float(row['avg_price']) if pd.notna(row['avg_price']) else 0.0,
                "type": row['restaurant_type'] if pd.notna(row['restaurant_type']) else "",
                "rating": float(row['rating']) if pd.notna(row['rating']) else 0.0,
                "recommended_food": row['recommended_food'] if pd.notna(row['recommended_food']) else "",
                "queue_time": float(row['queue_time']) if pd.notna(row['queue_time']) else 0.0,
                "duration": float(row['consumption_time']) if pd.notna(row['consumption_time']) else 0.0
            }
            result.append(restaurant)
        
        return jsonify(result)
    
    except Exception as e:
        return error_response(
            "Internal Server Error",
            "服务器内部错误",
            request.path,
            500,
            str(e)
        )


@app.route('/intra-city-transport/<city_name>', methods=['GET'])
def get_intra_city_transport(city_name):
    """获取市内交通数据"""
    try:
        city_name = city_name.strip()
        
        if not city_name:
            return error_response(
                "Invalid Parameter",
                "城市名称不能为空",
                request.path,
                400
            )
        
        # 查询市内路径
        paths = data['path_in_city'][data['path_in_city']['city_name'] == city_name]
        
        if paths.empty:
            return error_response(
                "Data Not Found",
                f"未找到城市'{city_name}'的市内交通数据",
                request.path,
                404
            )
        
        result = {}
        for _, row in paths.iterrows():
            key = f"{row['origin_id']},{row['destination_id']}"
            result[key] = {
                "taxi_duration": str(int(row['taxi_duration'])) if pd.notna(row['taxi_duration']) and row['taxi_duration'] > 0 else "0",
                "taxi_cost": str(row['taxi_cost']) if pd.notna(row['taxi_cost']) and float(row['taxi_cost']) > 0 else "0",
                "bus_duration": str(int(row['bus_duration'])) if pd.notna(row['bus_duration']) and row['bus_duration'] > 0 else "0",
                "bus_cost": str(int(row['bus_cost'])) if pd.notna(row['bus_cost']) and row['bus_cost'] > 0 else "0"
            }
        
        return jsonify(result)
    
    except Exception as e:
        return error_response(
            "Internal Server Error",
            "服务器内部错误",
            request.path,
            500,
            str(e)
        )


@app.route('/poi-data/<city_name>', methods=['GET'])
def get_poi_data(city_name):
    """获取城市所有POI数据"""
    try:
        city_name = city_name.strip()
        
        if not city_name:
            return error_response(
                "Invalid Parameter",
                "城市名称不能为空",
                request.path,
                400
            )
        
        # 获取景点数据
        attractions_data = data['attractions'][data['attractions']['city_name'] == city_name]
        attractions_list = []
        for _, row in attractions_data.iterrows():
            attractions_list.append({
                "id": row['attraction_id'],
                "name": row['attraction_name'],
                "cost": float(row['avg_consumption']) if pd.notna(row['avg_consumption']) else 0.0,
                "attraction_type": row['attraction_type'] if pd.notna(row['attraction_type']) else "",
                "rating": float(row['rating']) if pd.notna(row['rating']) else 0.0,
                "duration": str(int(row['suggested_duration'])) if pd.notna(row['suggested_duration']) else "0"
            })
        
        # 获取住宿数据
        accommodations_data = data['accommodations'][data['accommodations']['city_name'] == city_name]
        accommodations_list = []
        for _, row in accommodations_data.iterrows():
            accommodations_list.append({
                "id": row['accommodation_id'],
                "name": row['accommodation_name'],
                "cost": float(row['avg_price']) if pd.notna(row['avg_price']) else 0.0,
                "type": row['accommodation_type'] if pd.notna(row['accommodation_type']) else "",
                "rating": float(row['rating']) if pd.notna(row['rating']) else 0.0,
                "feature": row['feature_hotel_type'] if pd.notna(row['feature_hotel_type']) else ""
            })
        
        # 获取餐厅数据
        restaurants_data = data['restaurants'][data['restaurants']['city_name'] == city_name]
        restaurants_list = []
        for _, row in restaurants_data.iterrows():
            restaurants_list.append({
                "id": row['restaurant_id'],
                "name": row['restaurant_name'],
                "cost": float(row['avg_price']) if pd.notna(row['avg_price']) else 0.0,
                "rating": float(row['rating']) if pd.notna(row['rating']) else 0.0,
                "type": row['restaurant_type'] if pd.notna(row['restaurant_type']) else "",
                "recommended_food": row['recommended_food'] if pd.notna(row['recommended_food']) else "",
                "queue_time": int(row['queue_time']) if pd.notna(row['queue_time']) else 0,
                "duration": int(row['consumption_time']) if pd.notna(row['consumption_time']) else 0
            })
        
        if not attractions_list and not accommodations_list and not restaurants_list:
            return error_response(
                "Data Not Found",
                f"未找到城市'{city_name}'的POI数据",
                request.path,
                404
            )
        
        return jsonify({
            "attractions": attractions_list,
            "accommodations": accommodations_list,
            "restaurants": restaurants_list
        })
    
    except Exception as e:
        return error_response(
            "Internal Server Error",
            "服务器内部错误",
            request.path,
            500,
            str(e)
        )


@app.route('/poi/<poi_id>', methods=['GET'])
def get_poi_by_id(poi_id):
    """根据POI ID获取POI数据"""
    try:
        poi_id = poi_id.strip()
        
        if not poi_id:
            return error_response(
                "Invalid Parameter",
                "POI ID不能为空",
                request.path,
                400
            )
        
        # 在景点中查找
        attraction = data['attractions'][data['attractions']['attraction_id'] == poi_id]
        if not attraction.empty:
            row = attraction.iloc[0]
            return jsonify({
                "id": row['attraction_id'],
                "name": row['attraction_name'],
                "cost": float(row['avg_consumption']) if pd.notna(row['avg_consumption']) else 0.0,
                "type": row['attraction_type'] if pd.notna(row['attraction_type']) else "",
                "rating": float(row['rating']) if pd.notna(row['rating']) else 0.0,
                "duration": str(int(row['suggested_duration'])) if pd.notna(row['suggested_duration']) else "0",
                "city_name": row['city_name']
            })
        
        # 在住宿中查找
        accommodation = data['accommodations'][data['accommodations']['accommodation_id'] == poi_id]
        if not accommodation.empty:
            row = accommodation.iloc[0]
            return jsonify({
                "id": row['accommodation_id'],
                "name": row['accommodation_name'],
                "cost": float(row['avg_price']) if pd.notna(row['avg_price']) else 0.0,
                "type": row['accommodation_type'] if pd.notna(row['accommodation_type']) else "",
                "rating": float(row['rating']) if pd.notna(row['rating']) else 0.0,
                "city_name": row['city_name']
            })
        
        # 在餐厅中查找
        restaurant = data['restaurants'][data['restaurants']['restaurant_id'] == poi_id]
        if not restaurant.empty:
            row = restaurant.iloc[0]
            return jsonify({
                "id": row['restaurant_id'],
                "name": row['restaurant_name'],
                "cost": float(row['avg_price']) if pd.notna(row['avg_price']) else 0.0,
                "type": row['restaurant_type'] if pd.notna(row['restaurant_type']) else "",
                "rating": float(row['rating']) if pd.notna(row['rating']) else 0.0,
                "duration": int(row['consumption_time']) if pd.notna(row['consumption_time']) else 0,
                "city_name": row['city_name']
            })
        
        # 在交通站点中查找
        transport = data['transport'][data['transport']['transport_id'] == poi_id]
        if not transport.empty:
            row = transport.iloc[0]
            return jsonify({
                "id": row['transport_id'],
                "name": row['transport_name'],
                "type": row['transport_type'] if pd.notna(row['transport_type']) else "",
                "city_name": row['city_name']
            })
        
        return error_response(
            "Data Not Found",
            f"未找到ID为'{poi_id}'的POI",
            request.path,
            404
        )
    
    except Exception as e:
        return error_response(
            "Internal Server Error",
            "服务器内部错误",
            request.path,
            500,
            str(e)
        )


@app.route('/transport-params', methods=['POST'])
def get_transport_params():
    """获取两点间交通参数"""
    try:
        req_data = request.get_json()
        
        if not req_data:
            return error_response(
                "Validation Error",
                "请求参数验证失败",
                request.path,
                422,
                [{"type": "missing", "msg": "Request body required"}]
            )
        
        origin_id = req_data.get('origin_id', '').strip()
        destination_id = req_data.get('destination_id', '').strip()
        
        # 验证参数
        if not origin_id:
            return error_response(
                "Validation Error",
                "请求参数验证失败",
                request.path,
                422,
                [{"type": "missing", "loc": ["body", "origin_id"], "msg": "Field required", "input": req_data}]
            )
        
        if not destination_id:
            return error_response(
                "Validation Error",
                "请求参数验证失败",
                request.path,
                422,
                [{"type": "missing", "loc": ["body", "destination_id"], "msg": "Field required", "input": req_data}]
            )
        
        if origin_id == destination_id:
            return error_response(
                "Invalid Parameter",
                "起点ID和终点ID不能相同",
                request.path,
                400
            )
        
        # 查找路径
        path = data['path_in_city'][
            (data['path_in_city']['origin_id'] == origin_id) &
            (data['path_in_city']['destination_id'] == destination_id)
        ]
        
        if path.empty:
            return error_response(
                "Data Not Found",
                f"未找到从'{origin_id}'到'{destination_id}'的交通参数",
                request.path,
                404
            )
        
        row = path.iloc[0]
        return jsonify({
            "bus_duration": str(int(row['bus_duration'])) if pd.notna(row['bus_duration']) else "0",
            "bus_cost": str(int(row['bus_cost'])) if pd.notna(row['bus_cost']) else "0",
            "taxi_duration": str(int(row['taxi_duration'])) if pd.notna(row['taxi_duration']) else "0",
            "taxi_cost": str(row['taxi_cost']) if pd.notna(row['taxi_cost']) else "0"
        })
    
    except Exception as e:
        return error_response(
            "Internal Server Error",
            "服务器内部错误",
            request.path,
            500,
            str(e)
        )


@app.route('/train', methods=['GET'])
def get_train_by_number():
    """根据车次号获取列车信息"""
    try:
        train_number = request.args.get('train_number', '').strip()
        origin_id = request.args.get('origin_id', '').strip()
        destination_id = request.args.get('destination_id', '').strip()
        
        # 参数验证
        if not train_number:
            return error_response(
                "Validation Error",
                "请求参数验证失败",
                request.path,
                422,
                [{"type": "missing", "loc": ["query", "train_number"], "msg": "Field required"}]
            )
        
        if len(train_number) > 20:
            return error_response(
                "Validation Error",
                "请求参数验证失败",
                request.path,
                422,
                [{"type": "string_too_long", "loc": ["query", "train_number"], 
                  "msg": "String should have at most 20 characters", "input": train_number}]
            )
        
        if not origin_id or not destination_id:
            return error_response(
                "Invalid Parameter",
                "始发站ID和终点站ID不能为空",
                request.path,
                400
            )
        
        if origin_id == destination_id:
            return error_response(
                "Invalid Parameter",
                "始发站ID和终点站ID不能相同",
                request.path,
                400
            )
        
        # 查找列车信息
        train = data['path_cross_city'][
            (data['path_cross_city']['train_plan_train_number'].astype(str) == train_number) &
            (data['path_cross_city']['origin_id'] == origin_id) &
            (data['path_cross_city']['destination_id'] == destination_id)
        ]
        
        if train.empty:
            return error_response(
                "Data Not Found",
                f"未找到车次号为'{train_number}'的列车",
                request.path,
                404
            )
        
        row = train.iloc[0]
        
        # 获取城市信息
        origin_station = data['transport'][data['transport']['transport_id'] == origin_id]
        dest_station = data['transport'][data['transport']['transport_id'] == destination_id]
        
        return jsonify({
            "train_number": str(row['train_plan_train_number']),
            "origin_id": origin_id,
            "origin_city": origin_station.iloc[0]['city_name'] if not origin_station.empty else "",
            "origin_station": row['train_plan_origin_station'],
            "destination_id": destination_id,
            "destination_city": dest_station.iloc[0]['city_name'] if not dest_station.empty else "",
            "destination_station": row['train_plan_destination_station'],
            "price": str(row['train_plan_cost']) if pd.notna(row['train_plan_cost']) else "0",
            "duration": str(int(row['train_plan_duration'])) if pd.notna(row['train_plan_duration']) else "0"
        })
    
    except Exception as e:
        return error_response(
            "Internal Server Error",
            "服务器内部错误",
            request.path,
            500,
            str(e)
        )


@app.route('/all-cities', methods=['GET'])
def get_all_cities():
    """获取所有城市列表"""
    try:
        # 获取唯一城市列表
        cities_set = set()
        
        # 从各个数据源收集城市
        if 'city_name' in data['attractions'].columns:
            cities_set.update(data['attractions']['city_name'].dropna().unique())
        
        if 'city_name' in data['accommodations'].columns:
            cities_set.update(data['accommodations']['city_name'].dropna().unique())
        
        if 'city_name' in data['restaurants'].columns:
            cities_set.update(data['restaurants']['city_name'].dropna().unique())
        
        # 获取城市代码
        city_info = data['city_info']
        result = []
        city_code_map = {}
        
        for _, row in city_info.iterrows():
            city_name = row['cityname']
            city_code = row['citycode']
            if city_name not in city_code_map:
                city_code_map[city_name] = city_code
        
        for city_name in sorted(cities_set):
            city_code = city_code_map.get(city_name, "")
            if city_code:
                result.append({
                    "city_code": city_code,
                    "city_name": city_name
                })
        
        if not result:
            return error_response(
                "Database Error",
                "数据库查询城市列表错误",
                request.path,
                503
            )
        
        return jsonify(result)
    
    except Exception as e:
        return error_response(
            "Internal Server Error",
            "服务器内部错误",
            request.path,
            500,
            str(e)
        )


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })


if __name__ == '__main__':
    # 加载数据
    if not load_data():
        print("数据加载失败，无法启动服务器")
        exit(1)
    
    # 启动服务器
    print("\n" + "="*50)
    print("API服务器正在启动...")
    print("服务地址: http://localhost:12457")
    print("="*50 + "\n")
    
    app.run(host='0.0.0.0', port=12457, debug=False)

