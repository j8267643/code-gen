"""
Advanced Workflow System - 高级工作流系统
Inspired by PraisonAI's Hierarchical Process and Workflow Orchestration

特性：
1. 管理代理模式（Manager Agent）- 动态任务分配
2. 条件分支任务（Decision Tasks）- 工作流决策
3. 循环任务处理（Loop Tasks）- 批量数据处理
4. 工作流管理器（Workflow Manager）- 统一管理工作流
5. 动态路由（Dynamic Routing）- 基于上下文路由
"""
from typing import Dict, Any, List, Optional, Callable, Union, Set
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import json
import asyncio
import csv
import re
from datetime import datetime

from .agent import Agent
from .enhanced_reflect_executor import EnhancedReflectiveExecutor
from .tool_registry import get_tool_registry


class TaskType(str, Enum):
    """任务类型"""
    NORMAL = "normal"           # 普通任务
    DECISION = "decision"       # 决策/条件分支任务
    LOOP = "loop"               # 循环任务
    PARALLEL = "parallel"       # 并行任务
    VALIDATION = "validation"   # 验证任务


@dataclass
class TaskContext:
    """任务上下文 - 在工作流步骤间共享数据"""
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    
    def get(self, key: str, default=None) -> Any:
        """获取上下文数据"""
        return self.data.get(key, default)
    
    def set(self, key: str, value: Any):
        """设置上下文数据"""
        self.data[key] = value
    
    def add_history(self, task_name: str, result: Dict[str, Any]):
        """添加执行历史"""
        self.history.append({
            "task": task_name,
            "timestamp": datetime.now().isoformat(),
            "result": result
        })


@dataclass
class Route:
    """路由规则 - 用于动态任务路由"""
    condition: Callable[[TaskContext], str]
    routes: Dict[str, str]  # 条件值 -> 目标任务名
    default: Optional[str] = None
    
    def evaluate(self, context: TaskContext) -> str:
        """评估路由条件"""
        try:
            result = self.condition(context)
            return self.routes.get(result, self.default)
        except Exception as e:
            print(f"   ⚠️ 路由评估失败: {e}")
            return self.default


