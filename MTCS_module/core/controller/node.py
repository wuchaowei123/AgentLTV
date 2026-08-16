"""
Tree Search Node Structure
=========================

Data structure for representing nodes in the Universal Tree Search algorithm.
Each node represents a scientific code solution with performance metrics.
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
    Represents a single solution in the tree search space.
    
    Each node contains:
    - Generated scientific code
    - Performance metrics
    - Tree search statistics (visits, etc.)
    - Genealogy information for tracking evolution
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
        """
        Initialize a new tree search node.
        
        Args:
            code: The scientific Python code represented by this node
            parent: Parent node (None for root node)
            score: Primary performance score
            secondary_scores: Additional performance metrics
            execution_time: Time taken to execute the code
            mutation_type: Type of mutation applied to create this node
            research_ideas_used: Research ideas incorporated in this node
            node_id: Optional database node ID for tracking
        """
        # Core identifiers
        self.id = str(uuid.uuid4())
        self.node_id = node_id  # Database node ID for integration
        self.parent = parent
        self.children: List['Node'] = []
        
        # Code and performance
        self.code = code
        self.metrics = NodeMetrics(
            primary_score=score,
            secondary_scores=secondary_scores or {},
            execution_time=execution_time,
            success=score > 0.0  # Assume positive scores indicate success
        )
        
        # Tree search statistics
        self.visits = 1
        self.total_reward = score
        self.creation_time = time.time()
        
        # Genealogy tracking
        generation = 0 if parent is None else parent.genealogy.generation + 1
        self.genealogy = NodeGenealogy(
            generation=generation,
            mutation_type=mutation_type,
            research_ideas_used=research_ideas_used or [],
            parent_id=parent.id if parent else None
        )
        
        # Add to parent's children if parent exists
        if parent:
            parent.children.append(self)
    
    @property
    def score(self) -> float:
        """Primary performance score."""
        return self.metrics.primary_score
    
    @score.setter
    def score(self, value: float):
        """Set primary performance score."""
        self.metrics.primary_score = value
        self.metrics.success = value > 0.0
        self.total_reward = value * self.visits  # Update total reward
    
    @property
    def average_reward(self) -> float:
        """Average reward across all visits."""
        return self.total_reward / self.visits if self.visits > 0 else 0.0
    
    @property
    def is_root(self) -> bool:
        """Check if this is the root node."""
        return self.parent is None
    
    @property
    def is_leaf(self) -> bool:
        """Check if this is a leaf node."""
        return len(self.children) == 0
    
    @property
    def depth(self) -> int:
        """Depth of this node in the tree."""
        return self.genealogy.generation
    
    @property
    def path_to_root(self) -> List['Node']:
        """Get path from this node to the root."""
        path = []
        current = self
        while current is not None:
            path.append(current)
            current = current.parent
        return path
    
    def add_visit(self, reward: float = None) -> None:
        """
        Add a visit to this node.
        
        Args:
            reward: Optional reward value (uses current score if None)
        """
        self.visits += 1
        if reward is not None:
            self.total_reward += reward
        else:
            self.total_reward += self.score
    
    def update_metrics(
        self, 
        score: float,
        secondary_scores: Optional[Dict[str, float]] = None,
        execution_time: Optional[float] = None,
        error_count: int = 0,
        auto_fixes: int = 0
    ) -> None:
        """
        Update node performance metrics.
        
        Args:
            score: Primary performance score
            secondary_scores: Additional performance metrics
            execution_time: Time taken to execute the code
            error_count: Number of errors encountered
            auto_fixes: Number of automatic fixes applied
        """
        self.score = score
        
        if secondary_scores:
            self.metrics.secondary_scores.update(secondary_scores)
        
        if execution_time is not None:
            self.metrics.execution_time = execution_time
        
        self.metrics.error_count = error_count
        self.metrics.auto_fixes = auto_fixes
        self.metrics.success = score > 0.0 and error_count == 0
    
    def get_ancestors(self) -> List['Node']:
        """Get all ancestor nodes."""
        ancestors = []
        current = self.parent
        while current is not None:
            ancestors.append(current)
            current = current.parent
        return ancestors
    
    def get_descendants(self) -> List['Node']:
        """Get all descendant nodes."""
        descendants = []
        
        def collect_descendants(node: 'Node'):
            for child in node.children:
                descendants.append(child)
                collect_descendants(child)
        
        collect_descendants(self)
        return descendants
    
    def get_sibling_nodes(self) -> List['Node']:
        """Get sibling nodes (same parent)."""
        if self.parent is None:
            return []
        return [child for child in self.parent.children if child != self]
    
    def get_best_descendant(self) -> Optional['Node']:
        """Get the descendant with the highest score."""
        descendants = self.get_descendants()
        if not descendants:
            return None
        return max(descendants, key=lambda n: n.score)
    
    def get_research_ideas_lineage(self) -> List[str]:
        """Get all research ideas used in the lineage to this node."""
        ideas = set()
        for node in self.path_to_root:
            ideas.update(node.genealogy.research_ideas_used)
        return list(ideas)
    
    def clone(self, new_code: str = None, mutation_type: str = None) -> 'Node':
        """
        Create a child node with similar properties.
        
        Args:
            new_code: New code for the child node (uses parent's code if None)
            mutation_type: Type of mutation applied
            
        Returns:
            New child node
        """
        return Node(
            code=new_code or self.code,
            parent=self,
            score=0.0,  # Will be updated after evaluation
            mutation_type=mutation_type,
            research_ideas_used=self.genealogy.research_ideas_used.copy()
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary representation."""
        return {
            'id': self.id,
            'parent_id': self.parent.id if self.parent else None,
            'score': self.score,
            'secondary_scores': self.metrics.secondary_scores,
            'visits': self.visits,
            'average_reward': self.average_reward,
            'generation': self.genealogy.generation,
            'mutation_type': self.genealogy.mutation_type,
            'research_ideas_used': self.genealogy.research_ideas_used,
            'execution_time': self.metrics.execution_time,
            'error_count': self.metrics.error_count,
            'auto_fixes': self.metrics.auto_fixes,
            'success': self.metrics.success,
            'creation_time': self.genealogy.creation_time.isoformat(),
            'code_length': len(self.code),
            'is_leaf': self.is_leaf,
            'num_children': len(self.children)
        }
    
    def __lt__(self, other: 'Node') -> bool:
        """Compare nodes by score (for sorting)."""
        return self.score < other.score
    
    def __gt__(self, other: 'Node') -> bool:
        """Compare nodes by score (for sorting)."""
        return self.score > other.score
    
    def __eq__(self, other: 'Node') -> bool:
        """Compare nodes by ID."""
        return isinstance(other, Node) and self.id == other.id
    
    def __hash__(self) -> int:
        """Hash based on node ID."""
        return hash(self.id)
    
    def __repr__(self) -> str:
        """String representation of the node."""
        return (f"Node(id={self.id[:8]}, score={self.score:.4f}, "
                f"visits={self.visits}, gen={self.genealogy.generation})")
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        status = "✅" if self.metrics.success else "❌"
        mutation = f" ({self.genealogy.mutation_type})" if self.genealogy.mutation_type else ""
        
        return (f"{status} Node {self.id[:8]}: {self.score:.4f} "
                f"[Gen {self.genealogy.generation}, Visits {self.visits}]{mutation}")


class NodeCollection:
    """
    Collection of nodes with useful search and analysis methods.
    """
    
    def __init__(self, nodes: Optional[List[Node]] = None):
        """Initialize with optional list of nodes."""
        self.nodes = nodes or []
        self._nodes_by_id = {node.id: node for node in self.nodes}
    
    def add_node(self, node: Node) -> None:
        """Add a node to the collection."""
        if node.id not in self._nodes_by_id:
            self.nodes.append(node)
            self._nodes_by_id[node.id] = node
    
    def get_node(self, node_id: str) -> Optional[Node]:
        """Get node by ID."""
        return self._nodes_by_id.get(node_id)
    
    def get_best_nodes(self, n: int = 10) -> List[Node]:
        """Get the top N nodes by score."""
        return sorted(self.nodes, key=lambda x: x.score, reverse=True)[:n]
    
    def get_successful_nodes(self) -> List[Node]:
        """Get nodes that executed successfully."""
        return [node for node in self.nodes if node.metrics.success]
    
    def get_nodes_by_generation(self, generation: int) -> List[Node]:
        """Get all nodes from a specific generation."""
        return [node for node in self.nodes if node.genealogy.generation == generation]
    
    def get_leaf_nodes(self) -> List[Node]:
        """Get all leaf nodes."""
        return [node for node in self.nodes if node.is_leaf]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get collection statistics."""
        if not self.nodes:
            return {}
        
        scores = [node.score for node in self.nodes]
        successful_nodes = self.get_successful_nodes()
        
        return {
            'total_nodes': len(self.nodes),
            'successful_nodes': len(successful_nodes),
            'success_rate': len(successful_nodes) / len(self.nodes),
            'best_score': max(scores),
            'worst_score': min(scores),
            'average_score': sum(scores) / len(scores),
            'max_generation': max(node.genealogy.generation for node in self.nodes),
            'total_visits': sum(node.visits for node in self.nodes),
            'unique_mutations': len(set(node.genealogy.mutation_type for node in self.nodes if node.genealogy.mutation_type))
        }
    
    def __len__(self) -> int:
        """Number of nodes in collection."""
        return len(self.nodes)
    
    def __iter__(self):
        """Iterate over nodes."""
        return iter(self.nodes)
    
    def __getitem__(self, index: int) -> Node:
        """Get node by index."""
        return self.nodes[index]