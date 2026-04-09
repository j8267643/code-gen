"""Test cost tracker system"""
import asyncio
import shutil
from pathlib import Path
from code_gen.cost_tracker import CostTracker

async def test_cost_tracker():
    """Test cost tracker functionality"""
    print("\n" + "="*60)
    print("测试成本跟踪系统")
    print("="*60)
    
    # Create test directory
    test_dir = Path(__file__).parent.parent / "test_workspace"
    test_dir.mkdir(exist_ok=True)
    
    try:
        # Initialize cost tracker
        cost_tracker = CostTracker(test_dir)
        print(f"\n✓ CostTracker 初始化成功")
        print(f"  配置文件: {cost_tracker.config_path}")
        
        # Test recording usage
        print("\n--- 测试记录使用情况 ---")
        
        # Simulate API usage
        cost_tracker.record_usage(
            session_id="test_session_1",
            model="claude-3-5-sonnet",
            input_tokens=1000,
            output_tokens=500
        )
        print(f"✓ 记录使用: claude-3-5-sonnet (输入: 1000, 输出: 500)")
        
        cost_tracker.record_usage(
            session_id="test_session_2",
            model="claude-3-opus",
            input_tokens=2000,
            output_tokens=1000
        )
        print(f"✓ 记录使用: claude-3-opus (输入: 2000, 输出: 1000)")
        
        cost_tracker.record_usage(
            session_id="test_session_3",
            model="gpt-4",
            input_tokens=500,
            output_tokens=250
        )
        print(f"✓ 记录使用: gpt-4 (输入: 500, 输出: 250)")
        
        # Test cost summary
        print("\n--- 测试成本汇总 ---")
        summary = cost_tracker.get_cost_summary()
        
        print(f"✓ 成本汇总:")
        print(f"  总成本: ${summary['total_cost']:.6f}")
        print(f"  总输入Token: {summary['total_input_tokens']}")
        print(f"  总输出Token: {summary['total_output_tokens']}")
        print(f"  总会话数: {summary['total_sessions']}")
        
        print(f"\n  模型详细:")
        for model, data in summary['model_breakdown'].items():
            print(f"    {model}:")
            print(f"      成本: ${data['cost']:.6f}")
            print(f"      输入Token: {data['input_tokens']}")
            print(f"      输出Token: {data['output_tokens']}")
            print(f"      会话数: {data['sessions']}")
        
        # Test model usage
        print("\n--- 测试模型使用情况 ---")
        sonnet_usage = cost_tracker.get_model_usage("claude-3-5-sonnet")
        print(f"✓ claude-3-5-sonnet 使用:")
        print(f"  输入Token: {sonnet_usage.input_tokens}")
        print(f"  输出Token: {sonnet_usage.output_tokens}")
        print(f"  总Token: {sonnet_usage.total_tokens}")
        
        # Test recent sessions
        print("\n--- 测试最近会话 ---")
        recent = cost_tracker.get_recent_sessions(2)
        print(f"✓ 最近 {len(recent)} 个会话:")
        for session in recent:
            print(f"  - {session.session_id}: ${session.cost:.6f} ({session.model})")
        
        print("\n" + "="*60)
        print("成本跟踪系统测试完成!")
        print("="*60)
        
    finally:
        # Cleanup
        if test_dir.exists():
            shutil.rmtree(test_dir)
        print(f"\n✓ 测试目录已清理: {test_dir}")

if __name__ == "__main__":
    asyncio.run(test_cost_tracker())
