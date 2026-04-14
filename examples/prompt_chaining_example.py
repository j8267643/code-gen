"""
Prompt Chaining Example - 提示链示例

展示 PraisonAI 风格的链式任务执行
将复杂任务拆解为顺序执行的子任务链
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from code_gen.agents import (
    PromptChain,
    ChainStep,
    FunctionStep,
    LLMStep,
    ConditionalStep,
    ParallelStep,
    ChainContext,
    ChainStatus,
    ChainPresets,
    run_chain,
    create_step,
    create_llm_step,
    create_parallel_step
)


async def example_1_basic_chain():
    """示例1: 基础链式执行"""
    print("\n" + "="*60)
    print("示例1: 基础链式执行")
    print("="*60 + "\n")
    
    # 创建链
    chain = PromptChain("BasicChain")
    
    # 添加步骤
    chain.add(FunctionStep(
        name="step1",
        func=lambda ctx: f"处理: {ctx.get('input', 'default')}",
        description="第一步处理"
    ))
    
    chain.add(FunctionStep(
        name="step2",
        func=lambda ctx: f"{ctx.get('step1_output')} -> 第二步",
        description="第二步处理"
    ))
    
    chain.add(FunctionStep(
        name="step3",
        func=lambda ctx: f"{ctx.get('step2_output')} -> 完成",
        description="第三步处理"
    ))
    
    # 执行链
    result = await chain.execute(initial_context={"input": "Hello"})
    
    print(f"链执行结果:")
    print(f"  成功: {result.success}")
    print(f"  总步骤: {result.total_steps}")
    print(f"  完成步骤: {result.completed_steps}")
    print(f"  最终输出: {result.final_output}")
    print(f"  执行时间: {result.execution_time:.2f}s")
    
    # 打印执行报告
    print("\n" + chain.get_execution_report())


async def example_2_chain_operators():
    """示例2: 链式操作符"""
    print("\n" + "="*60)
    print("示例2: 链式操作符 (>>)")
    print("="*60 + "\n")
    
    # 使用 >> 操作符创建链
    chain = PromptChain("OperatorChain")
    
    step1 = create_step("extract", lambda ctx: f"提取: {ctx.get('data')}")
    step2 = create_step("transform", lambda ctx: f"转换: {ctx.get('extract_output')}")
    step3 = create_step("load", lambda ctx: f"加载: {ctx.get('transform_output')}")
    
    # 使用 >> 连接
    chain >> step1 >> step2 >> step3
    
    result = await chain.execute(initial_context={"data": "原始数据"})
    
    print("使用 >> 操作符连接步骤:")
    print(f"  extract >> transform >> load")
    print(f"\n执行结果: {result.final_output}")


async def example_3_conditional_chain():
    """示例3: 条件分支链"""
    print("\n" + "="*60)
    print("示例3: 条件分支链")
    print("="*60 + "\n")
    
    chain = PromptChain("ConditionalChain")
    
    # 条件步骤
    def check_type(ctx):
        return ctx.get("type") == "code"
    
    code_step = create_step("code_process", lambda ctx: "处理代码...")
    text_step = create_step("text_process", lambda ctx: "处理文本...")
    
    conditional = ConditionalStep(
        name="router",
        condition_func=check_type,
        true_step=code_step,
        false_step=text_step,
        description="根据类型路由"
    )
    
    chain.add(conditional)
    
    # 测试代码类型
    print("测试1: 类型 = code")
    result1 = await chain.execute(initial_context={"type": "code"})
    print(f"  结果: {result1.final_output}")
    
    # 测试文本类型
    print("\n测试2: 类型 = text")
    result2 = await chain.execute(initial_context={"type": "text"})
    print(f"  结果: {result2.final_output}")


async def example_4_parallel_chain():
    """示例4: 并行步骤"""
    print("\n" + "="*60)
    print("示例4: 并行步骤")
    print("="*60 + "\n")
    
    chain = PromptChain("ParallelChain")
    
    # 创建并行步骤
    parallel_steps = [
        create_step("task_a", lambda ctx: "任务A结果"),
        create_step("task_b", lambda ctx: "任务B结果"),
        create_step("task_c", lambda ctx: "任务C结果"),
    ]
    
    # 聚合函数
    def aggregate_results(results):
        return f"聚合结果: {' | '.join(str(r) for r in results)}"
    
    parallel = create_parallel_step(
        name="parallel_tasks",
        steps=parallel_steps,
        aggregate_func=aggregate_results
    )
    
    chain.add(parallel)
    
    result = await chain.execute()
    
    print("并行执行3个任务:")
    print(f"  结果: {result.final_output}")


async def example_5_preset_chains():
    """示例5: 预设链"""
    print("\n" + "="*60)
    print("示例5: 预设链")
    print("="*60 + "\n")
    
    # 代码生成链
    print("1. 代码生成链:")
    code_chain = ChainPresets.code_generation()
    code_result = await code_chain.execute(initial_context={
        "requirements": "创建一个用户认证系统"
    })
    print(f"   步骤: {code_result.total_steps}")
    print(f"   完成: {code_result.completed_steps}")
    
    # 文档生成链
    print("\n2. 文档生成链:")
    doc_chain = ChainPresets.document_generation()
    doc_result = await doc_chain.execute(initial_context={
        "topic": "Python 最佳实践"
    })
    print(f"   步骤: {doc_result.total_steps}")
    print(f"   完成: {doc_result.completed_steps}")
    
    # 数据处理链
    print("\n3. 数据处理链:")
    data_chain = ChainPresets.data_processing()
    data_result = await data_chain.execute(initial_context={
        "source": "database.csv"
    })
    print(f"   步骤: {data_result.total_steps}")
    print(f"   最终输出: {data_result.final_output}")


async def example_6_error_handling():
    """示例6: 错误处理"""
    print("\n" + "="*60)
    print("示例6: 错误处理")
    print("="*60 + "\n")
    
    chain = PromptChain("ErrorHandling")
    
    # 会失败的步骤
    def failing_step(ctx):
        raise ValueError("模拟错误")
    
    chain.add(FunctionStep(
        name="success_step",
        func=lambda ctx: "成功步骤",
        description="正常步骤"
    ))
    
    chain.add(FunctionStep(
        name="failing_step",
        func=failing_step,
        description="会失败的步骤"
    ))
    
    chain.add(FunctionStep(
        name="never_run",
        func=lambda ctx: "不会执行",
        description="不会执行的步骤"
    ))
    
    # 设置错误处理器
    async def error_handler(ctx, error):
        print(f"  捕获错误: {error}")
        ctx.set("error_handled", True)
    
    chain.on_error("failing_step", error_handler)
    
    # 执行（出错停止）
    print("执行链（出错时停止）:")
    result = await chain.execute(stop_on_error=True)
    print(f"  成功: {result.success}")
    print(f"  完成步骤: {result.completed_steps}")
    print(f"  失败步骤: {result.failed_steps}")
    
    # 执行（出错继续）
    print("\n执行链（出错时继续）:")
    result2 = await chain.execute(stop_on_error=False)
    print(f"  成功: {result2.success}")
    print(f"  完成步骤: {result2.completed_steps}")


async def example_7_context_management():
    """示例7: 上下文管理"""
    print("\n" + "="*60)
    print("示例7: 上下文管理")
    print("="*60 + "\n")
    
    chain = PromptChain("ContextChain")
    
    # 步骤之间传递数据
    chain.add(FunctionStep(
        name="set_data",
        func=lambda ctx: ctx.set("key", "value") or "数据已设置"
    ))
    
    chain.add(FunctionStep(
        name="get_data",
        func=lambda ctx: f"获取到: {ctx.get('key')}"
    ))
    
    chain.add(FunctionStep(
        name="update_data",
        func=lambda ctx: ctx.update({"key2": "value2", "key3": "value3"}) or "数据已更新"
    ))
    
    result = await chain.execute()
    
    print("上下文数据传递:")
    print(f"  最终上下文: {result.context.data}")


async def example_8_convenience_functions():
    """示例8: 便捷函数"""
    print("\n" + "="*60)
    print("示例8: 便捷函数")
    print("="*60 + "\n")
    
    # 使用 run_chain 便捷函数
    steps = [
        create_step("step1", lambda ctx: "步骤1"),
        create_step("step2", lambda ctx: "步骤2"),
        create_step("step3", lambda ctx: "步骤3"),
    ]
    
    result = await run_chain(
        steps=steps,
        initial_context={"start": "begin"},
        name="ConvenienceChain"
    )
    
    print("使用 run_chain 便捷函数:")
    print(f"  成功: {result.success}")
    print(f"  步骤数: {result.total_steps}")
    print(f"  最终输出: {result.final_output}")


async def example_9_complex_workflow():
    """示例9: 复杂工作流示例"""
    print("\n" + "="*60)
    print("示例9: 复杂工作流 - 代码审查流程")
    print("="*60 + "\n")
    
    chain = PromptChain("CodeReviewWorkflow")
    
    # 步骤1: 静态分析
    chain.add(FunctionStep(
        name="static_analysis",
        func=lambda ctx: "静态分析完成: 发现3个问题",
        description="静态代码分析"
    ))
    
    # 步骤2: 安全检查
    chain.add(FunctionStep(
        name="security_check",
        func=lambda ctx: "安全检查完成: 无高危漏洞",
        description="安全漏洞检查"
    ))
    
    # 步骤3: 并行审查
    review_steps = [
        FunctionStep("syntax_review", lambda ctx: "语法审查通过"),
        FunctionStep("style_review", lambda ctx: "风格审查通过"),
        FunctionStep("logic_review", lambda ctx: "逻辑审查通过"),
    ]
    
    chain.add(ParallelStep(
        name="parallel_reviews",
        steps=review_steps,
        aggregate_func=lambda results: f"审查结果: {len(results)}项通过"
    ))
    
    # 步骤4: 生成报告
    chain.add(FunctionStep(
        name="generate_report",
        func=lambda ctx: f"报告: {ctx.get('parallel_reviews_output')}",
        description="生成审查报告"
    ))
    
    result = await chain.execute(initial_context={
        "code": "def example(): pass",
        "language": "python"
    })
    
    print("代码审查工作流执行完成:")
    print(f"  总步骤: {result.total_steps}")
    print(f"  成功: {result.success}")
    print(f"  最终报告: {result.final_output}")
    
    print("\n执行详情:")
    for step_result in result.step_results:
        status = "✅" if step_result.success else "❌"
        print(f"  {status} {step_result.step_name}: {step_result.status.value}")


async def main():
    """运行所有示例"""
    print("\n" + "⛓️"*30)
    print("Prompt Chaining (提示链) 示例")
    print("⛓️"*30)
    
    await example_1_basic_chain()
    await example_2_chain_operators()
    await example_3_conditional_chain()
    await example_4_parallel_chain()
    await example_5_preset_chains()
    await example_6_error_handling()
    await example_7_context_management()
    await example_8_convenience_functions()
    await example_9_complex_workflow()
    
    print("\n" + "="*60)
    print("所有示例完成!")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
