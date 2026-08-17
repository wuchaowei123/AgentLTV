"""
Tree Search Node Structure
=========================
MCTS‑PUCT adapted node implementation for AgentLTV
Each node represents an executable LTV modeling pipeline.
"""

import uuid
import time
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class NodeMetrics:
    """Performance metrics for a tree search node."""
    primary_score: float = 0.0
    secondary_scores: Dict[str, float] = field(default_factory=dict)
    execution_time: Optional[float] = None
    error_count: int = 0
    auto_fixes: int = 0
    success: bool = False


@dataclass
class NodeGenealogy:
    """Track the ancestry and evolution of nodes."""
    generation: int = 0
    mutation_type: Optional[str] = None
    research_ideas_used: List[str] = field(default_factory=list)
    parent_id: Optional[str] = None
    creation_time: datetime = field(default_factory=datetime.now)


class Node:
    """
    Each node stores executable pipeline code, evaluation metrics, MCTS statistics.
    MCTS internal: visits / total_reward -> average_reward as Q‑value for PUCT.
    Real task metric: self.score for final solution ranking.
    """

    def __init__(
        self,
        code: str,
        parent: Optional['Node'] = None,
        score: float = 0.0,
        secondary_scores: Optional[Dict[str, float]] = None,
        execution_time: Optional[float] = None,
        mutation_type: Optional[str] = None,
        research_ideas_used: Optional[List[str]] = None,
        node_id: Optional[str] = None
    ):
        self.id = str(uuid.uuid4())
        self.node_id = node_id
        self.parent = parent
        self.children: List['Node'] = []

        # Pipeline code & real‑world evaluation metrics
        self.code = code
        self.metrics = NodeMetrics(
            primary_score=score,
            secondary_scores=secondary_scores or {},
            execution_time=execution_time,
            success=score > 0.0
        )

        # ===== MCTS statistics =====
        self.visits = 0
        self.total_reward = 0.0

        self.creation_time = time.time()

        generation = 0 if parent is None else parent.genealogy.generation + 1
        self.genealogy = NodeGenealogy(
            generation=generation,
            mutation_type=mutation_type,
            research_ideas_used=research_ideas_used or [],
            parent_id=parent.id if parent else None
        )

        # Important: constructor automatically attach to parent's children
        if parent:
            parent.children.append(self)

    @property
    def score(self) -> float:
        """Real evaluation score for model performance ranking."""
        return self.metrics.primary_score

    @score.setter
    def score(self, value: float):
        """Set real score, DO NOT modify MCTS total_reward."""
        self.metrics.primary_score = value
        self.metrics.success = value > 0.0

    @property
    def average_reward(self) -> float:
        """Q‑value used for PUCT selection."""
        return self.total_reward / self.visits if self.visits > 0 else 0.0

    @property
    def is_root(self) -> bool:
        return self.parent is None

    @property
    def is_leaf(self) -> bool:
        return len(self.children) == 0

    @property
    def depth(self) -> int:
        return self.genealogy.generation

    @property
    def path_to_root(self) -> List['Node']:
        path = []
        cur = self
        while cur is not None:
            path.append(cur)
            cur = cur.parent
        return path

    def add_visit(self, reward: float) -> None:
        """MCTS back‑propagation: accumulate visit and reward."""
        self.visits += 1
        self.total_reward += reward

    def update_metrics(
        self,
        score: float,
        secondary_scores: Optional[Dict[str, float]] = None,
        execution_time: Optional[float] = None,
        error_count: int = 0,
        auto_fixes: int = 0
    ) -> None:
        self.score = score
        if secondary_scores:
            self.metrics.secondary_scores.update(secondary_scores)
        if execution_time is not None:
            self.metrics.execution_time = execution_time
        self.metrics.error_count = error_count
        self.metrics.auto_fixes = auto_fixes
        self.metrics.success = score > 0.0 and error_count == 0

    def get_ancestors(self) -> List['Node']:
        ancestors = []
        cur = self.parent
        while cur is not None:
            ancestors.append(cur)
            cur = cur.parent
        return ancestors

    def get_descendants(self) -> List['Node']:
        descendants = []
        def dfs(n: "Node"):
            for c in n.children:
                descendants.append(c)
                dfs(c)
        dfs(self)
        return descendants

    def get_sibling_nodes(self) -> List['Node']:
        if self.parent is None:
            return []
        return [c for c in self.parent.children if c != self]

    def get_best_descendant(self) -> Optional['Node']:
        des = self.get_descendants()
        if not des:
            return None
        return max(des, key=lambda x: x.score)

    def get_research_ideas_lineage(self) -> List[str]:
        ideas = set()
        for n in self.path_to_root:
            ideas.update(n.genealogy.research_ideas_used)
        return list(ideas)

    def clone(self, new_code: str = None, mutation_type: str = None) -> 'Node':
        return Node(
            code=new_code or self.code,
            parent=self,
            score=0.0,
            mutation_type=mutation_type,
            research_ideas_used=self.genealogy.research_ideas_used.copy()
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "parent_id": self.parent.id if self.parent else None,
            "score": self.score,
            "secondary_scores": self.metrics.secondary_scores,
            "visits": self.visits,
            "average_reward": self.average_reward,
            "generation": self.genealogy.generation,
            "mutation_type": self.genealogy.mutation_type,
            "research_ideas_used": self.genealogy.research_ideas_used,
            "execution_time": self.metrics.execution_time,
            "error_count": self.metrics.error_count,
            "auto_fixes": self.metrics.auto_fixes,
            "success": self.metrics.success,
            "generation_time": self.genealogy.creation_time.isoformat(),
            "code_length": len(self.code),
            "is_leaf": self.is_leaf,
            "num_children": len(self.children)
        }

    def __lt__(self, other: "Node") -> bool:
        return self.score < other.score

    def __gt__(self, other: "Node") -> bool:
        return self.score > other.score

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Node):
            return False
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

    def __repr__(self):
        return f"Node(id={self.id[:8]}, score={self.score:.4f}, visits={self.visits}, gen={self.genealogy.generation})"


