"""
CLI UI Components - Inspired by Hermes Agent
Terminal UI helpers for better user experience
"""
import sys
import time
import threading
from typing import Optional, Callable


# ============================================================================
# Color System
# ============================================================================

class Colors:
    """ANSI color codes"""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"


def should_use_color() -> bool:
    """Check if terminal supports colors"""
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except:
            pass
    return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()


def colorize(text: str, *codes: str) -> str:
    """Apply color codes to text"""
    if not should_use_color():
        return text
    return "".join(codes) + text + Colors.RESET


# ============================================================================
# Print Helpers
# ============================================================================

def print_info(text: str) -> None:
    """Print dim informational message"""
    print(colorize(f"  {text}", Colors.DIM))


def print_success(text: str) -> None:
    """Print green success message with ✓ prefix"""
    print(colorize(f"✓ {text}", Colors.GREEN))


def print_warning(text: str) -> None:
    """Print yellow warning message with ⚠ prefix"""
    print(colorize(f"⚠ {text}", Colors.YELLOW))


def print_error(text: str) -> None:
    """Print red error message with ✗ prefix"""
    print(colorize(f"✗ {text}", Colors.RED))


def print_header(text: str) -> None:
    """Print bold yellow header"""
    print(colorize(f"\n  {text}", Colors.YELLOW, Colors.BOLD))


def print_tool_call(tool_name: str, preview: str = "") -> None:
    """Print tool call with style"""
    if preview:
        print(colorize(f"  🔧 {tool_name}", Colors.CYAN), colorize(preview, Colors.DIM))
    else:
        print(colorize(f"  🔧 {tool_name}", Colors.CYAN))


def print_tool_result(success: bool, message: str = "") -> None:
    """Print tool result"""
    if success:
        print(colorize(f"  ✓ Done", Colors.GREEN), end="")
    else:
        print(colorize(f"  ✗ Failed", Colors.RED), end="")
    if message:
        print(f" {colorize(message, Colors.DIM)}")
    else:
        print()


# ============================================================================
# Spinner
# ============================================================================

class Spinner:
    """Animated spinner for CLI feedback during operations"""
    
    FRAMES = {
        'dots': ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'],
        'bounce': ['⠁', '⠂', '⠄', '⡀', '⢀', '⠠', '⠐', '⠈'],
        'pulse': ['◜', '◠', '◝', '◞', '◡', '◟'],
        'moon': ['🌑', '🌒', '🌓', '🌔', '🌕', '🌖', '🌗', '🌘'],
        'brain': ['🧠', '💭', '💡', '✨', '💫', '🌟'],
    }
    
    EMOJIS = {
        'thinking': ['🤔', '🧐', '💭', '🔍', '📊'],
        'working': ['⚙️', '🔧', '🛠️', '⚡', '🔨'],
        'waiting': ['⏳', '⌛', '🕐', '🕑', '🕒'],
    }
    
    def __init__(
        self,
        message: str = "Processing...",
        spinner_type: str = 'dots',
        emoji_type: Optional[str] = None,
        print_fn: Optional[Callable[[str], None]] = None
    ):
        self.message = message
        self.frames = self.FRAMES.get(spinner_type, self.FRAMES['dots'])
        self.emojis = self.EMOJIS.get(emoji_type, []) if emoji_type else []
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.frame_idx = 0
        self.start_time: Optional[float] = None
        self.last_line_len = 0
        self._print_fn = print_fn
        self._out = sys.stdout
    
    def _write(self, text: str, end: str = '\n', flush: bool = False):
        """Write to stdout"""
        if self._print_fn is not None:
            try:
                self._print_fn(text)
            except:
                pass
            return
        try:
            self._out.write(text + end)
            if flush:
                self._out.flush()
        except (ValueError, OSError):
            pass
    
    @property
    def _is_tty(self) -> bool:
        """Check if output is a real terminal"""
        try:
            return hasattr(self._out, 'isatty') and self._out.isatty()
        except (ValueError, OSError):
            return False
    
    def _animate(self):
        """Animation loop"""
        # Non-TTY: just print once
        if not self._is_tty:
            self._write(f"  {self.message}", flush=True)
            while self.running:
                time.sleep(0.5)
            return
        
        # TTY: animate
        while self.running:
            frame = self.frames[self.frame_idx % len(self.frames)]
            
            # Add emoji if available
            if self.emojis:
                emoji = self.emojis[self.frame_idx % len(self.emojis)]
                line = f"  {frame} {emoji} {self.message}"
            else:
                line = f"  {frame} {self.message}"
            
            # Add elapsed time
            if self.start_time:
                elapsed = time.time() - self.start_time
                if elapsed > 2:  # Show after 2 seconds
                    line += f" ({elapsed:.1f}s)"
            
            # Clear previous line and write new one
            pad = max(self.last_line_len - len(line), 0)
            self._write(f"\r{line}{' ' * pad}", end='', flush=True)
            self.last_line_len = len(line)
            
            self.frame_idx += 1
            time.sleep(0.1)
    
    def start(self):
        """Start the spinner"""
        if self.running:
            return
        self.running = True
        self.start_time = time.time()
        self.thread = threading.Thread(target=self._animate, daemon=True)
        self.thread.start()
    
    def stop(self, message: Optional[str] = None):
        """Stop the spinner"""
        if not self.running:
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=0.5)
        
        # Clear the spinner line
        if self._is_tty:
            blanks = ' ' * (self.last_line_len + 5)
            self._write(f"\r{blanks}\r", end='')
        
        # Print completion message
        if message:
            self._write(f"  {message}")
        elif self.start_time:
            elapsed = time.time() - self.start_time
            self._write(f"  Done ({elapsed:.1f}s)")
    
    def update_message(self, new_message: str):
        """Update spinner message"""
        self.message = new_message
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.stop(f"Failed: {exc_val}")
        else:
            self.stop()
        return False


