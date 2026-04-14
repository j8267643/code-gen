"""
AutoDev - 自主开发系统

功能：
1. PRD 生成和管理
2. PRD 到 UnifiedAgent 任务转换
3. 自主执行循环
4. 进度跟踪和状态持久化
5. 与现有 Agent 系统集成

使用示例:
    >>> from code_gen.autodev import AutoDevIntegration
    >>> 
    >>> autodev = AutoDevIntegration(work_dir="./my-project")
    >>> 
    >>> # 创建 PRD
    >>> prd = autodev.create_prd("实现用户认证系统")
    >>> 
    >>> # 转换为可执行格式
    >>> autodev.convert_prd(prd)
    >>> 
    >>> # 开始执行
    >>> await autodev.run()
"""

from .core import AutoDevIntegration, AutoDevConfig
from .models import PRDData, UserStory
from .prd_parser import PRDParser
from .task_router import TaskRouter
from .progress_tracker import ProgressTracker
from .executor import AutoDevExecutor

__all__ = [
    "AutoDevIntegration",
    "AutoDevConfig",
    "PRDData",
    "PRDParser",
    "UserStory",
    "TaskRouter",
    "ProgressTracker",
    "AutoDevExecutor",
]
