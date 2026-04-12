#!/usr/bin/env python3
"""
多 Agent 协作演示
展示 Code Gen 的多 Agent 系统
"""
import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from code_gen.agents import Agent, AgentRole, Task, AgentTeam, ProcessType
from code_gen.agents.agent import AgentTemplates
from code_gen.agents.executor import MockExecutor
from code_gen.agents.workflow import new_feature, bug_fix, research


async def demo_basic():
    """基础演示 - 创建 Agents 和任务"""
    print("=" * 70)
    print("🎬 多 Agent 系统基础演示")
    print("=" * 70)
    
    work_dir = Path.cwd()
    
    # 1. 创建 Agents
    print("\n【步骤1】创建专业 Agents")
    print("-" * 70)
    
    researcher = AgentTemplates.researcher()
    architect = AgentTemplates.architect()
    builder = AgentTemplates.builder()
