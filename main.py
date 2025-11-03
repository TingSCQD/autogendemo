
import os
import sys
from tasks import ResearchTask, ReportTask



def check_api_key():
    if not os.getenv("SILICONFLOW_API_KEY"):
        print(" Error: SILICONFLOW_API_KEY environment variable is not set!")
        print("\n Setup Instructions:")
        print("1. 复制 .env.example 到 .env")
        print("2. 在 .env 文件中添加你的 SILICONFLOW API key，如 SILICONFLOW_API_KEY=sk-xxx")
        print("3. 重新运行应用程序")
        return False
    return True

def demo_research_task():
    print("\n" + "="*60)
    print("TASK 1: RESEARCH DEMONSTRATION")
    print("="*60)
    
    research_task = ResearchTask()
    topic = "Artificial Intelligence in Healthcare"
    
    print(f" Topic: {topic}")
    print("\n Starting multi-agent collaboration...")
    print("Watch how the agents communicate and collaborate:")
    
    try:
        result = research_task.execute(topic)
        print(f"\n {result}")
    except Exception as e:
        print(f"\n Error in research task: {e}")

def demo_report_task():
    print("\n" + "="*60)
    print("TASK 2: REPORT GENERATION DEMONSTRATION")
    print("="*60)
    
    report_task = ReportTask()
    topic = "Future of Remote Work Technology"
    
    print(f" Topic: {topic}")
    print("\n Starting multi-agent report generation...")
    print("Observe the coordinated effort between agents:")
    
    try:
        result = report_task.execute(topic, "comprehensive")
        print(f"\n {result}")
    except Exception as e:
        print(f"\n Error in report task: {e}")

def main():
    if not check_api_key():
        sys.exit(1)
    try:
        choice = input("\nSelect 1/2 ").strip()
        
        if choice == "1":
            demo_research_task()
        elif choice == "2":
            demo_report_task()

    except KeyboardInterrupt:
        print("\n\n Application terminated by user")
    except Exception as e:
        print(f"\n Unexpected error: {e}")

if __name__ == "__main__":
    main()