@dataclass
class AdvancedTask:
    """高级任务 - 支持条件、循环、路由等特性"""
    name: str
    description: str
    agent: Agent
    task_type: TaskType = TaskType.NORMAL
    
    # 条件分支
    condition: Optional[Dict[str, str]] = None  # {"结果": "下一个任务名"}
    condition_func: Optional[Callable[[str], str]] = None
    
    # 循环处理
    loop_data: Optional[Union[str, List[Any]]] = None  # CSV文件路径或列表
    loop_variable: str = "item"
    
    # 路由
    route: Optional[Route] = None
    
    # 验证
    validation_func: Optional[Callable[[str], bool]] = None
    max_retries: int = 3
    
    # 上下文
    context_tasks: List[str] = field(default_factory=list)  # 依赖的任务名
    retain_context: bool = True
    
    # 执行配置
    expected_output: Optional[str] = None
    enable_reflection: bool = True
    
    def __post_init__(self):
        """初始化后处理"""
        if isinstance(self.loop_data, str) and self.loop_data.endswith('.csv'):
            self._load_csv_data()
    
    def _load_csv_data(self):
        """加载CSV数据用于循环"""
        try:
            with open(self.loop_data, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self._csv_data = list(reader)
        except Exception as e:
            print(f"   ⚠️ 无法加载CSV文件 {self.loop_data}: {e}")
            self._csv_data = []


class ManagerAgent:
    """
    管理代理 - 动态协调任务执行
    
    职责：
    1. 分析任务复杂度
    2. 选择最适合的代理
    3. 确定最优执行顺序
    4. 处理异常和重试
    """
    
    def __init__(self, llm_model: str = None):
        self.model = llm_model or "gpt-4o"
        self.executor = None
    
    async def analyze_workflow(
        self,
        tasks: List[AdvancedTask],
        context: TaskContext
    ) -> Dict[str, Any]:
        """
        分析工作流并制定执行计划
        
        Returns:
            执行计划：{
                "execution_order": ["task1", "task2", ...],
                "assignments": {"task1": "agent_name", ...},
                "parallel_groups": [["task1", "task2"], ["task3"]],
                "reasoning": "分析原因..."
            }
        """
        # 构建分析提示词
        task_info = []
        for task in tasks:
            info = {
                "name": task.name,
                "type": task.task_type.value,
                "description": task.description[:100],
                "dependencies": task.context_tasks
            }
            task_info.append(info)
        
        analysis_prompt = f"""作为工作流管理专家，请分析以下任务并制定最优执行计划。

任务列表：
{json.dumps(task_info, indent=2, ensure_ascii=False)}

当前上下文：
{json.dumps(context.data, indent=2, ensure_ascii=False)}

请提供执行计划（JSON格式）：
{{
    "execution_order": ["按最优顺序排列的任务名"],
    "parallel_groups": [["可并行执行的任务组"]],
    "reasoning": "分析原因..."
}}
"""
        
        # 这里简化处理，实际应该调用AI
        # 返回基于依赖关系的拓扑排序
        execution_order = self._topological_sort(tasks)
        parallel_groups = self._find_parallel_groups(tasks, execution_order)
        
        return {
            "execution_order": execution_order,
            "parallel_groups": parallel_groups,
            "reasoning": "基于任务依赖关系进行拓扑排序"
        }
    
    def _topological_sort(self, tasks: List[AdvancedTask]) -> List[str]:
        """拓扑排序确定任务执行顺序"""
        task_map = {t.name: t for t in tasks}
        visited = set()
        order = []
        
        def visit(task_name: str):
            if task_name in visited:
                return
            visited.add(task_name)
            
            task = task_map.get(task_name)
            if task:
                for dep in task.context_tasks:
                    visit(dep)
            
            order.append(task_name)
        
        for task in tasks:
            visit(task.name)
        
        return order
    
    def _find_parallel_groups(
        self,
        tasks: List[AdvancedTask],
        execution_order: List[str]
    ) -> List[List[str]]:
        """找出可以并行执行的任务组"""
        task_map = {t.name: t for t in tasks}
        groups = []
        current_group = []
        completed = set()
        
        for task_name in execution_order:
            task = task_map.get(task_name)
            if not task:
                continue
            
            # 检查依赖是否都已完成
            deps_satisfied = all(d in completed for d in task.context_tasks)
            
            if deps_satisfied:
                current_group.append(task_name)
            else:
                if current_group:
                    groups.append(current_group)
                    current_group = []
                current_group.append(task_name)
            
            completed.add(task_name)
        
        if current_group:
            groups.append(current_group)
        
        return groups


class AdvancedWorkflowExecutor:
    """
    高级工作流执行器
    
    支持：
    - 顺序执行
    - 条件分支
    - 循环处理
    - 并行执行
    - 动态路由
    """
    
    def __init__(self, work_dir: Path, model: str = None):
        self.work_dir = work_dir
        self.model = model
        self.executor = EnhancedReflectiveExecutor(work_dir, model)
        self.context = TaskContext()
        self.manager = ManagerAgent(model)
        self.execution_log: List[Dict[str, Any]] = []
    
    async def execute_workflow(
        self,
        tasks: List[AdvancedTask],
        initial_input: str = "",
        use_manager: bool = False
    ) -> Dict[str, Any]:
        """
        执行完整工作流
        
        Args:
            tasks: 任务列表
            initial_input: 初始输入
            use_manager: 是否使用管理代理优化执行
        """
        print(f"\n{'='*60}")
        print(f"🚀 开始执行工作流 ({len(tasks)} 个任务)")
        print(f"{'='*60}\n")
        
        # 设置初始上下文
        self.context.set("initial_input", initial_input)
        self.context.set("start_time", datetime.now().isoformat())
        
        # 如果使用管理代理，先分析工作流
        if use_manager:
            plan = await self.manager.analyze_workflow(tasks, self.context)
            print(f"📋 管理代理执行计划:")
            print(f"   执行顺序: {' -> '.join(plan['execution_order'])}")
            print(f"   并行组数: {len(plan['parallel_groups'])}")
            print()
            
            # 按管理代理的计划排序任务
            task_map = {t.name: t for t in tasks}
            sorted_tasks = [task_map[name] for name in plan['execution_order'] if name in task_map]
        else:
            sorted_tasks = tasks
        
        # 执行任务
        results = {}
        for task in sorted_tasks:
            result = await self._execute_task(task)
            results[task.name] = result
            
            if not result.get("success"):
                print(f"   ❌ 任务 {task.name} 失败，工作流中断")
                break
        
        # 汇总结果
        final_result = {
            "success": all(r.get("success", False) for r in results.values()),
            "results": results,
            "context": self.context.data,
            "execution_log": self.execution_log
        }
        
        print(f"\n{'='*60}")
        print(f"✅ 工作流执行完成")
        print(f"{'='*60}\n")
        
        return final_result
    
    async def _execute_task(self, task: AdvancedTask) -> Dict[str, Any]:
        """执行单个任务（支持各种任务类型）"""
        print(f"▶️ 执行任务: {task.name} [{task.task_type.value}]")
        
        # 根据任务类型选择执行方式
        if task.task_type == TaskType.DECISION:
            return await self._execute_decision_task(task)
        elif task.task_type == TaskType.LOOP:
            return await self._execute_loop_task(task)
        elif task.task_type == TaskType.PARALLEL:
            return await self._execute_parallel_task(task)
        else:
            return await self._execute_normal_task(task)
    
    async def _execute_normal_task(self, task: AdvancedTask) -> Dict[str, Any]:
        """执行普通任务"""
        # 构建提示词，包含上下文
        context_prompt = self._build_context_prompt(task)
        full_prompt = f"{context_prompt}\n\n任务: {task.description}"
        
        # 执行任务
        result = await self.executor.execute(
            agent=task.agent,
            system_prompt=f"你是一个专业的 {task.agent.role}",
            user_prompt=full_prompt,
            expected_output=task.expected_output,
            enable_reflection=task.enable_reflection
        )
        
        # 更新上下文
        if task.retain_context:
            self.context.set(task.name, result.get("output", ""))
        self.context.add_history(task.name, result)
        
        # 检查是否需要路由
        if task.route:
            next_task = task.route.evaluate(self.context)
            result["next_task"] = next_task
            print(f"   🔄 路由到: {next_task}")
        
        return result
    
    async def _execute_decision_task(self, task: AdvancedTask) -> Dict[str, Any]:
        """执行决策/条件分支任务"""
        print(f"   🔀 执行决策任务")
        
        # 先执行评估
        eval_prompt = f"""请评估以下内容并给出决策：

{task.description}

上下文：
{json.dumps(self.context.data, indent=2, ensure_ascii=False)}

请从以下选项中选择一个：{list(task.condition.keys()) if task.condition else '根据判断'}
只返回选项值，不要解释。"""
        
        result = await self.executor.execute(
            agent=task.agent,
            system_prompt="你是一个决策专家，请给出明确的选择",
            user_prompt=eval_prompt,
            enable_reflection=False
        )
        
        decision = result.get("output", "").strip().lower()
        
        # 使用条件函数或映射
        if task.condition_func:
            next_task = task.condition_func(decision)
        elif task.condition:
            next_task = task.condition.get(decision, task.condition.get("default"))
        else:
            next_task = None
        
        print(f"   📍 决策结果: {decision} -> {next_task}")
        
        return {
            "success": True,
            "output": decision,
            "next_task": next_task,
            "decision": decision
        }
    
    async def _execute_loop_task(self, task: AdvancedTask) -> Dict[str, Any]:
        """执行循环任务"""
        print(f"   🔄 执行循环任务")
        
        # 获取循环数据
        if isinstance(task.loop_data, str) and hasattr(task, '_csv_data'):
            items = task._csv_data
        elif isinstance(task.loop_data, list):
            items = task.loop_data
        else:
            items = []
        
        print(f"   📊 循环项目数: {len(items)}")
        
        results = []
        for i, item in enumerate(items, 1):
            print(f"   [{i}/{len(items)}] 处理: {item}")
            
            # 设置循环变量
            self.context.set(task.loop_variable, item)
            
            # 构建带变量的提示词
            item_prompt = task.description
            if isinstance(item, dict):
                for key, value in item.items():
                    item_prompt = item_prompt.replace(f"{{{key}}}", str(value))
            else:
                item_prompt = item_prompt.replace(f"{{{task.loop_variable}}}", str(item))
            
            # 执行单次循环
            result = await self.executor.execute(
                agent=task.agent,
                system_prompt=f"你是一个专业的 {task.agent.role}",
                user_prompt=item_prompt,
                enable_reflection=False
            )
            
            results.append({
                "item": item,
                "result": result
            })
        
        # 汇总循环结果
        self.context.set(f"{task.name}_results", results)
        
        return {
            "success": True,
            "output": f"处理了 {len(items)} 个项目",
            "loop_count": len(items),
            "results": results
        }
    
    async def _execute_parallel_task(self, task: AdvancedTask) -> Dict[str, Any]:
        """执行并行任务（占位实现）"""
        print(f"   ⚡ 并行任务执行")
        # 实际实现需要分解子任务并并发执行
        return await self._execute_normal_task(task)
    
    def _build_context_prompt(self, task: AdvancedTask) -> str:
        """构建包含上下文的提示词"""
        context_parts = []
        
        # 添加上下文任务的结果
        for ctx_task_name in task.context_tasks:
            ctx_data = self.context.get(ctx_task_name)
            if ctx_data:
                context_parts.append(f"【{ctx_task_name} 的结果】\n{ctx_data}")
        
        if context_parts:
            return "上下文信息：\n\n" + "\n\n".join(context_parts)
        
        return ""


class WorkflowManager:
    """
    工作流管理器 - 统一管理和注册多个工作流
    """
    
    def __init__(self):
        self.workflows: Dict[str, Dict[str, Any]] = {}
        self.templates: Dict[str, Callable] = {}
    
    def register_workflow(
        self,
        name: str,
        tasks: List[AdvancedTask],
        description: str = ""
    ):
        """注册工作流"""
        self.workflows[name] = {
            "tasks": tasks,
            "description": description,
            "created_at": datetime.now().isoformat()
        }
        print(f"✅ 工作流 '{name}' 已注册")
    
    def register_template(
        self,
        name: str,
        template_func: Callable[..., List[AdvancedTask]]
    ):
        """注册工作流模板"""
        self.templates[name] = template_func
        print(f"✅ 模板 '{name}' 已注册")
    
    async def run(
        self,
        workflow_name: str,
        work_dir: Path,
        initial_input: str = "",
        use_manager: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """运行已注册的工作流"""
        if workflow_name not in self.workflows:
            raise ValueError(f"工作流 '{workflow_name}' 未找到")
        
        workflow = self.workflows[workflow_name]
        executor = AdvancedWorkflowExecutor(work_dir)
        
        return await executor.execute_workflow(
            tasks=workflow["tasks"],
            initial_input=initial_input,
            use_manager=use_manager
        )
    
    def create_from_template(
        self,
        template_name: str,
        workflow_name: str,
        **template_args
    ) -> List[AdvancedTask]:
        """从模板创建工作流"""
        if template_name not in self.templates:
            raise ValueError(f"模板 '{template_name}' 未找到")
        
        template_func = self.templates[template_name]
        tasks = template_func(**template_args)
        
        self.register_workflow(workflow_name, tasks)
        return tasks
    
    def list_workflows(self) -> List[str]:
        """列出所有工作流"""
        return list(self.workflows.keys())
    
    def get_workflow_info(self, name: str) -> Optional[Dict[str, Any]]:
        """获取工作流信息"""
        return self.workflows.get(name)


# 便捷函数
def route(condition: Callable[[TaskContext], str]):
    """路由装饰器"""
    def decorator(func):
        func._route_condition = condition
        return func
    return decorator


def create_decision_task(
    name: str,
    description: str,
    agent: Agent,
    condition_map: Dict[str, str],
    **kwargs
) -> AdvancedTask:
    """创建决策任务"""
    return AdvancedTask(
        name=name,
        description=description,
        agent=agent,
        task_type=TaskType.DECISION,
        condition=condition_map,
        **kwargs
    )


def create_loop_task(
    name: str,
    description: str,
    agent: Agent,
    loop_data: Union[str, List[Any]],
    loop_variable: str = "item",
    **kwargs
) -> AdvancedTask:
    """创建循环任务"""
    return AdvancedTask(
        name=name,
        description=description,
        agent=agent,
        task_type=TaskType.LOOP,
        loop_data=loop_data,
        loop_variable=loop_variable,
        **kwargs
    )
