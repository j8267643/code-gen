#!/usr/bin/env python3
"""
简单的 MCP 服务器示例
运行: python mcp_server_example.py
"""
import asyncio
import json
import sys
from typing import Dict, Any


class SimpleMCPServer:
    """简单的 MCP 服务器，通过 STDIO 通信"""

    def __init__(self):
        self.tools = {
            "get_current_time": {
                "description": "获取当前时间",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            "calculate": {
                "description": "执行数学计算",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "数学表达式，例如: 1 + 2 * 3"
                        }
                    },
                    "required": ["expression"]
                }
            },
            "echo": {
                "description": "回显消息",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "要回显的消息"
                        }
                    },
                    "required": ["message"]
                }
            }
        }

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """处理 MCP 请求"""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "simple-mcp-server",
                        "version": "1.0.0"
                    },
                    "capabilities": {
                        "tools": {}
                    }
                }
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": [
                        {
                            "name": name,
                            "description": info["description"],
                            "inputSchema": info["input_schema"]
                        }
                        for name, info in self.tools.items()
                    ]
                }
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            tool_params = params.get("arguments", {})

            result = await self.execute_tool(tool_name, tool_params)

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": result
                        }
                    ]
                }
            }

        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }

    async def execute_tool(self, name: str, params: Dict[str, Any]) -> str:
        """执行工具"""
        from datetime import datetime

        if name == "get_current_time":
            return f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        elif name == "calculate":
            expression = params.get("expression", "")
            try:
                # 安全计算 - 只允许基本数学运算
                import ast
                import operator

                # 定义允许的操作符
                allowed_ops = {
                    ast.Add: operator.add,
                    ast.Sub: operator.sub,
                    ast.Mult: operator.mul,
                    ast.Div: operator.truediv,
                    ast.Pow: operator.pow,
                    ast.USub: operator.neg,
                }

                def eval_node(node):
                    if isinstance(node, ast.Num):  # Python 3.7
                        return node.n
                    elif isinstance(node, ast.Constant):  # Python 3.8+
                        if isinstance(node.value, (int, float)):
                            return node.value
                        raise ValueError("Only numbers allowed")
                    elif isinstance(node, ast.BinOp):
                        left = eval_node(node.left)
                        right = eval_node(node.right)
                        op_type = type(node.op)
                        if op_type not in allowed_ops:
                            raise ValueError(f"Operator not allowed: {op_type.__name__}")
                        return allowed_ops[op_type](left, right)
                    elif isinstance(node, ast.UnaryOp):
                        operand = eval_node(node.operand)
                        op_type = type(node.op)
                        if op_type not in allowed_ops:
                            raise ValueError(f"Operator not allowed: {op_type.__name__}")
                        return allowed_ops[op_type](operand)
                    elif isinstance(node, ast.Call):
                        raise ValueError("Function calls not allowed")
                    elif isinstance(node, ast.Name):
                        raise ValueError("Variables not allowed")
                    else:
                        raise ValueError(f"Expression type not allowed: {type(node).__name__}")

                # 解析表达式
                tree = ast.parse(expression, mode='eval')
                result = eval_node(tree.body)
                return f"{expression} = {result}"
            except Exception as e:
                return f"计算错误: {e}"

        elif name == "echo":
            message = params.get("message", "")
            return f"Echo: {message}"

        else:
            return f"未知工具: {name}"

    async def run(self):
        """运行服务器"""
        print("Simple MCP Server started", file=sys.stderr)
        print("Waiting for requests...", file=sys.stderr)

        while True:
            try:
                # 读取一行输入
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )

                if not line:
                    break

                line = line.strip()
                if not line:
                    continue

                # 解析请求
                request = json.loads(line)
                print(f"Received: {request.get('method')}", file=sys.stderr)

                # 处理请求
                response = await self.handle_request(request)

                # 发送响应
                response_json = json.dumps(response)
                print(response_json, flush=True)

            except json.JSONDecodeError as e:
                print(f"JSON parse error: {e}", file=sys.stderr)
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)


if __name__ == "__main__":
    server = SimpleMCPServer()
    asyncio.run(server.run())
