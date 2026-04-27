"""
Unified AI client supporting multiple providers
"""
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional, Any
import json

import httpx
from anthropic import AsyncAnthropic
from rich.console import Console

from code_gen.core.config import settings, ModelProvider

console = Console()


class BaseAIClient(ABC):
    """Base class for AI clients"""
    
    @abstractmethod
    async def send_message(
        self,
        messages: list[dict],
        system: Optional[str] = None,
        tools: Optional[list] = None,
    ) -> str:
        """Send a message and get response"""
        pass
    
    @abstractmethod
    async def stream_message(
        self,
        messages: list[dict],
        system: Optional[str] = None,
        tools: Optional[list] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream a response"""
        pass


class AnthropicClient(BaseAIClient):
    """Anthropic Claude client"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.anthropic_api_key
        if not self.api_key:
            raise ValueError(
                "Anthropic API key not found. "
                "Set ANTHROPIC_API_KEY environment variable or run 'code-gen login'"
            )
        
        self.client = AsyncAnthropic(api_key=self.api_key)
        self.model = settings.anthropic_model
        self.max_tokens = settings.max_tokens
        self.temperature = settings.temperature
    
    async def send_message(
        self,
        messages: list[dict],
        system: Optional[str] = None,
        tools: Optional[list] = None,
    ) -> str:
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system,
                messages=messages,
                tools=tools,
            )
            
            # 调试输出
            console.print(f"[dim]Response content blocks: {len(response.content)}[/dim]")
            
            # 收集所有内容块
            text_parts = []
            tool_calls = []
            
            for i, content in enumerate(response.content):
                console.print(f"[dim]Block {i}: type={content.type}[/dim]")
                if content.type == "text":
                    text_parts.append(content.text)
                elif content.type == "tool_use":
                    tool_calls.append({
                        "tool": content.name,
                        "arguments": content.input
                    })
                    console.print(f"[dim]Tool call: {content.name}[/dim]")
            
            # 如果有工具调用，返回第一个工具调用
            if tool_calls:
                result = json.dumps(tool_calls[0])
                console.print(f"[dim]Returning tool call: {result[:100]}...[/dim]")
                return result
            
            # 否则返回文本
            result = "\n".join(text_parts)
            console.print(f"[dim]Returning text (length: {len(result)})[/dim]")
            return result
            
        except Exception as e:
            console.print(f"[red]Error calling Claude API: {e}[/red]")
            raise
    
    async def stream_message(
        self,
        messages: list[dict],
        system: Optional[str] = None,
        tools: Optional[list] = None,
    ) -> AsyncGenerator[str, None]:
        try:
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system,
                messages=messages,
                tools=tools,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
                    
        except Exception as e:
            console.print(f"[red]Error streaming from Claude API: {e}[/red]")
            raise


