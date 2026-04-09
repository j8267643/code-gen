"""
Main terminal UI application using Rich
"""
import asyncio
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys

from code_gen.client import ClaudeClient
from code_gen.session import SessionManager
from code_gen.tools.files import FileTools
from code_gen.tools.shell import ShellTools
from code_gen.tools.git import GitTools
from code_gen.tools.search import SearchTools
from code_gen.mcp import mcp_manager
from code_gen.memory import MemorySystem, memory_system
from code_gen.security import SecurityMonitor, SecurityConfig
from code_gen.cost_tracker import CostTracker
from code_gen.history import HistorySystem

# Import new integration module
from code_gen.integration import ClaudeCodeIntegration, integration_instance

console = Console()


class ClaudeCodeApp:
    """Main terminal UI application"""
    
    def __init__(self, session: SessionManager):
        self.session = session
        self.prompt_session = PromptSession()
        self.running = True
        self.skill_system = None
        
        # Initialize client first
        self.client = ClaudeClient()
        
        # System prompt
        self.system_prompt = self._build_system_prompt()
        
        # Available tools
        self.tools = (
            FileTools.get_tools() +
            ShellTools.get_tools() +
            GitTools.get_tools() +
            SearchTools.get_tools()
        )
        
        # Load skills
        self._load_skills()
        
        # Initialize MCP
        self._init_mcp()
        
        # Initialize integration
        self._init_integration()
        
        # Initialize memory system
        self._init_memory()
        
        # Initialize security monitor
        self._init_security()
        
        # Initialize cost tracker
        self._init_cost_tracker()
        
        # Initialize history system
        self._init_history()
        
    def _init_memory(self):
        """Initialize memory system"""
        from pathlib import Path
        
        work_dir = Path.cwd()
        self.memory_system = MemorySystem(work_dir)
        
    def _init_security(self):
        """Initialize security monitor"""
        from pathlib import Path
        
        work_dir = Path.cwd()
        self.security_monitor = SecurityMonitor(work_dir, SecurityConfig())
        
    def _load_skills(self):
        """Load skills from skill system"""
        from code_gen.skills import SkillSystem
        from pathlib import Path
        
        # Initialize skill system
        work_dir = Path.cwd()
        self.skill_system = SkillSystem(work_dir)
        self.skill_system.load_skills()
        
    def _init_mcp(self):
        """Initialize MCP system"""
        from code_gen.mcp import mcp_manager, MCPConnectionConfig, MCPServerType
        from pathlib import Path
        
        # Connect to default MCP server (if configured)
        config = MCPConnectionConfig(
            server_type=MCPServerType.STDIO,
            stdio_command=None
        )
        
        # Try to connect to a default MCP server
        try:
            if self.loop and not self.loop.is_closed():
                self.loop.run_until_complete(mcp_manager.connect_to_server("default", config))
        except:
            pass
        
    def _init_integration(self):
        """Initialize integration systems"""
        global integration_instance
        if integration_instance is None:
            from pathlib import Path
            work_dir = Path.cwd()
            integration_instance = ClaudeCodeIntegration(work_dir)
    
    def _init_cost_tracker(self):
        """Initialize cost tracker"""
        from pathlib import Path
        
        work_dir = Path.cwd()
        self.cost_tracker = CostTracker(work_dir)
        
    def _init_history(self):
        """Initialize history system"""
        from pathlib import Path
        
        work_dir = Path.cwd()
        self.history_system = HistorySystem(work_dir)
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for Claude"""
        return """You are Claude Code, an AI-powered coding assistant.
You help users write, understand, and modify code.

IMPORTANT: You have memory of previous conversations in this session.
If the user greets you with "你好" or "hello", they may be:
1. Starting a new conversation (in which case you should greet back)
2. Continuing a previous conversation (in which case you should acknowledge it)

When responding:
1. Be concise but thorough
2. Use markdown for code blocks with language tags
3. Explain your reasoning when making changes
4. Ask for clarification if needed
5. Use available tools when appropriate

Available tools:
- read_file: Read file contents
- write_file: Write content to a file
- list_directory: List directory contents
- execute_command: Execute shell commands
- view_directory_tree: View directory structure
- git_status: Check git status
- git_diff: Show git diff
- git_log: Show git log
- search_files: Search for text in files
- get_file_info: Get file information

Available MCP tools:
- mcp__file_read: Read files via MCP
- mcp__file_write: Write files via MCP
- mcp__execute_command: Execute commands via MCP

Available Skills:
- code_review: Review code and suggest improvements
- git_commit: Generate commit messages
- code_search: Search for code patterns

