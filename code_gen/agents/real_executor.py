"""
Real AI Executor for multi-agent system
使用真实的 AI 模型执行 Agent 任务
"""
from typing import Dict, Any, List, Optional
import asyncio
from pathlib import Path
import json

from .agent import Agent
from .executor import AgentExecutor
from code_gen.config import settings


class RealAgentExecutor(AgentExecutor):
    """
    真实的 Agent 执行器
    
    使用 Ollama 或其他 AI 模型调用真实的 AI API
    """
    
    def __init__(self, work_dir: Path, model: str = None):
        super().__init__(work_dir, model)
        self.model = model or settings.ollama_model or "qwen2.5"
        self.base_url = settings.ollama_base_url or "http://localhost:11434"
        self.client = None
    
    async def execute(
        self,
        agent: Agent,
        system_prompt: str,
        user_prompt: str,
        tools: List[Dict] = None
    ) -> Dict[str, Any]:
        """执行 Agent 任务 - 使用真实 AI"""
        try:
            # 根据角色添加特定的系统提示
            enhanced_system_prompt = self._enhance_prompt_by_role(agent, system_prompt)
            
            messages = [
                {"role": "system", "content": enhanced_system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            print(f"📝 发送请求到 {self.model}...")
            
            response = await self._call_ai(
                messages=messages,
                tools=tools
            )
            
            if response.get("success"):
                output = response.get("content", "")
                
                # 根据角色处理输出
                processed_output = self._process_output_by_role(agent, output)
                
                self.execution_history.append({
                    "agent": agent.name,
                    "prompt": user_prompt[:200],
                    "output": processed_output[:200],
                    "success": True
                })
                
                return {
                    "success": True,
                    "output": processed_output,
                    "error": "",
                    "tool_calls": response.get("tool_calls", [])
                }
            else:
                error = response.get("error", "未知错误")
                
                self.execution_history.append({
                    "agent": agent.name,
                    "prompt": user_prompt[:200],
                    "error": error,
                    "success": False
                })
                
                return {
                    "success": False,
                    "output": "",
                    "error": error,
                    "tool_calls": []
                }
                
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "tool_calls": []
            }
    
    def _enhance_prompt_by_role(self, agent: Agent, base_prompt: str) -> str:
        """根据 Agent 角色增强提示词"""
        role_enhancements = {
            "builder": """

你是代码构建者。你的任务是编写实际可运行的代码。

重要规则：
1. 必须生成实际的代码文件
2. 在响应中使用以下格式指定文件路径和内容：

---FILE: path/to/file.py---
```python
# 代码内容
```
---END FILE---

3. 可以生成多个文件，每个文件使用上述格式
4. 确保代码完整、可运行，包含必要的导入和依赖
5. 文件路径应该是相对于工作目录的相对路径
""",
            "architect": """

你是系统架构师。你的任务是设计系统架构。

请提供：
1. 系统架构图（使用文本或 Mermaid 格式）
2. 核心组件设计
3. 数据流设计
4. 接口定义
5. 技术选型建议
""",
            "validator": """

你是代码验证者。你的任务是检查代码质量。

请检查：
1. 代码风格和规范
2. 潜在的错误和漏洞
3. 性能问题
4. 安全最佳实践
5. 提供改进建议
""",
            "tester": """

你是测试工程师。你的任务是编写测试代码。

请提供：
1. 单元测试代码
2. 集成测试方案
3. 测试用例设计
4. 使用 pytest 或其他测试框架

测试文件格式：
---FILE: tests/test_xxx.py---
```python
# 测试代码
```
---END FILE---
"""
        }
        
        enhancement = role_enhancements.get(agent.role.value, "")
        return base_prompt + enhancement
    
    def _process_output_by_role(self, agent: Agent, output: str) -> str:
        """根据 Agent 角色处理输出"""
        if agent.role.value == "builder":
            return self._process_builder_output(output)
        elif agent.role.value == "tester":
            return self._process_tester_output(output)
        return output
    
    def _process_builder_output(self, output: str) -> str:
        """处理 builder 输出，提取并保存代码文件"""
        import re
        from pathlib import Path as PathLib
        
        saved_files = []
        
        def is_safe_path(file_path: str) -> bool:
            """检查文件路径是否安全"""
            if not file_path:
                return False
            
            path_obj = PathLib(file_path)
            
            # 检查是否为绝对路径
            if path_obj.is_absolute():
                return False
            
            # 检查是否包含 .. 或其他路径遍历尝试
            if '..' in path_obj.parts or '..' in str(path_obj):
                return False
            
            # 检查是否尝试访问隐藏文件或系统文件
            if any(part.startswith('.') for part in path_obj.parts):
                return False
            
            # 检查是否在工作目录内
            try:
                full_path = self.work_dir / file_path
                resolved_path = full_path.resolve()
                resolved_work_dir = self.work_dir.resolve()
                # 确保解析后的路径以工作目录开头
                if not str(resolved_path).startswith(str(resolved_work_dir)):
                    return False
            except (ValueError, RuntimeError):
                return False
            
            return True
        
        try:
            # 匹配文件块格式：---FILE: path --- content ---END FILE---
            # 使用更健壮的模式：
            # - ([^\n]+?) 匹配文件路径（不包含换行符）
            # - (?:\w+)? 非捕获组匹配可选的语言标识
            pattern = r'---FILE:\s*([^\n]+?)\s*---\s*```(?:\w+)?\n(.*?)```\s*---END FILE---'
            matches = re.findall(pattern, output, re.DOTALL)
            
            for file_path, content in matches:
                file_path = file_path.strip()
                content = content.strip()
                
                # 验证文件路径安全性
                if not is_safe_path(file_path):
                    print(f"  ⚠️ 跳过不安全的文件路径: {file_path}")
                    continue
                
                # 构建完整路径
                full_path = self.work_dir / file_path
                
                # 确保目录存在
                try:
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    print(f"  ❌ 无法创建目录 {full_path.parent}: {e}")
                    continue
                
                # 保存文件
                try:
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    saved_files.append(file_path)
                    print(f"  💾 已保存文件: {file_path}")
                except Exception as e:
                    print(f"  ❌ 保存文件失败 {file_path}: {e}")
            
            # 如果没有匹配到文件格式，尝试其他格式
            if not saved_files:
                # 尝试匹配 ```python filename.py 格式
                alt_pattern = r'```(?:\w+)?\s*#?\s*(\S+\.(?:py|js|ts|jsx|tsx|java|go|rs|cpp|c|h|yaml|yml|json|md))\n(.*?)```'
                matches = re.findall(alt_pattern, output, re.DOTALL)
                
                for file_path, content in matches:
                    file_path = file_path.strip()
                    
                    # 验证文件路径安全性
                    if not is_safe_path(file_path):
                        print(f"  ⚠️ 跳过不安全的文件路径: {file_path}")
                        continue
                    
                    full_path = self.work_dir / file_path
                    
                    try:
                        full_path.parent.mkdir(parents=True, exist_ok=True)
                    except Exception as e:
                        print(f"  ❌ 无法创建目录 {full_path.parent}: {e}")
                        continue
                    
                    try:
                        with open(full_path, 'w', encoding='utf-8') as f:
                            f.write(content.strip())
                        saved_files.append(file_path)
                        print(f"  💾 已保存文件: {file_path}")
                    except Exception as e:
                        print(f"  ❌ 保存文件失败 {file_path}: {e}")
        
        except re.error as e:
            print(f"  ❌ 正则表达式错误: {e}")
        except Exception as e:
            print(f"  ❌ 处理输出时发生错误: {e}")
        
        if saved_files:
            return output + f"\n\n[已生成 {len(saved_files)} 个文件: {', '.join(saved_files)}]"
        
        return output
    
    def _process_tester_output(self, output: str) -> str:
        """处理 tester 输出，保存测试文件"""
        # 复用 builder 的文件处理逻辑
        return self._process_builder_output(output)
    
    async def _call_ai(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        调用真实的 AI API
        
        使用 httpx 调用 Ollama API
        """
        try:
            import httpx
            
            # 转换消息格式为 Ollama 格式
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
            
            # 准备请求数据
            request_data = {
                "model": self.model,
                "messages": ollama_messages,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 4096,
                }
            }
            
            # 发送请求到 Ollama
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=request_data
                )
                response.raise_for_status()
                data = response.json()
                
                # 提取回复内容
                content = data.get("message", {}).get("content", "")
                
                if not content:
                    return {
                        "success": False,
                        "error": "AI 返回空响应",
                        "content": "",
                        "tool_calls": []
                    }
                
                return {
                    "success": True,
                    "content": content,
                    "tool_calls": []
                }
                
        except httpx.ConnectError as e:
            return {
                "success": False,
                "error": f"无法连接到 Ollama ( {self.base_url} )。请确保 Ollama 正在运行。",
                "content": "",
                "tool_calls": []
            }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {
                    "success": False,
                    "error": f"模型 '{self.model}' 未找到。请运行: ollama pull {self.model}",
                    "content": "",
                    "tool_calls": []
                }
            return {
                "success": False,
                "error": f"AI API 错误: {e.response.status_code} - {e.response.text}",
                "content": "",
                "tool_calls": []
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"AI 调用失败: {str(e)}",
                "content": "",
                "tool_calls": []
            }


class RealDynamicWorkflowExecutor(RealAgentExecutor):
    """
    用于动态工作流的真实执行器
    
    支持生成执行计划和执行任务
    """
    
    async def generate_plan(
        self,
        goal: str,
        input_text: str,
        available_agents: List[Dict[str, Any]],
        strategy: str = "adaptive"
    ) -> Dict[str, Any]:
        """
        使用 AI 生成执行计划
        
        Args:
            goal: 工作流目标
            input_text: 输入信息
            available_agents: 可用的 Agents
            strategy: 执行策略
            
        Returns:
            执行计划
        """
        # 构建规划提示
        agents_info = "\n".join([
            f"- {a.get('name', 'unknown')} (role: {a.get('role', 'unknown')}): {a.get('goal', '')}"
            for a in available_agents
        ])
        
        planning_prompt = f"""你是一个任务规划专家。请为以下目标制定详细的执行计划。

目标: {goal}
输入: {input_text}
策略: {strategy}

可用 Agents:
{agents_info}

请分析这个目标需要哪些步骤来完成，并以 JSON 格式返回计划：

{{
    "reasoning": "你的规划思路...",
    "estimated_time": 60,
    "steps": [
        {{
            "id": "step_1",
            "name": "步骤名称",
            "description": "详细描述这个步骤要做什么",
            "agent_role": "researcher",
            "estimated_minutes": 15,
            "depends_on": []
        }}
    ]
}}

注意：
1. 步骤应该合理，有明确的依赖关系
2. agent_role 必须是可用的 agent 角色之一
3. 根据策略选择合适的执行方式（顺序、并行或混合）
4. estimated_time 是总预计时间（分钟）

请只返回 JSON，不要包含其他内容。"""

        messages = [
            {"role": "user", "content": planning_prompt}
        ]
        
        response = await self._call_ai(messages)
        
        if not response.get("success"):
            return {
                "success": False,
                "error": response.get("error", "规划失败"),
                "steps": []
            }
        
        # 解析 JSON 响应
        try:
            content = response.get("content", "")
            # 提取 JSON 部分
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                plan = json.loads(json_str)
                return {
                    "success": True,
                    "reasoning": plan.get("reasoning", ""),
                    "estimated_time": plan.get("estimated_time", 30),
                    "steps": plan.get("steps", [])
                }
            else:
                return {
                    "success": False,
                    "error": "无法解析 AI 的规划响应",
                    "raw_response": content
                }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"JSON 解析错误: {e}",
                "raw_response": response.get("content", "")
            }
