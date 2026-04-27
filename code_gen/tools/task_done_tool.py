"""
Task Done Tool - 任务完成标记工具

明确标记任务完成，强制要求验证后才能调用
"""
from typing import Optional, List
from code_gen.tools.base import Tool, ToolResult
from code_gen.features.task_done import TaskDoneManager, CompletionStatus, VerificationStatus


class TaskDoneTool(Tool):
    """
    任务完成标记工具 - 用于明确标记任务完成状态
    
    功能：
    - 标记任务准备完成
    - 验证任务完成情况
    - 记录完成摘要和产物
    - 防止 AI 过早结束任务
    
    使用流程：
    1. 任务执行过程中，AI 使用此工具标记准备完成
    2. 系统检查验证步骤是否完成
    3. 如果验证通过，任务正式标记为完成
    4. 如果验证失败，返回继续执行
    """
    
    name = "task_done"
    description = """标记任务完成。在确认任务真正完成后使用此工具。

使用场景：
- 代码修复完成后
- 功能实现完成后
- 调试问题解决后
- 任何任务完成时

重要：调用此工具前，请确保：
1. 所有要求的功能已实现
2. 代码可以正常运行
3. 没有明显的错误
4. 已验证修复/实现有效

参数说明：
- status: "ready" 表示准备完成，需要验证
- summary: 任务完成摘要
- verification_steps: 验证步骤列表
"""
    
    input_schema = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["ready", "completed"],
                "description": "完成状态：ready(准备完成，需要验证), completed(已完成)",
            },
            "summary": {
                "type": "string",
                "description": "任务完成摘要，描述完成了什么",
            },
            "artifacts": {
                "type": "array",
                "items": {"type": "string"},
                "description": "生成的文件/产物列表",
            },
            "verification_steps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "step_name": {"type": "string"},
                        "description": {"type": "string"},
                        "status": {"type": "string", "enum": ["unverified", "partial", "verified", "failed"]},
                        "result": {"type": "string"},
                    },
                    "required": ["step_name", "description"],
                },
                "description": "验证步骤列表",
            },
            "test_results": {
                "type": "string",
                "description": "测试结果或验证结果",
            },
            "task_id": {
                "type": "string",
                "description": "任务ID（可选）",
            },
        },
        "required": ["status", "summary"],
    }
    
    def __init__(self):
        super().__init__()
        self.manager = TaskDoneManager()
    
    async def execute(
        self,
        status: str,
        summary: str,
        artifacts: Optional[List[str]] = None,
        verification_steps: Optional[List[dict]] = None,
        test_results: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> ToolResult:
        """执行任务完成标记"""
        try:
            # 创建或获取任务完成记录
            task = self.manager.create_task_completion(
                task_id=task_id or f"task_{id(self)}",
                task_description=summary
            )
            
            # 添加验证步骤
            if verification_steps:
                for step_data in verification_steps:
                    from code_gen.task_done import VerificationStep
                    step = VerificationStep(
                        step_name=step_data["step_name"],
                        description=step_data["description"],
                        status=VerificationStatus(step_data.get("status", "unverified")),
                        result=step_data.get("result")
                    )
                    task.verification_steps.append(step)
            
            # 更新任务信息
            task.summary = summary
            task.artifacts = artifacts or []
            task.test_results = test_results
            
            # 根据状态处理
            if status == "ready":
                task.completion_status = CompletionStatus.READY_TO_COMPLETE
                
                # 检查验证状态
                if task.verification_steps:
                    unverified = [s for s in task.verification_steps if s.status == VerificationStatus.UNVERIFIED]
                    failed = [s for s in task.verification_steps if s.status == VerificationStatus.FAILED]
                    
                    if failed:
                        result_text = f"""⚠️ 任务标记为准备完成，但存在验证失败的步骤

📝 摘要: {summary}

❌ 验证失败步骤 ({len(failed)}):
"""
                        for step in failed:
                            result_text += f"  - {step.step_name}: {step.description}\n"
                        result_text += "\n请修复这些问题后再标记完成。"
                        
                        return ToolResult(
                            success=False,
                            content=result_text,
                            error="存在验证失败的步骤",
                            data={"task": task.to_dict()}
                        )
                    
                    if unverified:
                        result_text = f"""⏳ 任务标记为准备完成，但还有未验证的步骤

📝 摘要: {summary}

🔄 未验证步骤 ({len(unverified)}):
"""
                        for step in unverified:
                            result_text += f"  - {step.step_name}: {step.description}\n"
                        result_text += "\n请完成这些验证步骤后再标记完成。"
                        
                        return ToolResult(
                            success=True,
                            content=result_text,
                            data={"task": task.to_dict(), "needs_verification": True}
                        )
                
                # 验证通过
                result_text = f"""✅ 任务准备完成

📝 摘要: {summary}

📦 产物 ({len(artifacts) if artifacts else 0}):
"""
                if artifacts:
                    for artifact in artifacts:
                        result_text += f"  - {artifact}\n"
                else:
                    result_text += "  (无)\n"
                
                if test_results:
                    result_text += f"\n🧪 测试结果:\n{test_results}\n"
                
                result_text += "\n所有验证步骤已通过，任务可以标记为完成。"
                
                return ToolResult(
                    success=True,
                    content=result_text,
                    data={"task": task.to_dict(), "can_complete": True}
                )
                
            elif status == "completed":
                success = self.manager.complete_task(task.task_id)
                
                if success:
                    result_text = f"""🎉 任务已完成

📝 摘要: {summary}

📦 产物 ({len(artifacts) if artifacts else 0}):
"""
                    if artifacts:
                        for artifact in artifacts:
                            result_text += f"  - {artifact}\n"
                    
                    if test_results:
                        result_text += f"\n🧪 测试结果:\n{test_results}\n"
                    
                    result_text += "\n✅ 任务已成功完成并验证！"
                    
                    return ToolResult(
                        success=True,
                        content=result_text,
                        data={"task": task.to_dict(), "completed": True}
                    )
                else:
                    return ToolResult(
                        success=False,
                        content="",
                        error="无法完成任务，可能存在未通过的验证步骤",
                        data={"task": task.to_dict()}
                    )
            
            else:
                return ToolResult(
                    success=False,
                    content="",
                    error=f"无效的状态: {status}"
                )
                
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"任务完成标记失败: {str(e)}"
            )


