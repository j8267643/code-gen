"""
Main terminal UI application using Rich
"""
import asyncio
import os
from typing import Optional
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from prompt_toolkit import PromptSession

from code_gen.core.client import ClaudeClient
from code_gen.core.session import SessionManager
from code_gen.tools.files import FileTools
from code_gen.tools.shell import ShellTools
from code_gen.tools.git import GitTools
from code_gen.tools.search import SearchTools

# Import SimpleAgent (with V2 features)
from code_gen.agent.simple_agent import SimpleAgent

console = Console()


class CodeGenApp:
    """Main terminal UI application"""
    
    def __init__(self, session: SessionManager):
        self.session = session
        self.prompt_session = PromptSession()
        self.running = True

        # Initialize client
        self.client = ClaudeClient()

        # Core tools
        self.tools = (
            FileTools.get_tools() +
            ShellTools.get_tools() +
            SearchTools.get_tools() +
            GitTools.get_tools()
        )
        
        # Add web search tools
        from code_gen.tools.web import DuckDuckGoSearchTool, WebFetchTool
        self.tools.append(DuckDuckGoSearchTool())
        self.tools.append(WebFetchTool())
        
        # Add process management tools
        from code_gen.tools.process_manager import KillProcessTool, ListProcessesTool
        self.tools.extend([
            KillProcessTool(),
            ListProcessesTool(),
        ])
        
        # Add Trae Agent style tools
        from code_gen.tools.sequential_thinking_tool import SequentialThinkingTool, GetThinkingChainTool
        from code_gen.tools.task_done_tool import TaskDoneTool
        from code_gen.tools.browser_tool import get_browser_tools
        from code_gen.tools.bash_session import BashSessionTool
        
        self.thinking_tool = SequentialThinkingTool()
        self.bash_tool = BashSessionTool()
        self.tools.extend([
            self.thinking_tool,
            GetThinkingChainTool(self.thinking_tool.engine),
            TaskDoneTool(),
            self.bash_tool,
        ])
        
        # Add browser automation tools
        self.tools.extend(get_browser_tools())
        
        # Initialize skill system
        self._init_skill_system()

    def run(self):
        """Run the main application loop"""
        try:
            self.loop = asyncio.get_event_loop()
            if self.loop.is_closed():
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
        
        try:
            console.print("[dim]Type 'exit' or press Ctrl+C to quit[/dim]\n")
            
            console.print("\n")
            console.print(r"[bold cyan]╔══════════════════════════════════════════════════════════════╗[/bold cyan]")
            console.print(r"[bold cyan]║  ██████╗ ██████╗ ██████╗ ███████╗ ██████╗ ███████╗ ███╗   ██╗║[/bold cyan]")
            console.print(r"[bold cyan]║ ██╔════╝██╔═████╗██╔══██╗██╔════╝██╔════╝ ██╔════╝ ████╗  ██║║[/bold cyan]")
            console.print(r"[bold cyan]║ ██║     ██║██╔██║██║  ██║█████╗  ██║█████╗█████╗   ██╔██╗ ██║║[/bold cyan]")
            console.print(r"[bold cyan]║ ██║     ████╔╝██║██║  ██║██╔══╝  ██╚═══██║██╔══╝   ██║╚██╗██║║[/bold cyan]")
            console.print(r"[bold cyan]║ ╚██████╗╚██████╔╝██████╔╝███████╗╚██████╔╝███████╗ ██║ ╚████║║[/bold cyan]")
            console.print(r"[bold cyan]║  ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝ ╚═════╝ ╚══════╝ ╚═╝  ╚═══╝║[/bold cyan]")
            console.print(r"[bold cyan]╚══════════════════════════════════════════════════════════════╝[/bold cyan]")
            console.print(r"[bold cyan]              C O D E G E N                       [/bold cyan]")
            console.print(r"[dim]              AI Programming Assistant            [/dim]")
            console.print("\n")
            
            # 显示系统信息
            self._show_system_info()
            
            while self.running:
                try:
                    # Get user input
                    user_input = self.prompt_session.prompt(
                        "\n[You]: ",
                        multiline=False,
                    )
                    
                    if not user_input.strip():
                        continue
                    
                    if user_input.lower() in ('exit', 'quit', 'q'):
                        break
                    
                    # Handle special commands
                    if user_input.startswith('/'):
                        self._handle_command(user_input)
                        continue
                    
                    # Process with SimpleAgent
                    self.loop.run_until_complete(self._process_message(user_input))
                    
                except KeyboardInterrupt:
                    break
                except EOFError:
                    break
                    
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
        finally:
            console.print("\n[yellow]Goodbye! 👋[/yellow]")
    
    async def _process_message(self, user_input: str):
        """Process user message using SimpleAgent"""
        try:
            console.print("[dim]Processing...[/dim]")
            
            # Use SimpleAgent (with V2 features)
            agent = SimpleAgent(
                client=self.client,
                tools=self.tools,
                work_dir=os.getcwd()
            )
            
            result = await agent.process(user_input, os.getcwd())
            
            # Display result
            console.print(f"\n[bold blue]CodeGen:[/bold blue]")
            console.print(Markdown(result))
            
            # Save to session
            self.session.add_message("user", user_input)
            self.session.add_message("assistant", result)
            
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            import traceback
            console.print(traceback.format_exc())
    
    def _handle_command(self, command: str):
        """Handle special commands"""
        cmd = command.lower().strip()
        
        if cmd == '/help':
            console.print("\n[bold]Available Commands:[/bold]")
            console.print("  /help - Show this help message")
            console.print("  /exit - Exit the application")
            console.print("  /tools - List available tools")
            console.print("")
        elif cmd == '/tools':
            console.print("\n[bold]Available Tools:[/bold]")
            for tool in self.tools:
                desc = getattr(tool, 'description', 'No description')[:60]
                console.print(f"  - {tool.name}: {desc}")
            console.print("")
        elif cmd in ['/exit', '/quit']:
            self.running = False
        else:
            console.print(f"[yellow]Unknown command: {command}[/yellow]")

    def _init_skill_system(self):
        """Initialize skill system"""
        try:
            from code_gen.agent.skills import SkillSystem, skill_system as global_skill_system
            import code_gen.agent.skills as skills_module
            
            # Create skill system with work_dir pointing to code-gen root
            work_dir = Path("d:/LX/code-gen")
            skill_sys = SkillSystem(work_dir)
            skill_sys.load_skills()
            
            # Set global instance
            skills_module.skill_system = skill_sys
            
        except Exception as e:
            console.print(f"[dim]Skill system not initialized: {e}[/dim]")

    def _show_system_info(self):
        """显示系统信息：技能、MCP、工具等"""
        from rich.table import Table
        from rich.panel import Panel
        from rich.columns import Columns
        
        # 工具信息
        tool_table = Table(title="[bold cyan]🛠️  Available Tools[/bold cyan]", show_header=False, box=None)
        tool_table.add_column("Name", style="green")
        tool_table.add_column("Description", style="dim")
        
        for tool in self.tools[:10]:  # 只显示前10个
            desc = getattr(tool, 'description', 'No description')[:40]
            tool_table.add_row(f"  {tool.name}", desc)
        if len(self.tools) > 10:
            tool_table.add_row(f"  ...", f"and {len(self.tools) - 10} more tools")
        
        # Skills 信息
        skill_table = Table(title="[bold magenta]🎯 Skills[/bold magenta]", show_header=False, box=None)
        skill_table.add_column("Name", style="yellow")
        skill_table.add_column("Status", style="dim")
        
        # 尝试加载 skills
        try:
            from code_gen.agent.skills import skill_system
            if skill_system and skill_system.skills:
                for skill_name in list(skill_system.skills.keys())[:5]:
                    skill_table.add_row(f"  {skill_name}", "✓ ready")
                if len(skill_system.skills) > 5:
                    skill_table.add_row(f"  ...", f"and {len(skill_system.skills) - 5} more")
            else:
                skill_table.add_row("  No skills loaded", "")
        except Exception:
            skill_table.add_row("  Skills not available", "")
        
        # MCP 信息
        mcp_table = Table(title="[bold blue]🔌 MCP Servers[/bold blue]", show_header=False, box=None)
        mcp_table.add_column("Name", style="cyan")
        mcp_table.add_column("Status", style="dim")
        
        try:
            from code_gen.core.mcp_simple import mcp_client
            if mcp_client and mcp_client.servers:
                for server_name in list(mcp_client.servers.keys())[:3]:
                    mcp_table.add_row(f"  {server_name}", "✓ connected")
                if len(mcp_client.servers) > 3:
                    mcp_table.add_row(f"  ...", f"and {len(mcp_client.servers) - 3} more")
            else:
                mcp_table.add_row("  No MCP servers", "")
        except Exception:
            mcp_table.add_row("  MCP not available", "")
        
        # 创建并显示面板
        console.print(Panel(Columns([tool_table, skill_table, mcp_table]), 
                           title="[bold white]System Status[/bold white]",
                           border_style="dim"))
        console.print()
