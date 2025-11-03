import json
import os
import sys
import time
from tasks import GenerateTask,GenResultTask,CheckTask,EvaluateTask
from agents.evaluator import TravelPlanEvaluator



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
    根据用户输入的编号，从 questions.json 文件中获取对应的问题文本和ID。
    如果文件不存在或编号无效，将给出友好的提示。
    
    Returns:
        tuple: (question_id, question_text) 或 (question_id, question_text, item_dict)
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

def evaluate_result(result, question_id, question, inference_time_seconds=None):
    """
    对生成的行程计划结果进行评估
    
    Args:
        result: 生成的行程计划结果（字典或JSON字符串）
        question_id: 问题ID
        question: 问题文本
        inference_time_seconds: 推理时间（秒）
    
    Returns:
        评估结果字典
    """
    if result is None:
        print("\n 无法评估：结果为 None")
        return None
    
    print("\n" + "="*60)
    print("TASK 2: Evaluate the generated results")
    print("="*60)
    
    evaluator = TravelPlanEvaluator()
    
    # 注意：correct_entities 需要从标准答案中获取，这里暂时设为 None
    # 如果有标准答案数据，可以从 question.json 或其他来源获取
    correct_entities = None  # TODO: 从标准答案中获取正确实体列表
    
    # 执行综合评估
    eval_result = evaluator.comprehensive_evaluate(
        result=result,
        question=question,
        correct_entities=correct_entities,
        inference_time_seconds=inference_time_seconds
    )
    
    # 打印评估结果摘要
    print("\n" + "-" * 60)
    print("评估结果摘要")
    print("-" * 60)
    
    # ER
    er = eval_result.get("er", {})
    print(f"\n1. 可执行率(ER): {er.get('score', 0.0):.2f}")
    print(f"   说明: {er.get('message', 'N/A')}")
    
    # AR
    ar = eval_result.get("ar", {})
    print(f"\n2. 求解准确率(AR): {ar.get('score', 0.0):.2f}")
    explanation = ar.get('explanation', 'N/A')
    if len(explanation) > 300:
        explanation = explanation[:300] + "..."
    print(f"   说明: {explanation}")
    
    # ECR
    ecr = eval_result.get("ecr", {})
    ecr_score = ecr.get('score', 0.0)
    print(f"\n3. 实体覆盖率(ECR): {ecr_score:.2f}")
    ecr_details = ecr.get('details', {})
    if isinstance(ecr_details, dict) and 'entity_details' in ecr_details:
        entity_details = ecr_details['entity_details']
        for entity_type, details in entity_details.items():
            if isinstance(details, dict):
                total = details.get('total', 0)
                detected = details.get('detected', 0)
                coverage = details.get('coverage', 0.0)
                if total > 0:
                    print(f"   {entity_type}: {detected}/{total} ({coverage:.2%})")
    
    # ART
    art = eval_result.get("art", {})
    if "art_star" in art:
        print(f"\n4. 平均推理时间(ART): {art.get('minutes', 0.0):.2f} 分钟")
        print(f"   ART*评分: {art.get('art_star', 0.0):.2f}")
    else:
        print(f"\n4. 平均推理时间(ART): {art.get('message', 'N/A')}")
    
    # Final Score
    final_score = eval_result.get("final_score", {})
    score = final_score.get("final_score", 0.0)
    print(f"\n5. 最终分数(Final Score): {score:.4f}")
    print(f"   计算公式: {final_score.get('formula', 'N/A')}")
    print(f"   组成: ER={final_score.get('er', 0.0):.2f}, AR={final_score.get('ar', 0.0):.2f}, ECR={final_score.get('ecr', 0.0):.2f}")
    
    print("\n" + "-" * 60)
    
    return eval_result


def main():
    if not check_api_key():
        sys.exit(1)
    try:
        choice = input("\nInput the query number : (1-120) ").strip()
        question_id, question, question_item = get_query(choice)
        
        # 记录开始时间
        start_time = time.time()
        
        # 获取结果
        result = get_result_task(question)
        
        # 计算推理时间
        inference_time_seconds = time.time() - start_time
        
        # 评估结果
        if result:
            eval_result = evaluate_result(
                result=result,
                question_id=str(question_id),
                question=question,
                inference_time_seconds=inference_time_seconds
            )
            
            # 可选：保存评估结果到文件
            # if eval_result:
            #     output_file = f"evaluation_result_{question_id}.json"
            #     with open(output_file, "w", encoding="utf-8") as f:
            #         json.dump(eval_result, f, ensure_ascii=False, indent=2)
            #     print(f"\n评估结果已保存到: {output_file}")
        else:
            print("\n 无法进行评估：未生成有效结果")
        
    except KeyboardInterrupt:
        print("\n\n Application terminated by user")
    except Exception as e:
        print(f"\n Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()