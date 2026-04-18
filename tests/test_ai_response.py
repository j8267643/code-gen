#!/usr/bin/env python3
"""Test AI response with MCP tools"""
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from code_gen.ui.app import CodeGenApp
from code_gen.session import SessionManager

# Create session
work_dir = Path.cwd()
session = SessionManager(work_dir, "gpt-oss:20b")

# Create app
print("Creating CodeGenApp...")
app = CodeGenApp(session)

print("\n" + "="*60)
print("SYSTEM PROMPT (MCP section):")
print("="*60)

# Extract MCP section
if "Available MCP tools:" in app.system_prompt:
    start = app.system_prompt.find("Available MCP tools:")
    end = app.system_prompt.find("\n\n", start)
    if end == -1:
        end = len(app.system_prompt)
    print(app.system_prompt[start:end])
else:
    print("No MCP section found")

print("\n" + "="*60)
print("Testing AI response...")
print("="*60)

async def test_ai_response():
    """测试 AI 响应 - test_ai_response 入口"""
    # Create a simple conversation
    messages = [
        {"role": "user", "content": "你会使用哪些MCP工具？请列出所有可用的MCP工具名称。"}
    ]

    print("\nSending message to AI...")
    try:
        response = await app.client.send_message(
            messages=messages,
            system=app.system_prompt,
            tools=[]  # Don't include regular tools for this test
        )

        print("\nAI Response:")
        print("-"*60)
        print(response)
        print("-"*60)
    except Exception as e:
        print(f"\nAI Response failed (expected without real API): {e}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_ai_response())
