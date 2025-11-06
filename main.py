import json
import os
import sys
import time
from tasks import GenerateTask,GenResultTask,CheckTask



def check_api_key():
    if not os.getenv("SILICONFLOW_API_KEY"):
        print(" Error: SILICONFLOW_API_KEY environment variable is not set!")
        print("\n Setup Instructions:")
        print("1. 复制 .env.example 到 .env")
        print("2. 在 .env 文件中添加你的 SILICONFLOW API key，如 SILICONFLOW_API_KEY=sk-xxx")
        print("3. 重新运行应用程序")
        return False
    return True

def get_all_queries():
    """
    获取所有问题（1-120）
    
    Returns:
        list: [(question_id, question_text, item_dict), ...]
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
    
    queries = []
    for item in data:
        question_id = int(item.get("question_id"))
        if 1 <= question_id <= 120:
            queries.append((question_id, item.get("question"), item))
    
    return sorted(queries, key=lambda x: x[0])


def get_query(choice):
    """
    根据用户输入的编号，从 questions.json 文件中获取对应的问题文本和ID。
    如果文件不存在或编号无效，将给出友好的提示。
    
    Args:
        choice: 用户输入的编号（字符串，可以为空）
    
    Returns:
        tuple: (question_id, question_text, item_dict) 或 None（如果choice为空）
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

    # 如果choice为空，返回None（表示处理所有问题）
    if not choice or choice.strip() == "":
        return None

    # 支持数字字符串或整数输入
    try:
        question_id = int(choice)
    except ValueError:
        print("\n Error: 输入的编号无效，请输入数字或直接回车（处理所有问题）。")
        sys.exit(1)

    # 查找匹配问题
    for item in data:
        if int(item.get("question_id")) == question_id:
            return question_id, item.get("question"), item

    print(f"\n Error: 在 {json_path} 中未找到编号为 {question_id} 的问题。")
    sys.exit(1)

def get_result_task(question):
    """
    获取可行的行程计划结果
    
    Returns:
        result: 行程计划结果字典，或 None（如果失败）
    """
    global temp_plan
    print("\n" + "="*60)
    print("TASK 1: Obtain feasible results")
    print("="*60)

    print(f" Question: {question}")
    prompt = question

    times = 0
    try:
        for times in range(3):
            generate_task = GenerateTask()
            temp_plan = generate_task.execute(prompt)
            check_task = CheckTask()
            check_result = check_task.execute(temp_plan)
            if check_result.get("is_valid", True):
                result_task = GenResultTask()
                final_prompt = str(temp_plan) + f"\n\nNote that be wary of the following errors and warnings: \nErrors: {check_result.get('errors', [])}\nWarnings: {check_result.get('warnings', [])}"
                result = result_task.execute(final_prompt)
                return result
            else:
                times += 1
                prompt = question + f"\n\nNote that be wary of the following errors and warnings: \nErrors: {check_result.get('errors', [])}\nWarnings: {check_result.get('warnings', [])}"
        if times == 3:
            print(f"\n No correct plan was produced after 3 attempts")
            return None
    except Exception as e:
        print(f"\n Error in research task: {e}")
        return None
    return None

def save_result(result, question_id):
    """
    保存生成的行程计划结果到文件
    
    Args:
        result: 生成的行程计划结果（字典）
        question_id: 问题ID
    
    Returns:
        保存的文件路径，如果失败则返回None
    """
    if result is None:
        print(f"\n 无法保存：结果为 None")
        return None
    
    # 确保results目录存在
    results_dir = "results"
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
        print(f"\n 创建目录: {results_dir}")
    
    # 构建文件路径
    output_file = os.path.join(results_dir, f"id_{question_id}.json")
    
    try:
        # 保存JSON文件
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
        print(f"\n✓ 结果已保存到: {output_file}")
        return output_file
    except Exception as e:
        print(f"\n✗ 保存结果时出错: {e}")
        return None


def main():
    if not check_api_key():
        sys.exit(1)
    try:
        choice = input("\nInput the query number (1-120, or press Enter for all): ").strip()
        query_info = get_query(choice)
        
        # 如果用户直接回车，处理所有问题
        if query_info is None:
            all_queries = get_all_queries()
            print(f"\n 将处理所有 {len(all_queries)} 个问题（1-120）")
            
            # 批量处理
            success_count = 0
            fail_count = 0
            
            for idx, (question_id, question, question_item) in enumerate(all_queries, 1):
                print(f"\n{'='*60}")
                print(f"处理问题 {idx}/{len(all_queries)}: Question ID {question_id}")
                print(f"{'='*60}")
                
                # 记录开始时间
                start_time = time.time()
                
                # 获取结果
                result = get_result_task(question)
                
                # 计算推理时间
                inference_time_seconds = time.time() - start_time
                
                if result:
                    # 保存结果
                    save_result(result, question_id)
                    success_count += 1
                    print(f"✓ 问题 {question_id} 处理完成，推理时间: {inference_time_seconds:.2f} 秒")
                else:
                    fail_count += 1
                    print(f"✗ 问题 {question_id} 处理失败")
            
            # 打印处理摘要
            print("\n" + "="*60)
            print("批量处理完成")
            print("="*60)
            print(f"\n成功处理: {success_count} 个问题")
            print(f"处理失败: {fail_count} 个问题")
            print(f"总计: {len(all_queries)} 个问题")
        
        else:
            # 处理单个问题
            question_id, question, question_item = query_info
            
            # 记录开始时间
            start_time = time.time()
            
            # 获取结果
            result = get_result_task(question)
            
            # 计算推理时间
            inference_time_seconds = time.time() - start_time
            
            # 保存结果
            if result:
                save_result(result, question_id)
                print(f"\n✓ 处理完成，推理时间: {inference_time_seconds:.2f} 秒")
            else:
                print("\n✗ 处理失败：未生成有效结果")
        
    except KeyboardInterrupt:
        print("\n\n Application terminated by user")
    except Exception as e:
        print(f"\n Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()