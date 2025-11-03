# 旅行规划 API 服务器

这是一个基于 Flask 的 RESTful API 服务器，用于提供旅行规划相关的数据查询服务。

## 功能特性

- ✅ 跨城市交通查询（火车）
- ✅ 城市景点查询
- ✅ 城市住宿查询
- ✅ 城市餐厅查询
- ✅ 市内交通查询
- ✅ POI 数据查询
- ✅ 城市列表查询
- ✅ 完整的错误处理和异常响应

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务器

**方式一：使用启动脚本**

```bash
chmod +x start_api.sh
./start_api.sh
```

**方式二：直接运行**

```bash
python3 run_api.py
```

服务器将在 `http://localhost:12457` 启动。

## API 接口文档

### 1. 获取跨城市交通数据

```
GET /cross-city-transport/?origin_city={起始城市}&destination_city={目的地城市}
```

**示例：**
```bash
curl "http://localhost:12457/cross-city-transport/?origin_city=广州市&destination_city=杭州市"
```

### 2. 获取城市所有 POI 数据

```
GET /poi-data/{city_name}
```

**示例：**
```bash
curl "http://localhost:12457/poi-data/广州市"
```

### 3. 获取城市景点数据

```
GET /attractions/{city_name}
```

**示例：**
```bash
curl "http://localhost:12457/attractions/杭州市"
```

### 4. 获取城市住宿数据

```
GET /accommodations/{city_name}
```

**示例：**
```bash
curl "http://localhost:12457/accommodations/广州市"
```

### 5. 获取城市餐厅数据

```
GET /restaurants/{city_name}
```

**示例：**
```bash
curl "http://localhost:12457/restaurants/广州市"
```

### 6. 获取市内交通数据

```
GET /intra-city-transport/{city_name}
```

**示例：**
```bash
curl "http://localhost:12457/intra-city-transport/杭州市"
```

### 7. 根据 ID 获取 POI 数据

```
GET /poi/{poi_id}
```

**示例：**
```bash
curl "http://localhost:12457/poi/B0FFG8V7SH"
```

### 8. 获取两点间交通参数

```
POST /transport-params
Content-Type: application/json

{
  "origin_id": "起点POI_ID",
  "destination_id": "终点POI_ID"
}
```

**示例：**
```bash
curl -X POST "http://localhost:12457/transport-params" \
  -H "Content-Type: application/json" \
  -d '{"origin_id":"B0FFG8V7SH","destination_id":"B0017091IQ"}'
```

### 9. 根据车次号获取列车信息

```
GET /train?train_number={车次号}&origin_id={起点ID}&destination_id={终点ID}
```

**示例：**
```bash
curl "http://localhost:12457/train?train_number=G1484&origin_id=xxx&destination_id=yyy"
```

### 10. 获取所有城市列表

```
GET /all-cities
```

**示例：**
```bash
curl "http://localhost:12457/all-cities"
```

### 健康检查

```
GET /health
```

**示例：**
```bash
curl "http://localhost:12457/health"
```

## 错误响应

API 使用标准的 HTTP 状态码，所有错误响应都遵循以下格式：

```json
{
  "error": "错误类型",
  "message": "错误描述",
  "timestamp": "2025-05-29T10:30:45.123456",
  "path": "/api/path"
}
```

常见状态码：
- `400` - 参数错误
- `404` - 数据未找到
- `422` - 请求验证失败
- `500` - 服务器内部错误
- `503` - 数据库连接失败

## 数据来源

API 从以下 CSV 文件读取数据：
- `database/csv/poi_attraction.csv` - 景点数据
- `database/csv/poi_accommodation.csv` - 住宿数据
- `database/csv/poi_restaurant.csv` - 餐厅数据
- `database/csv/poi_transport.csv` - 交通站点数据
- `database/csv/path_planning_in_city.csv` - 市内路径数据
- `database/csv/path_planning_cross_city.csv` - 跨城路径数据
- `database/csv/city_info.csv` - 城市信息数据

## 依赖项

- **Flask** - Web 框架
- **Pandas** - 数据处理
- **Python 3.8+** - 运行环境