# ============================================================================
# Tool Preview Builder
# ============================================================================

def build_tool_preview(tool_name: str, args: dict, max_len: int = 50) -> str:
    """Build a short preview of tool call arguments"""
    if not args:
        return ""
    
    # Key arguments to show for different tools
    key_args = {
        'read_file': 'path',
        'write_file': 'path',
        'execute_command': 'command',
        'bash': 'command',
        'search_files': 'query',
        'list_directory': 'path',
        'view_directory_tree': 'path',
    }
    
    key = key_args.get(tool_name)
    if not key:
        # Find first string argument
        for k, v in args.items():
            if isinstance(v, str) and k not in ('reason', 'description'):
                key = k
                break
    
    if not key or key not in args:
        return ""
    
    value = str(args[key])
    # Truncate if too long
    if len(value) > max_len:
        value = value[:max_len - 3] + "..."
    
    return value


# ============================================================================
# Progress Display
# ============================================================================

class ProgressDisplay:
    """Display progress for multi-step operations"""
    
    def __init__(self, total: int, description: str = "Processing"):
        self.total = total
        self.current = 0
        self.description = description
    
    def update(self, n: int = 1, message: Optional[str] = None):
        """Update progress"""
        self.current = min(self.current + n, self.total)
        pct = (self.current / self.total) * 100 if self.total > 0 else 0
        
        msg = message or f"{self.current}/{self.total}"
        bar = self._render_bar(pct)
        
        print(f"\r  {self.description}: {bar} {pct:.0f}% {msg}", end='', flush=True)
        
        if self.current >= self.total:
            print()  # New line when complete
    
    def _render_bar(self, pct: float, width: int = 20) -> str:
        """Render progress bar"""
        filled = int(width * pct / 100)
        empty = width - filled
        bar = "█" * filled + "░" * empty
        return f"[{bar}]"
    
    def finish(self, message: str = "Complete"):
        """Mark as finished"""
        self.current = self.total
        self.update(0, message)
        print_success(message)


# ============================================================================
# Session Info Display
# ============================================================================

def print_session_info(
    session_id: str,
    model: str,
    project_root: str,
    iterations: Optional[str] = None
):
    """Print session information header"""
    print()
    print(colorize("═" * 60, Colors.DIM))
    print(f"  {colorize('Session:', Colors.BOLD)} {session_id[:8]}...")
    print(f"  {colorize('Model:', Colors.BOLD)} {model}")
    print(f"  {colorize('Project:', Colors.BOLD)} {project_root}")
    if iterations:
        print(f"  {colorize('Budget:', Colors.BOLD)} {iterations}")
    print(colorize("═" * 60, Colors.DIM))
    print()


def print_divider(char: str = "─", color: str = Colors.DIM):
    """Print a divider line"""
    width = min(60, shutil.get_terminal_size().columns - 4) if hasattr(shutil, 'get_terminal_size') else 60
    print(colorize(char * width, color))