Always use tools when the user asks you to:
- Read or write files
- Execute commands
- Search code
- Check git status
- Use MCP tools when available
- Use skills for specialized tasks

If the user asks you to remember something or if you've discussed something important,
use the write_file tool to save it to a memory file."""

    def run(self):
        """Run the main application loop"""
        # Create event loop once
        try:
            self.loop = asyncio.get_event_loop()
            if self.loop.is_closed():
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
        
        try:
            # Use existing client from __init__
            if not hasattr(self, 'client') or self.client is None:
                self.client = ClaudeClient()
            
            console.print("[dim]Type 'exit' or press Ctrl+C to quit[/dim]\n")
            
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
                    
                    # Check for skill matches
                    matching_skills = []
                    if self.skill_system:
                        matching_skills = self.skill_system.get_matching_skills(user_input)
                    if matching_skills:
                        console.print(f"[dim]Matching skills: {', '.join(s.name for s in matching_skills)}[/dim]")
                        # Add skill information to the message
                        skill_info = "\n\nMatching skills:\n" + "\n".join(
                            f"- {s.name}: {s.description}" for s in matching_skills
                        )
                        user_input += skill_info
                    
                    # Check security before processing
                    if self.security_monitor:
                        if self.security_monitor.check_prompt_injection(user_input):
                            console.print("[red]Security alert: Prompt injection detected![/red]")
                            console.print("[dim]Message blocked for security reasons.[/dim]")
                            continue
                    
                    # Check if it's time to dream
                    self._check_dream_schedule()
                    
                    # Process with Claude using the persistent loop
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
        """Process user message with Claude"""
        try:
            # Show processing status
            console.print("\n[dim]Claude Code is thinking...[/dim]")
            
            # Add user message to session
            self.session.add_message("user", user_input)
            
            # Save user input as memory
            if self.memory_system:
                self.memory_system.add_memory(
                    content=user_input,
                    memory_type="user",
                    tags=["conversation"]
                )
            
            # Get all messages to check session state
            all_messages = self.session.get_messages()
            
            # Check if this is a new session (no previous messages)
            if len(all_messages) <= 1:
                # Only send the current message, no history
                conversation = [{"role": "user", "content": user_input}]
            else:
                # Get recent messages for context
                recent_messages = self.session.get_recent_messages(10)
                
                # Build conversation history
                conversation = []
                for msg in recent_messages:
                    if msg.role == "user":
                        conversation.append({"role": "user", "content": msg.content})
                    elif msg.role == "assistant":
                        conversation.append({"role": "assistant", "content": msg.content})
            
            # Prepare tools for API call
            tools = [tool.to_claude_format() for tool in self.tools]
            
            # Call Claude API
            response = await self.client.send_message(
                messages=conversation,
                system=self.system_prompt,
                tools=tools
            )
            
            # Check if response is a tool call
            import json
            tool_call_data = None
            
            # Check for JSON format tool call (new format with parameters)
            if isinstance(response, str):
                try:
                    response_data = json.loads(response)
                    if "tool" in response_data and "arguments" in response_data:
                        tool_call_data = response_data
                except json.JSONDecodeError:
                    pass
            
            # Check for old format "Using tool: name"
            if not tool_call_data and isinstance(response, str) and response.startswith("Using tool:"):
                tool_name = response.replace("Using tool: ", "").strip()
                tool_call_data = {"tool": tool_name, "arguments": "{}"}
            
            # Handle tool calls (may need to call multiple times)
            max_iterations = 5
            iteration = 0
            
            while tool_call_data and iteration < max_iterations:
                iteration += 1
                tool_name = tool_call_data["tool"]
                arguments_str = tool_call_data["arguments"]
                
                # Parse arguments - handle both string and dict formats
                if isinstance(arguments_str, str):
                    tool_params = json.loads(arguments_str)
                else:
                    tool_params = arguments_str
                
                # Display tool execution
                console.print(f"\n[yellow]正在执行工具: {tool_name}[/yellow]")
                console.print(f"[dim]参数: {tool_params}[/dim]")
                
                # Check for accidental damage potential
                if self.security_monitor:
                    if self.security_monitor.check_accidental_damage(tool_name, tool_params):
                        console.print("[red]Security alert: Potential accidental damage detected![/red]")
                        console.print("[dim]Tool execution blocked for security reasons.[/dim]")
                        return "Tool execution blocked due to potential security risk"
                
                # Find and execute the tool
                tool_result = await self._execute_tool_with_params(tool_name, tool_params)
                
                # Display tool result
                console.print(f"\n[green]工具执行结果:[/green]")
                console.print(f"[dim]{tool_result}[/dim]")
                
                # Add tool result to conversation
                conversation.append({"role": "assistant", "content": json.dumps(tool_call_data)})
                conversation.append({
                    "role": "user",
                    "content": f"Tool execution result: {tool_result}"
                })
                
                # Call API again with tool result
                response = await self.client.send_message(
                    messages=conversation[-5:],  # Use last 5 messages for context
                    system=self.system_prompt,
                    tools=tools
                )
                
                # Check if response is another tool call
                tool_call_data = None
                if isinstance(response, str):
                    try:
                        response_data = json.loads(response)
                        if "tool" in response_data and "arguments" in response_data:
                            tool_call_data = response_data
                    except json.JSONDecodeError:
                        pass
                
                if not tool_call_data and isinstance(response, str) and response.startswith("Using tool:"):
                    tool_name = response.replace("Using tool: ", "").strip()
                    tool_call_data = {"tool": tool_name, "arguments": "{}"}
            
            # Add assistant response to session
            self.session.add_message("assistant", response)
            
            # Record cost if available
            if self.cost_tracker:
                # Get token usage from response
                token_usage = getattr(self.client, 'last_token_usage', None)
                if token_usage:
                    self.cost_tracker.record_usage(
                        session_id=self.session.session.id,
                        model=self.session.model,
                        input_tokens=token_usage.get("input_tokens", 0),
                        output_tokens=token_usage.get("output_tokens", 0)
                    )
            
            # Add to history
            if self.history_system:
                self.history_system.add_item(
                    item_type="message",
                    content=user_input,
                    role="user",
                    session_id=self.session.session.id
                )
                self.history_system.add_item(
                    item_type="message",
                    content=str(response),
                    role="assistant",
                    session_id=self.session.session.id
                )
            
            # Display response with prompt
            console.print(f"\n[bold blue]Claude Code:[/bold blue]")
            console.print(Markdown(response))
            console.print(f"\n[dim]Type your message or use /help for commands[/dim]")
            
        except Exception as e:
            console.print(f"[red]Error processing message: {e}[/red]")
            raise
    
    async def _execute_tool_with_params(self, tool_name: str, params: dict) -> str:
        """Execute a tool with parameters"""
        # Find the tool
        for tool in self.tools:
            if tool.name == tool_name:
                try:
                    # Execute the tool with provided parameters
                    result = await tool.execute(**params)
                    
                    # Handle both ToolResult and old format
                    if hasattr(result, 'content'):
                        output = result.content
                        error = result.error
                    else:
                        output = result.output
                        error = result.error
                    
                    # Check if file was created (for write_file tool)
                    if tool_name == "write_file" and result.success:
                        file_path = params.get("path", "")
                        if file_path:
                            from pathlib import Path
                            full_path = Path.cwd() / file_path
                            if full_path.exists():
                                console.print(f"\n[green]✓ 文件已创建: {full_path}[/green]")
                                file_size = full_path.stat().st_size
                                console.print(f"[dim]文件大小: {file_size} 字节[/dim]")
                            else:
                                console.print(f"\n[yellow]⚠ 警告: 文件似乎没有创建成功![/yellow]")
                                console.print(f"[dim]预期路径: {full_path}[/dim]")
                    
                    return f"Output: {output}\nError: {error}" if error else f"Output: {output}"
                    
                except Exception as e:
                    return f"Error executing tool: {str(e)}"
        
        return f"Tool not found: {tool_name}"
    
    async def _execute_tool(self, tool_name: str, conversation: list) -> str:
        """Execute a tool by name (legacy method for old format)"""
        # Find the tool
        for tool in self.tools:
            if tool.name == tool_name:
                try:
                    # Extract parameters from conversation
                    last_user_msg = None
                    for msg in reversed(conversation):
                        if msg.get("role") == "user":
                            last_user_msg = msg.get("content", "")
                            break
                    
                    # Parse parameters from user message
                    import re
                    params = {}
                    
                    # Try to extract command from the message
                    if tool_name == "execute_command":
                        # Look for command in the message
                        match = re.search(r'execute\s+(.+?)(?:\.|$)', last_user_msg or "", re.IGNORECASE)
                        if match:
                            params["command"] = match.group(1).strip()
                        else:
                            # Use the whole message as command
                            params["command"] = last_user_msg or ""
                    
                    # Execute the tool
                    result = await tool.execute(**params)
                    # Handle both ToolResult and old format
                    if hasattr(result, 'content'):
                        return f"Output: {result.content}\nError: {result.error}" if result.error else f"Output: {result.content}"
                    else:
                        return f"Output: {result.output}\nError: {result.error}" if result.error else f"Output: {result.output}"
                    
                except Exception as e:
                    return f"Error executing tool: {str(e)}"
        
        return f"Tool not found: {tool_name}"
    
    def _handle_command(self, command: str):
        """Handle special slash commands"""
        parts = command.split()
        cmd = parts[0].lower()
        args = parts[1:]
        
        if cmd == '/clear':
            console.clear()
            self.session.clear()
            console.print("[dim]Session cleared[/dim]")
            
        elif cmd == '/new':
            # Create a new session with a fresh ID
            console.print("[bold]Creating new session...[/bold]")
            from pathlib import Path
            from code_gen.session import SessionManager
            from datetime import datetime
            
            # Save current session before creating new one
            self.session._save_session()
            
            # Create a new session with timestamp-based ID to force fresh start
            current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
            new_session_id = f"{self.session.work_dir.name}_session_{current_time}"
            
            # Create new session manually
            from code_gen.session import Session
            new_session = Session(
                id=new_session_id,
                work_dir=self.session.work_dir,
                model=self.session.model
            )
            
            # Create new session manager
            new_sm = SessionManager.__new__(SessionManager)
            new_sm.work_dir = self.session.work_dir
            new_sm.model = self.session.model
            new_sm.session = new_session
            
            self.session = new_sm
            
            console.print("[green]New session created![/green]")
            console.print(f"[dim]Session ID: {new_session.id}[/dim]")
            console.print(f"[dim]Messages: {len(new_session.messages)}[/dim]")
            
        elif cmd == '/files':
            # Show context files
            files = self.session.session.context_files
            if files:
                console.print("[bold]Context files:[/bold]")
                for f in files:
                    console.print(f"  • {f}")
            else:
                console.print("[dim]No context files[/dim]")
                
        elif cmd == '/help':
            self._show_help()
            
        elif cmd == '/skills':
            # Show available skills
            console.print("[bold]Available Skills:[/bold]")
            if self.skill_system:
                for skill in self.skill_system.skills.values():
                    console.print(f"  • {skill.name}: {skill.description}")
                    if skill.patterns:
                        console.print(f"    Patterns: {', '.join(skill.patterns)}")
                    if skill.commands:
                        console.print(f"    Commands: {', '.join(skill.commands)}")
            else:
                console.print("[dim]No skills loaded[/dim]")
                    
        elif cmd == '/mcp':
            # Show MCP status
            console.print("[bold]MCP Status:[/bold]")
            if mcp_manager.clients:
                for server_name, client in mcp_manager.clients.items():
                    console.print(f"  • {server_name}: {'Connected' if client.connected else 'Disconnected'}")
                    tools = mcp_manager.get_all_tools()
                    if tools:
                        console.print(f"    Tools: {len(tools)}")
                        for tool in tools[:5]:  # Show first 5 tools
                            console.print(f"      - {tool.name}")
        
        elif cmd == '/dream':
            # Run dream process
            console.print("[bold]Starting Dream Process...[/bold]")
            from pathlib import Path
            from code_gen.memory import MemorySystem
            work_dir = Path.cwd()
            memory_system = MemorySystem(work_dir)
            
            if not memory_system.memories:
                console.print("[yellow]No memories to dream about.[/yellow]")
                return
            
            console.print(f"[dim]Found {len(memory_system.memories)} memories[/dim]\n")
            
            # Run dream
            asyncio.run(self._run_dream_process(memory_system))
            
            console.print("\n[yellow]Dream process completed![/yellow]")
        
        elif cmd == '/memories':
            # Show memories
            console.print("[bold]Memories[/bold]")
            from pathlib import Path
            from code_gen.memory import MemorySystem
            work_dir = Path.cwd()
            memory_system = MemorySystem(work_dir)
            
            if not memory_system.memories:
                console.print("[dim]No memories found.[/dim]")
                return
            
            console.print(f"\n[dim]Found {len(memory_system.memories)} memories:[/dim]\n")
            
            for memory in memory_system.memories:
                console.print(f"[bold]{memory.type}:[/bold] {memory.id}")
                console.print(f"  {memory.content[:200]}...")
                if memory.tags:
                    console.print(f"  [dim]Tags: {', '.join(memory.tags)}[/dim]")
                console.print()
        
        elif cmd == '/security':
            # Run security monitor
            console.print("[bold]Security Monitor[/bold]")
            from pathlib import Path
            from code_gen.security import SecurityMonitor, SecurityConfig
            work_dir = Path.cwd()
            security = SecurityMonitor(work_dir, SecurityConfig())
            security.print_security_report()
        
        elif cmd == '/cost':
            # Show cost tracking
            console.print("[bold]Cost Tracking[/bold]")
            if self.cost_tracker:
                summary = self.cost_tracker.get_cost_summary()
                console.print(f"\n[bold]Total Cost:[/bold] ${summary['total_cost']:.6f}")
                console.print(f"[bold]Total Input Tokens:[/bold] {summary['total_input_tokens']}")
                console.print(f"[bold]Total Output Tokens:[/bold] {summary['total_output_tokens']}")
                console.print(f"[bold]Total Sessions:[/bold] {summary['total_sessions']}")
                
                if summary['model_breakdown']:
                    console.print("\n[bold]Model Breakdown:[/bold]")
                    for model, data in summary['model_breakdown'].items():
                        console.print(f"  {model}:")
                        console.print(f"    Cost: ${data['cost']:.6f}")
                        console.print(f"    Input Tokens: {data['input_tokens']}")
                        console.print(f"    Output Tokens: {data['output_tokens']}")
                        console.print(f"    Sessions: {data['sessions']}")
            else:
                console.print("[dim]Cost tracker not initialized[/dim]")
        
        elif cmd == '/history':
            # Show history
            console.print("[bold]History[/bold]")
            if self.history_system:
                items = self.history_system.get_recent_items(10)
                console.print(f"\n[dim]Found {len(items)} recent items:[/dim]\n")
                
                for item in items:
                    console.print(f"[bold]{item.type}:[/bold] {item.id}")
                    console.print(f"  {item.content[:100]}...")
                    console.print(f"  [dim]{item.timestamp}[/dim]")
                    console.print()
            else:
                console.print("[dim]History system not initialized[/dim]")
    
    async def _run_dream_process(self, memory_system):
        """Run dream process using AI"""
        try:
            # Show progress
            console.print("\n[dim]Dreaming...[/dim]")
            
            # Run dream
            result = await memory_system.dream_async()
            
            # Display dream result
            console.print("\n" + "=" * 60)
            console.print(Panel(
                result,
                title="[bold green]Dream Result[/bold green]",
                border_style="green"
            ))
            console.print("=" * 60 + "\n")
            
            # Save dream result
            from code_gen.commands.dream import _save_dream_result
            await _save_dream_result(Path.cwd(), result)
            
        except Exception as e:
            console.print(f"[red]Dream process failed: {e}[/red]")
            raise
    
    def _check_dream_schedule(self):
        """Check if it's time to dream automatically"""
        from pathlib import Path
        from datetime import datetime, timedelta
        
        # Dream directory
        dream_dir = Path.cwd() / ".claude" / "dreams"
        dream_dir.mkdir(parents=True, exist_ok=True)
        
        # Check last dream time
        last_dream_file = dream_dir / ".last_dream"
        
        try:
            if last_dream_file.exists():
                # Read last dream time
                with open(last_dream_file, 'r', encoding='utf-8') as f:
                    last_dream_str = f.read().strip()
                
                last_dream = datetime.fromisoformat(last_dream_str)
                
                # Dream every 24 hours
                if datetime.now() - last_dream < timedelta(hours=24):
                    return
            else:
                # First time, no dream yet
                pass
            
            # Check if there are memories to dream about
            from code_gen.memory import MemorySystem
            memory_system = MemorySystem(Path.cwd())
            
            if not memory_system.memories:
                return
            
            # Run automatic dream
            console.print("\n[dim]Automatic dream scheduled...[/dim]")
            asyncio.run(self._run_dream_process(memory_system))
            
            # Update last dream time
            with open(last_dream_file, 'w', encoding='utf-8') as f:
                f.write(datetime.now().isoformat())
                
        except Exception as e:
            console.print(f"[yellow]Warning: Dream check failed: {e}[/yellow]")
    
    def _show_help(self):
        """Show help information"""
        console.print("[bold]Available Commands:[/bold]")
        console.print("  /clear    - Clear the screen")
        console.print("  /files    - Show context files")
        console.print("  /skills   - Show available skills")
        console.print("  /mcp      - Show MCP status")
        console.print("  /dream    - Run dream process to extract insights")
        console.print("  /memories - Show stored memories")
        console.print("  /security - Run security monitor")
        console.print("  /cost     - Show cost tracking")
        console.print("  /history  - Show conversation history")
        console.print("  /help     - Show this help")
        console.print("\nType 'exit' or press Ctrl+C to quit")
