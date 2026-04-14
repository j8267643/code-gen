"""
Budget Manager - 预算管理和成本追踪

基于 GSD-2 的预算管理设计，用于：
1. 设置和管理预算限制
2. 追踪 API 调用成本
3. 预警和告警
4. 成本报告和分析
5. 预算超支保护
"""
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import json
import asyncio
from collections import defaultdict

from .utils import atomic_write_json


class BudgetPeriod(str, Enum):
    """预算周期"""
    SESSION = "session"  # 会话级别
    DAILY = "daily"      # 每日
    WEEKLY = "weekly"    # 每周
    MONTHLY = "monthly"  # 每月
    TOTAL = "total"      # 总计


class AlertLevel(str, Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class CostType(str, Enum):
    """成本类型"""
    API_CALL = "api_call"
    TOKEN_USAGE = "token_usage"
    TOOL_EXECUTION = "tool_execution"
    STORAGE = "storage"
    COMPUTE = "compute"
    EXTERNAL_SERVICE = "external_service"


@dataclass
class CostRecord:
    """成本记录"""
    record_id: str
    cost_type: str
    amount: float
    currency: str = "USD"
    description: str = ""
    agent_id: str = ""
    session_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CostRecord":
        return cls(**data)


@dataclass
class BudgetLimit:
    """预算限制"""
    period: str
    max_amount: float
    currency: str = "USD"
    alert_thresholds: List[float] = field(default_factory=lambda: [0.5, 0.8, 0.95])
    # 阈值：50%、80%、95%
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BudgetLimit":
        return cls(**data)


@dataclass
class BudgetAlert:
    """预算告警"""
    alert_id: str
    level: str
    message: str
    current_usage: float
    budget_limit: float
    percentage: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    acknowledged: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BudgetReport:
    """预算报告"""
    period: str
    total_budget: float
    total_spent: float
    remaining: float
    usage_percentage: float
    cost_breakdown: Dict[str, float] = field(default_factory=dict)
    top_expenses: List[Dict[str, Any]] = field(default_factory=list)
    alerts_triggered: int = 0
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BudgetManager:
    """
    预算管理器
    
    管理预算限制、追踪成本、触发告警
    """
    
    def __init__(
        self,
        storage_path: Optional[Path] = None,
        currency: str = "USD",
        enable_persistence: bool = True
    ):
        self.storage_path = storage_path or Path(".agent/budget")
        self.currency = currency
        self.enable_persistence = enable_persistence
        
        if self.enable_persistence:
            self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 预算限制
        self._budgets: Dict[str, BudgetLimit] = {}
        
        # 成本记录
        self._costs: List[CostRecord] = []
        
        # 告警历史
        self._alerts: List[BudgetAlert] = []
        
        # 回调
        self._on_alert: List[Callable[[BudgetAlert], None]] = []
        self._on_budget_exceeded: List[Callable[[str, float, float], None]] = []
        
        # 统计缓存
        self._stats_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_valid = False
    
    def set_budget(
        self,
        period: Union[BudgetPeriod, str],
        max_amount: float,
        alert_thresholds: Optional[List[float]] = None
    ):
        """
        设置预算限制
        
        Args:
            period: 预算周期
            max_amount: 最大金额
            alert_thresholds: 告警阈值列表（如 [0.5, 0.8, 0.95]）
        """
        period_str = period.value if isinstance(period, BudgetPeriod) else period
        
        self._budgets[period_str] = BudgetLimit(
            period=period_str,
            max_amount=max_amount,
            currency=self.currency,
            alert_thresholds=alert_thresholds or [0.5, 0.8, 0.95]
        )
        
        self._cache_valid = False
        
        if self.enable_persistence:
            self._persist_budgets()
        
        print(f"💰 预算已设置 [{period_str}]: {max_amount} {self.currency}")
    
    def record_cost(
        self,
        cost_type: Union[CostType, str],
        amount: float,
        description: str = "",
        agent_id: str = "",
        session_id: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> CostRecord:
        """
        记录成本
        
        Args:
            cost_type: 成本类型
            amount: 金额
            description: 描述
            agent_id: Agent ID
            session_id: 会话ID
            metadata: 元数据
        
        Returns:
            CostRecord 对象
        """
        cost_type_str = cost_type.value if isinstance(cost_type, CostType) else cost_type
        
        record = CostRecord(
            record_id=self._generate_record_id(),
            cost_type=cost_type_str,
            amount=amount,
            currency=self.currency,
            description=description,
            agent_id=agent_id,
            session_id=session_id,
            metadata=metadata or {}
        )
        
        self._costs.append(record)
        self._cache_valid = False
        
        # 检查预算
        self._check_budgets()
        
        # 持久化
        if self.enable_persistence:
            self._persist_cost(record)
        
        return record
    
    def _generate_record_id(self) -> str:
        """生成记录ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        import hashlib
        hash_suffix = hashlib.md5(
            str(datetime.now().timestamp()).encode()
        ).hexdigest()[:6]
        return f"cost_{timestamp}_{hash_suffix}"
    
    def _generate_alert_id(self) -> str:
        """生成告警ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        import hashlib
        hash_suffix = hashlib.md5(
            str(datetime.now().timestamp()).encode()
        ).hexdigest()[:4]
        return f"alert_{timestamp}_{hash_suffix}"
    
    def _check_budgets(self):
        """检查所有预算限制"""
        for period, budget in self._budgets.items():
            spent = self._get_spent_for_period(period)
            percentage = spent / budget.max_amount if budget.max_amount > 0 else 0
            
            # 检查是否超过阈值
            for threshold in sorted(budget.alert_thresholds, reverse=True):
                if percentage >= threshold:
                    self._trigger_alert(
                        period=period,
                        level=self._get_alert_level(threshold, percentage),
                        current_usage=spent,
                        budget_limit=budget.max_amount,
                        percentage=percentage
                    )
                    break
            
            # 检查是否超过预算
            if spent > budget.max_amount:
                for callback in self._on_budget_exceeded:
                    try:
                        callback(period, spent, budget.max_amount)
                    except:
                        pass
    
    def _get_alert_level(self, threshold: float, actual: float) -> str:
        """根据阈值确定告警级别"""
        if actual >= 1.0:
            return AlertLevel.CRITICAL.value
        elif actual >= 0.9 or threshold >= 0.9:
            return AlertLevel.CRITICAL.value
        elif actual >= 0.7 or threshold >= 0.7:
            return AlertLevel.WARNING.value
        else:
            return AlertLevel.INFO.value
    
    def _trigger_alert(
        self,
        period: str,
        level: str,
        current_usage: float,
        budget_limit: float,
        percentage: float
    ):
        """触发告警"""
        # 检查是否已经触发过相同级别的告警
        recent_alerts = [
            a for a in self._alerts
            if a.period == period and a.level == level
            and datetime.now() - datetime.fromisoformat(a.timestamp) < timedelta(hours=1)
        ]
        
        if recent_alerts:
            return  # 避免重复告警
        
        alert = BudgetAlert(
            alert_id=self._generate_alert_id(),
            level=level,
            message=f"预算使用达到 {percentage*100:.1f}% [{period}]: {current_usage:.2f} / {budget_limit:.2f} {self.currency}",
            current_usage=current_usage,
            budget_limit=budget_limit,
            percentage=percentage
        )
        
        self._alerts.append(alert)
        
        # 触发回调
        for callback in self._on_alert:
            try:
                callback(alert)
            except:
                pass
        
        # 打印告警
        emoji = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}.get(level, "ℹ️")
        print(f"{emoji} 预算告警: {alert.message}")
    
    def _get_spent_for_period(self, period: str) -> float:
        """获取指定周期的总支出"""
        now = datetime.now()
        
        if period == BudgetPeriod.SESSION.value:
            # 会话级别需要外部传入 session_id
            return sum(
                c.amount for c in self._costs
                if c.session_id  # 简化处理，实际应该按 session 过滤
            )
        
        elif period == BudgetPeriod.DAILY.value:
            today = now.date()
            return sum(
                c.amount for c in self._costs
                if datetime.fromisoformat(c.timestamp).date() == today
            )
        
        elif period == BudgetPeriod.WEEKLY.value:
            week_start = now - timedelta(days=now.weekday())
            return sum(
                c.amount for c in self._costs
                if datetime.fromisoformat(c.timestamp) >= week_start
            )
        
        elif period == BudgetPeriod.MONTHLY.value:
            month_start = now.replace(day=1)
            return sum(
                c.amount for c in self._costs
                if datetime.fromisoformat(c.timestamp) >= month_start
            )
        
        else:  # TOTAL
            return sum(c.amount for c in self._costs)
    
    def get_usage(self, period: str) -> Dict[str, Any]:
        """获取预算使用情况"""
        budget = self._budgets.get(period)
        if not budget:
            return {"error": f"未设置预算: {period}"}
        
        spent = self._get_spent_for_period(period)
        remaining = budget.max_amount - spent
        percentage = (spent / budget.max_amount * 100) if budget.max_amount > 0 else 0
        
        return {
            "period": period,
            "budget": budget.max_amount,
            "spent": spent,
            "remaining": remaining,
            "percentage": percentage,
            "currency": self.currency,
            "is_exceeded": spent > budget.max_amount
        }
    
    def get_all_usage(self) -> Dict[str, Dict[str, Any]]:
        """获取所有预算的使用情况"""
        return {
            period: self.get_usage(period)
            for period in self._budgets.keys()
        }
    
    def get_cost_breakdown(self, period: str = "total") -> Dict[str, float]:
        """获取成本明细"""
        costs = self._get_costs_for_period(period)
        
        breakdown = defaultdict(float)
        for cost in costs:
            breakdown[cost.cost_type] += cost.amount
        
        return dict(breakdown)
    
    def _get_costs_for_period(self, period: str) -> List[CostRecord]:
        """获取指定周期的成本记录"""
        now = datetime.now()
        
        if period == BudgetPeriod.DAILY.value:
            today = now.date()
            return [
                c for c in self._costs
                if datetime.fromisoformat(c.timestamp).date() == today
            ]
        
        elif period == BudgetPeriod.WEEKLY.value:
            week_start = now - timedelta(days=now.weekday())
            return [
                c for c in self._costs
                if datetime.fromisoformat(c.timestamp) >= week_start
            ]
        
        elif period == BudgetPeriod.MONTHLY.value:
            month_start = now.replace(day=1)
            return [
                c for c in self._costs
                if datetime.fromisoformat(c.timestamp) >= month_start
            ]
        
        return self._costs
    
    def get_top_expenses(self, period: str = "total", limit: int = 10) -> List[Dict[str, Any]]:
        """获取最大支出项"""
        costs = self._get_costs_for_period(period)
        sorted_costs = sorted(costs, key=lambda c: c.amount, reverse=True)
        
        return [
            {
                "record_id": c.record_id,
                "cost_type": c.cost_type,
                "amount": c.amount,
                "description": c.description,
                "timestamp": c.timestamp
            }
            for c in sorted_costs[:limit]
        ]
    
    def generate_report(self, period: str = "total") -> BudgetReport:
        """生成预算报告"""
        usage = self.get_usage(period)
        
        return BudgetReport(
            period=period,
            total_budget=usage.get("budget", 0),
            total_spent=usage.get("spent", 0),
            remaining=usage.get("remaining", 0),
            usage_percentage=usage.get("percentage", 0),
            cost_breakdown=self.get_cost_breakdown(period),
            top_expenses=self.get_top_expenses(period),
            alerts_triggered=len([
                a for a in self._alerts
                if datetime.fromisoformat(a.timestamp).date() == datetime.now().date()
            ])
        )
    
    def can_execute(self, estimated_cost: float, period: str = "total") -> bool:
        """
        检查是否可以执行（预算是否充足）
        
        Args:
            estimated_cost: 预估成本
            period: 预算周期
        
        Returns:
            是否可以执行
        """
        budget = self._budgets.get(period)
        if not budget:
            return True  # 没有设置预算，默认允许
        
        spent = self._get_spent_for_period(period)
        return (spent + estimated_cost) <= budget.max_amount
    
    def on_alert(self, callback: Callable[[BudgetAlert], None]):
        """注册告警回调"""
        self._on_alert.append(callback)
    
    def on_budget_exceeded(self, callback: Callable[[str, float, float], None]):
        """注册预算超支回调"""
        self._on_budget_exceeded.append(callback)
    
    def acknowledge_alert(self, alert_id: str):
        """确认告警"""
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                break
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """获取未确认的活动告警"""
        return [
            alert.to_dict()
            for alert in self._alerts
            if not alert.acknowledged
        ]
    
    def _persist_budgets(self):
        """持久化预算设置"""
        file_path = self.storage_path / "budgets.json"
        data = {
            period: budget.to_dict()
            for period, budget in self._budgets.items()
        }
        atomic_write_json(str(file_path), data)
    
    def _persist_cost(self, record: CostRecord):
        """持久化成本记录"""
        file_path = self.storage_path / f"cost_{record.record_id}.json"
        atomic_write_json(str(file_path), record.to_dict())
    
    def export_report(self, file_path: Optional[str] = None) -> str:
        """导出完整报告"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "currency": self.currency,
            "budgets": {
                period: self.get_usage(period)
                for period in self._budgets.keys()
            },
            "cost_summary": {
                "total_records": len(self._costs),
                "total_spent": sum(c.amount for c in self._costs),
                "by_type": self.get_cost_breakdown()
            },
            "alerts": {
                "total": len(self._alerts),
                "active": len(self.get_active_alerts())
            }
        }
        
        if file_path:
            atomic_write_json(file_path, report)
            return file_path
        
        return json.dumps(report, indent=2, ensure_ascii=False)


# 全局预算管理器实例
_budget_manager: Optional[BudgetManager] = None


def get_budget_manager(
    storage_path: Optional[Path] = None,
    **kwargs
) -> BudgetManager:
    """
    获取或创建全局预算管理器
    
    Args:
        storage_path: 存储路径
        **kwargs: 传递给 BudgetManager 的参数
    
    Returns:
        BudgetManager 实例
    """
    global _budget_manager
    
    if _budget_manager is None:
        _budget_manager = BudgetManager(storage_path=storage_path, **kwargs)
    
    return _budget_manager