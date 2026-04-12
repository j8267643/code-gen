"""
Resumable Dynamic Workflow
支持断点续跑的动态工作流
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
import json
import asyncio

from .agent import Agent, AgentRole
from .task import Task, TaskStatus
from .team import AgentTeam, ProcessType, TeamResult
from .executor import AgentExecutor
from .dynamic_workflow import DynamicWorkflowConfig, ExecutionPlan
from .workflow_state import WorkflowState, StepState, get_state_manager


class ResumableDynamicWorkflow:
    """
    支持断点续跑的动态工作流
    
    特性：
    1. 自动保存执行状态
    2. 支持从失败处恢复
    3. 支持重试失败的步骤
    4. 可以查看执行历史
    """
    
    def __init__(
        self,
        config: DynamicWorkflowConfig,
        work_dir: Path,
        executor: AgentExecutor
    ):
        self.config = config
        self.work_dir = work_dir
        self.executor = executor
        self.plan: Optional[ExecutionPlan] = None
        self.team: Optional[AgentTeam] = None
        self.state_manager = get_state_manager(work_dir)
        self.state: Optional[WorkflowState] = None
    
    async def run(self, resume: bool = True, retry_failed: bool = False) -> TeamResult:
        """
        运行工作流
        
        Args:
            resume: 是否尝试从上次状态恢复
            retry_failed: 是否重试失败的步骤
        """
        print(f"\n{'='*60}")
        print(f"🎯 启动动态工作流: {self.config.name}")
        print(f"{'='*60}")
        print(f"目标: {self.config.goal}")
        print(f"策略: {self.config.strategy}")
        print(f"模型: {getattr(self.executor, 'model', 'default')}")
        print(f"")
        
        # 检查是否有现有状态
        if resume:
            self.state = self.state_manager.load_state(self.config.name)
            if self.state:
                print(f"📂 发现现有执行状态:")
                print(f"   状态: {self.state.status}")
                print(f"   已完成: {len(self.state.completed_steps)} 个步骤")
                print(f"   失败: {len(self.state.failed_steps)} 个步骤")
                
                if self.state.status == "completed":
                    print(f"\n✅ 工作流已完成，跳过执行")
                    return self._create_result_from_state()
                
                if retry_failed and self.state.failed_steps:
                    print(f"\n🔄 将重试失败的步骤")
                    for step_id in self.state.failed_steps:
                        self.state.step_states[step_id].status = "pending"
                        self.state.step_states[step_id].retry_count += 1
                    self.state.failed_steps = []
                
                # 恢复计划
                if self.state.plan:
                    self.plan = ExecutionPlan(
                        steps=self.state.plan.get("steps", []),
                        reasoning=self.state.plan.get("reasoning", ""),
                        estimated_time=self.state.plan.get("estimated_time", 0)
                    )
                    print(f"\n📋 已恢复执行计划")
                    self._display_plan()
        
        # 如果没有状态或计划，创建新的
        if not self.state:
            self.state = WorkflowState(
                workflow_name=self.config.name,
                goal=self.config.goal,
                status="pending"
            )
        
        # 阶段 1: 规划（如果没有计划）
        if not self.plan:
            print("\n📋 阶段 1: 制定执行计划...")
            self.plan = await self._create_plan()
            
            if not self.plan or not self.plan.steps:
                return TeamResult(
                    success=False,
                    tasks_completed=0,
                    tasks_failed=1,
                    tasks_skipped=0,
                    total_time=0,
                    errors=["无法创建执行计划"]
                )
            
            # 保存计划到状态
            self.state.plan = {
                "steps": self.plan.steps,
                "reasoning": self.plan.reasoning,
                "estimated_time": self.plan.estimated_time
            }
            
            # 初始化步骤状态
            for step in self.plan.steps:
                step_id = step.get("id", f"step_{len(self.state.step_states)}")
                self.state.step_states[step_id] = StepState(
                    step_id=step_id,
                    name=step.get("name", ""),
                    agent_role=step.get("agent_role", ""),
                    status="pending"
                )
            
            print(f"✅ 计划制定完成")
            print(f"   步骤数: {len(self.plan.steps)}")
            print(f"   预计时间: {self.plan.estimated_time} 分钟")
            print()
            self._display_plan()
        
        # 阶段 2: 执行
        print("\n🚀 阶段 2: 执行计划...")
        self.state.status = "running"
        self.state.start_time = datetime.now().isoformat()
        
        result = await self._execute_plan_with_state()
        
        # 更新最终状态
        if result.success:
            self.state.status = "completed"
        else:
            self.state.status = "failed"
        
        self.state_manager.save_state(self.state)
        
        # 保存结果到文件
        self._save_results(result)
        
        # 阶段 3: 总结
        print("\n📊 阶段 3: 执行总结...")
        self._display_summary(result)
        
        return result
    
    async def _execute_plan_with_state(self) -> TeamResult:
        """带状态管理的计划执行"""
        from .dynamic_workflow import DynamicWorkflow
        
        # 创建临时 DynamicWorkflow 来执行
        temp_workflow = DynamicWorkflow(self.config, self.work_dir, self.executor)
        temp_workflow.plan = self.plan
        
        # 获取待执行的步骤
        pending_steps = self._get_executable_steps()
        
        if not pending_steps:
            print("✅ 所有步骤已完成")
            return TeamResult(
                success=True,
                tasks_completed=len(self.state.completed_steps),
                tasks_failed=len(self.state.failed_steps),
                tasks_skipped=0,
                total_time=0,
                outputs={},
                errors=[]
            )
        
        print(f"📋 待执行步骤: {len(pending_steps)} 个")
        for step_id in pending_steps:
            step_state = self.state.step_states.get(step_id)
            if step_state:
                print(f"   - {step_state.name} ({step_state.agent_role})")
        
        # 执行待处理的步骤
        try:
            # 标记待执行步骤为运行中状态
            for step_id in pending_steps:
                if step_id in self.state.step_states:
                    self.state.step_states[step_id].status = "running"
                    self.state.step_states[step_id].start_time = datetime.now().isoformat()
            
            # 保存运行中状态
            self.state_manager.save_state(self.state)
            
            result = await temp_workflow._execute_plan()
            
            # 更新状态 - 同步所有任务状态
            if temp_workflow.team:
                for task in temp_workflow.team.tasks:
                    step_id = task.name.lower().replace(" ", "_")
                    if step_id in self.state.step_states:
                        step_state = self.state.step_states[step_id]
                        step_state.status = task.status.value
                        step_state.end_time = datetime.now().isoformat()
                        
                        if task.status == TaskStatus.COMPLETED:
                            # 添加到已完成列表
                            if step_id not in self.state.completed_steps:
                                self.state.completed_steps.append(step_id)
                            # 从失败列表中移除（重试成功的情况）
                            if step_id in self.state.failed_steps:
                                self.state.failed_steps.remove(step_id)
                            # 保存输出
                            step_state.output = task.output[:500] if task.output else ""
                            self.state.outputs[step_id] = task.output or ""
                            
                        elif task.status == TaskStatus.FAILED:
                            # 添加到失败列表
                            if step_id not in self.state.failed_steps:
                                self.state.failed_steps.append(step_id)
                            # 从已完成列表中移除（以防万一）
                            if step_id in self.state.completed_steps:
                                self.state.completed_steps.remove(step_id)
                            # 保存错误信息
                            step_state.error = task.error or "执行失败"
                            self.state.errors[step_id] = task.error or "执行失败"
                            
                        elif task.status == TaskStatus.SKIPPED:
                            step_state.error = task.error or "步骤被跳过"
            
            # 更新工作流整体状态
            if self.state.failed_steps:
                self.state.status = "failed"
            elif len(self.state.completed_steps) == len(self.state.step_states):
                self.state.status = "completed"
            else:
                self.state.status = "running"
                
        except Exception as e:
            # 执行异常，标记失败的步骤
            print(f"❌ 执行计划时发生错误: {e}")
            for step_id in pending_steps:
                if step_id in self.state.step_states:
                    step_state = self.state.step_states[step_id]
                    step_state.status = "failed"
                    step_state.error = str(e)
                    step_state.end_time = datetime.now().isoformat()
                    if step_id not in self.state.failed_steps:
                        self.state.failed_steps.append(step_id)
            self.state.status = "failed"
            
            # 返回失败结果
            result = TeamResult(
                success=False,
                tasks_completed=len(self.state.completed_steps),
                tasks_failed=len(self.state.failed_steps),
                tasks_skipped=0,
                total_time=0,
                outputs=self.state.outputs,
                errors=list(self.state.errors.values())
            )
        
        # 保存中间状态
        self.state_manager.save_state(self.state)
        
        return result
    
    def _get_executable_steps(self) -> List[str]:
        """获取可以执行的步骤（考虑依赖关系）"""
        if not self.plan:
            return []
        
        executable = []
        
        for step in self.plan.steps:
            step_id = step.get("id", "")
            if not step_id:
                continue
            
            step_state = self.state.step_states.get(step_id)
            if not step_state:
                continue
            
            # 检查是否已完成
            if step_id in self.state.completed_steps:
                continue
            
            # 检查依赖是否满足
            depends_on = step.get("depends_on", [])
            deps_satisfied = all(
                dep in self.state.completed_steps 
                for dep in depends_on
            )
            
            if deps_satisfied and step_state.status in ["pending", "failed"]:
                executable.append(step_id)
        
        return executable
    
    async def _create_plan(self) -> ExecutionPlan:
        """创建执行计划"""
        # 使用 executor 的 generate_plan 方法
        if hasattr(self.executor, 'generate_plan'):
            available_agents = [
                {
                    "name": data.get("name", aid),
                    "role": data.get("role", "assistant"),
                    "goal": data.get("goal", "")
                }
                for aid, data in self.config.agents.items()
            ]
            
            plan_result = await self.executor.generate_plan(
                goal=self.config.goal,
                input_text=self.config.input,
                available_agents=available_agents,
                strategy=self.config.strategy
            )
            
            if plan_result.get("success"):
                return ExecutionPlan(
                    reasoning=plan_result.get("reasoning", ""),
                    estimated_time=plan_result.get("estimated_time", 30),
                    steps=plan_result.get("steps", [])
                )
            else:
                print(f"⚠️ AI 规划失败: {plan_result.get('error', '未知错误')}")
        
        # 使用默认计划
        return self._generate_mock_plan()
    
    def _generate_mock_plan(self) -> ExecutionPlan:
        """生成默认计划"""
        return ExecutionPlan(
            reasoning="使用默认执行计划",
            estimated_time=30,
            steps=[
                {
                    "id": "step_1",
                    "name": "分析需求",
                    "description": f"分析 {self.config.input}",
                    "agent_role": "researcher",
                    "estimated_minutes": 10,
                    "depends_on": []
                },
                {
                    "id": "step_2",
                    "name": "实现功能",
                    "description": f"实现 {self.config.goal}",
                    "agent_role": "builder",
                    "estimated_minutes": 20,
                    "depends_on": ["step_1"]
                }
            ]
        )
    
    def _create_result_from_state(self) -> TeamResult:
        """从状态创建结果"""
        return TeamResult(
            success=self.state.status == "completed",
            tasks_completed=len(self.state.completed_steps),
            tasks_failed=len(self.state.failed_steps),
            tasks_skipped=0,
            total_time=0,
            outputs={},
            errors=[
                self.state.step_states[sid].error 
                for sid in self.state.failed_steps
                if sid in self.state.step_states
            ]
        )
    
    def _display_plan(self):
        """显示执行计划"""
        if not self.plan:
            return
        
        print("📋 执行计划:")
        print("-" * 60)
        
        for i, step in enumerate(self.plan.steps, 1):
            step_id = step.get("id", f"step_{i}")
            status = "⏳"
            
            if self.state:
                if step_id in self.state.completed_steps:
                    status = "✅"
                elif step_id in self.state.failed_steps:
                    status = "❌"
                elif step_id in self._get_executable_steps():
                    status = "🔄"
            
            print(f"  {i}. [{status}] [{step.get('agent_role', 'unknown')}] {step.get('name', 'unnamed')}")
            print(f"     描述: {step.get('description', '')[:50]}...")
            
            depends_on = step.get("depends_on", [])
            if depends_on:
                print(f"     依赖: {', '.join(depends_on)}")
        
        print()
    
    def _display_summary(self, result: TeamResult):
        """显示执行总结"""
        print(f"\n{'='*60}")
        print("📊 执行总结")
        print(f"{'='*60}")
        print(f"✅ 完成任务: {result.tasks_completed}")
        print(f"❌ 失败任务: {result.tasks_failed}")
        print(f"⏭️ 跳过任务: {result.tasks_skipped}")
        print(f"⏱️ 总耗时: {result.total_time:.2f} 秒")
        print(f"{'='*60}")
        
        if result.success:
            print("\n🎉 所有任务执行成功！")
        else:
            print("\n⚠️ 部分任务执行失败")
            for error in result.errors[:5]:
                print(f"  - {error}")
        
        # 显示状态文件位置
        state_file = self.state_manager._get_state_file(self.config.name)
        print(f"\n💾 执行状态已保存: {state_file}")
    
    def _save_results(self, result: TeamResult):
        """保存执行结果"""
        results_dir = self.work_dir / ".workflow_results"
        results_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = results_dir / f"{self.config.name}_{timestamp}.json"
        
        result_data = {
            "workflow": self.config.name,
            "goal": self.config.goal,
            "success": result.success,
            "stats": {
                "tasks_completed": result.tasks_completed,
                "tasks_failed": result.tasks_failed,
                "total_time": result.total_time
            },
            "state": self.state.to_dict() if self.state else {},
            "outputs": result.outputs,
            "errors": result.errors
        }
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 结果已保存到: {result_file}")


class WorkflowResumer:
    """工作流恢复器 - 用于命令行工具"""
    
    def __init__(self, work_dir: Path):
        self.work_dir = work_dir
        self.state_manager = get_state_manager(work_dir)
    
    def list_workflows(self) -> List[Dict]:
        """列出所有可以恢复的工作流"""
        return self.state_manager.list_saved_states()
    
    def can_resume(self, workflow_name: str) -> bool:
        """检查工作流是否可以恢复"""
        state = self.state_manager.load_state(workflow_name)
        if not state:
            return False
        return state.status in ["running", "paused", "failed"]
    
    def get_workflow_status(self, workflow_name: str) -> Optional[Dict]:
        """获取工作流状态"""
        state = self.state_manager.load_state(workflow_name)
        if not state:
            return None
        
        return {
            "name": state.workflow_name,
            "status": state.status,
            "progress": f"{len(state.completed_steps)}/{len(state.step_states)}",
            "completed_steps": state.completed_steps,
            "failed_steps": state.failed_steps,
            "pending_steps": state.get_pending_steps()
        }
    
    def reset_workflow(self, workflow_name: str):
        """重置工作流状态"""
        self.state_manager.delete_state(workflow_name)
        print(f"🗑️ 工作流 '{workflow_name}' 状态已重置")