class OllamaClient(BaseAIClient):
    """Ollama local model client"""
    
    def __init__(self):
        import os
        # Read from environment variables directly to ensure fresh values
        self.base_url = os.getenv('OLLAMA_BASE_URL', settings.ollama_base_url).rstrip('/')
        self.model = os.getenv('OLLAMA_MODEL', settings.ollama_model)
        # Use Ollama-specific max_tokens if available, otherwise fall back to general setting
        self.max_tokens = settings.ollama_max_tokens or 65535
        self.temperature = settings.temperature
        # Initialize httpx client for streaming
        self.client = httpx.AsyncClient(timeout=120.0)
    
    async def _get_available_models(self, client: httpx.AsyncClient) -> tuple[bool, list[str]]:
        """Get available models from Ollama and check if current model exists.
        
        Returns:
            tuple: (model_exists: bool, available_models: list of model names)
        """
        try:
            response = await client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            return self.model in models, models
        except Exception:
            return False, []
    
    async def send_message(
        self,
        messages: list[dict],
        system: Optional[str] = None,
        tools: Optional[list] = None,
    ) -> str:
        try:
            # Create client first to check model availability
            async with httpx.AsyncClient(timeout=30.0) as check_client:
                model_exists, available_models = await self._get_available_models(check_client)
                if not model_exists:
                    console.print(f"[yellow]Warning: Model '{self.model}' not found in Ollama.[/yellow]")
                    console.print("[dim]Available models:[/dim]")
                    for model_name in available_models[:5]:
                        console.print(f"  - {model_name}")
                    console.print(f"\n[yellow]Try pulling the model:[/yellow]")
                    console.print(f"  [dim]ollama pull {self.model}[/dim]")
            
            # Convert messages to Ollama chat format
            ollama_messages = []
            
            # Add system message if provided
            if system:
                ollama_messages.append({
                    "role": "system",
                    "content": system
                })
            
            for msg in messages:
                if msg["role"] == "user":
                    ollama_messages.append({
                        "role": "user",
                        "content": msg["content"]
                    })
                elif msg["role"] == "assistant":
                    ollama_messages.append({
                        "role": "assistant",
                        "content": msg["content"]
                    })
            
            # Create new client for each request to avoid connection issues
            async with httpx.AsyncClient(timeout=300.0) as client:
                # Prepare request data
                request_data = {
                    "model": self.model,
                    "messages": ollama_messages,
                    "stream": False,
                    "options": {
                        "temperature": self.temperature,
                        "num_predict": self.max_tokens,
                    }
                }
                
                # Add tools if provided
                if tools:
                    request_data["tools"] = tools
                
                # Try /api/chat endpoint first (for newer Ollama versions)
                try:
                    response = await client.post(
                        f"{self.base_url}/api/chat",
                        json=request_data
                    )
                    response.raise_for_status()
                    data = response.json()
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 500:
                        # Try /api/generate as fallback (for older versions or some models)
                        console.print("[yellow]Chat endpoint failed, trying generate endpoint...[/yellow]")
                        prompt = self._build_prompt(ollama_messages, system, tools)
                        response = await client.post(
                            f"{self.base_url}/api/generate",
                            json={
                                "model": self.model,
                                "prompt": prompt,
                                "stream": False,
                                "options": {
                                    "temperature": self.temperature,
                                    "num_predict": self.max_tokens,
                                }
                            }
                        )
                        response.raise_for_status()
                        data = response.json()
                        # Convert generate response to chat format
                        data = {"message": {"content": data.get("response", "")}}
                    else:
                        raise
                
                # Handle tool calls
                message = data.get("message", {})
                content = message.get("content", "")
                
                # 调试输出
                console.print(f"[dim]Ollama response - content length: {len(content)}, tool_calls: {bool(message.get('tool_calls'))}[/dim]")
                
                # If content is empty but has tool calls, return tool call info with parameters
                if message.get("tool_calls"):
                    tool_call = message["tool_calls"][0]
                    tool_name = tool_call['function']['name']
                    tool_params = tool_call['function'].get('arguments', '{}')
                    
                    # Ensure tool_params is a dict for the arguments field
                    if isinstance(tool_params, str):
                        try:
                            arguments_dict = json.loads(tool_params)
                        except:
                            arguments_dict = {"raw": tool_params}
                    else:
                        arguments_dict = tool_params
                    
                    result = json.dumps({
                        "tool": tool_name,
                        "arguments": arguments_dict
                    }, ensure_ascii=False)
                    console.print(f"[dim]Returning tool call: {result[:100]}...[/dim]")
                    return result
                
                console.print(f"[dim]Returning text (length: {len(content)})[/dim]")
                return content
            
        except Exception as e:
            console.print(f"[red]Error calling Ollama: {e}[/red]")
            
            # 显示当前配置信息
            console.print(f"\n[dim]Current configuration:[/dim]")
            console.print(f"  Model: {self.model}")
            console.print(f"  Base URL: {self.base_url}")
            
            # 提供详细的排查建议
            console.print("\n[yellow]Troubleshooting steps:[/yellow]")
            console.print("  1. Check if Ollama is running:")
            console.print(f"     [dim]curl {self.base_url}/api/tags[/dim]")
            console.print("  2. List installed models:")
            console.print("     [dim]ollama list[/dim]")
            console.print("  3. Test model directly:")
            console.print(f"     [dim]ollama run {self.model} \"Hello\"[/dim]")
            console.print("  4. Check Ollama version:")
            console.print("     [dim]ollama --version[/dim]")
            console.print("  5. View Ollama logs:")
            console.print("     [dim]ollama logs[/dim]")
            console.print("  6. Restart Ollama:")
            console.print("     [dim]ollama serve[/dim]")
            
            console.print("\n[yellow]Configuration file:[/yellow]")
            config_path = Path.cwd() / ".code_gen" / "config.yaml"
            console.print(f"  [dim]{config_path}[/dim]")
            raise
    
    async def stream_message(
        self,
        messages: list[dict],
        system: Optional[str] = None,
        tools: Optional[list] = None,
    ) -> AsyncGenerator[str, None]:
        try:
            ollama_messages = []
            for msg in messages:
                if msg["role"] == "user":
                    ollama_messages.append({
                        "role": "user",
                        "content": msg["content"]
                    })
                elif msg["role"] == "assistant":
                    ollama_messages.append({
                        "role": "assistant",
                        "content": msg["content"]
                    })
            
            prompt = self._build_prompt(ollama_messages, system, tools)
            
            async with self.client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": True,
                    "options": {
                        "temperature": self.temperature,
                        "num_predict": min(self.max_tokens, 2048),  # Limit tokens for faster response
                    }
                }
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "response" in data:
                                yield data["response"]
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            console.print(f"[red]Error streaming from Ollama: {e}[/red]")
            raise
    
    def _build_prompt(self, messages: list, system: Optional[str], tools: Optional[list]) -> str:
        """Build prompt from messages - simplified for Ollama with tool support"""
        prompt_parts = []
        
        # Build system prompt with tool information
        system_parts = ["System: You are a helpful coding assistant."]
        
        if system:
            system_parts.append(system)
        
        # Add tool information
        if tools:
            system_parts.append("\nAvailable tools:")
            for tool in tools:
                tool_name = tool.get('name', tool.get('function', {}).get('name', 'unknown'))
                tool_desc = tool.get('description', tool.get('function', {}).get('description', ''))
                system_parts.append(f"- {tool_name}: {tool_desc}")
            
            system_parts.append("\nTo use a tool, respond with JSON format:")
            system_parts.append('{\"tool\": \"tool_name\", \"arguments\": {\"param1\": \"value1\"}}')
            system_parts.append("\nIf no tool is needed, respond normally.")
        
        prompt_parts.append("\n".join(system_parts))
        prompt_parts.append("")
        
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        prompt_parts.append("Assistant: ")
        return "\n".join(prompt_parts)


