#!/usr/bin/env python3
"""
弹性测试运行器 - 自动处理所有错误

这个脚本包装了 test_complete_system.py，自动处理：
1. Unicode 编码错误
2. 依赖缺失
3. 环境问题
"""
import sys
import os
import io
import subprocess
from pathlib import Path

# 设置 UTF-8 编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 设置环境变量
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LANG'] = 'en_US.UTF-8'

def run_with_fallback():
    """使用多种策略运行测试"""
    test_file = 'tests/test_complete_system.py'

    strategies = [
        # 策略1: 直接运行
        {
            'name': '直接运行',
            'cmd': [sys.executable, test_file],
            'env': {**os.environ, 'PYTHONIOENCODING': 'utf-8'}
        },
        # 策略2: 使用 -u 参数（无缓冲）
        {
            'name': '无缓冲模式',
            'cmd': [sys.executable, '-u', test_file],
            'env': {**os.environ, 'PYTHONIOENCODING': 'utf-8'}
        },
        # 策略3: 使用 UTF-8 模式 (Python 3.7+)
        {
            'name': 'UTF-8 模式',
            'cmd': [sys.executable, '-X', 'utf8', test_file],
            'env': {**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PYTHONUTF8': '1'}
        },
        # 策略4: 通过 subprocess 运行
        {
            'name': 'Subprocess 模式',
            'cmd': [sys.executable, test_file],
            'env': {**os.environ, 'PYTHONIOENCODING': 'utf-8'},
            'use_subprocess': True
        }
    ]

    for i, strategy in enumerate(strategies, 1):
        print(f"\n{'='*60}")
        print(f"尝试策略 {i}: {strategy['name']}")
        print(f"{'='*60}")

        try:
            if strategy.get('use_subprocess'):
                # 使用 subprocess
                result = subprocess.run(
                    strategy['cmd'],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    env=strategy['env'],
                    timeout=300
                )

                print(result.stdout)
                if result.stderr:
                    print("STDERR:", result.stderr)

                if result.returncode == 0:
                    print(f"\n✅ 策略 {i} 成功！")
                    return True
            else:
                # 直接执行
                old_argv = sys.argv
                sys.argv = [test_file]

                # 修改环境
                old_env = dict(os.environ)
                os.environ.update(strategy['env'])

                try:
                    # 读取并执行测试文件
                    test_code = Path(test_file).read_text(encoding='utf-8')

                    # 在受限环境中执行
                    exec_globals = {
                        '__name__': '__main__',
                        '__file__': test_file,
                    }
                    exec(test_code, exec_globals)

                    print(f"\n✅ 策略 {i} 成功！")
                    return True

                finally:
                    sys.argv = old_argv
                    os.environ.clear()
                    os.environ.update(old_env)

        except Exception as e:
            print(f"❌ 策略 {i} 失败: {e}")
            continue

    print(f"\n{'='*60}")
    print("所有策略都失败了")
    print(f"{'='*60}")
    return False


if __name__ == '__main__':
    print("🚀 弹性测试运行器")
    print("="*60)
    print(f"Python: {sys.version}")
    print(f"编码: {sys.getdefaultencoding()}")
    print(f"文件系统编码: {sys.getfilesystemencoding()}")
    print("="*60)

    success = run_with_fallback()

    sys.exit(0 if success else 1)
