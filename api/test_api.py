#!/usr/bin/env python3
"""
API测试脚本
用于验证API服务器的各个接口是否正常工作
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:12457"

def test_health():
    """测试健康检查接口"""
    print("测试 /health 接口...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ 健康检查通过")
            return True
        else:
            print(f"❌ 健康检查失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 无法连接到服务器: {e}")
        return False


def test_attractions():
    """测试获取景点接口"""
    print("\n测试 /attractions/{city_name} 接口...")
    try:
        response = requests.get(f"{BASE_URL}/attractions/北京市", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 成功获取 {len(data)} 个景点")
            if len(data) > 0:
                print(f"   示例: {data[0]['name']}")
            return True
        else:
            print(f"❌ 请求失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 请求出错: {e}")
        return False


def test_accommodations():
    """测试获取住宿接口"""
    print("\n测试 /accommodations/{city_name} 接口...")
    try:
        response = requests.get(f"{BASE_URL}/accommodations/北京市", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 成功获取 {len(data)} 个酒店")
            if len(data) > 0:
                print(f"   示例: {data[0]['name']}")
            return True
        else:
            print(f"❌ 请求失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 请求出错: {e}")
        return False


def test_restaurants():
    """测试获取餐厅接口"""
    print("\n测试 /restaurants/{city_name} 接口...")
    try:
        response = requests.get(f"{BASE_URL}/restaurants/北京市", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 成功获取 {len(data)} 个餐厅")
            if len(data) > 0:
                print(f"   示例: {data[0]['name']}")
            return True
        else:
            print(f"❌ 请求失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 请求出错: {e}")
        return False


def test_cross_city_transport():
    """测试跨城市交通接口"""
    print("\n测试 /cross-city-transport/ 接口...")
    try:
        response = requests.get(
            f"{BASE_URL}/cross-city-transport/",
            params={"origin_city": "广州市", "destination_city": "杭州市"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 成功获取 {len(data)} 个车次")
            if len(data) > 0:
                print(f"   示例: {data[0]['train_number']} - {data[0]['origin_station']} → {data[0]['destination_station']}")
            return True
        else:
            print(f"❌ 请求失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ 请求出错: {e}")
        return False


def test_intra_city_transport():
    """测试市内交通接口"""
    print("\n测试 /intra-city-transport/{city_name} 接口...")
    try:
        response = requests.get(f"{BASE_URL}/intra-city-transport/重庆市", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 成功获取 {len(data)} 条市内路径")
            # 显示第一条记录
            if len(data) > 0:
                first_key = list(data.keys())[0]
                print(f"   示例路径: {first_key}")
            return True
        else:
            print(f"❌ 请求失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 请求出错: {e}")
        return False


def test_all_cities():
    """测试获取所有城市接口"""
    print("\n测试 /all-cities 接口...")
    try:
        response = requests.get(f"{BASE_URL}/all-cities", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 成功获取 {len(data)} 个城市")
            if len(data) > 0:
                print(f"   示例: {data[0]['city_name']} ({data[0]['city_code']})")
            return True
        else:
            print(f"❌ 请求失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 请求出错: {e}")
        return False


def test_poi_data():
    """测试获取POI数据接口"""
    print("\n测试 /poi-data/{city_name} 接口...")
    try:
        response = requests.get(f"{BASE_URL}/poi-data/广州市", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 成功获取POI数据")
            print(f"   - 景点: {len(data['attractions'])} 个")
            print(f"   - 酒店: {len(data['accommodations'])} 个")
            print(f"   - 餐厅: {len(data['restaurants'])} 个")
            return True
        else:
            print(f"❌ 请求失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 请求出错: {e}")
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("API 服务器测试")
    print("=" * 60)
    
    # 等待服务器启动
    print("\n等待服务器启动...")
    time.sleep(2)
    
    # 运行测试
    tests = [
        test_health,
        test_attractions,
        test_accommodations,
        test_restaurants,
        test_cross_city_transport,
        test_intra_city_transport,
        test_all_cities,
        test_poi_data
    ]
    
    results = []
    for test in tests:
        results.append(test())
        time.sleep(0.5)
    
    # 统计结果
    passed = sum(results)
    total = len(results)
    
    print("\n" + "=" * 60)
    print(f"测试结果: {passed}/{total} 通过")
    print("=" * 60)
    
    if passed == total:
        print("✅ 所有测试通过！")
        return 0
    else:
        print("❌ 部分测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())

