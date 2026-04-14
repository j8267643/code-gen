"""
Advanced Workflow Examples - 高级工作流示例

展示 PraisonAI 风格的高级工作流特性：
1. 管理代理模式
2. 条件分支任务
3. 循环任务处理
4. 工作流管理器
5. 动态路由
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from code_gen.agents import (
    Agent,
    AdvancedWorkflowExecutor,
    AdvancedTask,
    TaskType,
    TaskContext,
    WorkflowManager,
    Route,
    create_decision_task,
    create_loop_task
)


async def example_1_basic_workflow():
    """示例1: 基础顺序工作流"""
    print("\n" + "="*60)
    print("示例1: 基础顺序工作流")
    print("="*60 + "\n")
    
    # 创建代理
    researcher = Agent(
        name="researcher",
        role="研究员",
        goal="收集信息",
        backstory="专业的信息研究员"
    )
    
    writer = Agent(
        name="writer",
        role="作家",
        goal="撰写内容",
        backstory="经验丰富的作家"
    )
    
    # 创建任务
    tasks = [
        AdvancedTask(
            name="research",
            description="研究人工智能的最新发展趋势",
            agent=researcher
        ),
        AdvancedTask(
            name="write",
            description="基于研究结果撰写一篇简短的文章",
            agent=writer,
            context_tasks=["research"]  # 依赖 research 任务的结果
        )
    ]
    
    # 执行工作流
    executor = AdvancedWorkflowExecutor(Path("."))
    result = await executor.execute_workflow(
        tasks=tasks,
        initial_input="AI发展趋势"
    )
    
    print(f"\n工作流结果: {'成功' if result['success'] else '失败'}")
    return result


async def example_2_decision_workflow():
    """示例2: 条件分支工作流"""
    print("\n" + "="*60)
    print("示例2: 条件分支工作流（内容质量检查）")
    print("="*60 + "\n")
    
    # 创建代理
    writer = Agent(
        name="writer",
        role="内容创作者",
        goal="创建内容",
        backstory="创意内容创作者"
    )
    
    editor = Agent(
        name="editor",
        role="编辑",
        goal="审核内容",
        backstory="资深内容编辑"
    )
    
    publisher = Agent(
        name="publisher",
        role="发布者",
        goal="发布内容",
        backstory="内容发布专家"
    )
    
    # 创建任务
    tasks = [
        AdvancedTask(
            name="create_content",
            description="创建一段关于Python编程的简介",
            agent=writer
        ),
        create_decision_task(
            name="quality_check",
            description="评估内容质量，判断是 'good'（优秀）还是 'poor'（需改进）",
            agent=editor,
            condition_map={
                "good": "publish",
                "poor": "revise",
                "default": "revise"
            },
            context_tasks=["create_content"]
        ),
        AdvancedTask(
            name="revise",
            description="改进内容质量",
            agent=writer,
            context_tasks=["quality_check"]
        ),
        AdvancedTask(
            name="publish",
            description="发布最终内容",
            agent=publisher,
            context_tasks=["create_content"]
        )
    ]
    
    executor = AdvancedWorkflowExecutor(Path("."))
    result = await executor.execute_workflow(tasks)
    
    print(f"\n工作流结果: {'成功' if result['success'] else '失败'}")
    return result


async def example_3_loop_workflow():
    """示例3: 循环任务工作流"""
    print("\n" + "="*60)
    print("示例3: 循环任务工作流（批量数据处理）")
    print("="*60 + "\n")
    
    # 创建代理
    processor = Agent(
        name="processor",
        role="数据处理器",
        goal="处理数据",
        backstory="数据处理专家"
    )
    
    # 模拟循环数据
    items = [
        {"name": "产品A", "price": 100},
        {"name": "产品B", "price": 200},
        {"name": "产品C", "price": 150}
    ]
    
    tasks = [
        create_loop_task(
            name="process_items",
            description="分析产品 {name}，价格 {price} 元，给出简短评价",
            agent=processor,
            loop_data=items,
            loop_variable="item"
        )
    ]
    
    executor = AdvancedWorkflowExecutor(Path("."))
    result = await executor.execute_workflow(tasks)
    
    print(f"\n工作流结果: {'成功' if result['success'] else '失败'}")
    if result['success']:
        task_result = result['results'].get('process_items', {})
        print(f"处理项目数: {task_result.get('loop_count', 0)}")
    
    return result


async def example_4_workflow_manager():
    """示例4: 工作流管理器"""
    print("\n" + "="*60)
    print("示例4: 工作流管理器")
    print("="*60 + "\n")
    
    # 创建管理器
    manager = WorkflowManager()
    
    # 创建代理
    analyst = Agent(
        name="analyst",
        role="分析师",
        goal="分析数据",
        backstory="数据分析专家"
    )
    
    # 注册工作流
    analysis_tasks = [
        AdvancedTask(
            name="data_analysis",
            description="分析销售数据趋势",
            agent=analyst
        )
    ]
    
    manager.register_workflow(
        name="sales_analysis",
        tasks=analysis_tasks,
        description="销售数据分析工作流"
    )
    
    # 列出工作流
    print(f"已注册工作流: {manager.list_workflows()}")
    
    # 获取工作流信息
    info = manager.get_workflow_info("sales_analysis")
    print(f"工作流描述: {info.get('description')}")
    
    # 运行工作流
    # result = await manager.run("sales_analysis", Path("."))
    
    print("\n工作流管理器示例完成")


async def example_5_dynamic_routing():
    """示例5: 动态路由"""
    print("\n" + "="*60)
    print("示例5: 基于上下文的动态路由")
    print("="*60 + "\n")
    
    # 创建代理
    classifier = Agent(
        name="classifier",
        role="分类器",
        goal="分类问题类型",
        backstory="问题分类专家"
    )
    
    tech_agent = Agent(
        name="tech_support",
        role="技术支持",
        goal="解决技术问题",
        backstory="技术专家"
    )
    
    billing_agent = Agent(
        name="billing_support",
        role="账单支持",
        goal="解决账单问题",
        backstory="账单专家"
    )
    
    # 定义路由条件
    def route_by_type(context: TaskContext) -> str:
        """根据问题类型路由"""
        query = context.get("query", "").lower()
        if "账单" in query or "付款" in query or "价格" in query:
            return "billing"
        return "technical"
    
    # 创建带路由的任务
    route_task = AdvancedTask(
        name="classify_and_route",
        description="用户问题: {query}",
        agent=classifier,
        route=Route(
            condition=route_by_type,
            routes={
                "technical": "tech_support",
                "billing": "billing_support"
            },
            default="tech_support"
        )
    )
    
    # 模拟上下文
    context = TaskContext()
    context.set("query", "我的账单有问题")
    
    # 评估路由
    next_task = route_task.route.evaluate(context)
    print(f"问题: '{context.get('query')}'")
    print(f"路由到: {next_task}")
    
    # 另一个例子
    context.set("query", "软件无法启动")
    next_task = route_task.route.evaluate(context)
    print(f"\n问题: '{context.get('query')}'")
    print(f"路由到: {next_task}")


async def example_6_manager_agent():
    """示例6: 使用管理代理优化执行"""
    print("\n" + "="*60)
    print("示例6: 管理代理模式")
    print("="*60 + "\n")
    
    # 创建代理
    agent1 = Agent(name="agent1", role="角色1", goal="任务1", backstory="背景1")
    agent2 = Agent(name="agent2", role="角色2", goal="任务2", backstory="背景2")
    agent3 = Agent(name="agent3", role="角色3", goal="任务3", backstory="背景3")
    
    # 创建有依赖关系的任务
    tasks = [
        AdvancedTask(
            name="task_a",
            description="任务A",
            agent=agent1
        ),
        AdvancedTask(
            name="task_b",
            description="任务B",
            agent=agent2,
            context_tasks=["task_a"]  # 依赖 task_a
        ),
        AdvancedTask(
            name="task_c",
            description="任务C",
            agent=agent3,
            context_tasks=["task_a"]  # 也依赖 task_a
        ),
        AdvancedTask(
            name="task_d",
            description="任务D",
            agent=agent1,
            context_tasks=["task_b", "task_c"]  # 依赖 task_b 和 task_c
        )
    ]
    
    executor = AdvancedWorkflowExecutor(Path("."))
    
    # 使用管理代理分析工作流
    plan = await executor.manager.analyze_workflow(tasks, TaskContext())
    
    print("管理代理分析结果:")
    print(f"  执行顺序: {' -> '.join(plan['execution_order'])}")
    print(f"  并行组:")
    for i, group in enumerate(plan['parallel_groups'], 1):
        print(f"    组{i}: {', '.join(group)}")
    print(f"  分析原因: {plan['reasoning']}")


async def main():
    """运行所有示例"""
    print("\n" + "🚀"*30)
    print("高级工作流系统示例")
    print("🚀"*30)
    
    # 运行示例
    # await example_1_basic_workflow()
    # await example_2_decision_workflow()
    # await example_3_loop_workflow()
    await example_4_workflow_manager()
    await example_5_dynamic_routing()
    await example_6_manager_agent()
    
    print("\n" + "="*60)
    print("所有示例完成!")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
