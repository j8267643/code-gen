"""
Evaluator-Optimizer Example - 评估者-优化者示例

展示 PraisonAI 风格的迭代优化功能
通过生成-评估-优化的闭环提升输出质量
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from code_gen.agents import (
    EvaluatorOptimizer,
    LLMGenerator,
    LLMEvaluator,
    CodeEvaluator,
    OptimizationStatus,
    optimize_solution,
    create_code_optimizer,
    create_content_optimizer
)


async def example_1_basic_optimizer():
    """示例1: 基础优化器使用"""
    print("\n" + "="*60)
    print("示例1: 基础优化器使用")
    print("="*60 + "\n")
    
    # 创建生成器和评估器
    generator = LLMGenerator(name="ContentGenerator")
    evaluator = LLMEvaluator(name="ContentEvaluator")
    
    # 创建优化器
    optimizer = EvaluatorOptimizer(
        generator=generator,
        evaluator=evaluator,
        max_iterations=3,
        pass_threshold=0.8
    )
    
    print("任务: 生成一篇关于 Python 异步编程的文章")
    print("开始优化循环...\n")
    
    # 执行优化
    result = await optimizer.optimize(
        task="写一篇关于 Python 异步编程的简短文章",
        context={"target_audience": "初学者", "length": "short"}
    )
    
    print(f"优化完成!")
    print(f"  状态: {result.status.value}")
    print(f"  迭代次数: {result.total_iterations}")
    print(f"  最终评分: {result.final_score:.2f}")
    print(f"  执行时间: {result.execution_time:.2f}s")
    print(f"  是否成功: {'是' if result.success else '否'}")
    
    # 打印优化报告
    print("\n" + optimizer.get_optimization_report())


async def example_2_code_optimizer():
    """示例2: 代码优化器"""
    print("\n" + "="*60)
    print("示例2: 代码优化器")
    print("="*60 + "\n")
    
    # 创建代码优化器
    optimizer = create_code_optimizer(max_iterations=5)
    
    # 初始代码（有问题的）
    initial_code = """
def calculate(x, y)
    result = x + y
    return result
"""
    
    print("任务: 优化以下代码")
    print(f"初始代码:\n{initial_code}")
    
    # 执行优化
    result = await optimizer.optimize(
        task="编写一个计算两个数和的函数",
        initial_solution=initial_code
    )
    
    print(f"\n优化完成!")
    print(f"  迭代次数: {result.total_iterations}")
    print(f"  最终评分: {result.final_score:.2f}")
    
    # 显示每次迭代的评分
    print("\n迭代评分:")
    for iteration in result.iterations:
        eval_result = iteration.evaluation
        print(f"  迭代 {iteration.iteration}: {eval_result.score:.2f} - {'通过' if eval_result.passed else '未通过'}")
        if eval_result.suggestions:
            print(f"    建议: {', '.join(eval_result.suggestions)}")


async def example_3_convenience_function():
    """示例3: 便捷函数使用"""
    print("\n" + "="*60)
    print("示例3: 便捷函数使用")
    print("="*60 + "\n")
    
    print("使用 optimize_solution 便捷函数:\n")
    
    # 通用优化
    result = await optimize_solution(
        task="生成一个数据处理的方案",
        solution_type="general",
        max_iterations=2
    )
    
    print(f"通用优化结果:")
    print(f"  成功: {result.success}")
    print(f"  迭代: {result.total_iterations}")
    print(f"  评分: {result.final_score:.2f}")


async def example_4_content_optimizer():
    """示例4: 内容优化器"""
    print("\n" + "="*60)
    print("示例4: 内容优化器")
    print("="*60 + "\n")
    
    # 创建内容优化器
    optimizer = create_content_optimizer(max_iterations=3)
    
    print("任务: 优化产品描述")
    
    # 执行优化
    result = await optimizer.optimize(
        task="为一款智能手表撰写产品描述",
        context={
            "product": "智能手表",
            "features": ["心率监测", "GPS", "防水"],
            "target": "运动爱好者"
        }
    )
    
    print(f"优化完成!")
    print(f"  总迭代: {result.total_iterations}")
    print(f"  最终评分: {result.final_score:.2f}")
    
    # 显示每次迭代的反馈
    print("\n优化过程:")
    for iteration in result.iterations:
        print(f"\n  迭代 {iteration.iteration}:")
        print(f"    评分: {iteration.evaluation.score:.2f}")
        print(f"    反馈: {iteration.evaluation.feedback}")


async def example_5_early_stopping():
    """示例5: 早停机制"""
    print("\n" + "="*60)
    print("示例5: 早停机制")
    print("="*60 + "\n")
    
    generator = LLMGenerator()
    evaluator = LLMEvaluator()
    
    # 启用早停
    optimizer = EvaluatorOptimizer(
        generator=generator,
        evaluator=evaluator,
        max_iterations=10,  # 设置较大的最大迭代
        early_stopping=True  # 启用早停
    )
    
    print("任务: 生成文档（启用早停）")
    print("如果连续2次评分没有提升，将提前停止\n")
    
    result = await optimizer.optimize(
        task="生成 API 文档",
        context={"api": "REST API", "endpoint": "/users"}
    )
    
    print(f"实际迭代次数: {result.total_iterations}")
    print(f"早停节省了 {10 - result.total_iterations} 次迭代")


async def example_6_custom_evaluator():
    """示例6: 自定义评估器"""
    print("\n" + "="*60)
    print("示例6: 自定义评估器")
    print("="*60 + "\n")
    
    # 创建自定义评估器
    class CustomEvaluator(LLMEvaluator):
        """自定义评估器 - 检查特定关键词"""
        
        async def evaluate(self, solution, task, criteria=None):
            # 调用父类评估
            result = await super().evaluate(solution, task, criteria)
            
            # 添加自定义检查
            required_keywords = ["Python", "async"]
            found_keywords = [k for k in required_keywords if k in solution]
            
            if len(found_keywords) < len(required_keywords):
                result.score *= 0.8
                result.passed = result.score >= 0.8
                result.suggestions.append(f"缺少关键词: {set(required_keywords) - set(found_keywords)}")
            
            return result
    
    generator = LLMGenerator()
    evaluator = CustomEvaluator()
    
    optimizer = EvaluatorOptimizer(
        generator=generator,
        evaluator=evaluator,
        max_iterations=3
    )
    
    print("使用自定义评估器（检查关键词）")
    
    result = await optimizer.optimize(
        task="编写 Python 异步编程教程"
    )
    
    print(f"优化完成，迭代: {result.total_iterations}")


async def main():
    """运行所有示例"""
    print("\n" + "🔄"*30)
    print("Evaluator-Optimizer (评估者-优化者) 示例")
    print("🔄"*30)
    
    await example_1_basic_optimizer()
    await example_2_code_optimizer()
    await example_3_convenience_function()
    await example_4_content_optimizer()
    await example_5_early_stopping()
    await example_6_custom_evaluator()
    
    print("\n" + "="*60)
    print("所有示例完成!")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
