#!/usr/bin/env python3
"""
AutoGen Multi-Agent Application Demo
====================================

This application demonstrates multi-agent collaboration using the AutoGen framework.
It includes three types of agents working together to complete research and reporting tasks.
"""

import os
import sys
from tasks import ResearchTask, ReportTask

def print_banner():
    """Print application banner"""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║              AutoGen Multi-Agent Application                 ║
    ║                     Demo Project                             ║
    ╚══════════════════════════════════════════════════════════════╝
    
    This demo showcases agent-to-agent communication and collaboration
    using the AutoGen framework with three specialized agents:
    
    🤖 Coordinator Agent - Manages tasks and coordinates between agents
    🔍 Research Agent   - Conducts research and gathers information  
    ✍️  Writer Agent     - Creates structured content and reports
    """
    print(banner)

def check_environment():
    """Check if required environment variables are set"""
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable is not set!")
        print("\n📝 Setup Instructions:")
        print("1. Copy .env.example to .env")
        print("2. Add your OpenAI API key to the .env file")
        print("3. Run the application again")
        return False
    return True

def demo_research_task():
    """Demonstrate the research task"""
    print("\n" + "="*60)
    print("TASK 1: RESEARCH DEMONSTRATION")
    print("="*60)
    
    research_task = ResearchTask()
    topic = "Artificial Intelligence in Healthcare"
    
    print(f"🎯 Topic: {topic}")
    print("\n🚀 Starting multi-agent collaboration...")
    print("Watch how the agents communicate and collaborate:")
    
    try:
        result = research_task.execute(topic)
        print(f"\n✅ {result}")
    except Exception as e:
        print(f"\n❌ Error in research task: {e}")

def demo_report_task():
    """Demonstrate the report generation task"""
    print("\n" + "="*60)
    print("TASK 2: REPORT GENERATION DEMONSTRATION")
    print("="*60)
    
    report_task = ReportTask()
    topic = "Future of Remote Work Technology"
    
    print(f"🎯 Topic: {topic}")
    print("\n🚀 Starting multi-agent report generation...")
    print("Observe the coordinated effort between agents:")
    
    try:
        result = report_task.execute(topic, "comprehensive")
        print(f"\n✅ {result}")
    except Exception as e:
        print(f"\n❌ Error in report task: {e}")

def main():
    """Main application entry point"""
    print_banner()
    
    # Check environment setup
    if not check_environment():
        sys.exit(1)
    
    # Show available options
    print("\n🎮 Available Demonstrations:")
    print("1. Research Task - Collaborative information gathering")
    print("2. Report Task - Coordinated report generation")
    print("3. Both tasks - Complete demonstration")
    
    try:
        choice = input("\nSelect demonstration (1/2/3) or press Enter for both: ").strip()
        
        if choice == "1":
            demo_research_task()
        elif choice == "2":
            demo_report_task()
        else:
            demo_research_task()
            demo_report_task()
        
        print("\n" + "="*60)
        print("🎉 DEMONSTRATION COMPLETED")
        print("="*60)
        print("\n📋 Summary:")
        print("✓ Multi-agent communication demonstrated")
        print("✓ Task coordination and delegation shown")
        print("✓ Collaborative problem-solving exhibited")
        print("\n💡 Key Features Demonstrated:")
        print("• Agent specialization and role definition")
        print("• Inter-agent message passing and coordination")
        print("• Task decomposition and parallel processing")
        print("• Result aggregation and presentation")
        
    except KeyboardInterrupt:
        print("\n\n👋 Application terminated by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()