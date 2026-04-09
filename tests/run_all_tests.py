"""Test all systems"""
import asyncio
import sys
from pathlib import Path

async def run_tests():
    """Run all system tests"""
    print("="*60)
    print("Claude Code 系统测试套件")
    print("="*60)
    
    # Test files
    test_files = [
        ("memory", "测试记忆系统"),
        ("security", "测试安全系统"),
        ("plugin", "测试插件系统"),
        ("dream", "测试Dream系统"),
        ("cost_tracker", "测试成本跟踪系统"),
        ("history", "测试历史系统"),
    ]
    
    # Import test modules
    tests_dir = Path(__file__).parent
    
    passed = 0
    failed = 0
    
    for test_name, test_description in test_files:
        try:
            print(f"\n{'='*60}")
            print(f"{test_description}")
            print('='*60)
            
            # Import and run test
            module_name = f"tests.test_{test_name}"
            module = __import__(module_name, fromlist=['test_' + test_name])
            
            test_func = getattr(module, f"test_{test_name}")
            await test_func()
            
            passed += 1
            print(f"\n✓ {test_description} 通过")
            
        except Exception as e:
            failed += 1
            print(f"\n✗ {test_description} 失败")
            print(f"  错误: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    print(f"通过: {passed}/{len(test_files)}")
    print(f"失败: {failed}/{len(test_files)}")
    
    if failed == 0:
        print("\n✓ 所有测试通过!")
        return 0
    else:
        print(f"\n✗ {failed} 个测试失败")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(run_tests())
    sys.exit(exit_code)
