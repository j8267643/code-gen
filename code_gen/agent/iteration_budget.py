"""
Iteration Budget Manager - Inspired by Hermes Agent
Manages tool-calling iterations with budget tracking
"""
import threading
from typing import Optional


class IterationBudget:
    """
    Thread-safe iteration counter for an agent.
    
    Tracks used iterations against a maximum budget. Supports parent-child
    delegation where child agents get their own sub-budget.
    
    Example:
        budget = IterationBudget(max_total=90)
        if budget.consume():
            # Do work
        else:
            # Budget exhausted
    """
    
    def __init__(self, max_total: int = 90, parent: Optional['IterationBudget'] = None):
        """
        Initialize iteration budget.
        
        Args:
            max_total: Maximum iterations allowed (default: 90)
            parent: Parent budget for delegation (optional)
        """
        self.max_total = max_total
        self._parent = parent
        self._used = 0
        self._lock = threading.Lock()
    
    @property
    def used(self) -> int:
        """Total iterations used"""
        with self._lock:
            return self._used
    
    @property
    def remaining(self) -> int:
        """Iterations remaining"""
        with self._lock:
            return max(0, self.max_total - self._used)
    
    def consume(self, count: int = 1) -> bool:
        """
        Consume iteration budget.
        
        Args:
            count: Number of iterations to consume (default: 1)
            
        Returns:
            True if budget available and consumed, False if exhausted
        """
        with self._lock:
            if self._used + count <= self.max_total:
                self._used += count
                return True
            return False
    
    def refund(self, count: int = 1) -> None:
        """
        Refund iterations back to budget (e.g., for execute_code turns).
        
        Args:
            count: Number of iterations to refund (default: 1)
        """
        with self._lock:
            self._used = max(0, self._used - count)
    
    def create_sub_budget(self, max_iterations: int) -> 'IterationBudget':
        """
        Create a child budget for sub-agent delegation.
        
        Args:
            max_iterations: Maximum iterations for the child
            
        Returns:
            New IterationBudget with this budget as parent
        """
        return IterationBudget(max_total=max_iterations, parent=self)
    
    def get_summary(self) -> str:
        """Get budget summary string"""
        return f"{self._used}/{self.max_total} iterations used"
