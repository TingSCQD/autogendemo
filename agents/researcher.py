import autogen
import requests
import sys
import os
from typing import Dict, List, Optional
from urllib.parse import quote

# 添加父目录到 Python 路径，以便可以导入 config 模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import AGENT_CONFIG, TRAVEL_API_BASE_URL, TRAVEL_API_TIMEOUT


class ResearcherAgent:
    def __init__(self):
        # 使用 config.py 中已配置的 system_message
        self.agent = autogen.AssistantAgent(**AGENT_CONFIG["researcher"])
        self.api_base_url = TRAVEL_API_BASE_URL
        self.api_timeout = TRAVEL_API_TIMEOUT
    
    def get_agent(self):
        return self.agent
    
    def _make_request(self, endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Optional[Dict]:
        """通用请求方法"""
        try:
            url = f"{self.api_base_url}{endpoint}"
            if method == "GET":
                response = requests.get(url, timeout=self.api_timeout)
            elif method == "POST":
                response = requests.post(url, json=data, timeout=self.api_timeout, headers={"Content-Type": "application/json"})
            else:
                return None
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            # 尝试获取错误消息
            try:
                error_info = e.response.json()
                print(f"API 请求错误 ({e.response.status_code}): {error_info.get('message', str(e))}")
            except:
                print(f"API 请求错误 ({e.response.status_code}): {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"API 请求错误: {e}")
            return None
    
    def get_cross_city_transport(self, origin_city: str, destination_city: str) -> Optional[List[Dict]]:
        """获取跨城市交通数据（火车）"""
        # 使用 params 参数而不是手动拼接，这样可以自动处理 URL 编码
        endpoint = "/cross-city-transport/"
        url = f"{self.api_base_url}{endpoint}"
        params = {
            "origin_city": origin_city,
            "destination_city": destination_city
        }
        try:
            response = requests.get(url, params=params, timeout=self.api_timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            try:
                error_info = e.response.json()
                print(f"API 请求错误 ({e.response.status_code}): {error_info.get('message', str(e))}")
            except:
                print(f"API 请求错误 ({e.response.status_code}): {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"API 请求错误: {e}")
            return None
    
    def get_intra_city_transport(self, city_name: str) -> Optional[Dict]:
        """获取市内交通数据（返回字典格式，键为 origin_id,destination_id）"""
        endpoint = f"/intra-city-transport/{quote(city_name)}"
        return self._make_request(endpoint)
    
    def get_attractions(self, city_name: str) -> Optional[List[Dict]]:
        """获取城市景点数据"""
        endpoint = f"/attractions/{quote(city_name)}"
        return self._make_request(endpoint)
    
    def get_accommodations(self, city_name: str) -> Optional[List[Dict]]:
        """获取城市住宿数据"""
        endpoint = f"/accommodations/{quote(city_name)}"
        return self._make_request(endpoint)
    
    def get_restaurants(self, city_name: str) -> Optional[List[Dict]]:
        """获取城市餐厅数据"""
        endpoint = f"/restaurants/{quote(city_name)}"
        return self._make_request(endpoint)
    
    def get_poi_data(self, city_name: str) -> Optional[Dict]:
        """获取城市所有 POI 数据"""
        endpoint = f"/poi-data/{quote(city_name)}"
        return self._make_request(endpoint)
    
    def get_poi_by_id(self, poi_id: str) -> Optional[Dict]:
        """根据 ID 获取 POI 数据"""
        endpoint = f"/poi/{quote(poi_id)}"
        return self._make_request(endpoint)
    
    def get_transport_params(self, origin_id: str, destination_id: str) -> Optional[Dict]:
        """获取两点间交通参数"""
        endpoint = "/transport-params"
        data = {
            "origin_id": origin_id,
            "destination_id": destination_id
        }
        return self._make_request(endpoint, method="POST", data=data)
    
    def get_train_info(self, train_number: str, origin_id: str, destination_id: str) -> Optional[Dict]:
        """根据车次号获取列车信息"""
        endpoint = "/train"
        url = f"{self.api_base_url}{endpoint}"
        params = {
            "train_number": train_number,
            "origin_id": origin_id,
            "destination_id": destination_id
        }
        try:
            response = requests.get(url, params=params, timeout=self.api_timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            try:
                error_info = e.response.json()
                print(f"API 请求错误 ({e.response.status_code}): {error_info.get('message', str(e))}")
            except:
                print(f"API 请求错误 ({e.response.status_code}): {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"API 请求错误: {e}")
            return None
    
    def get_all_cities(self) -> Optional[List[Dict]]:
        """获取所有城市列表（返回字典列表，每个元素包含 city_code 和 city_name）"""
        endpoint = "/all-cities"
        return self._make_request(endpoint)
    
    def conduct_research(self, topic: str, **kwargs) -> Dict:
        """根据研究主题查询相关数据
        
        Args:
            topic: 研究主题，可以是城市名、交通查询等
            **kwargs: 额外的查询参数（如 origin_city, destination_city 等）
        
        Returns:
            包含查询结果的字典
        """
        results = {}
        
        # 如果提供了城市名，获取该城市的 POI 数据
        city_name = kwargs.get("city_name")
        if city_name:
            results["attractions"] = self.get_attractions(city_name)
            results["accommodations"] = self.get_accommodations(city_name)
            results["restaurants"] = self.get_restaurants(city_name)
            results["intra_city_transport"] = self.get_intra_city_transport(city_name)
            results["poi_data"] = self.get_poi_data(city_name)
        
        # 如果提供了起始城市和目的地城市，获取跨城市交通数据
        origin_city = kwargs.get("origin_city")
        destination_city = kwargs.get("destination_city")
        if origin_city and destination_city:
            results["cross_city_transport"] = self.get_cross_city_transport(origin_city, destination_city)
        
        # 如果提供了 POI ID，获取 POI 详细信息
        poi_id = kwargs.get("poi_id")
        if poi_id:
            results["poi_detail"] = self.get_poi_by_id(poi_id)
        
        # 如果提供了起点和终点 ID，获取交通参数
        origin_id = kwargs.get("origin_id")
        destination_id = kwargs.get("destination_id")
        if origin_id and destination_id:
            results["transport_params"] = self.get_transport_params(origin_id, destination_id)
        
        # 如果没有特定参数，返回所有城市列表
        if not any([city_name, origin_city, poi_id, origin_id]):
            results["all_cities"] = self.get_all_cities()
        
        return results


def main():
    """测试 ResearcherAgent 的各种 API 功能"""
    print("=" * 60)
    print("ResearcherAgent API 测试")
    print("=" * 60)
    
    # 创建 ResearcherAgent 实例
    researcher = ResearcherAgent()
    
    # 测试 1: 获取所有城市列表
    print("\n[测试 1] 获取所有城市列表")
    print("-" * 60)
    cities = researcher.get_all_cities()
    if cities:
        print(f"✅ 成功获取城市列表，共 {len(cities)} 个城市")
        if len(cities) > 0:
            print(f"前 5 个城市:")
            for i, city in enumerate(cities[:5], 1):
                print(f"  {i}. {city.get('city_name', 'N/A')} ({city.get('city_code', 'N/A')})")
    else:
        print("❌ 获取城市列表失败")
    
    # 测试 2: 跨城市交通查询（用户提供的示例）
    print("\n[测试 2] 跨城市交通查询：广州市 -> 杭州市")
    print("-" * 60)
    train_data = researcher.get_cross_city_transport("广州市", "杭州市")
    if train_data:
        print(f"✅ 成功获取交通数据，共 {len(train_data)} 条记录")
        if len(train_data) > 0:
            print("\n前 2 条记录:")
            for i, item in enumerate(train_data[:2], 1):
                print(f"  {i}. 车次: {item.get('train_number')}, "
                      f"起点站: {item.get('origin_station')}, "
                      f"终点站: {item.get('destination_station')}, "
                      f"时长: {item.get('duration')}分钟, "
                      f"费用: {item.get('cost')}元")
    else:
        print("❌ 获取跨城市交通数据失败")
    
    # 测试 3: 获取城市景点数据
    print("\n[测试 3] 获取杭州市景点数据")
    print("-" * 60)
    attractions = researcher.get_attractions("杭州市")
    if attractions:
        print(f"✅ 成功获取景点数据，共 {len(attractions)} 个景点")
        if len(attractions) > 0:
            print("\n前 3 个景点:")
            for i, attr in enumerate(attractions[:3], 1):
                print(f"  {i}. {attr.get('name', 'N/A')} "
                      f"(ID: {attr.get('id', 'N/A')})")
    else:
        print("❌ 获取景点数据失败")
    
    # 测试 4: 获取城市住宿数据
    print("\n[测试 4] 获取广州市住宿数据")
    print("-" * 60)
    accommodations = researcher.get_accommodations("广州市")
    if accommodations:
        print(f"✅ 成功获取住宿数据，共 {len(accommodations)} 个住宿")
        if len(accommodations) > 0:
            print("\n前 2 个住宿:")
            for i, acc in enumerate(accommodations[:2], 1):
                print(f"  {i}. {acc.get('name', 'N/A')} "
                      f"(ID: {acc.get('id', 'N/A')})")
    else:
        print("❌ 获取住宿数据失败")
    
    # 测试 5: 获取城市餐厅数据
    print("\n[测试 5] 获取广州市餐厅数据")
    print("-" * 60)
    restaurants = researcher.get_restaurants("广州市")
    if restaurants:
        print(f"✅ 成功获取餐厅数据，共 {len(restaurants)} 个餐厅")
        if len(restaurants) > 0:
            print("\n前 2 个餐厅:")
            for i, rest in enumerate(restaurants[:2], 1):
                print(f"  {i}. {rest.get('name', 'N/A')} "
                      f"(ID: {rest.get('id', 'N/A')})")
    else:
        print("❌ 获取餐厅数据失败")
    
    # 测试 6: 获取市内交通数据
    print("\n[测试 6] 获取杭州市市内交通数据")
    print("-" * 60)
    intra_transport = researcher.get_intra_city_transport("杭州市")
    if intra_transport:
        if isinstance(intra_transport, list):
            print(f"✅ 成功获取市内交通数据，共 {len(intra_transport)} 条记录")
            if len(intra_transport) > 0:
                print("\n前 2 条记录:")
                for i, trans in enumerate(intra_transport[:2], 1):
                    print(f"  {i}. {trans}")
        elif isinstance(intra_transport, dict):
            print(f"✅ 成功获取市内交通数据（字典格式），共 {len(intra_transport)} 个键")
            # 如果是字典，显示前 2 个键值对
            items = list(intra_transport.items())[:2]
            print("\n前 2 条记录:")
            for i, (key, value) in enumerate(items, 1):
                print(f"  {i}. {key}: {value}")
        else:
            print(f"✅ 成功获取市内交通数据，类型: {type(intra_transport)}")
            print(f"  数据: {intra_transport}")
    else:
        print("❌ 获取市内交通数据失败")
    
    # 测试 7: 综合查询测试（conduct_research）
    print("\n[测试 7] 综合查询测试：查询广州市的所有信息")
    print("-" * 60)
    results = researcher.conduct_research("广州市信息查询", city_name="广州市")
    if results:
        print("✅ 成功执行综合查询")
        for key, value in results.items():
            if value:
                if isinstance(value, list):
                    print(f"  - {key}: {len(value)} 条记录")
                elif isinstance(value, dict):
                    print(f"  - {key}: 包含 {len(value)} 个字段")
                else:
                    print(f"  - {key}: {value}")
            else:
                print(f"  - {key}: 无数据")
    else:
        print("❌ 综合查询失败")
    
    # 测试 8: 使用景点 ID 测试获取两点间交通参数
    # transport-params 接口需要市内 POI ID，而不是跨城市交通站点 ID
    print("\n[测试 8] 获取两点间交通参数（使用景点 POI ID）")
    print("-" * 60)
    # 使用之前获取的杭州市景点数据
    if attractions and isinstance(attractions, list) and len(attractions) >= 2:
        # 获取前两个景点的 ID
        origin_id = attractions[0].get('id')
        destination_id = attractions[1].get('id')
        if origin_id and destination_id:
            print(f"使用 POI ID: {origin_id} -> {destination_id}")
            transport_params = researcher.get_transport_params(origin_id, destination_id)
            if transport_params:
                print("✅ 成功获取交通参数:")
                print(f"  - 公交时长: {transport_params.get('bus_duration', 'N/A')} 分钟")
                print(f"  - 公交费用: {transport_params.get('bus_cost', 'N/A')} 元")
                print(f"  - 出租车时长: {transport_params.get('taxi_duration', 'N/A')} 分钟")
                print(f"  - 出租车费用: {transport_params.get('taxi_cost', 'N/A')} 元")
            else:
                print("❌ 获取交通参数失败（可能这两个 POI 之间没有路径数据）")
        else:
            print("❌ 景点数据中缺少 ID 字段")
    else:
        print("❌ 无法获取景点数据用于测试")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()