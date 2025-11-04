# 智能旅行规划系统

基于多智能体协作的智能旅行规划系统，使用 AutoGen 框架实现多智能体协作，通过约束优化生成个性化的旅行计划。

## 项目结构

```
autogendemo/
├── agents/          # 智能体模块
│   ├── coordinator.py    # 协调器智能体
│   ├── researcher.py     # 研究者智能体（数据查询）
│   ├── planner.py        # 规划者智能体（优化求解）
│   ├── feedback.py       # 反馈智能体（冲突检测）
│   ├── check.py          # 检查智能体（合理性验证）
│   ├── writer.py         # 写作者智能体（结果生成）
│   └── evaluator.py      # 评估器（结果评分）
├── tasks/           # 任务模块
│   ├── generate_task.py  # 生成任务
│   ├── check_task.py     # 检查任务
│   ├── Gen_result_task.py # 结果生成任务
│   └── evaluate_task.py  # 评估任务
├── api/             # API 服务
│   ├── run_api.py   # API 服务器（Flask）
│   └── data/        # 数据文件（CSV格式）
├── prompts/         # 提示词和问题
│   └── question.json # 问题数据集（1-120）
├── config.py        # 配置文件
├── main.py          # 主程序入口
└── requirements.txt # Python 依赖

```

## 环境要求

- Python 3.8+

## 安装步骤

### 1. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件（在项目根目录）：

```env
# SiliconFlow API 配置（必需）
SILICONFLOW_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 可选配置
SILICONFLOW_MODEL=Qwen/QwQ-32B
SILICONFLOW_TEMPERATURE=0.7
SILICONFLOW_API_BASE_URL=https://api.siliconflow.cn/v1

# 旅行规划 API 服务器配置（默认值）
TRAVEL_API_BASE_URL=http://localhost:12457
TRAVEL_API_TIMEOUT=10
```

**重要：** 必须设置 `SILICONFLOW_API_KEY`，否则程序无法运行。

## 启动项目

### 步骤 1: 启动 API 服务器

首先需要启动旅行规划 API 服务器，提供数据查询服务：

```bash
cd autogendemo/api
python run_api.py
```

API 服务器将在 `http://localhost:12457` 启动。

**注意：** 确保 API 服务器正常运行后再进行下一步。你会看到类似以下输出：

```
正在加载数据...
已加载 XXX 条景点数据
已加载 XXX 条住宿数据
...
所有数据加载完成!
 * Running on http://127.0.0.1:12457
```

### 步骤 2: 启动主程序

在**新的终端窗口**中，进入项目根目录并运行主程序：

```bash
cd autogendemo
python main.py
```

### 使用方式

程序启动后，会提示输入问题编号：

```
Input the query number (1-120, or press Enter for all): 
```

**选项 1：处理单个问题**
- 输入 1-120 之间的数字，例如：`1`
- 系统将处理该问题并生成旅行计划，然后进行评估

**选项 2：处理所有问题（批量模式）**
- 直接按回车键（不输入任何内容）
- 系统将依次处理所有 120 个问题
- 最后会计算并显示平均得分

## 工作流程

1. **TASK 1: 生成可行结果**
   - `GenerateTask`: 调用 Researcher 和 Planner 生成初步行程
   - `CheckTask`: 使用 Check 和 Feedback 验证合理性
   - `GenResultTask`: 使用 Writer 生成最终 JSON 格式的行程计划

2. **TASK 2: 评估生成的结果**
   - 评估可执行率 (ER)：检查 JSON 格式是否正确
   - 评估求解准确率 (AR)：使用 LLM 评估规划合理性
   - 评估实体覆盖率 (ECR)：计算正确实体的覆盖率
   - 计算平均推理时间 (ART)：记录全流程运行时间
   - 计算最终分数：Final Score = ER × (0.7 × AR + 0.3 × ECR)

## 输出示例

### 单个问题评估结果

```
============================================================
TASK 2: Evaluate the generated results
============================================================

------------------------------------------------------------
评估结果摘要
------------------------------------------------------------

1. 可执行率(ER): 1.00
   说明: JSON格式正确

2. 求解准确率(AR): 0.85
   说明: 规划在预算、时间、路线可达性等方面表现良好...

3. 实体覆盖率(ECR): 0.90
   attractions: 3/3 (100.00%)
   restaurants: 8/9 (88.89%)
   accommodations: 1/1 (100.00%)

4. 平均推理时间(ART): 3.50 分钟
   ART*评分: 0.60

5. 最终分数(Final Score): 0.8560
   计算公式: Final Score = ER * (0.7 * AR + 0.3 * ECR)
   组成: ER=1.00, AR=0.85, ECR=0.90
```

### 批量评估结果

```
批量评估结果摘要
------------------------------------------------------------

样本数量: 120

平均指标:
  平均ER: 0.9500
  平均AR: 0.8200
  平均ECR: 0.8500
  平均ART: 3.25 分钟
  平均ART*: 0.60
  平均最终分数: 0.8125
```

## 评估指标说明

- **ER (可执行率)**: 评估 JSON 是否可以解析且格式符合要求 (0-1)
- **AR (求解准确率)**: 使用 LLM 评估规划在预算、时间、路线可达性、地点连贯性上的合理性 (0-1)
- **ECR (实体覆盖率)**: 结果中正确景点、饭店、住宿的覆盖率 (0-1)
- **ART (平均推理时间)**: 包含数据处理、模型响应、代码执行、结果评估全流程的运行时间（分钟）
- **ART\***: 根据 ART 的分段评分函数（<1min: 1.0, 1-5min: 0.6, 5-10min: 0.2, ≥10min: 0.0）
- **Final Score**: 最终分数 = ER × (0.7 × AR + 0.3 × ECR)

