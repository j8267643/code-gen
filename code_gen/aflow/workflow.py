"""AFLOW Workflow Graph"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime


class NodeType(Enum):
    """节点类型"""
    START = "start"              # 开始节点
    END = "end"                  # 结束节点
    ACTION = "action"            # 动作节点
    CONDITION = "condition"      # 条件节点
    PARALLEL = "parallel"        # 并行节点
    LOOP = "loop"                # 循环节点
    LLM = "llm"                  # LLM 调用节点
    TOOL = "tool"                # 工具调用节点


class EdgeType(Enum):
    """边类型"""
    SEQUENTIAL = "sequential"    # 顺序执行
    CONDITIONAL = "conditional"  # 条件执行
    PARALLEL = "parallel"        # 并行执行
    LOOP = "loop"                # 循环执行


@dataclass
class WorkflowNode:
    """工作流节点"""
    name: str
    node_type: NodeType
    description: str = ""
    
    # 执行配置
    action: Optional[str] = None           # 动作名称
    config: Dict[str, Any] = field(default_factory=dict)  # 节点配置
    
    # 输入输出定义
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    
    # 元数据
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "node_type": self.node_type.value,
            "description": self.description,
            "action": self.action,
            "config": self.config,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WorkflowNode:
        return cls(
            id=data.get("id"),
            name=data["name"],
            node_type=NodeType(data["node_type"]),
            description=data.get("description", ""),
            action=data.get("action"),
            config=data.get("config", {}),
            input_schema=data.get("input_schema", {}),
            output_schema=data.get("output_schema", {}),
        )


@dataclass
class WorkflowEdge:
    """工作流边"""
    source: str          # 源节点 ID
    target: str          # 目标节点 ID
    edge_type: EdgeType = EdgeType.SEQUENTIAL
    
    # 条件配置（用于条件边）
    condition: Optional[str] = None
    condition_func: Optional[Callable] = None
    
    # 元数据
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "edge_type": self.edge_type.value,
            "condition": self.condition,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WorkflowEdge:
        return cls(
            id=data.get("id"),
            source=data["source"],
            target=data["target"],
            edge_type=EdgeType(data.get("edge_type", "sequential")),
            condition=data.get("condition"),
        )


@dataclass
class WorkflowGraph:
    """工作流图
    
    表示一个完整的工作流结构
    """
    name: str
    description: str = ""
    
    nodes: List[WorkflowNode] = field(default_factory=list)
    edges: List[WorkflowEdge] = field(default_factory=list)
    
    # 性能指标
    score: float = 0.0           # 综合评分
    success_rate: float = 0.0    # 成功率
    avg_latency: float = 0.0     # 平均延迟
    cost: float = 0.0            # 成本
    
    # 元数据
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    version: int = 1
    parent_id: Optional[str] = None  # 父工作流 ID（用于进化）
    
    def add_node(self, node: WorkflowNode) -> WorkflowNode:
        """添加节点"""
        self.nodes.append(node)
        self.updated_at = datetime.now()
        return node
    
    def add_edge(self, edge: WorkflowEdge) -> WorkflowEdge:
        """添加边"""
        self.edges.append(edge)
        self.updated_at = datetime.now()
        return edge
    
    def get_node(self, node_id: str) -> Optional[WorkflowNode]:
        """获取节点"""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None
    
    def get_node_by_name(self, name: str) -> Optional[WorkflowNode]:
        """通过名称获取节点"""
        for node in self.nodes:
            if node.name == name:
                return node
        return None
    
    def get_start_node(self) -> Optional[WorkflowNode]:
        """获取开始节点"""
        for node in self.nodes:
            if node.node_type == NodeType.START:
                return node
        return None
    
    def get_end_nodes(self) -> List[WorkflowNode]:
        """获取结束节点"""
        return [n for n in self.nodes if n.node_type == NodeType.END]
    
    def get_outgoing_edges(self, node_id: str) -> List[WorkflowEdge]:
        """获取节点的出边"""
        return [e for e in self.edges if e.source == node_id]
    
    def get_incoming_edges(self, node_id: str) -> List[WorkflowEdge]:
        """获取节点的入边"""
        return [e for e in self.edges if e.target == node_id]
    
    def get_neighbors(self, node_id: str) -> List[WorkflowNode]:
        """获取相邻节点"""
        outgoing = self.get_outgoing_edges(node_id)
        return [self.get_node(e.target) for e in outgoing if self.get_node(e.target)]
    
    def get_execution_order(self) -> List[List[str]]:
        """获取执行顺序（拓扑排序分层）"""
        # 计算入度
        in_degree = {n.id: 0 for n in self.nodes}
        for edge in self.edges:
            in_degree[edge.target] = in_degree.get(edge.target, 0) + 1
        
        # 分层执行
        layers = []
        remaining = set(n.id for n in self.nodes)
        
        while remaining:
            layer = [n_id for n_id in remaining if in_degree.get(n_id, 0) == 0]
            if not layer:
                # 存在循环
                raise ValueError("Workflow contains cycles")
            
            layers.append(layer)
            remaining -= set(layer)
            
            # 更新入度
            for n_id in layer:
                for edge in self.get_outgoing_edges(n_id):
                    in_degree[edge.target] = max(0, in_degree.get(edge.target, 0) - 1)
        
        return layers
    
    def validate(self) -> List[str]:
        """验证工作流"""
        errors = []
        
        # 检查开始节点
        start_nodes = [n for n in self.nodes if n.node_type == NodeType.START]
        if len(start_nodes) != 1:
            errors.append(f"Expected exactly 1 start node, found {len(start_nodes)}")
        
        # 检查结束节点
        end_nodes = [n for n in self.nodes if n.node_type == NodeType.END]
        if len(end_nodes) < 1:
            errors.append("Expected at least 1 end node")
        
        # 检查节点名称唯一性
        names = [n.name for n in self.nodes]
        if len(names) != len(set(names)):
            errors.append("Duplicate node names found")
        
        # 检查边引用的节点是否存在
        node_ids = {n.id for n in self.nodes}
        for edge in self.edges:
            if edge.source not in node_ids:
                errors.append(f"Edge references non-existent source node: {edge.source}")
            if edge.target not in node_ids:
                errors.append(f"Edge references non-existent target node: {edge.target}")
        
        # 检查循环
        try:
            self.get_execution_order()
        except ValueError as e:
            errors.append(str(e))
        
        return errors
    
    def clone(self, new_name: Optional[str] = None) -> WorkflowGraph:
        """克隆工作流"""
        # 创建新 ID 映射
        id_mapping = {}
        new_nodes = []
        for node in self.nodes:
            new_node = WorkflowNode(
                name=node.name,
                node_type=node.node_type,
                description=node.description,
                action=node.action,
                config=node.config.copy(),
                input_schema=node.input_schema.copy(),
                output_schema=node.output_schema.copy(),
            )
            id_mapping[node.id] = new_node.id
            new_nodes.append(new_node)
        
        # 复制边
        new_edges = []
        for edge in self.edges:
            new_edge = WorkflowEdge(
                source=id_mapping.get(edge.source, edge.source),
                target=id_mapping.get(edge.target, edge.target),
                edge_type=edge.edge_type,
                condition=edge.condition,
            )
            new_edges.append(new_edge)
        
        return WorkflowGraph(
            name=new_name or f"{self.name}_copy",
            description=self.description,
            nodes=new_nodes,
            edges=new_edges,
            parent_id=self.id,
            version=self.version + 1,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "score": self.score,
            "success_rate": self.success_rate,
            "avg_latency": self.avg_latency,
            "cost": self.cost,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
            "parent_id": self.parent_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WorkflowGraph:
        """从字典创建"""
        return cls(
            id=data.get("id"),
            name=data["name"],
            description=data.get("description", ""),
            nodes=[WorkflowNode.from_dict(n) for n in data.get("nodes", [])],
            edges=[WorkflowEdge.from_dict(e) for e in data.get("edges", [])],
            score=data.get("score", 0.0),
            success_rate=data.get("success_rate", 0.0),
            avg_latency=data.get("avg_latency", 0.0),
            cost=data.get("cost", 0.0),
            version=data.get("version", 1),
            parent_id=data.get("parent_id"),
        )


# 预定义的工作流模板

class WorkflowTemplates:
    """工作流模板"""
    
    @staticmethod
    def sequential(actions: List[str], name: str = "sequential") -> WorkflowGraph:
        """创建顺序工作流"""
        wf = WorkflowGraph(name=name, description="Sequential workflow")
        
        # 开始节点
        start = wf.add_node(WorkflowNode(
            name="start",
            node_type=NodeType.START,
            description="Start of workflow",
        ))
        
        prev_node = start
        for i, action in enumerate(actions):
            # 动作节点
            action_node = wf.add_node(WorkflowNode(
                name=f"action_{i}",
                node_type=NodeType.ACTION,
                description=f"Action: {action}",
                action=action,
            ))
            
            # 连接边
            wf.add_edge(WorkflowEdge(
                source=prev_node.id,
                target=action_node.id,
            ))
            
            prev_node = action_node
        
        # 结束节点
        end = wf.add_node(WorkflowNode(
            name="end",
            node_type=NodeType.END,
            description="End of workflow",
        ))
        wf.add_edge(WorkflowEdge(
            source=prev_node.id,
            target=end.id,
        ))
        
        return wf
    
    @staticmethod
    def parallel(actions: List[str], name: str = "parallel") -> WorkflowGraph:
        """创建并行工作流"""
        wf = WorkflowGraph(name=name, description="Parallel workflow")
        
        # 开始节点
        start = wf.add_node(WorkflowNode(
            name="start",
            node_type=NodeType.START,
        ))
        
        # 并行节点
        parallel_node = wf.add_node(WorkflowNode(
            name="parallel_split",
            node_type=NodeType.PARALLEL,
        ))
        wf.add_edge(WorkflowEdge(
            source=start.id,
            target=parallel_node.id,
        ))
        
        # 并行动作
        action_nodes = []
        for i, action in enumerate(actions):
            action_node = wf.add_node(WorkflowNode(
                name=f"action_{i}",
                node_type=NodeType.ACTION,
                action=action,
            ))
            wf.add_edge(WorkflowEdge(
                source=parallel_node.id,
                target=action_node.id,
                edge_type=EdgeType.PARALLEL,
            ))
            action_nodes.append(action_node)
        
        # 合并节点
        join_node = wf.add_node(WorkflowNode(
            name="parallel_join",
            node_type=NodeType.PARALLEL,
        ))
        for action_node in action_nodes:
            wf.add_edge(WorkflowEdge(
                source=action_node.id,
                target=join_node.id,
            ))
        
        # 结束节点
        end = wf.add_node(WorkflowNode(
            name="end",
            node_type=NodeType.END,
        ))
        wf.add_edge(WorkflowEdge(
            source=join_node.id,
            target=end.id,
        ))
        
        return wf
    
    @staticmethod
    def conditional(
        condition: str,
        true_action: str,
        false_action: str,
        name: str = "conditional",
    ) -> WorkflowGraph:
        """创建条件工作流"""
        wf = WorkflowGraph(name=name, description="Conditional workflow")
        
        # 开始节点
        start = wf.add_node(WorkflowNode(
            name="start",
            node_type=NodeType.START,
        ))
        
        # 条件节点
        condition_node = wf.add_node(WorkflowNode(
            name="condition",
            node_type=NodeType.CONDITION,
            description=condition,
        ))
        wf.add_edge(WorkflowEdge(
            source=start.id,
            target=condition_node.id,
        ))
        
        # True 分支
        true_node = wf.add_node(WorkflowNode(
            name="true_action",
            node_type=NodeType.ACTION,
            action=true_action,
        ))
        wf.add_edge(WorkflowEdge(
            source=condition_node.id,
            target=true_node.id,
            edge_type=EdgeType.CONDITIONAL,
            condition="true",
        ))
        
        # False 分支
        false_node = wf.add_node(WorkflowNode(
            name="false_action",
            node_type=NodeType.ACTION,
            action=false_action,
        ))
        wf.add_edge(WorkflowEdge(
            source=condition_node.id,
            target=false_node.id,
            edge_type=EdgeType.CONDITIONAL,
            condition="false",
        ))
        
        # 结束节点
        end = wf.add_node(WorkflowNode(
            name="end",
            node_type=NodeType.END,
        ))
        wf.add_edge(WorkflowEdge(
            source=true_node.id,
            target=end.id,
        ))
        wf.add_edge(WorkflowEdge(
            source=false_node.id,
            target=end.id,
        ))
        
        return wf
