"""
Agent Executor - 执行 Agent 任务
"""
from typing import Dict, Any, List, Optional
import asyncio
from pathlib import Path

from .agent import Agent
from code_gen.config import settings


class AgentExecutor:
    """
    Agent 执行器
    
    负责：
    - 调用 AI 模型执行 Agent 任务
    - 管理工具调用
    - 处理执行结果
    
    默认使用 Ollama API 进行真实的 AI 调用
    """
    
    def __init__(self, work_dir: Path, model: str = None):
        self.work_dir = work_dir
        self.model = model or settings.ollama_model or "qwen2.5"
        self.base_url = settings.ollama_base_url or "http://localhost:11434"
        self.execution_history: List[Dict[str, Any]] = []
    
    async def execute(
        self,
        agent: Agent,
        system_prompt: str,
        user_prompt: str,
        tools: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        执行 Agent 任务
        
        Args:
            agent: 执行的 Agent
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            tools: 可用工具
        
        Returns:
            {
                "success": bool,
                "output": str,
                "error": str,
                "tool_calls": List[Dict]
            }
        """
        try:
            # 构建消息
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            print(f"📝 发送请求到 {agent.model}...")
            
            # 调用 AI
            response = await self._call_ai(
                messages=messages,
                tools=tools
            )
            
            # 处理响应
            if response.get("success"):
                output = response.get("content", "")
                
                # 记录执行历史
                self.execution_history.append({
                    "agent": agent.name,
                    "prompt": user_prompt[:200],
                    "output": output[:200],
                    "success": True
                })
                
                return {
                    "success": True,
                    "output": output,
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
    
    async def _call_ai(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        调用 AI 模型
        
        使用 Ollama API 进行真实的 AI 调用
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
                
        except ImportError:
            return {
                "success": False,
                "error": "缺少 httpx 库，请安装: pip install httpx",
                "content": "",
                "tool_calls": []
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"AI 调用失败: {e}",
                "content": "",
                "tool_calls": []
            }
    
    def get_history(self) -> List[Dict[str, Any]]:
        """获取执行历史"""
        return self.execution_history
    
    def clear_history(self):
        """清除执行历史"""
        self.execution_history = []


class MockExecutor(AgentExecutor):
    """
    模拟执行器 - 用于测试
    
    不调用真实的 AI，返回预设的响应
    """
    
    def __init__(self, work_dir: Path, responses: Dict[str, str] = None):
        super().__init__(work_dir)
        self.responses = responses or {}
        self.default_response = "这是一个模拟的 Agent 响应。"
    
    async def _call_ai(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict] = None
    ) -> Dict[str, Any]:
        """模拟 AI 调用"""
        await asyncio.sleep(0.1)  # 短暂延迟模拟
        
        # 根据提示词关键词返回不同响应
        prompt = messages[-1]["content"].lower()
        
        for key, response in self.responses.items():
            if key in prompt:
                return {
                    "success": True,
                    "content": response,
                    "tool_calls": []
                }
        
        return {
            "success": True,
            "content": self.default_response,
            "tool_calls": []
        }
