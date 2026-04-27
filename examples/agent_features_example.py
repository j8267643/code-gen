"""
Agent 增强功能使用示例

展示了如何使用五大核心功能：
1. Lakeview - 智能步骤摘要
2. Sequential Thinking - 序列化思考
3. Trajectory Recording - 轨迹记录
4. Task Done Tool - 任务完成标记
5. Advanced Edit Tools - 高级编辑工具
"""

from code_gen.agent_features import create_agent_features


def example_lakeview():
    """Lakeview 步骤摘要示例"""
    print("=" * 60)
    print("🌊 Lakeview 步骤摘要示例")
    print("=" * 60)
    
    features = create_agent_features(
        lakeview=True,
        sequential_thinking=False,
        trajectory=False,
        task_done=False,
        advanced_edit=False
    )
    
    # 模拟 Agent 执行步骤
    steps = [
        ("分析项目结构", "检测到全栈项目", "analyze_project"),
        ("读取后端代码", "读取了 main.py", "read_file"),
        ("搜索 bug 位置", "在 routes.py 找到问题", "search_codebase"),
        ("编写修复代码", "修复了空指针异常", "write_file"),
        ("运行测试", "测试通过", "run_command"),
        ("报告结果", "任务完成", "report"),
    ]
    
    for action, result, tool in steps:
        summary = features.lakeview.record_step(action, result, tool)
        print(f"  {summary}")
    
    print("\n📊 完整摘要:")
    print(features.lakeview.get_summary())


def example_sequential_thinking():
    """序列化思考示例"""
    print("\n" + "=" * 60)
    print("🧠 Sequential Thinking 序列化思考示例")
    print("=" * 60)
    
    features = create_agent_features(
        lakeview=False,
        sequential_thinking=True,
        trajectory=False,
        task_done=False,
        advanced_edit=False
    )
    
    # 开始思考
    print(features.thinking.start("如何设计一个高性能的缓存系统"))
    
    # 逐步思考
    print(features.thinking.think(
        "首先分析需求：需要支持高并发读写，数据一致性要求高",
        "analysis"
    ))
    
    print(features.thinking.think(
        "考虑使用 Redis 作为缓存层，支持分布式部署",
        "hypothesis"
    ))
    
    print(features.thinking.think(
        "验证方案：Redis 可以支持 10万+ QPS，满足需求",
        "verification"
    ))
    
    print(features.thinking.think(
        "但需要考虑缓存穿透和雪崩问题，需要添加布隆过滤器和熔断机制",
        "analysis"
    ))
    
    # 得出结论
    print(features.thinking.conclude(
        "采用 Redis 集群 + 布隆过滤器 + 熔断机制的方案"
    ))


def example_trajectory():
    """轨迹记录示例"""
    print("\n" + "=" * 60)
    print("📈 Trajectory Recording 轨迹记录示例")
    print("=" * 60)
    
    features = create_agent_features(
        lakeview=False,
        sequential_thinking=False,
        trajectory=True,
        task_done=False,
        advanced_edit=False,
        trajectory_output_dir="./example_trajectories"
    )
    
    # 开始记录
    print(features.trajectory.start(
        task="修复用户登录 bug",
        provider="ollama",
        model="qwen2.5-coder:14b",
        max_steps=50
    ))
    
    # 记录 Agent 步骤
    step_id = features.trajectory.record_agent_step(
        action="分析登录失败原因",
        reasoning="用户报告登录时返回 500 错误"
    )
    print(f"  记录步骤: {step_id}")
    
    # 记录工具调用
    tool_id = features.trajectory.record_tool_call(
        tool_name="read_file",
        arguments={"path": "auth.py"}
    )
    print(f"  记录工具调用: {tool_id}")
    
    # 记录工具结果
    features.trajectory.record_tool_result(
        tool_id,
        result="发现第 45 行空指针异常"
    )
    print("  记录工具结果")
    
    # 完成记录
    result = features.trajectory.finish(
        success=True,
        result="修复了 auth.py 中的空指针异常"
    )
    print(f"\n{result}")