class VerifyTaskStepTool(Tool):
    """验证任务步骤工具"""
    
    name = "verify_task_step"
    description = "验证任务的一个步骤，更新验证状态"
    
    input_schema = {
        "type": "object",
        "properties": {
            "task_id": {
                "type": "string",
                "description": "任务ID",
            },
            "step_name": {
                "type": "string",
                "description": "步骤名称",
            },
            "status": {
                "type": "string",
                "enum": ["verified", "failed", "partial"],
                "description": "验证状态",
            },
            "result": {
                "type": "string",
                "description": "验证结果描述",
            },
        },
        "required": ["task_id", "step_name", "status"],
    }
    
    def __init__(self, manager: TaskDoneManager):
        super().__init__()
        self.manager = manager
    
    async def execute(
        self,
        task_id: str,
        step_name: str,
        status: str,
        result: Optional[str] = None,
    ) -> ToolResult:
        """验证任务步骤"""
        try:
            status_enum = VerificationStatus(status)
            success = self.manager.verify_step(task_id, step_name, status_enum, result)
            
            if success:
                emoji = {"verified": "✅", "failed": "❌", "partial": "⚠️"}.get(status, "✓")
                return ToolResult(
                    success=True,
                    content=f"{emoji} 步骤 '{step_name}' 已标记为 {status}",
                    data={"step_name": step_name, "status": status, "result": result}
                )
            else:
                return ToolResult(
                    success=False,
                    content="",
                    error=f"无法验证步骤 '{step_name}'，任务或步骤不存在"
                )
                
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"验证步骤失败: {str(e)}"
            )
