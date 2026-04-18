#!/usr/bin/env python3
"""Test Code Gen startup and MCP connection"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from code_gen.ui.app import CodeGenApp
from code_gen.session import SessionManager

# Create session
work_dir = Path.cwd()
session = SessionManager(work_dir, "gpt-oss:20b")

# Create app (this will initialize MCP)
print("Creating CodeGenApp...")
app = CodeGenApp(session)

print(f"\nSystem prompt length: {len(app.system_prompt)}")
print("\nSystem prompt MCP section:")

# Extract MCP section
if "Available MCP tools:" in app.system_prompt:
    start = app.system_prompt.find("Available MCP tools:")
    end = app.system_prompt.find("\n\n", start)
    if end == -1:
        end = len(app.system_prompt)
    print(app.system_prompt[start:end])
else:
    print("No MCP section found")

print("\nDone!")


async def test_startup():
    """测试启动 - test_startup 入口"""
    # 测试已完成在模块加载时
    pass


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_startup())
