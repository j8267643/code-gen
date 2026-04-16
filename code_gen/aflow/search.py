"""AFLOW Workflow Search Space"""

from typing import List, Dict, Any, Optional, Callable
import random
import copy

from .workflow import WorkflowGraph, WorkflowNode, WorkflowEdge, NodeType, EdgeType


class WorkflowSearchSpace:
    """工作流搜索空间
    
    定义可能的节点、边和配置选项
    """
    
    def __init__(self):
        # 可用动作
        self.available_actions: List[str] = [
            "analyze_requirements",
            "design_architecture",
            "write_code",
            "review_code",
            "write_tests",
            "run_tests",
            "debug_error",
            "refactor_code",
            "optimize_code",
            "generate_docs",
        ]
        
        # 可用节点类型
        self.node_types: List[NodeType] = [
            NodeType.ACTION,
            NodeType.CONDITION,
            NodeType.PARALLEL,
            NodeType.LLM,
            NodeType.TOOL,
        ]
        
        # 可用边类型
        self.edge_types: List[EdgeType] = [
            EdgeType.SEQUENTIAL,
            EdgeType.CONDITIONAL,
            EdgeType.PARALLEL,
        ]
        
        # 条件模板
        self.condition_templates: List[str] = [
            "success",
            "failure",
            "needs_review",
            "has_errors",
            "test_passed",
            "complexity_high",
        ]
    
    def sample_action(self) -> str:
        """采样动作"""
        return random.choice(self.available_actions)
    
    def sample_node_type(self) -> NodeType:
        """采样节点类型"""
        return random.choice(self.node_types)
    
    def sample_edge_type(self) -> EdgeType:
        """采样边类型"""
        return random.choice(self.edge_types)
    
    def sample_condition(self) -> str:
        """采样条件"""
        return random.choice(self.condition_templates)
    
    def create_random_workflow(
        self,
        name: str = "random",
        min_nodes: int = 3,
        max_nodes: int = 10,
    ) -> WorkflowGraph:
        """创建随机工作流"""
        wf = WorkflowGraph(name=name, description="Randomly generated workflow")
        
        # 开始节点
        start = wf.add_node(WorkflowNode(
            name="start",
            node_type=NodeType.START,
        ))
        
        # 随机节点数
        num_nodes = random.randint(min_nodes, max_nodes)
        
        # 创建节点
        nodes = [start]
        for i in range(num_nodes):
            node_type = self.sample_node_type()
            
            if node_type == NodeType.ACTION:
                node = wf.add_node(WorkflowNode(
                    name=f"node_{i}",
                    node_type=node_type,
                    action=self.sample_action(),
                ))
            elif node_type == NodeType.CONDITION:
                node = wf.add_node(WorkflowNode(
                    name=f"condition_{i}",
                    node_type=node_type,
                    description=self.sample_condition(),
                ))
            else:
                node = wf.add_node(WorkflowNode(
                    name=f"node_{i}",
                    node_type=node_type,
                ))
            
            nodes.append(node)
        
        # 结束节点
        end = wf.add_node(WorkflowNode(
            name="end",
            node_type=NodeType.END,
        ))
        nodes.append(end)
        
        # 创建边（确保连通性）
        for i in range(len(nodes) - 1):
            # 每个节点至少连接到下一个
            wf.add_edge(WorkflowEdge(
                source=nodes[i].id,
                target=nodes[i + 1].id,
                edge_type=EdgeType.SEQUENTIAL,
            ))
            
            # 随机添加额外连接
            if random.random() < 0.3 and i < len(nodes) - 2:
                target_idx = random.randint(i + 2, len(nodes) - 1)
                edge_type = self.sample_edge_type()
                condition = self.sample_condition() if edge_type == EdgeType.CONDITIONAL else None
                
                wf.add_edge(WorkflowEdge(
                    source=nodes[i].id,
                    target=nodes[target_idx].id,
                    edge_type=edge_type,
                    condition=condition,
                ))
        
        return wf


