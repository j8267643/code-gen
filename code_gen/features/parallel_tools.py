"""
并行工具调用模块
支持同时执行多个独立工具，提高响应速度
"""
import asyncio
import json
import hashlib
from typing import List, Dict, Any, Optional, Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import inspect


class ToolExecutionStatus(Enum):
    """工具执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ToolResult:
    """工具执行结果"""
    tool_name: str
    tool_id: str
    status: ToolExecutionStatus
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    dependencies: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "tool_name": self.tool_name,
            "tool_id": self.tool_id,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "execution_time": self.execution_time,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class ToolCall:
    """工具调用定义"""
    tool_name: str
    tool_id: str = field(default_factory=lambda: hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8])
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)  # 依赖的其他工具ID
    priority: int = 0  # 优先级，数字越大优先级越高
    timeout: float = 30.0  # 超时时间（秒）
    
    def __hash__(self):
        return hash(self.tool_id)


class ParallelToolExecutor:
    """并行工具执行器"""
    
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.results: Dict[str, ToolResult] = {}
        self._tool_registry: Dict[str, Callable] = {}
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
    
    def register_tool(self, name: str, func: Callable):
        """注册工具函数"""
        self._tool_registry[name] = func
    
    async def execute_parallel(
        self,
        tool_calls: List[ToolCall],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, ToolResult]:
        """
        并行执行多个工具调用
        
        支持依赖关系：如果工具A依赖工具B，会先执行B，然后将B的结果作为A的参数
        """
        context = context or {}
        self.results = {}
        
        # 按依赖关系分组
        execution_groups = self._build_execution_groups(tool_calls)
        
        # 按组顺序执行
        for group in execution_groups:
            # 同组内的工具可以并行执行
            tasks = []
            for tool_call in group:
                task = self._execute_single_tool(tool_call, context)
                tasks.append(task)
            
            # 等待当前组所有工具完成
            await asyncio.gather(*tasks, return_exceptions=True)
        
        return self.results
    
    def _build_execution_groups(self, tool_calls: List[ToolCall]) -> List[List[ToolCall]]:
        """
        根据依赖关系构建执行组
        同组内的工具没有依赖关系，可以并行执行
        """
        # 构建依赖图
        tool_map = {tc.tool_id: tc for tc in tool_calls}
        pending = set(tc.tool_id for tc in tool_calls)
        groups = []
        
        while pending:
            # 找出当前没有未满足依赖的工具
            current_group = []
            for tool_id in list(pending):
                tool_call = tool_map[tool_id]
                # 检查依赖是否都已满足
                deps_satisfied = all(
                    dep not in pending and dep in self.results
                    for dep in tool_call.dependencies
                )
                if deps_satisfied or not tool_call.dependencies:
                    current_group.append(tool_call)
            
            if not current_group:
                # 存在循环依赖，打破循环
                tool_id = pending.pop()
                current_group.append(tool_map[tool_id])
            
            # 按优先级排序
            current_group.sort(key=lambda x: x.priority, reverse=True)
            
            groups.append(current_group)
            for tc in current_group:
                pending.discard(tc.tool_id)
        
        return groups
    
    async def _execute_single_tool(
        self,
        tool_call: ToolCall,
        context: Dict[str, Any]
    ) -> ToolResult:
        """执行单个工具"""
        tool_id = tool_call.tool_id
        
        # 检查是否已经执行过
        if tool_id in self.results:
            return self.results[tool_id]
        
        # 创建结果对象
        result = ToolResult(
            tool_name=tool_call.tool_name,
            tool_id=tool_id,
            status=ToolExecutionStatus.RUNNING,
            started_at=datetime.now(),
            dependencies=tool_call.dependencies
        )
        self.results[tool_id] = result
        
        # 检查工具是否注册
        if tool_call.tool_name not in self._tool_registry:
            result.status = ToolExecutionStatus.FAILED
            result.error = f"Tool '{tool_call.tool_name}' not registered"
            result.completed_at = datetime.now()
            return result
        
        # 准备参数（注入依赖结果）
        parameters = self._prepare_parameters(tool_call, context)
        
        # 执行工具
        try:
            func = self._tool_registry[tool_call.tool_name]
            
            # 检查是否是异步函数
            if inspect.iscoroutinefunction(func):
                # 异步执行
                task = asyncio.wait_for(
                    func(**parameters),
                    timeout=tool_call.timeout
                )
                tool_result = await task
            else:
                # 在线程池中执行同步函数
                loop = asyncio.get_event_loop()
                task = loop.run_in_executor(
                    self._executor,
                    lambda: func(**parameters)
                )
                tool_result = await asyncio.wait_for(task, timeout=tool_call.timeout)
            
            result.result = tool_result
            result.status = ToolExecutionStatus.COMPLETED
            
        except asyncio.TimeoutError:
            result.status = ToolExecutionStatus.FAILED
            result.error = f"Timeout after {tool_call.timeout}s"
        except Exception as e:
            result.status = ToolExecutionStatus.FAILED
            result.error = str(e)
        
        result.completed_at = datetime.now()
        if result.started_at:
            result.execution_time = (result.completed_at - result.started_at).total_seconds()
        
        return result
    
    def _prepare_parameters(
        self,
        tool_call: ToolCall,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """准备工具参数，注入依赖结果和上下文"""
        parameters = tool_call.parameters.copy()
        
        # 注入上下文
        parameters['_context'] = context
        
        # 注入依赖结果
        if tool_call.dependencies:
            dep_results = {}
            for dep_id in tool_call.dependencies:
                if dep_id in self.results:
                    dep_results[dep_id] = self.results[dep_id].result
            parameters['_dependencies'] = dep_results
        
        return parameters
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """获取执行摘要"""
        total = len(self.results)
        completed = sum(1 for r in self.results.values() if r.status == ToolExecutionStatus.COMPLETED)
        failed = sum(1 for r in self.results.values() if r.status == ToolExecutionStatus.FAILED)
        
        total_time = sum(r.execution_time for r in self.results.values())
        
        return {
            "total_tools": total,
            "completed": completed,
            "failed": failed,
            "success_rate": f"{completed/total*100:.1f}%" if total > 0 else "0%",
            "total_execution_time": f"{total_time:.2f}s",
            "average_time": f"{total_time/total:.2f}s" if total > 0 else "0s"
        }
    
    def get_results_for_llm(self) -> List[Dict]:
        """获取适合LLM使用的格式化结果"""
        return [
            {
                "tool": r.tool_name,
                "status": r.status.value,
                "result": r.result,
                "error": r.error
            }
            for r in self.results.values()
        ]


class ToolChain:
    """工具链 - 支持工具输出自动作为下一个工具的输入"""
    
    def __init__(self, executor: ParallelToolExecutor):
        self.executor = executor
        self.steps: List[ToolCall] = []
    
    def add_step(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        input_mapping: Optional[Dict[str, str]] = None
    ) -> "ToolChain":
        """
        添加工具链步骤
        
        input_mapping: 将上一步的输出映射到当前步骤的参数
        例如：{"file_path": "previous.output.file"} 表示将上一步结果的 output.file 映射到 file_path 参数
        """
        tool_id = f"step_{len(self.steps)}"
        
        # 如果有上一步，建立依赖关系
        dependencies = []
        if self.steps:
            dependencies.append(self.steps[-1].tool_id)
        
        tool_call = ToolCall(
            tool_name=tool_name,
            tool_id=tool_id,
            parameters=parameters,
            dependencies=dependencies
        )
        
        self.steps.append(tool_call)
        return self
    
    async def execute(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, ToolResult]:
        """执行工具链"""
        return await self.executor.execute_parallel(self.steps, context)


# 预定义的工具函数示例
async def search_files(query: str, _context: Dict = None, **kwargs) -> List[str]:
    """搜索文件"""
    # 模拟文件搜索
    await asyncio.sleep(0.5)
    return [f"file_{i}.py" for i in range(3)]


async def read_file(file_path: str, _context: Dict = None, **kwargs) -> str:
    """读取文件内容"""
    # 模拟读取文件
    await asyncio.sleep(0.3)
    return f"Content of {file_path}"


async def analyze_code(code: str, _context: Dict = None, **kwargs) -> Dict:
    """分析代码"""
    # 模拟代码分析
    await asyncio.sleep(0.4)
    return {"complexity": "medium", "issues": []}


# 创建默认执行器并注册常用工具
def create_default_executor() -> ParallelToolExecutor:
    """创建默认的工具执行器"""
    executor = ParallelToolExecutor(max_workers=5)
    executor.register_tool("search_files", search_files)
    executor.register_tool("read_file", read_file)
    executor.register_tool("analyze_code", analyze_code)
    return executor