class NodeCollection:
    def __init__(self, nodes: Optional[List[Node]] = None):
        self.nodes = nodes or []
        self._nodes_by_id = {n.id: n for n in self.nodes}

    def add_node(self, node: Node) -> None:
        if node.id not in self._nodes_by_id:
            self.nodes.append(node)
            self._nodes_by_id[node.id] = node

    def get_node(self, node_id: str) -> Optional[Node]:
        return self._nodes_by_id.get(node_id)

    def get_best_nodes(self, n: int = 10) -> List[Node]:
        return sorted(self.nodes, key=lambda x: x.score, reverse=True)[:n]

    def get_successful_nodes(self) -> List[Node]:
        return [n for n in self.nodes if n.metrics.success]

    def get_nodes_by_generation(self, generation: int) -> List[Node]:
        return [n for n in self.nodes if n.genealogy.generation == generation]

    def get_leaf_nodes(self) -> List[Node]:
        return [n for n in self.nodes if n.is_leaf]

    def get_statistics(self) -> Dict[str, Any]:
        if not self.nodes:
            return {}
        scores = [n.score for n in self.nodes]
        success_nodes = self.get_successful_nodes()
        return {
            "total_nodes": len(self.nodes),
            "successful_nodes": len(success_nodes),
            "success_rate": len(success_nodes)/len(self.nodes),
            "best_score": max(scores),
            "worst_score": min(scores),
            "avg_score": sum(scores)/len(scores),
            "max_generation": max(n.genealogy.generation for n in self.nodes),
            "total_visits": sum(n.visits for n in self.nodes),
        }

    def __len__(self):
        return len(self.nodes)

    def __iter__(self):
        return iter(self.nodes)

    def __getitem__(self, idx: int):
        return self.nodes[idx]