def example_task_done():
    """任务完成标记示例"""
    print("\n" + "=" * 60)
    print("✅ Task Done Tool 任务完成标记示例")
    print("=" * 60)
    
    features = create_agent_features(
        lakeview=False,
        sequential_thinking=False,
        trajectory=False,
        task_done=True,
        advanced_edit=False
    )
    
    # 开始任务（使用 code_fix 模板）
    print(features.task_done.start(
        task_description="修复用户登录 bug",
        verification_template="code_fix"
    ))
    
    # 尝试直接完成（会失败，因为验证未完成）
    print("\n尝试直接完成...")
    result = features.task_done.done(
        summary="修复了登录 bug",
        force=False
    )
    print(result)
    
    # 完成验证步骤
    print("\n完成验证步骤...")
    print(features.task_done.verify("reproduce_bug", "成功复现登录失败"))
    print(features.task_done.verify("apply_fix", "修复了空指针异常"))
    print(features.task_done.verify("test_fix", "单元测试通过"))
    print(features.task_done.verify("check_regression", "未发现新问题"))
    
    # 再次尝试完成
    print("\n再次尝试完成...")
    result = features.task_done.done(
        summary="修复了 auth.py 中的空指针异常，所有测试通过",
        artifacts="auth.py, test_auth.py"
    )
    print(result)


def example_advanced_edit():
    """高级编辑工具示例"""
    print("\n" + "=" * 60)
    print("📝 Advanced Edit Tools 高级编辑工具示例")
    print("=" * 60)
    
    import tempfile
    import os
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as tmpdir:
        features = create_agent_features(
            lakeview=False,
            sequential_thinking=False,
            trajectory=False,
            task_done=False,
            advanced_edit=True,
            working_dir=tmpdir
        )
        
        # 创建示例文件
        print("1. 创建文件...")
        content = """def hello():
    print("Hello, World!")

def goodbye():
    print("Goodbye!")

if __name__ == "__main__":
    hello()
    goodbye()
"""
        result = features.edit.create("example.py", content)
        print(result)
        
        # 查看文件
        print("\n2. 查看文件...")
        print(features.edit.view("example.py"))
        
        # 查看特定行范围
        print("\n3. 查看 3-5 行...")
        print(features.edit.view("example.py", "3-5"))
        
        # 字符串替换
        print("\n4. 替换字符串...")
        old_str = '''def hello():
    print("Hello, World!")'''
        new_str = '''def hello(name="World"):
    print(f"Hello, {name}!")'''
        print(features.edit.str_replace("example.py", old_str, new_str))
        
        # 插入内容
        print("\n5. 插入内容...")
        print(features.edit.insert("example.py", 2, "# 这是一个示例函数\n"))
        
        # 查看修改后的文件
        print("\n6. 查看修改后的文件...")
        print(features.edit.view("example.py"))


def example_full_workflow():
    """完整工作流示例 - 结合所有功能"""
    print("\n" + "=" * 60)
    print("🚀 完整工作流示例 - 结合所有功能")
    print("=" * 60)
    
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # 启用所有功能
        features = create_agent_features(
            trajectory_output_dir=f"{tmpdir}/trajectories",
            working_dir=tmpdir
        )
        
        print("开始任务: 修复登录 bug\n")
        
        # 1. 开始轨迹记录
        features.trajectory.start("修复登录 bug", "ollama", "qwen2.5-coder:14b")
        
        # 2. 开始任务（带验证）
        features.task_done.start("修复登录 bug", "code_fix")
        
        # 3. 记录步骤
        features.lakeview.record_step("分析问题", "用户报告登录失败", "analyze")
        
        # 4. 序列化思考
        features.thinking.start("登录失败原因分析")
        features.thinking.think("检查日志发现 500 错误", "analysis")
        features.thinking.think("可能是数据库连接问题", "hypothesis")
        features.thinking.conclude("确认是空指针异常导致")
        
        # 5. 创建修复文件
        features.lakeview.record_step("编写修复", "创建修复代码", "write_fix")
        features.edit.create("fix.py", "# 修复代码\ndef fix_login():\n    pass")
        
        # 6. 完成验证
        features.task_done.verify("reproduce_bug", "已复现")
        features.task_done.verify("apply_fix", "已修复")
        features.task_done.verify("test_fix", "测试通过")
        features.task_done.verify("check_regression", "无回归")
        
        # 7. 完成任务
        features.task_done.done("修复完成")
        features.lakeview.record_step("完成任务", "登录 bug 已修复", "report")
        
        # 8. 保存轨迹
        result = features.trajectory.finish(success=True, result="修复完成")
        
        print("\n📊 执行摘要:")
        print(features.lakeview.get_summary())
        print(f"\n{result}")


if __name__ == "__main__":
    # 运行所有示例
    example_lakeview()
    example_sequential_thinking()
    example_trajectory()
    example_task_done()
    example_advanced_edit()
    example_full_workflow()
    
    print("\n" + "=" * 60)
    print("✨ 所有示例运行完成!")
    print("=" * 60)
