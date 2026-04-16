"""
流式输出使用示例

展示如何使用 client.py 中的流式输出功能
"""
import asyncio
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from code_gen.client import AIClient

console = Console()


async def stream_chat_example():
    """流式聊天示例"""
    console.print("[bold cyan]流式输出示例[/bold cyan]\n")
    
    # 创建 AI 客户端
    client = AIClient()
    
    # 准备消息
    messages = [
        {"role": "user", "content": "请用 Python 编写一个快速排序算法，并解释其工作原理。"}
    ]
    
    # 系统提示
    system_prompt = "你是一个专业的编程助手，擅长编写清晰、高效的代码。"
    
    # 使用流式输出
    console.print("[bold green]Assistant:[/bold green] ", end="")
    
    full_response = []
    
    # 流式接收响应
    async for chunk in client.stream_message(
        messages=messages,
        system=system_prompt
    ):
        # 实时打印每个块
        console.print(chunk, end="")
        full_response.append(chunk)
    
    console.print("\n")  # 换行
    
    # 显示完整响应
    complete_response = "".join(full_response)
    console.print(Panel(
        complete_response,
        title="完整响应",
        border_style="blue"
    ))


async def stream_with_live_display():
    """使用 Live 显示流式输出（更流畅的 UI）"""
    console.print("[bold cyan]Live 流式显示示例[/bold cyan]\n")
    
    client = AIClient()
    
    messages = [
        {"role": "user", "content": "简述机器学习的主要类型和应用场景。"}
    ]
    
    # 使用 Rich 的 Live 组件实现更流畅的显示
    text = Text()
    
    with Live(
        Panel(text, title="Assistant", border_style="green"),
        console=console,
        refresh_per_second=10
    ) as live:
        async for chunk in client.stream_message(messages=messages):
            text.append(chunk)
            live.update(Panel(text, title="Assistant", border_style="green"))
    
    console.print("\n")


async def stream_chat_session():
    """多轮对话流式聊天"""
    console.print("[bold cyan]多轮对话流式聊天[/bold cyan]")
    console.print("输入 'quit' 退出聊天\n")
    
    client = AIClient()
    conversation = []
    
    while True:
        # 获取用户输入
        user_input = console.input("[bold blue]You:[/bold blue] ")
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            break
        
        # 添加到对话历史
        conversation.append({"role": "user", "content": user_input})
        
        # 流式显示助手响应
        console.print("[bold green]Assistant:[/bold green] ", end="")
        
        assistant_response = []
        async for chunk in client.stream_message(messages=conversation):
            console.print(chunk, end="")
            assistant_response.append(chunk)
        
        console.print("\n")
        
        # 将助手响应添加到对话历史
        conversation.append({
            "role": "assistant",
            "content": "".join(assistant_response)
        })


async def main():
    """主函数"""
    console.print("=" * 60)
    console.print("流式输出功能演示".center(60))
    console.print("=" * 60)
    console.print()
    
    # 选择示例
    console.print("[1] 基础流式输出示例")
    console.print("[2] Live 流式显示示例")
    console.print("[3] 多轮对话流式聊天")
    console.print()
    
    choice = console.input("请选择示例 [1-3]: ").strip()
    
    if choice == "1":
        await stream_chat_example()
    elif choice == "2":
        await stream_with_live_display()
    elif choice == "3":
        await stream_chat_session()
    else:
        console.print("[red]无效选择[/red]")


if __name__ == "__main__":
    asyncio.run(main())
