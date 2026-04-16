"""
集成系统演示

展示如何使用 SOP、经验池、AFLOW 和 Action Node 四大系统
"""

import asyncio
from pathlib import Path

# 导入我们的新系统
from code_gen.sop import SOP, SOPStep, SOPContext, SOPRegistry, SOPExecutor, StepType
from code_gen.exp_pool import (
    ExperienceManager, 
    ExperienceType,
    ExperienceStatus
)
from code_gen.aflow import (
    WorkflowGraph, 
    WorkflowNode, 
    WorkflowEdge,
    NodeType,
    EdgeType,
    WorkflowTemplates,
    WorkflowOptimizer,
    SimpleEvaluator,
)
from code_gen.action_node import (
    ActionNode,
    FieldDefinition,
    ActionTemplates,
    ActionExecutor,
    ActionChain,
    ActionRegistry,
)


async def demo_sop_system():
    """演示 SOP 系统"""
    print("=" * 60)
    print("SOP 系统演示")
    print("=" * 60)
    
    # 创建 SOP 注册表
    registry = SOPRegistry()
    
    # 列出内置 SOP
    print("\n内置 SOP 模板:")
    for sop in registry.list_sops():
        print(f"  - {sop.name}: {sop.description}")
        print(f"    步骤: {[s.name for s in sop.steps]}")
    
    # 获取代码生成 SOP
    code_gen_sop = registry.get("code_generation")
    print(f"\n代码生成 SOP 执行顺序:")
    for i, layer in enumerate(code_gen_sop.get_execution_order()):
        print(f"  第 {i+1} 层: {layer}")
    
    # 创建执行上下文
    context = code_gen_sop.create_context(inputs={
        "requirement": "创建一个 Python 类来管理用户认证",
        "language": "python",
    })
    
    # 创建执行器
    executor = SOPExecutor()
    
    # 注册动作处理器（模拟）
    async def mock_handler(inputs, ctx):
        print(f"  执行: {inputs.get('step_name')}")
        return {"status": "success", "output": f"Completed {inputs.get('step_name')}"}
    
    for step in code_gen_sop.steps:
        executor.register_action(step.action, mock_handler)
    
    # 执行 SOP
    print("\n执行 SOP:")
    result_context = await executor.execute(code_gen_sop, context)
    
    # 生成执行报告
    report = executor.get_execution_report(result_context)
    print(f"\n执行报告:")
    print(f"  状态: {report['status']}")
    print(f"  完成步骤: {report['completed_steps']}/{report['total_steps']}")
    print(f"  成功率: {report['success_rate']:.2%}")
    
    print("\n")
    return code_gen_sop, result_context


async def demo_exp_pool_system(sop_context):
    """演示经验池系统"""
    print("=" * 60)
    print("经验池系统演示")
    print("=" * 60)
    
    # 创建经验管理器
    manager = ExperienceManager(storage_path=Path(".demo_exp_pool"))
    
    # 从 SOP 执行中收集经验
    print("\n从 SOP 执行中收集经验...")
    experience = manager.collect_from_sop_execution(
        sop_context=sop_context,
        success=True,
        lessons=[
            "需求分析阶段需要更详细",
            "代码审查步骤很有价值",
            "测试用例应该覆盖边界情况",
        ],
    )
    
    print(f"经验已收集: {experience.id}")
    print(f"  任务: {experience.task_description}")
    print(f"  类型: {experience.experience_type.value}")
    print(f"  教训: {experience.lessons_learned}")
    
    # 添加更多示例经验
    print("\n添加更多经验...")
    
    exp2 = manager.collect_from_execution(
        task_description="修复用户登录的 bug",
        task_type=ExperienceType.BUG_FIX,
        input_context={"bug_description": "登录时密码验证失败"},
        output_result={"fix": "修复了密码哈希比较逻辑"},
        steps=[
            {"action": "analyze", "description": "分析问题"},
            {"action": "fix", "description": "修复代码"},
            {"action": "test", "description": "验证修复"},
        ],
        success=True,
        lessons=["密码比较应该使用恒定时间算法"],
        tags=["authentication", "security", "bugfix"],
    )
    
    # 评估经验
    print("\n评估经验...")
    manager.evaluate_experience(experience.id)
    manager.evaluate_experience(exp2.id)
    
    # 检索经验
    print("\n检索相关经验:")
    results = manager.retrieve_experiences(
        query="代码生成",
        exp_type=ExperienceType.CODE_GENERATION,
        limit=3,
    )
    
    for i, result in enumerate(results, 1):
        print(f"  {i}. {result.experience.task_description}")
        print(f"     评分: {result.score:.2f}, 相关度: {result.relevance:.2f}")
    
    # 获取统计
    stats = manager.get_statistics()
    print(f"\n经验池统计:")
    print(f"  总经验数: {stats['total_experiences']}")
    print(f"  总使用次数: {stats['total_usage']}")
    print(f"  整体成功率: {stats['overall_success_rate']:.2%}")
    
    print("\n")
    return manager


