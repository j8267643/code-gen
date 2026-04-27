"""
Enhanced AI Executor with Tool Support
支持工具调用的增强版执行器
"""
from typing import Dict, Any, List, Optional
import asyncio
from pathlib import Path
import json
import re

from .agent import Agent
from .executor import AgentExecutor
from .tool_registry import ToolRegistry, get_tool_registry
from code_gen.config import settings


class EnhancedAgentExecutor(AgentExecutor):
    """
    增强的 Agent 执行器
    
    特点：
    1. 所有 Agent 共享工具注册器
    2. 支持 AI 工具调用
    3. 自动处理工具调用结果
    4. 支持多轮对话
    """
    
    def __init__(self, work_dir: Path, model: str = None):
        # 调用父类初始化，父类会处理 model 和 base_url 的默认值
        super().__init__(work_dir, model)
        # 初始化子类特有的属性
        self.tool_registry = get_tool_registry(work_dir)
        self.max_iterations = 10  # 最大工具调用轮数
    
    async def execute(
        self,
        agent: Agent,
        system_prompt: str,
        user_prompt: str,
        tools: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        执行 Agent 任务 - 支持工具调用
        
        流程：
        1. 构建包含工具说明的提示词
        2. 调用 AI
        3. 如果 AI 请求工具调用，执行工具并返回结果
        4. 重复直到任务完成或达到最大迭代次数
        """
        try:
            # 构建增强的系统提示词
            enhanced_prompt = self._build_system_prompt(agent, system_prompt)
            
            messages = [
                {"role": "system", "content": enhanced_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            print(f"📝 [{agent.name}] 开始任务...")
            
            # 多轮对话，支持工具调用
            final_output = []
            tool_calls_made = []
            
            for iteration in range(self.max_iterations):
                print(f"   迭代 {iteration + 1}/{self.max_iterations}...")
                
                response = await self._call_ai(messages)
                
                if not response.get("success"):
                    error = response.get("error", "未知错误")
                    print(f"   ❌ AI 调用失败: {error}")
                    return {
                        "success": False,
                        "output": "",
                        "error": error,
                        "tool_calls": tool_calls_made
                    }
                
                content = response.get("content", "")
                
                # 检查是否有工具调用请求
                tool_calls = self._extract_tool_calls(content)
                
                if not tool_calls:
                    # 没有工具调用，任务完成
                    final_output.append(content)
                    break
                
                # 执行工具调用
                print(f"   🔧 检测到 {len(tool_calls)} 个工具调用")
                
                for tool_call in tool_calls:
                    tool_name = tool_call.get("tool")
                    parameters = tool_call.get("parameters", {})
                    
                    print(f"   ⚙️ 执行: {tool_name}({json.dumps(parameters, ensure_ascii=False)})")
                    
                    result = await self.tool_registry.execute(tool_name, **parameters)
                    tool_calls_made.append({
                        "tool": tool_name,
                        "parameters": parameters,
                        "result": result
                    })
                    
                    # 添加工具调用和结果到对话历史
                    messages.append({"role": "assistant", "content": content})
                    messages.append({
                        "role": "user",
                        "content": f"工具 '{tool_name}' 执行结果:\n{json.dumps(result, ensure_ascii=False, indent=2)}"
                    })
                    
                    if result.get("success"):
                        print(f"   ✅ 工具执行成功")
                    else:
                        print(f"   ⚠️ 工具执行失败: {result.get('error', '未知错误')}")
            
            # 处理最终输出
            full_output = "\n\n".join(final_output)
            processed_output = self._process_output_by_role(agent, full_output)
            
            # 记录执行历史
            self.execution_history.append({
                "agent": agent.name,
                "prompt": user_prompt[:200],
                "output": processed_output[:200],
                "tool_calls": len(tool_calls_made),
                "success": True
            })
            
            print(f"   ✅ 任务完成")
            
            return {
                "success": True,
                "output": processed_output,
                "error": "",
                "tool_calls": tool_calls_made
            }
            
        except Exception as e:
            print(f"   ❌ 执行异常: {e}")
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "tool_calls": []
            }
    
    def _build_system_prompt(self, agent: Agent, base_prompt: str) -> str:
        """构建完整的系统提示词"""
        parts = [base_prompt]
        
        # 添加角色特定指导
        role_guidance = self._get_role_guidance(agent)
        if role_guidance:
            parts.append(role_guidance)
        
        # 添加工具说明
        tools_prompt = self.tool_registry.get_tools_prompt()
        parts.append(tools_prompt)
        
        # 添加输出格式说明
        parts.append("""
## 输出要求

1. 你可以使用上述工具来完成任务
2. 当你需要使用工具时，请使用指定的格式
3. 工具调用结果会自动返回给你
4. 根据工具返回的结果继续你的任务
5. 最终输出应该清晰、完整
""")
        
        return "\n\n".join(parts)
    
    def _get_role_guidance(self, agent: Agent) -> str:
        """获取角色特定指导"""
        guidance = {
            "builder": """
## 代码构建指导

作为代码构建者，你的任务是编写实际可运行的代码。

你可以：
1. 使用 read_file 工具查看现有代码
2. 使用 write_file 工具创建新文件
3. 使用 search_replace 工具修改现有代码
4. 使用 shell 工具执行命令（如安装依赖）

代码文件应该使用以下格式：
---FILE: path/to/file.py---
```python
# 代码内容
```
---END FILE---
""",
            "architect": """
## 架构设计指导

作为系统架构师，你的任务是设计系统架构。

你可以：
1. 使用 read_file 工具查看现有代码和配置
2. 使用 search 工具搜索项目结构
3. 提供详细的架构设计文档

请包含：
- 系统架构图
- 核心组件设计
- 数据流设计
- 接口定义
- 技术选型
""",
            "researcher": """
## 研究指导

作为研究员，你的任务是收集和分析信息。

你可以：
1. 使用 read_file 工具阅读文档
2. 使用 search 工具搜索代码库
3. 使用 shell 工具运行查询命令

请提供：
- 技术方案对比
- 最佳实践总结
- 参考资料链接
""",
            "validator": """
## 代码审查指导

作为代码验证者，你的任务是检查代码质量。

你可以：
1. 使用 read_file 工具查看代码
2. 使用 search 工具查找相关问题
3. 提供详细的审查报告

请检查：
- 代码风格和规范
- 潜在的错误和漏洞
- 性能问题
- 安全最佳实践
""",
            "tester": """
## 测试指导

作为测试工程师，你的任务是编写测试代码。

你可以：
1. 使用 read_file 工具查看被测试代码
2. 使用 write_file 工具创建测试文件
3. 使用 shell 工具运行测试

请提供：
- 单元测试代码
- 集成测试方案
- 测试覆盖率报告
"""
        }
        
        return guidance.get(agent.role.value, "")
    
    def _extract_tool_calls(self, content: str) -> List[Dict[str, Any]]:
        """从 AI 响应中提取工具调用"""
        tool_calls = []
        
        # 匹配 ```tool ... ``` 格式
        pattern = r'```tool\s*(.*?)```'
        matches = re.findall(pattern, content, re.DOTALL)
        
        for match in matches:
            try:
                data = json.loads(match.strip())
                if "tool" in data:
                    tool_calls.append(data)
            except json.JSONDecodeError:
                continue
        
        return tool_calls
    
    def _process_output_by_role(self, agent: Agent, output: str) -> str:
        """根据 Agent 角色处理输出"""
        if agent.role.value == "builder":
            return self._process_builder_output(output)
        elif agent.role.value == "tester":
            return self._process_tester_output(output)
        return output
    
    def _process_builder_output(self, output: str) -> str:
        """处理 builder 输出，提取并保存代码文件"""
        # 匹配文件块格式
        pattern = r'---FILE:\s*(.+?)---\s*```\w*\n(.*?)```\s*---END FILE---'
        matches = re.findall(pattern, output, re.DOTALL)
        
        saved_files = []
        
        for file_path, content in matches:
            file_path = file_path.strip()
            content = content.strip()
            full_path = self.work_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                saved_files.append(file_path)
                print(f"   💾 已保存文件: {file_path}")
            except Exception as e:
                print(f"   ❌ 保存文件失败 {file_path}: {e}")
        
        if saved_files:
            return output + f"\n\n[已生成 {len(saved_files)} 个文件: {', '.join(saved_files)}]"
        
        return output
    
    def _process_tester_output(self, output: str) -> str:
        """处理 tester 输出"""
        return self._process_builder_output(output)
    
    async def _call_ai(
        self,
        messages: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """调用 AI API"""
        try:
            import httpx
            
            # 转换消息格式
            ollama_messages = []
            system_content = None
            
            for msg in messages:
                if msg["role"] == "system":
                    system_content = msg["content"]
                elif msg["role"] == "user":
                    ollama_messages.append({
                        "role": "user",
                        "content": msg["content"]
                    })
                elif msg["role"] == "assistant":
                    ollama_messages.append({
                        "role": "assistant",
                        "content": msg["content"]
                    })
            
            # 如果有系统提示，添加到第一条用户消息
            if system_content and ollama_messages:
                ollama_messages[0]["content"] = f"{system_content}\n\n{ollama_messages[0]['content']}"
            
            request_data = {
                "model": self.model,
                "messages": ollama_messages,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 4096,
                }
            }
            
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=request_data
                )
                response.raise_for_status()
                data = response.json()
                
                content = data.get("message", {}).get("content", "")
                
                if not content:
                    return {
                        "success": False,
                        "error": "AI 返回空响应",
                        "content": ""
                    }
                
                return {
                    "success": True,
                    "content": content
                }
                
        except httpx.ConnectError:
            return {
                "success": False,
                "error": f"无法连接到 Ollama ({self.base_url})",
                "content": ""
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "content": ""
            }


class EnhancedDynamicWorkflowExecutor(EnhancedAgentExecutor):
    """支持动态工作流的增强执行器"""
    
    async def generate_plan(
        self,
        goal: str,
        input_text: str,
        available_agents: List[Dict],
        strategy: str = "adaptive"
    ) -> Dict[str, Any]:
        """使用 AI 生成执行计划"""
        prompt = f"""请为以下目标制定执行计划：

目标: {goal}
输入: {input_text}
策略: {strategy}

可用 Agents:
{json.dumps(available_agents, ensure_ascii=False, indent=2)}

请以 JSON 格式返回计划：
{{
    "reasoning": "规划思路...",
    "estimated_time": 30,
    "steps": [
        {{
            "id": "step_1",
            "name": "步骤名称",
            "description": "步骤描述",
            "agent_role": "researcher",
            "estimated_minutes": 10,
            "depends_on": []
        }}
    ]
}}"""
        
        messages = [
            {"role": "system", "content": "你是一个任务规划专家。制定详细的执行计划。"},
            {"role": "user", "content": prompt}
        ]
        
        response = await self._call_ai(messages)
        
        if not response.get("success"):
            return {
                "success": False,
                "error": response.get("error", "规划失败")
            }
        
        try:
            content = response.get("content", "")
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                plan = json.loads(content[json_start:json_end])
                return {
                    "success": True,
                    "reasoning": plan.get("reasoning", ""),
                    "estimated_time": plan.get("estimated_time", 30),
                    "steps": plan.get("steps", [])
                }
            else:
                return {
                    "success": False,
                    "error": "无法解析规划响应"
                }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"JSON 解析错误: {e}"
            }
