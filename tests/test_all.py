"""Test all systems"""
import asyncio
import sys
import importlib.util
from pathlib import Path

async def run_test_file(test_file: Path):
    """Run a single test file"""
    try:
        # Load module from file
        spec = importlib.util.spec_from_file_location(
            test_file.stem, 
            test_file
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[test_file.stem] = module
        spec.loader.exec_module(module)
        
        # Run test function - try different naming patterns
        test_func = None
        
        # Try test_<filename> first
        func_name = test_file.stem
        if hasattr(module, func_name):
            test_func = getattr(module, func_name)
        else:
            # Try test_<filename>_system
            func_name = f"{test_file.stem}_system"
            if hasattr(module, func_name):
                test_func = getattr(module, func_name)
        
        if test_func:
            await test_func()
            return True
        else:
            print(f"✗ 未找到测试函数")
            return False
            
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def run_all_tests():
    """Run all system tests"""
    print("="*60)
    print("Claude Code 系统测试套件")
    print("="*60)
    
    tests_dir = Path(__file__).parent
    test_files = list(tests_dir.glob("test_*.py"))
    test_files = [f for f in test_files if f.name != "test_all.py"]
    
    print(f"\n找到 {len(test_files)} 个测试文件")
    
    passed = 0
    failed = 0
    
    for test_file in sorted(test_files):
        print(f"\n{'='*60}")
        print(f"运行测试: {test_file.stem}")
        print('='*60)
        
        if await run_test_file(test_file):
            passed += 1
            print(f"\n✓ {test_file.stem} 通过")
        else:
            failed += 1
            print(f"\n✗ {test_file.stem} 失败")
    
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
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
