"""
Claude Code CLI
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from code_gen.cli import main

if __name__ == "__main__":
    main()
