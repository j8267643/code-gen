"""
Agent Team for multi-agent collaboration
"""
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import asyncio
from datetime import datetime

from .agent import Agent
from .task import Task, TaskStatus


class ProcessType(str, Enum):
    """执行流程类型"""
    SEQUENTIAL = "sequential"    # 顺序执行
    PARALLEL = "parallel"        # 并行执行
    HYBRID = "hybrid"            # 混合执行（默认）


@dataclass
class TeamResult:
    """团队执行结果"""
    success: bool
    tasks_completed: int
    tasks_failed: int
    tasks_skipped: int
    total_time: float
    outputs: Dict[str, str] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


class AgentTeam:
    """
    Agent 团队 - 管理多个 Agent 协作
    
    支持：
    - 顺序执行：任务按依赖顺序依次执行
    - 并行执行：无依赖的任务并行执行
    - 混合执行：智能调度，最大化并行度
    """
    
    def __init__(
        self,
        name: str,
        agents: List[Agent],
        tasks: List[Task],
        process: ProcessType = ProcessType.HYBRID,
        callback: Optional[Callable[[Task, str], None]] = None
    ):
        self.name = name
        self.agents = {agent.id: agent for agent in agents}
        self.tasks = {task.id: task for task in tasks}
        self.process = process
        self.callback = callback
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
    
    def get_ready_tasks(self) -> List[Task]:
        """获取准备好执行的任务"""
        return [
            task for task in self.tasks.values()
            if task.status == TaskStatus.PENDING and task.is_ready()
        ]
    
    def get_blocked_tasks(self) -> List[Task]:
        """获取被阻塞的任务"""
        return [
            task for task in self.tasks.values()
            if task.status == TaskStatus.PENDING and task.is_blocked()
        ]
    
    def get_completed_tasks(self) -> List[Task]:
        """获取已完成的任务"""
        return [
            task for task in self.tasks.values()
            if task.status == TaskStatus.COMPLETED
        ]
    
    def get_failed_tasks(self) -> List[Task]:
        """获取失败的任务"""
        return [
            task for task in self.tasks.values()
            if task.status == TaskStatus.FAILED
        ]
    
    def is_complete(self) -> bool:
        """检查所有任务是否完成"""
        return all(
            task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.SKIPPED]
            for task in self.tasks.values()
        )
    
    async def execute_task(self, task: Task, executor) -> bool:
        """执行单个任务"""
        if not task.agent:
            print(f"⚠️ 任务 {task.name} 没有指定 Agent，跳过")
            task.skip()
            return False
        
        print(f"\n{'='*60}")
        print(f"🤖 Agent: {task.agent.name} ({task.agent.role.value})")
        print(f"📋 任务: {task.name}")
        print(f"{'='*60}\n")
        
        task.start()
        
        try:
            # 构建提示词
            prompt = task.build_prompt()
            
            # 获取 Agent 的系统提示词
            system_prompt = task.agent.get_system_prompt()
            
            # 执行任务
            result = await executor.execute(
                agent=task.agent,
                system_prompt=system_prompt,
                user_prompt=prompt
            )
            
            if result.get("success"):
                task.complete(result.get("output", ""))
                print(f"✅ 任务完成: {task.name}")
                
                # 调用回调
                if self.callback:
                    self.callback(task, result.get("output", ""))
                
                return True
            else:
                error = result.get("error", "未知错误")
                task.fail(error)
                print(f"❌ 任务失败: {task.name} - {error}")
                return False
                
        except Exception as e:
            task.fail(str(e))
            print(f"❌ 任务异常: {task.name} - {e}")
            return False
    
    async def run_sequential(self, executor) -> TeamResult:
        """顺序执行所有任务"""
        print(f"\n🔄 顺序执行模式\n")
        
        # 按依赖顺序排序任务
        sorted_tasks = self._topological_sort()
        
        for task in sorted_tasks:
            if task.status == TaskStatus.PENDING:
                await self.execute_task(task, executor)
        
        return self._build_result()
    
    async def run_parallel(self, executor, max_concurrency: int = 3) -> TeamResult:
        """并行执行所有任务"""
        print(f"\n⚡ 并行执行模式 (最大并发: {max_concurrency})\n")
        
        semaphore = asyncio.Semaphore(max_concurrency)
        
        async def execute_with_limit(task: Task):
            async with semaphore:
                return await self.execute_task(task, executor)
        
        while not self.is_complete():
            ready_tasks = self.get_ready_tasks()
            
            if not ready_tasks:
                # 检查是否有阻塞的任务
                blocked = self.get_blocked_tasks()
                if blocked:
                    print(f"⚠️ {len(blocked)} 个任务被阻塞，跳过")
                    for task in blocked:
                        task.skip()
                break
            
            # 并行执行准备好的任务
            tasks = [execute_with_limit(task) for task in ready_tasks]
            await asyncio.gather(*tasks, return_exceptions=True)
        
        return self._build_result()
    
    async def run_hybrid(self, executor, max_concurrency: int = 3) -> TeamResult:
        """混合执行 - 智能调度"""
        print(f"\n🔀 混合执行模式\n")
        
        semaphore = asyncio.Semaphore(max_concurrency)
        
        async def execute_with_limit(task: Task):
            async with semaphore:
                return await self.execute_task(task, executor)
        
        while not self.is_complete():
            ready_tasks = self.get_ready_tasks()
            blocked_tasks = self.get_blocked_tasks()
            
            # 处理阻塞的任务
            for task in blocked_tasks:
                if task.status == TaskStatus.PENDING:
                    print(f"⏭️ 跳过阻塞任务: {task.name}")
                    task.skip()
            
            if not ready_tasks:
                break
            
            # 并行执行准备好的任务
            tasks = [execute_with_limit(task) for task in ready_tasks]
            await asyncio.gather(*tasks, return_exceptions=True)
        
        return self._build_result()
    
    async def run(self, executor, max_concurrency: int = 3) -> TeamResult:
        """运行团队任务"""
        self.started_at = datetime.now()
        
        print(f"\n{'='*60}")
        print(f"🚀 启动 Agent 团队: {self.name}")
        print(f"{'='*60}")
        print(f"👥 Agents: {len(self.agents)}")
        print(f"📋 Tasks: {len(self.tasks)}")
        print(f"🔄 Process: {self.process.value}")
        print(f"{'='*60}\n")
        
        # 根据流程类型执行
        if self.process == ProcessType.SEQUENTIAL:
            result = await self.run_sequential(executor)
        elif self.process == ProcessType.PARALLEL:
            result = await self.run_parallel(executor, max_concurrency)
        else:  # HYBRID
            result = await self.run_hybrid(executor, max_concurrency)
        
        self.completed_at = datetime.now()
        
        # 打印总结
        self._print_summary(result)
        
        return result
    
    def _topological_sort(self) -> List[Task]:
        """拓扑排序任务（按依赖顺序）"""
        sorted_tasks = []
        visited = set()
        temp_mark = set()
        
        def visit(task: Task):
            if task.id in temp_mark:
                raise ValueError(f"检测到循环依赖: {task.name}")
            if task.id in visited:
                return
            
            temp_mark.add(task.id)
            for dep in task.depends_on:
                visit(dep)
            temp_mark.remove(task.id)
            visited.add(task.id)
            sorted_tasks.append(task)
        
        for task in self.tasks.values():
            if task.id not in visited:
                visit(task)
        
        return sorted_tasks
    
    def _build_result(self) -> TeamResult:
        """构建执行结果"""
        completed = self.get_completed_tasks()
        failed = self.get_failed_tasks()
        skipped = [t for t in self.tasks.values() if t.status == TaskStatus.SKIPPED]
        
        total_time = 0.0
        if self.started_at and self.completed_at:
            total_time = (self.completed_at - self.started_at).total_seconds()
        
        outputs = {task.name: task.output for task in completed}
        errors = [task.error for task in failed if task.error]
        
        return TeamResult(
            success=len(failed) == 0,
            tasks_completed=len(completed),
            tasks_failed=len(failed),
            tasks_skipped=len(skipped),
            total_time=total_time,
            outputs=outputs,
            errors=errors
        )
    
    def _print_summary(self, result: TeamResult):
        """打印执行总结"""
        print(f"\n{'='*60}")
        print(f"📊 执行总结")
        print(f"{'='*60}")
        print(f"✅ 完成: {result.tasks_completed}")
        print(f"❌ 失败: {result.tasks_failed}")
        print(f"⏭️ 跳过: {result.tasks_skipped}")
        print(f"⏱️ 总耗时: {result.total_time:.2f} 秒")
        print(f"{'='*60}\n")
        
        if result.success:
            print("🎉 所有任务执行成功！")
        else:
            print("⚠️ 部分任务执行失败")
            for error in result.errors[:5]:  # 只显示前5个错误
                print(f"  - {error}")
