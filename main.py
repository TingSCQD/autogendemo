import json
import os
import sys
from tasks import GenerateTask,GenResultTask,CheckTask,EvaluateTask



def check_api_key():
    if not os.getenv("SILICONFLOW_API_KEY"):
        print(" Error: SILICONFLOW_API_KEY environment variable is not set!")
        print("\n Setup Instructions:")
        print("1. 复制 .env.example 到 .env")
        print("2. 在 .env 文件中添加你的 SILICONFLOW API key，如 SILICONFLOW_API_KEY=sk-xxx")
        print("3. 重新运行应用程序")
        return False
    return True

def get_query(choice):
    """
    根据用户输入的编号，从 questions.json 文件中获取对应的问题文本。
    如果文件不存在或编号无效，将给出友好的提示。
    """
    json_path = "prompts/question.json"
    if not os.path.exists(json_path):
        print(f"\n Error: 找不到 {json_path} 文件，请确保该文件存在于程序目录中。")
        sys.exit(1)
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"\n Error: 无法解析 {json_path} 文件，请检查其 JSON 格式是否正确。")
        print(f" 详细错误信息: {e}")
        sys.exit(1)

    # 支持数字字符串或整数输入
    try:
        question_id = int(choice)
    except ValueError:
        print("\n Error: 输入的编号无效，请输入数字。")
        sys.exit(1)

    # 查找匹配问题
    for item in data:
        if int(item.get("question_id")) == question_id:
            return item.get("question")

    print(f"\n Error: 在 {json_path} 中未找到编号为 {question_id} 的问题。")
    sys.exit(1)

def get_result_task(question):
    global temp_plan
    print("\n" + "="*60)
    print("TASK 1: Obtain feasible results")
    print("="*60)


    generate_task = GenerateTask()
    check_task = CheckTask()
    print(f" Question: {question}")
    print("\n Starting multi-agent collaboration...")

    times = 0
    try:
        for times in range(3):
            temp_plan = generate_task.execute(question)
            print(f"\n {temp_plan}")
            check_result = check_task.execute(temp_plan)
            if check_result:
                print(f"\n {temp_plan}")
                break
            else:
                times += 1
        if times == 3:
            print(f"\n No correct plan was produced")
    except Exception as e:
        print(f"\n Error in research task: {e}")

def evaluate_task(choice):
    print("\n" + "=" * 60)
    print("TASK 2: Evaluate the generated results")
    print("=" * 60)

    research_task = ResearchTask()


    print(f" Topic: {topic}")
    print("\n Starting multi-agent collaboration...")
    print("Watch how the agents communicate and collaborate:")

    try:
        result = research_task.execute(topic)
        print(f"\n {result}")
    except Exception as e:
        print(f"\n Error in research task: {e}")

def main():
    if not check_api_key():
        sys.exit(1)
    try:
        choice = input("\nInput the query number : (1-120) ").strip()
        question = get_query(choice)

        result = get_result_task(question)

    except KeyboardInterrupt:
        print("\n\n Application terminated by user")
    except Exception as e:
        print(f"\n Unexpected error: {e}")

if __name__ == "__main__":
    main()