async def demo_aflow_system():
    """演示 AFLOW 系统"""
    print("=" * 60)
    print("AFLOW 系统演示")
    print("=" * 60)
    
    # 创建工作流模板
    print("\n创建工作流模板:")
    
    # 顺序工作流
    seq_wf = WorkflowTemplates.sequential([
        "analyze_requirements",
        "design_architecture",
        "write_code",
        "review_code",
    ], name="sequential_dev")
    print(f"  顺序工作流: {len(seq_wf.nodes)} 个节点")
    
    # 并行工作流
    par_wf = WorkflowTemplates.parallel([
        "write_tests",
        "write_docs",
        "optimize_code",
    ], name="parallel_tasks")
    print(f"  并行工作流: {len(par_wf.nodes)} 个节点")
    
    # 条件工作流
    cond_wf = WorkflowTemplates.conditional(
        condition="tests_passed",
        true_action="deploy",
        false_action="debug",
        name="conditional_deploy",
    )
    print(f"  条件工作流: {len(cond_wf.nodes)} 个节点")
    
    # 验证工作流
    print("\n验证工作流:")
    errors = seq_wf.validate()
    if errors:
        print(f"  错误: {errors}")
    else:
        print("  工作流验证通过!")
    
    # 获取执行顺序
    print(f"\n顺序工作流执行顺序:")
    for i, layer in enumerate(seq_wf.get_execution_order()):
        nodes = [seq_wf.get_node(nid).name for nid in layer]
        print(f"  第 {i+1} 层: {nodes}")
    
    # 评估工作流
    print("\n评估工作流:")
    evaluator = SimpleEvaluator()
    result = evaluator.quick_evaluate(seq_wf)
    print(f"  评分: {result.score:.2f}")
    print(f"  预估延迟: {result.avg_latency:.2f}s")
    print(f"  预估成本: ${result.cost:.2f}")
    
    # 分析瓶颈
    print("\n工作流瓶颈分析:")
    optimizer = WorkflowOptimizer()
    bottlenecks = optimizer.analyze_bottlenecks(seq_wf)
    for b in bottlenecks:
        print(f"  [{b['severity'].upper()}] {b['description']}")
    
    # 改进建议
    print("\n改进建议:")
    suggestions = optimizer.suggest_improvements(seq_wf)
    for s in suggestions:
        print(f"  - {s}")
    
    print("\n")
    return seq_wf


async def demo_action_node_system():
    """演示 Action Node 系统"""
    print("=" * 60)
    print("Action Node 系统演示")
    print("=" * 60)
    
    # 获取注册表
    registry = ActionRegistry()
    
    # 列出内置动作
    print("\n内置动作:")
    for action in registry.list_actions():
        print(f"  - {action.name}: {action.description}")
        print(f"    输入: {[f.name for f in action.input_fields]}")
        print(f"    输出: {[f.name for f in action.output_fields]}")
    
    # 创建自定义动作
    print("\n创建自定义动作:")
    custom_action = registry.create_action(
        name="database_migration",
        description="Generate database migration scripts",
        instruction="Generate a database migration script based on the schema changes.",
        input_fields=[
            {"name": "schema_changes", "type": "str", "description": "Description of schema changes", "required": True},
            {"name": "database_type", "type": "str", "description": "Type of database", "default": "postgresql"},
        ],
        output_fields=[
            {"name": "migration_script", "type": "str", "description": "The migration script", "required": True},
            {"name": "rollback_script", "type": "str", "description": "The rollback script", "required": True},
            {"name": "is_destructive", "type": "bool", "description": "Whether the migration is destructive", "required": True},
        ],
        tags=["database", "migration"],
    )
    print(f"  已创建: {custom_action.name}")
    
    # 验证输入
    print("\n验证输入:")
    valid_inputs = {
        "schema_changes": "Add users table with id, name, email columns",
        "database_type": "postgresql",
    }
    is_valid, errors = custom_action.validate_inputs(valid_inputs)
    print(f"  有效输入: {is_valid}")
    if errors:
        print(f"  错误: {errors}")
    
    # 构建提示
    print("\n构建提示:")
    prompt = custom_action.build_prompt(valid_inputs)
    print(f"  提示长度: {len(prompt)} 字符")
    print(f"  提示预览: {prompt[:200]}...")
    
    # 演示动作链
    print("\n动作链演示:")
    executor = ActionExecutor()
    
    chain = ActionChain(executor)
    chain.add_action(ActionTemplates.code_generation())
    chain.add_action(ActionTemplates.code_review())
    
    print(f"  动作链包含 {len(chain.actions)} 个动作")
    print(f"  动作: {[a.name for a in chain.actions]}")
    
    # 演示动作管道
    print("\n动作管道演示:")
    pipeline = ActionPipeline(executor)
    pipeline.add_step(ActionTemplates.code_generation(), name="generate")
    pipeline.add_parallel([
        ActionTemplates.code_review(),
        ActionTemplates.test_generation(),
    ], name="review_and_test")
    
    print(f"  管道包含 {len(pipeline.steps)} 个步骤")
    
    print("\n")
    return custom_action


