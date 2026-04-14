"""
AutoDev Executor - 自主开发执行器

执行自主开发循环的核心逻辑
"""
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
import asyncio

from code_gen.agents.unified_agent import UnifiedAgent
from code_gen.agents.git_integration import GitIntegration

from .progress_tracker import ProgressTracker
from .task_router import TaskRouter


@dataclass
class ExecutionContext:
    """执行上下文"""
    story: Dict[str, Any]
    analysis: Dict[str, Any]
    agent_config: Dict[str, Any]
    iteration: int = 0
    start_time: datetime = field(default_factory=datetime.now)


class AutoDevExecutor:
    """
    自主开发执行器
    
    负责执行单个用户故事的完整流程
    """
    
    def __init__(
        self,
        agent: UnifiedAgent,
        git: Optional[GitIntegration] = None,
        progress_tracker: Optional[ProgressTracker] = None,
        task_router: Optional[TaskRouter] = None
    ):
        self.agent = agent
        self.git = git
        self.progress_tracker = progress_tracker
        self.task_router = task_router or TaskRouter()
        self.pre_execution_hooks: List[Callable] = []
        self.post_execution_hooks: List[Callable] = []
    
    def add_pre_execution_hook(self, hook: Callable):
        """添加执行前钩子"""
        self.pre_execution_hooks.append(hook)
    
    def add_post_execution_hook(self, hook: Callable):
        """添加执行后钩子"""
        self.post_execution_hooks.append(hook)
    
    async def execute(
        self,
        story: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行用户故事
        
        Args:
            story: 用户故事
            context: 额外上下文
            
        Returns:
            执行结果
        """
        story_id = story.get("id", "unknown")
        story_title = story.get("title", "Untitled")
        
        print(f"\n{'='*60}")
        print(f"🎯 开始执行: {story_id} - {story_title}")
        print(f"{'='*60}")
        
        # 1. 分析任务
        routing_result = self.task_router.route(story)
        analysis = routing_result["analysis"]
        agent_config = routing_result["execution_config"]
        
        print(f"📊 类别: {analysis['category']}")
        print(f"📈 复杂度: {analysis['complexity']}/5")
        print(f"⏱️  预计时间: {analysis['estimated_time']} 分钟")
        print(f"🤖 推荐 Agent: {analysis['suggested_agent']}")
        
        # 2. 创建执行上下文
        exec_context = ExecutionContext(
            story=story,
            analysis=analysis,
            agent_config=agent_config
        )
        
        # 3. 执行前钩子
        for hook in self.pre_execution_hooks:
            try:
                await hook(exec_context)
            except Exception as e:
                print(f"⚠️  执行前钩子失败: {e}")
        
        # 4. 构建任务
        task = self._build_task(story, analysis, context)
        
        # 5. 执行
        start_time = datetime.now()
        
        try:
            result = await self._run_with_agent(task, agent_config)
            
            # 6. 后处理
            result = await self._post_process(result, story, exec_context)
            
        except Exception as e:
            result = {
                "success": False,
                "error": str(e),
                "story_id": story_id,
                "story_title": story_title
            }
        
        # 7. 执行后钩子
        for hook in self.post_execution_hooks:
            try:
                await hook(exec_context, result)
            except Exception as e:
                print(f"⚠️  执行后钩子失败: {e}")
        
        # 8. 记录进度
        if self.progress_tracker:
            self.progress_tracker.add_entry(
                story_id=story_id,
                story_title=story_title,
                status="completed" if result.get("success") else "failed",
                output=result.get("output", "")[:500],
                learnings=result.get("learnings", []),
                files_changed=result.get("files_changed", [])
            )
        
        # 9. 输出结果
        elapsed = (datetime.now() - start_time).total_seconds()
        status_emoji = "✅" if result.get("success") else "❌"
        print(f"\n{status_emoji} 执行完成 ({elapsed:.1f}s)")
        
        return result
    
    def _build_task(
        self,
        story: Dict[str, Any],
        analysis: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """构建任务描述"""
        story_id = story.get("id", "unknown")
        title = story.get("title", "")
        description = story.get("description", "")
        acceptance_criteria = story.get("acceptanceCriteria", [])
        
        task = f"""# 用户故事: {story_id} - {title}

## 描述
{description}

## 任务类别
{analysis['category']} (复杂度: {analysis['complexity']}/5)

## 验收标准
"""
        for i, criterion in enumerate(acceptance_criteria, 1):
            task += f"{i}. {criterion}\n"
        
        task += """
## 执行要求
1. 实现上述所有验收标准
2. 遵循项目的代码规范和最佳实践
3. 确保代码质量（类型检查、测试通过）
4. 完成后提交更改并记录修改的文件

## 输出格式
请返回以下信息：
- 完成的文件列表
- 实现摘要
- 遇到的问题和解决方案
"""
        
        # 添加上下文信息
        if context:
            task += "\n## 额外上下文\n"
            for key, value in context.items():
                task += f"- {key}: {value}\n"
        
        return task
    
    async def _run_with_agent(
        self,
        task: str,
        agent_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """使用 Agent 执行任务"""
        # 使用 UnifiedAgent 执行
        result = await self.agent.execute(task)
        
        return result
    
    async def _post_process(
        self,
        result: Dict[str, Any],
        story: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """后处理执行结果"""
        # 提取学习点
        learnings = self._extract_learnings(result)
        result["learnings"] = learnings
        
        # 提取修改的文件
        files_changed = self._extract_files_changed(result)
        result["files_changed"] = files_changed
        
        # Git 提交
        if self.git and result.get("success") and files_changed:
            await self._commit_changes(story, files_changed)
        
        return result
    
    def _extract_learnings(self, result: Dict[str, Any]) -> List[str]:
        """从结果中提取学习点"""
        learnings = []
        output = result.get("output", "")
        
        # 查找学习点部分
        import re
        learning_section = re.search(
            r'(?:学习点|learnings?|patterns?)[：:]\s*(.+?)(?=\n\n|$)',
            output,
            re.IGNORECASE | re.DOTALL
        )
        
        if learning_section:
            text = learning_section.group(1)
            # 提取列表项
            items = re.findall(r'[-\*]\s*(.+)', text)
            learnings = [item.strip() for item in items if item.strip()]
        
        return learnings
    
    def _extract_files_changed(self, result: Dict[str, Any]) -> List[str]:
        """提取修改的文件"""
        files = []
        output = result.get("output", "")
        
        # 查找文件列表
        import re
        file_section = re.search(
            r'(?:文件|files?|修改)[：:]\s*(.+?)(?=\n\n|$)',
            output,
            re.IGNORECASE | re.DOTALL
        )
        
        if file_section:
            text = file_section.group(1)
            # 提取文件路径
            items = re.findall(r'[-\*]\s*(.+)', text)
            files = [item.strip() for item in items if item.strip()]
        
        return files
    
    async def _commit_changes(
        self,
        story: Dict[str, Any],
        files_changed: List[str]
    ):
        """提交更改"""
        story_id = story.get("id", "unknown")
        title = story.get("title", "")
        
        commit_message = f"feat: {story_id} - {title}"
        
        try:
            # 添加文件
            for file in files_changed:
                self.git.execute_command(["add", file])
            
            # 提交
            result = self.git.execute_command([
                "commit",
                "-m", commit_message
            ])
            
            if result.status == "success":
                print(f"✅ 已提交: {commit_message}")
            else:
                print(f"⚠️  提交失败: {result.message}")
                
        except Exception as e:
            print(f"⚠️  Git 操作失败: {e}")


class AutoDevLoop:
    """
    自主开发执行循环
    
    管理多个用户故事的连续执行
    """
    
    def __init__(
        self,
        executor: AutoDevExecutor,
        max_iterations: int = 100,
        stop_on_error: bool = False
    ):
        self.executor = executor
        self.max_iterations = max_iterations
        self.stop_on_error = stop_on_error
        self.stories: List[Dict[str, Any]] = []
        self.current_index: int = 0
        self.stats = {
            "total": 0,
            "completed": 0,
            "failed": 0,
            "skipped": 0
        }
    
    def load_stories(self, stories: List[Dict[str, Any]]):
        """加载用户故事"""
        # 按优先级排序
        self.stories = sorted(stories, key=lambda x: x.get("priority", 999))
        self.stats["total"] = len(self.stories)
    
    def get_next_story(self) -> Optional[Dict[str, Any]]:
        """获取下一个待执行的故事"""
        while self.current_index < len(self.stories):
            story = self.stories[self.current_index]
            if not story.get("passes", False):
                return story
            self.current_index += 1
        return None
    
    async def run(self) -> Dict[str, Any]:
        """运行执行循环"""
        print(f"\n🚀 自主开发执行循环开始")
        print(f"📋 总故事数: {len(self.stories)}")
        print(f"⏹️  停止条件: {'错误时停止' if self.stop_on_error else '忽略错误'}")
        
        iteration = 0
        while iteration < self.max_iterations:
            story = self.get_next_story()
            
            if not story:
                print("\n✨ 所有故事已完成！")
                break
            
            # 执行故事
            result = await self.executor.execute(story)
            
            # 更新状态
            story["passes"] = result.get("success", False)
            story["execution_result"] = result
            
            if result.get("success"):
                self.stats["completed"] += 1
            else:
                self.stats["failed"] += 1
                if self.stop_on_error:
                    print(f"\n⏹️  执行失败，停止循环")
                    break
            
            self.current_index += 1
            iteration += 1
            
            # 暂停一下
            await asyncio.sleep(0.5)
        
        return {
            "success": self.stats["failed"] == 0,
            "stats": self.stats,
            "completed_stories": self.current_index
        }