class LMStudioClient(BaseAIClient):
    """LM Studio local model client (OpenAI compatible)"""
    
    def __init__(self):
        self.base_url = settings.lmstudio_base_url.rstrip('/')
        self.model = settings.lmstudio_model
        self.max_tokens = settings.max_tokens
        self.temperature = settings.temperature
        self.client = httpx.AsyncClient(timeout=120.0)
    
    def _convert_tools_to_openai(self, tools: list) -> list:
        """Convert Claude format tools to OpenAI format"""
        openai_tools = []
        for tool in tools:
            if "input_schema" in tool:
                # Claude format -> OpenAI format
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": tool["input_schema"]
                    }
                })
            else:
                # Already OpenAI format
                openai_tools.append(tool)
        return openai_tools
    
    async def send_message(
        self,
        messages: list[dict],
        system: Optional[str] = None,
        tools: Optional[list] = None,
    ) -> str:
        try:
            # Add system message if provided
            api_messages = messages.copy()
            if system:
                api_messages.insert(0, {"role": "system", "content": system})
            
            # Build request data
            request_data = {
                "model": self.model,
                "messages": api_messages,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "stream": False,
            }
            
            # Try with tools first
            if tools:
                request_data_with_tools = request_data.copy()
                # Convert tools to OpenAI format
                openai_tools = self._convert_tools_to_openai(tools)
                request_data_with_tools["tools"] = openai_tools
                
                try:
                    response = await self.client.post(
                        f"{self.base_url}/chat/completions",
                        json=request_data_with_tools
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    message = data["choices"][0]["message"]
                    content = message.get("content", "")
                    tool_calls = message.get("tool_calls")
                    
                    # Debug output
                    console.print(f"[dim]LM Studio response - content length: {len(content)}, has tool_calls: {bool(tool_calls)}[/dim]")
                    if content:
                        console.print(f"[dim]Content preview: {content[:100]}...[/dim]")
                    
                    # Handle tool calls
                    if tool_calls:
                        tool_call = tool_calls[0]
                        tool_name = tool_call['function']['name']
                        tool_params = tool_call['function'].get('arguments', '{}')
                        
                        console.print(f"[dim]Tool call detected: {tool_name}[/dim]")
                        
                        # Ensure tool_params is a dict
                        if isinstance(tool_params, str):
                            try:
                                arguments_dict = json.loads(tool_params)
                            except:
                                arguments_dict = {"raw": tool_params}
                        else:
                            arguments_dict = tool_params
                        
                        result = json.dumps({
                            "tool": tool_name,
                            "arguments": arguments_dict
                        }, ensure_ascii=False)
                        console.print(f"[dim]Returning tool call: {result[:100]}...[/dim]")
                        return result
                    
                    console.print(f"[dim]No tool calls, returning text content[/dim]")
                    return content
                    
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 400:
                        # Model doesn't support tools, fallback to text mode
                        console.print("[yellow]Model doesn't support tools, using text mode[/yellow]")
                    else:
                        raise
            
            # Fallback: request without tools
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=request_data
            )
            response.raise_for_status()
            data = response.json()
            
            content = data["choices"][0]["message"].get("content", "")
            console.print(f"[dim]LM Studio response (text mode) - length: {len(content)}[/dim]")
            return content
            
        except Exception as e:
            console.print(f"[red]Error calling LM Studio: {e}[/red]")
            raise
    
    async def stream_message(
        self,
        messages: list[dict],
        system: Optional[str] = None,
        tools: Optional[list] = None,
    ) -> AsyncGenerator[str, None]:
        try:
            api_messages = messages.copy()
            if system:
                api_messages.insert(0, {"role": "system", "content": system})
            
            async with self.client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": api_messages,
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                    "stream": True,
                }
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data["choices"][0]["delta"]
                            if "content" in delta:
                                yield delta["content"]
                        except (json.JSONDecodeError, KeyError):
                            continue
                            
        except Exception as e:
            console.print(f"[red]Error streaming from LM Studio: {e}[/red]")
            raise