async def demo_integration():
    """演示系统集成"""
    print("=" * 60)
    print("系统集成演示")
    print("=" * 60)
    
    print("\n场景: 使用 SOP + 经验池 + Action Node 完成代码生成任务")
    print("-" * 60)
    
    # 1. 使用经验池增强 SOP
    print("\n1. 经验池增强 SOP")
    manager = ExperienceManager()
    
    # 添加一些经验
    manager.collect_from_execution(
        task_description="Python 类设计",
        task_type=ExperienceType.CODE_GENERATION,
        input_context={"language": "python", "pattern": "class"},
        output_result={"code": "class User:\n    pass"},
        steps=[{"action": "design"}, {"action": "implement"}],
        success=True,
        lessons=["使用 dataclass 简化类定义"],
        tags=["python", "class", "oop"],
    )
    
    # 检索相关经验
    experiences = manager.get_relevant_experiences_for_task(
        task_description="设计用户管理类",
        task_type=ExperienceType.CODE_GENERATION,
        limit=2,
    )
    print(f"  检索到 {len(experiences)} 条相关经验")
    
    # 2. 使用 Action Node 定义 SOP 步骤
    print("\n2. Action Node 定义 SOP 步骤")
    
    # 创建 SOP 步骤对应的 Action Node
    analyze_action = ActionNode(
        name="analyze_requirements",
        description="Analyze user requirements",
        instruction="Analyze the requirements and provide a detailed breakdown.",
        input_fields=[
            FieldDefinition(name="requirements", field_type=str, required=True),
        ],
        output_fields=[
            FieldDefinition(name="analysis", field_type=dict, required=True),
            FieldDefinition(name="complexity", field_type=str, required=True),
        ],
    )
    
    code_action = ActionNode(
        name="generate_code",
        description="Generate code based on analysis",
        instruction="Generate high-quality code based on the analysis.",
        input_fields=[
            FieldDefinition(name="analysis", field_type=dict, required=True),
            FieldDefinition(name="language", field_type=str, default="python"),
        ],
        output_fields=[
            FieldDefinition(name="code", field_type=str, required=True),
            FieldDefinition(name="explanation", field_type=str, required=True),
        ],
    )
    
    print(f"  创建了 {analyze_action.name} 和 {code_action.name} 动作")
    
    # 3. 使用 AFLOW 优化工作流
    print("\n3. AFLOW 优化工作流")
    
    # 创建初始工作流
    initial_wf = WorkflowTemplates.sequential([
        "analyze_requirements",
        "generate_code",
        "review_code",
    ], name="code_generation_optimized")
    
    print(f"  初始工作流: {len(initial_wf.nodes)} 个节点")
    
    # 分析并建议改进
    optimizer = WorkflowOptimizer()
    suggestions = optimizer.suggest_improvements(initial_wf)
    print(f"  优化建议:")
    for s in suggestions[:3]:
        print(f"    - {s}")
    
    print("\n" + "=" * 60)
    print("系统集成演示完成!")
    print("=" * 60)


async def main():
    """主函数"""
    print("\n")
    print("#" * 60)
    print("# 集成系统演示")
    print("# SOP + 经验池 + AFLOW + Action Node")
    print("#" * 60)
    print("\n")
    
    # 演示各个系统
    sop, sop_context = await demo_sop_system()
    manager = await demo_exp_pool_system(sop_context)
    workflow = await demo_aflow_system()
    action = await demo_action_node_system()
    
    # 演示集成
    await demo_integration()
    
    # 总结
    print("\n" + "=" * 60)
    print("总结")
    print("=" * 60)
    print("""
四大系统已成功集成:

1. SOP 系统 (code_gen.sop)
   - 标准作业程序定义和执行
   - 支持顺序、并行、条件等执行模式
   - 内置代码生成、Bug 修复等模板

2. 经验池系统 (code_gen.exp_pool)
   - 经验收集和积累
   - 智能检索和复用
   - 持续学习和优化

3. AFLOW 系统 (code_gen.aflow)
   - 工作流图定义
   - 自动化工作流生成和优化
   - 性能评估和瓶颈分析

4. Action Node 系统 (code_gen.action_node)
   - 标准化动作定义
   - 输入输出模式验证
   - 支持链式、并行、条件执行

这些系统可以组合使用，构建强大的 AI Agent 工作流!
""")


if __name__ == "__main__":
    asyncio.run(main())
