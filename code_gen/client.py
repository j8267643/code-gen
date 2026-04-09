"""
Unified AI client supporting multiple providers
"""
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional, Any
import json

import httpx
from anthropic import AsyncAnthropic
from rich.console import Console

from code_gen.config import settings, ModelProvider

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
                "Set ANTHROPIC_API_KEY environment variable or run 'claude-code login'"
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
            
            content = response.content[0]
            if content.type == "tool_use":
                return content
            
            return content.text
            
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
        self.max_tokens = settings.max_tokens
        self.temperature = settings.temperature
    
    async def send_message(
        self,
        messages: list[dict],
        system: Optional[str] = None,
        tools: Optional[list] = None,
    ) -> str:
        try:
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
                        "num_predict": min(self.max_tokens, 2048),
                    }
                }
                
                # Add tools if provided
                if tools:
                    request_data["tools"] = tools
                
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=request_data
                )
                response.raise_for_status()
                data = response.json()
                
                # Handle tool calls
                message = data.get("message", {})
                content = message.get("content", "")
                
                # If content is empty but has tool calls, return tool call info with parameters
                if not content and message.get("tool_calls"):
                    tool_call = message["tool_calls"][0]
                    tool_name = tool_call['function']['name']
                    tool_params = tool_call['function'].get('arguments', '{}')
                    
                    # Ensure tool_params is a string for the arguments field
                    if isinstance(tool_params, dict):
                        arguments_str = json.dumps(tool_params, ensure_ascii=False)
                    else:
                        arguments_str = tool_params
                    
                    return json.dumps({
                        "tool": tool_name,
                        "arguments": arguments_str
                    }, ensure_ascii=False)
                
                return content
            
        except Exception as e:
            from rich.console import Console
            console = Console()
            console.print(f"[red]Error calling Ollama: {e}[/red]")
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
        """Build prompt from messages - simplified for Ollama"""
        prompt_parts = []
        
        # Use simplified system prompt for Ollama with file access permission
        prompt_parts.append("""System: You are a helpful coding assistant. You have FULL ACCESS to the local file system.
You can:
- Read any file the user mentions
- List directory contents
- Analyze code and project structures
- Write or modify files when requested
- Execute shell commands

When a user asks about a file or directory, assume you can access it directly.

""")
        
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "user":
                prompt_parts.append(f"User: {content}\n")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}\n")
        
        prompt_parts.append("Assistant: ")
        return "".join(prompt_parts)


class LMStudioClient(BaseAIClient):
    """LM Studio local model client (OpenAI compatible)"""
    
    def __init__(self):
        self.base_url = settings.lmstudio_base_url.rstrip('/')
        self.model = settings.lmstudio_model
        self.max_tokens = settings.max_tokens
        self.temperature = settings.temperature
        self.client = httpx.AsyncClient(timeout=120.0)
    
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