class OpenAICompatibleClient(BaseAIClient):
    """Generic OpenAI compatible API client"""
    
    def __init__(self):
        self.base_url = settings.openai_compatible_base_url
        if not self.base_url:
            raise ValueError("OPENAI_COMPATIBLE_BASE_URL not set")
        self.base_url = self.base_url.rstrip('/')
        
        self.api_key = settings.openai_compatible_api_key
        self.model = settings.openai_compatible_model
        self.max_tokens = settings.max_tokens
        self.temperature = settings.temperature
        
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        self.client = httpx.AsyncClient(timeout=120.0, headers=headers)
    
    async def send_message(
        self,
        messages: list[dict],
        system: Optional[str] = None,
        tools: Optional[list] = None,
    ) -> str:
        try:
            api_messages = messages.copy()
            if system:
                api_messages.insert(0, {"role": "system", "content": system})
            
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": api_messages,
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                    "stream": False,
                }
            )
            response.raise_for_status()
            data = response.json()
            
            return data["choices"][0]["message"]["content"]
            
        except Exception as e:
            console.print(f"[red]Error calling API: {e}[/red]")
            raise
    
    async def stream_message(
        self,
        messages: list[dict],
        system: Optional[str] = None,
        tools: Optional[list] = None,
    ) -> AsyncGenerator[str, None]:
        try:
            api_messages = messages.copy()
            if system:
                api_messages.insert(0, {"role": "system", "content": system})
            
            async with self.client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": api_messages,
                    "max_tokens": self.max_tokens,
                    "temperature": self.temperature,
                    "stream": True,
                }
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data["choices"][0]["delta"]
                            if "content" in delta:
                                yield delta["content"]
                        except (json.JSONDecodeError, KeyError):
                            continue
                            
        except Exception as e:
            console.print(f"[red]Error streaming from API: {e}[/red]")
            raise


class ClaudeClient:
    """Factory for creating appropriate AI client"""
    
    def __new__(cls, *args, **kwargs):
        """Create appropriate client based on settings"""
        import os
        # Read from environment variable directly to ensure fresh value
        provider_str = os.getenv('MODEL_PROVIDER', settings.model_provider.value)
        try:
            provider = ModelProvider(provider_str.lower())
        except ValueError:
            provider = settings.model_provider
        
        console.print(f"[dim]Using provider: {provider.value}[/dim]")
        
        if provider == ModelProvider.ANTHROPIC:
            return AnthropicClient(*args, **kwargs)
        elif provider == ModelProvider.OLLAMA:
            return OllamaClient(*args, **kwargs)
        elif provider == ModelProvider.LMSTUDIO:
            return LMStudioClient(*args, **kwargs)
        elif provider == ModelProvider.OPENAI_COMPATIBLE:
            return OpenAICompatibleClient(*args, **kwargs)
        else:
            raise ValueError(f"Unknown provider: {provider}")
