"""
LSP integration for Claude Code
Based on services/lsp/ from TypeScript project
"""
from typing import Optional
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
import subprocess
import asyncio
import json


@dataclass
class LSPInitialization:
    """LSP initialization result"""
    success: bool
    generation: int
    error: Optional[str] = None


class LSPClient:
    """LSP client for language server protocol"""
    
    def __init__(self, server_command: str, working_dir: Path):
        self.server_command = server_command
        self.working_dir = working_dir
        self.process = None
        self.initialization_generation = 0
        self.capabilities = {}
        self.connected = False
    
    async def start(self) -> LSPInitialization:
        """Start LSP server"""
        try:
            # Increment generation
            self.initialization_generation += 1
            generation = self.initialization_generation
            
            # Start process
            self.process = await asyncio.create_subprocess_exec(
                *self.server_command.split(),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.working_dir)
            )
            
            # Send initialize request
            initialize_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "processId": self.process.pid,
                    "rootUri": self.working_dir.as_uri(),
                    "capabilities": {}
                }
            }
            
            await self._send_message(initialize_request)
            
            # Wait for initialize response
            response = await self._read_message()
            
            if response and response.get("result"):
                self.capabilities = response["result"].get("capabilities", {})
                self.connected = True
                return LSPInitialization(success=True, generation=generation)
            
            return LSPInitialization(
                success=False,
                generation=generation,
                error="Failed to initialize LSP server"
            )
            
        except Exception as e:
            return LSPInitialization(
                success=False,
                generation=self.initialization_generation,
                error=str(e)
            )
    
    async def _send_message(self, message: dict):
        """Send a message to LSP server"""
        if not self.process or not self.process.stdin:
            return
        
        content = json.dumps(message)
        headers = f"Content-Length: {len(content)}\r\n\r\n"
        
        self.process.stdin.write((headers + content).encode())
        await self.process.stdin.drain()
    
    async def _read_message(self) -> Optional[dict]:
        """Read a message from LSP server"""
        if not self.process or not self.process.stdout:
            return None
        
        try:
            # Read headers
            headers = b""
            while not headers.endswith(b"\r\n\r\n"):
                chunk = await self.process.stdout.read(1)
                if not chunk:
                    return None
                headers += chunk
            
            # Parse Content-Length
            headers_str = headers.decode()
            for line in headers_str.split("\r\n"):
                if line.startswith("Content-Length:"):
                    length = int(line.split(":")[1].strip())
                    break
            else:
                return None
            
            # Read content
            content = await self.process.stdout.read(length)
            return json.loads(content.decode())
            
        except Exception as e:
            print(f"Failed to read LSP message: {e}")
            return None
    
    async def shutdown(self):
        """Shutdown LSP server"""
        if self.process:
            self.process.terminate()
            await self.process.wait()
            self.connected = False
    
    async def did_open(self, file_path: str, language_id: str, content: str):
        """Notify server that a file was opened"""
        if not self.connected:
            return
        
        message = {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": Path(file_path).as_uri(),
                    "languageId": language_id,
                    "version": 1,
                    "text": content
                }
            }
        }
        
        await self._send_message(message)
    
    async def did_change(self, file_path: str, content: str):
        """Notify server that a file changed"""
        if not self.connected:
            return
        
        message = {
            "jsonrpc": "2.0",
            "method": "textDocument/didChange",
            "params": {
                "textDocument": {
                    "uri": Path(file_path).as_uri(),
                    "version": 2
                },
                "contentChanges": [
                    {"text": content}
                ]
            }
        }
        
        await self._send_message(message)
    
    async def completion(self, file_path: str, line: int, character: int) -> list:
        """Get completion suggestions"""
        if not self.connected:
            return []
        
        message = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "textDocument/completion",
            "params": {
                "textDocument": {
                    "uri": Path(file_path).as_uri()
                },
                "position": {
                    "line": line,
                    "character": character
                }
            }
        }
        
        await self._send_message(message)
        response = await self._read_message()
        
        if response and response.get("result"):
            return response["result"].get("items", [])
        
        return []
    
    async def hover(self, file_path: str, line: int, character: int) -> Optional[dict]:
        """Get hover information"""
        if not self.connected:
            return None
        
        message = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "textDocument/hover",
            "params": {
                "textDocument": {
                    "uri": Path(file_path).as_uri()
                },
                "position": {
                    "line": line,
                    "character": character
                }
            }
        }
        
        await self._send_message(message)
        response = await self._read_message()
        
        if response and response.get("result"):
            return response["result"]
        
        return None


# Global LSP client instance
lsp_client = None