class WorkflowSearcher:
    """工作流搜索器
    
    使用搜索算法找到最优工作流
    """
    
    def __init__(
        self,
        search_space: WorkflowSearchSpace,
        evaluator: Any,  # WorkflowEvaluator
        population_size: int = 20,
        num_generations: int = 10,
        mutation_rate: float = 0.3,
        crossover_rate: float = 0.5,
    ):
        self.search_space = search_space
        self.evaluator = evaluator
        self.population_size = population_size
        self.num_generations = num_generations
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
    
    async def search(
        self,
        initial_workflows: Optional[List[WorkflowGraph]] = None,
    ) -> WorkflowGraph:
        """搜索最优工作流
        
        使用遗传算法进化工作流
        """
        # 初始化种群
        if initial_workflows:
            population = initial_workflows[:self.population_size]
        else:
            population = [
                self.search_space.create_random_workflow(f"gen0_{i}")
                for i in range(self.population_size)
            ]
        
        # 补充种群
        while len(population) < self.population_size:
            population.append(self.search_space.create_random_workflow(f"gen0_{len(population)}"))
        
        best_workflow = None
        best_score = 0.0
        
        for generation in range(self.num_generations):
            # 评估种群
            results = []
            for wf in population:
                try:
                    result = await self.evaluator.evaluate(wf)
                    results.append((wf, result))
                    
                    if result.score > best_score:
                        best_score = result.score
                        best_workflow = wf
                except Exception as e:
                    print(f"Evaluation failed for {wf.name}: {e}")
            
            if not results:
                continue
            
            # 选择（轮盘赌）
            selected = self._select(results)
            
            # 交叉
            offspring = []
            for i in range(0, len(selected) - 1, 2):
                if random.random() < self.crossover_rate:
                    child1, child2 = self._crossover(selected[i], selected[i + 1])
                    offspring.extend([child1, child2])
                else:
                    offspring.extend([selected[i], selected[i + 1]])
            
            # 变异
            for i in range(len(offspring)):
                if random.random() < self.mutation_rate:
                    offspring[i] = self._mutate(offspring[i])
            
            # 新一代
            population = offspring[:self.population_size]
            
            print(f"Generation {generation + 1}: Best score = {best_score:.4f}")
        
        return best_workflow or population[0]
    
    def _select(
        self,
        evaluated: List[tuple],
    ) -> List[WorkflowGraph]:
        """选择（轮盘赌选择）"""
        # 按评分排序
        evaluated.sort(key=lambda x: x[1].score, reverse=True)
        
        # 保留前 50%
        keep_count = len(evaluated) // 2
        return [x[0] for x in evaluated[:keep_count]]
    
    def _crossover(
        self,
        parent1: WorkflowGraph,
        parent2: WorkflowGraph,
    ) -> tuple:
        """交叉"""
        # 简化实现：随机交换子图
        child1 = parent1.clone(f"child_{random.randint(1000, 9999)}")
        child2 = parent2.clone(f"child_{random.randint(1000, 9999)}")
        
        # 随机选择交叉点
        if len(child1.nodes) > 3 and len(child2.nodes) > 3:
            # 交换部分节点
            idx1 = random.randint(1, len(child1.nodes) - 2)
            idx2 = random.randint(1, len(child2.nodes) - 2)
            
            # 复制节点动作
            child1.nodes[idx1].action = child2.nodes[idx2].action
            child1.nodes[idx1].node_type = child2.nodes[idx2].node_type
            
            child2.nodes[idx2].action = parent1.nodes[idx1].action
            child2.nodes[idx2].node_type = parent1.nodes[idx1].node_type
        
        return child1, child2
    
    def _mutate(self, workflow: WorkflowGraph) -> WorkflowGraph:
        """变异"""
        mutated = workflow.clone(f"mutated_{random.randint(1000, 9999)}")
        
        mutation_type = random.choice([
            "add_node",
            "remove_node",
            "change_action",
            "change_edge",
        ])
        
        if mutation_type == "add_node" and len(mutated.nodes) < 15:
            # 添加随机节点
            node_type = self.search_space.sample_node_type()
            new_node = WorkflowNode(
                name=f"mutated_node_{random.randint(1000, 9999)}",
                node_type=node_type,
                action=self.search_space.sample_action() if node_type == NodeType.ACTION else None,
            )
            mutated.add_node(new_node)
            
            # 连接到随机节点
            if len(mutated.nodes) > 2:
                source = random.choice([n for n in mutated.nodes if n.id != new_node.id])
                mutated.add_edge(WorkflowEdge(
                    source=source.id,
                    target=new_node.id,
                ))
        
        elif mutation_type == "remove_node" and len(mutated.nodes) > 4:
            # 移除随机节点（保留开始和结束）
            removable = [n for n in mutated.nodes if n.node_type not in [NodeType.START, NodeType.END]]
            if removable:
                to_remove = random.choice(removable)
                mutated.nodes = [n for n in mutated.nodes if n.id != to_remove.id]
                mutated.edges = [e for e in mutated.edges if e.source != to_remove.id and e.target != to_remove.id]
        
        elif mutation_type == "change_action":
            # 改变随机节点的动作
            action_nodes = [n for n in mutated.nodes if n.node_type == NodeType.ACTION]
            if action_nodes:
                node = random.choice(action_nodes)
                node.action = self.search_space.sample_action()
        
        elif mutation_type == "change_edge":
            # 改变随机边的类型
            if mutated.edges:
                edge = random.choice(mutated.edges)
                edge.edge_type = self.search_space.sample_edge_type()
        
        return mutated


class MCTSSearcher(WorkflowSearcher):
    """MCTS 搜索器
    
    使用蒙特卡洛树搜索优化工作流
    """
    
    def __init__(
        self,
        search_space: WorkflowSearchSpace,
        evaluator: Any,
        num_simulations: int = 100,
        exploration_weight: float = 1.414,
    ):
        super().__init__(search_space, evaluator)
        self.num_simulations = num_simulations
        self.exploration_weight = exploration_weight
    
    async def search(
        self,
        initial_workflows: Optional[List[WorkflowGraph]] = None,
    ) -> WorkflowGraph:
        """使用 MCTS 搜索"""
        # 简化实现：使用随机搜索 + 评估
        # 实际实现需要完整的 MCTS 树
        
        best_workflow = None
        best_score = 0.0
        
        for i in range(self.num_simulations):
            # 生成随机工作流
            wf = self.search_space.create_random_workflow(f"mcts_{i}")
            
            # 评估
            try:
                result = await self.evaluator.evaluate(wf)
                if result.score > best_score:
                    best_score = result.score
                    best_workflow = wf
            except Exception as e:
                print(f"Simulation {i} failed: {e}")
        
        return best_workflow or self.search_space.create_random_workflow("default")
