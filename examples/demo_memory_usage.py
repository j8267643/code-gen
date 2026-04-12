#!/usr/bin/env python3
"""
演示增强记忆系统的使用场景
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from code_gen.memory_enhanced import ConversationMemory, init_conversation_memory
from code_gen.memory_system import AdvancedMemorySystem, MemoryCategory


def demo_conversation_memory():
    """演示对话中的记忆使用"""
    work_dir = Path.cwd()
    
    print("=" * 70)
    print("增强记忆系统使用演示")
    print("=" * 70)
    
    # 初始化
    conv_memory = init_conversation_memory(work_dir)
    
    # 场景1: 保存用户偏好
    print("\n【场景1】保存用户偏好")
    conv_memory.save_user_preference(
        preference="用户喜欢使用 Ollama 本地模型，偏好中文回复",
        importance=9
    )
    conv_memory.save_user_preference(
        preference="用户是 Python 开发者，熟悉 asyncio 编程",
        importance=8
    )
