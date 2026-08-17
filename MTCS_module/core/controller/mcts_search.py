"""
Universal Tree Search Algorithm
==============================

Implements PUCT (Polynomial Upper Confidence Tree) algorithm for 
automated scientific software discovery. Works across any domain
with configurable evaluation metrics.
Modified: MCTS‑PUCT path‑from‑root‑to‑leaf selection, compatible with revised Node (visits initial=0, average_reward as Q‑value)
"""

import math
import time
import random
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass
import numpy as np

from .node1 import Node, NodeCollection, NodeMetrics
from ..task_manager import TaskConfiguration
from ..llm_worker import UniversalLLMWorker, LLMResponse


@dataclass
class SearchConfiguration:
    """Configuration for the tree search algorithm."""
    c_puct: float = 1.5  # PUCT exploration parameter
    max_iterations: int = 50
    max_depth: int = 10
    temperature: float = 0.7  # For LLM generation
    early_stopping_patience: int = 999999  # Disabled - search all iterations
    parallel_workers: int = 1  # Future: parallel evaluation
    random_seed: Optional[int] = None

    # NEW: Adaptive C‑PUCT settings
    use_adaptive_c_puct: bool = True  # Enable adaptive C‑PUCT
    c_puct_early: float = 2.5  # Early phase (0‑20% progress)
    c_puct_mid: float = 1.5    # Mid phase (20‑70% progress)
    c_puct_late: float = 0.8   # Late phase (70‑100% progress)

    # Score improvement thresholds
    min_improvement_threshold: float = 0.001
    significant_improvement_threshold: float = 0.05


@dataclass
class SearchStats:
    """Statistics tracking for the search process."""
    total_iterations: int = 0
    successful_evaluations: int = 0
    failed_evaluations: int = 0
    best_score_history: List[float] = None
    iteration_times: List[float] = None
    llm_call_count: int = 0
    auto_fix_count: int = 0

    def __post_init__(self):
        if self.best_score_history is None:
            self.best_score_history = []
        if self.iteration_times is None:
            self.iteration_times = []


class UniversalTreeSearch:
    """
    Universal Tree Search for automated scientific software discovery.

    Uses PUCT algorithm to balance exploration vs exploitation while
    generating increasingly better scientific code solutions.
    Revised: Standard MCTS selection: traverse root down to leaf node.
    """

    def __init__(
        self,
        task_config: TaskConfiguration,
        evaluator: Callable[[str], Dict[str, Any]],
        llm_worker: Optional[UniversalLLMWorker] = None,
        search_config: Optional[SearchConfiguration] = None
    ):
        """
        Initialize the Universal Tree Search.

        Args:
            task_config: Configuration for the scientific task
            evaluator: Function to evaluate code and return metrics
            llm_worker: LLM worker for code generation
            search_config: Search algorithm configuration
        """
        self.task_config = task_config
        self.evaluator = evaluator
        self.llm_worker = llm_worker or UniversalLLMWorker()
        self.config = search_config or SearchConfiguration()

        # Initialize search state
        self.nodes = NodeCollection()
        self.root: Optional[Node] = None
        self.best_node: Optional[Node] = None
        self.stats = SearchStats()
        self.current_iteration = 0  # Track current iteration for adaptive C‑PUCT

        # Set random seed for reproducibility
        if self.config.random_seed is not None:
            random.seed(self.config.random_seed)
            np.random.seed(self.config.random_seed)

        # Initialize root node
        self._initialize_root()

    def get_adaptive_c_puct(self) -> float:
        """
        Get adaptive C‑PUCT value based on search progress.

        Adapts exploration/exploitation balance throughout search:
        - Early phase (0‑20%): High exploration (C = 2.5)
        - Mid phase (20‑70%): Balanced (C = 1.5)
        - Late phase (70‑100%): High exploitation (C = 0.8)

        Returns:
            Adaptive C‑PUCT value
        """
        if not self.config.use_adaptive_c_puct:
            return self.config.c_puct  # Use fixed C‑PUCT if adaptive disabled

        # Calculate progress (0.0 to 1.0)
        progress = self.current_iteration / max(self.config.max_iterations, 1)

        if progress < 0.2:
            # Early phase: High exploration
            c = self.config.c_puct_early
        elif progress < 0.7:
            # Mid phase: Balanced
            c = self.config.c_puct_mid
        else:
            # Late phase: High exploitation (gradually decrease)
            # Interpolate from c_puct_mid to c_puct_late
            late_progress = (progress - 0.7) / 0.3  # 0.0 to 1.0 within late phase
            c = self.config.c_puct_mid * (1 - late_progress) + self.config.c_puct_late * late_progress

        return c

    def _initialize_root(self) -> None:
        """Initialize the root node with basic starting code."""
        print("🌱 Initializing root node...")

        # Generate initial code
        task_description = self.task_config.create_prompt_context(include_research_ideas=True)

        # Extract embedding model from code requirements if specified
        embedding_model = None
        if hasattr(self.task_config, 'code_requirements') and self.task_config.code_requirements:
            embedding_model = self.task_config.code_requirements.get('embedding_model')

        response = self.llm_worker.generate_initial_code(
            task_description=task_description,
            domain=self.task_config.domain,
            research_ideas=self.task_config.research_ideas,
            data_files=self.task_config.data_files,
            embedding_model=embedding_model
        )

        self.stats.llm_call_count += 1

        if not response.success or not response.code:
            # Fallback to simple initial code
            response.code = self._get_fallback_initial_code()
            print("⚠️ Using fallback initial code due to LLM failure")

        # Evaluate initial code
        print("📊 Evaluating initial code...")
        evaluation_result = self.evaluator(response.code)

        # Create root node
        self.root = Node(
            code=response.code,
            parent=None,
            score=evaluation_result.get('score', 0.0),
            secondary_scores=evaluation_result.get('secondary_scores', {}),
            execution_time=evaluation_result.get('execution_time'),
            mutation_type="initial_generation"
        )

        print(f"Root node id: {self.root.node_id}")

        # Update metrics based on evaluation
        if 'error_count' in evaluation_result:
            self.root.metrics.error_count = evaluation_result['error_count']
        if 'auto_fixes' in evaluation_result:
            self.root.metrics.auto_fixes = evaluation_result['auto_fixes']
            self.stats.auto_fix_count += evaluation_result['auto_fixes']

        self.root.metrics.success = evaluation_result.get('success', True)

        # Track statistics
        if self.root.metrics.success:
            self.stats.successful_evaluations += 1
        else:
            self.stats.failed_evaluations += 1

        # Set as best node
        self.best_node = self.root
        self.nodes.add_node(self.root)

        print(f"✅ Root node created with score: {self.root.score:.4f}")
        if self.root.metrics.auto_fixes > 0:
            print(f"🔧 Applied {self.root.metrics.auto_fixes} automatic fixes")

    def _get_fallback_initial_code(self) -> str:
        """Get fallback initial code when LLM fails."""
        # This is a basic template that should work for many ML tasks
        return """
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import cross_val_score
import warnings
warnings.filterwarnings('ignore')

# Load data (assumes train_df and val_df are available)
try:
    # Get feature columns (exclude target and ID columns)
    feature_cols = [col for col in train_df.columns 
                   if col not in ['Machine failure', 'UDI', 'Product ID', 'TWF', 'HDF', 'PWF', 'OSF', 'RNF', 'Failure Type']]

    X_train = train_df[feature_cols].copy()
    y_train = train_df['Machine failure'].copy()
    X_val = val_df[feature_cols].copy()

    # Handle categorical variables
    for col in X_train.columns:
        if X_train[col].dtype == 'object':
            le = LabelEncoder()
            X_train[col] = le.fit_transform(X_train[col].astype(str))
            X_val[col] = le.transform(X_val[col].astype(str))

    # Basic preprocessing
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)

    # Simple model
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train_scaled, y_train)

    # Predictions
    val_predictions = pd.Series(model.predict_proba(X_val_scaled)[:, 1], index=X_val.index)

except Exception as e:
    # Emergency fallback - random predictions
    val_predictions = pd.Series(np.random.rand(len(val_df)), index=val_df.index)
"""

    def _puct_value(self, child: Node, parent_visits: int, c_puct: float) -> float:
        """Standard PUCT: Q(a) + c * sqrt( log(N_parent) / N_child )"""
        q_val = child.average_reward
        if child.visits == 0:
            return float("inf")
        explore_term = c_puct * math.sqrt(math.log(parent_visits) / child.visits)
        return q_val + explore_term

    def select_node(self) -> Node:
        """
        Standard MCTS Selection: traverse from root down to leaf node via PUCT.
        Returns leaf node ready for expansion.
        """
        cur = self.root
        c_puct = self.get_adaptive_c_puct()

        while True:
            # Reach leaf node: stop selection
            if cur.is_leaf or cur.genealogy.generation >= self.config.max_depth:
                return cur

            # Select best child by PUCT
            parent_visits = cur.visits
            best_child = max(cur.children, key=lambda ch: self._puct_value(ch, parent_visits, c_puct))
            cur = best_child

    def expand_and_evaluate(self, parent_node: Node) -> Optional[Node]:
        """
        Expand a node by generating and evaluating new code.

        Args:
            parent_node: Node to expand from

        Returns:
            New child node or None if expansion failed
        """
        print(f"\n🔄 Expanding node {parent_node.id[:8]} (score: {parent_node.score:.4f}, gen: {parent_node.genealogy.generation})")

        # Select mutation strategy based on parent performance
        mutation_type = self._select_mutation_strategy(parent_node)

        # Get research ideas to incorporate
        research_ideas = self._select_research_ideas(parent_node)

        # Generate new code
        task_description = self.task_config.create_prompt_context(include_research_ideas=False)

        response = self.llm_worker.generate_code_mutation(
            previous_code=parent_node.code,
            score=parent_node.score,
            task_description=task_description,
            research_ideas=research_ideas,
            domain=self.task_config.domain,
            data_files=self.task_config.data_files
        )

        self.stats.llm_call_count += 1

        if not response.success or not response.code:
            print(f"❌ LLM generation failed: {response.error_message}")
            return None

        # Evaluate new code
        print("📊 Evaluating generated code...")
        start_time = time.time()
        evaluation_result = self.evaluator(response.code)
        evaluation_time = time.time() - start_time

        # Create new node: Node constructor automatically appends to parent.children
        new_node = Node(
            code=response.code,
            parent=parent_node,
            score=evaluation_result.get('score', 0.0),
            secondary_scores=evaluation_result.get('secondary_scores', {}),
            execution_time=evaluation_time,
            mutation_type=mutation_type,
            research_ideas_used=research_ideas
        )

        # Update metrics
        if 'error_count' in evaluation_result:
            new_node.metrics.error_count = evaluation_result['error_count']
        if 'auto_fixes' in evaluation_result:
            new_node.metrics.auto_fixes = evaluation_result['auto_fixes']
            self.stats.auto_fix_count += evaluation_result['auto_fixes']

        new_node.metrics.success = evaluation_result.get('success', True)

        # Track statistics
        if new_node.metrics.success:
            self.stats.successful_evaluations += 1
        else:
            self.stats.failed_evaluations += 1

        # Add to collection
        self.nodes.add_node(new_node)

        # Check if this is a new best solution
        if new_node.score > self.best_node.score:
            improvement = new_node.score - self.best_node.score
            self.best_node = new_node
            print(f"🎉 NEW BEST SCORE: {new_node.score:.4f} (+{improvement:.4f})")
            if new_node.metrics.auto_fixes > 0:
                print(f"🔧 Applied {new_node.metrics.auto_fixes} automatic fixes")
        else:
            improvement = new_node.score - parent_node.score
            print(f"📈 Score: {new_node.score:.4f} ({improvement:+.4f} vs parent)")
            if new_node.metrics.auto_fixes > 0:
                print(f"🔧 Applied {new_node.metrics.auto_fixes} automatic fixes")

        return new_node

    def _select_mutation_strategy(self, parent_node: Node) -> str:
        """Select mutation strategy based on parent node performance."""
        if parent_node.score < 0.3:
            return "major_refactor"
        elif parent_node.score < 0.6:
            return "algorithm_change"
        elif parent_node.score < 0.8:
            return "hyperparameter_tuning"
        else:
            return "fine_tuning"

    def _select_research_ideas(self, parent_node: Node) -> List[str]:
        """Select research ideas to incorporate based on context."""
        available_ideas = self.task_config.research_ideas.copy()
        used_ideas = parent_node.get_research_ideas_lineage()

        # Prefer unused ideas
        unused_ideas = [idea for idea in available_ideas if idea not in used_ideas]

        if unused_ideas:
            # Select 1‑2 unused ideas
            num_ideas = min(2, len(unused_ideas))
            return random.sample(unused_ideas, num_ideas)
        else:
            # All ideas used, select randomly
            num_ideas = min(2, len(available_ideas))
            return random.sample(available_ideas, num_ideas) if available_ideas else []

    def backpropagate(self, node: Node) -> None:
        """
        Update visit counts and rewards along the path to root.
        Use evaluated node.score as MCTS reward, use Node.add_visit().
        Args:
            node: Node to backpropagate from
        """
        current = node
        reward = node.score
        while current is not None:
            current.add_visit(reward)
            current = current.parent

    def run(self, max_iterations: Optional[int] = None) -> Node:
        """
        Run the tree search algorithm.

        Args:
            max_iterations: Maximum number of iterations (uses config if None)

        Returns:
            Best node found
        """
        max_iter = max_iterations or self.config.max_iterations

        print(f"🚀 Starting Universal Tree Search")
        print(f"📋 Task: {self.task_config.task_name}")
        print(f"🎯 Metric: {self.task_config.evaluation_metric}")
        print(f"🔄 Max iterations: {max_iter}")
        print(f"🌟 Initial score: {self.best_node.score:.4f}")
        print("-" * 50)

        no_improvement_count = 0
        last_best_score = self.best_node.score

        for iteration in range(max_iter):
            self.current_iteration = iteration  # Update for adaptive C‑PUCT
            start_time = time.time()

            # Display adaptive C‑PUCT info
            if self.config.use_adaptive_c_puct and iteration % 10 == 0:
                c_value = self.get_adaptive_c_puct()
                progress = iteration / max_iter
                phase = "Early" if progress < 0.2 else ("Mid" if progress < 0.7 else "Late")
                print(f"\n📊 {phase} Phase: C‑PUCT = {c_value:.2f} (progress: {progress*100:.1f}%)")

            print(f"\n🔍 Iteration {iteration + 1}/{max_iter}")

            # 1. Selection
            selected_node = self.select_node()
            print(f"🎯 Selected leaf node: {selected_node.id[:8]} (score: {selected_node.score:.4f})")

            # 2. Expansion & Evaluation
            new_node = self.expand_and_evaluate(selected_node)

            if new_node is None:
                print("⚠️ Expansion failed, skipping iteration")
                continue

            # 3. Backpropagation
            self.backpropagate(new_node)

            # Track iteration time
            iteration_time = time.time() - start_time
            self.stats.iteration_times.append(iteration_time)
            self.stats.total_iterations += 1

            # Track best score history
            self.stats.best_score_history.append(self.best_node.score)

            # Early stopping check
            if self.best_node.score > last_best_score + self.config.min_improvement_threshold:
                no_improvement_count = 0
                last_best_score = self.best_node.score
            else:
                no_improvement_count += 1

            if no_improvement_count >= self.config.early_stopping_patience:
                print(f"\n🛑 Early stopping: No improvement for {no_improvement_count} iterations")
                break

            # Progress update
            if (iteration + 1) % 5 == 0:
                self._print_progress_summary()

        print("\n" + "=" * 50)
        print("🏁 SEARCH COMPLETED")
        self._print_final_summary()

        return self.best_node

    def _print_progress_summary(self) -> None:
        """Print progress summary."""
        stats = self.nodes.get_statistics()
        print(f"\n📊 Progress Summary:")
        print(f"   • Best score: {self.best_node.score:.4f}")
        print(f"   • Total nodes: {stats['total_nodes']}")
        print(f"   • Success rate: {stats['success_rate']:.1%}")
        print(f"   • LLM calls: {self.stats.llm_call_count}")
        print(f"   • Auto‑fixes: {self.stats.auto_fix_count}")

    def _print_final_summary(self) -> None:
        """Print final search summary."""
        stats = self.nodes.get_statistics()

        print(f"🏆 BEST SOLUTION FOUND:")
        print(f"   • Score: {self.best_node.score:.4f}")
        print(f"   • Generation: {self.best_node.genealogy.generation}")
        print(f"   • Mutation: {self.best_node.genealogy.mutation_type}")

        if self.best_node.genealogy.research_ideas_used:
            print(f"   • Research ideas: {', '.join(self.best_node.genealogy.research_ideas_used)}")

        print(f"\n📈 SEARCH STATISTICS:")
        print(f"   • Total iterations: {self.stats.total_iterations}")
        print(f"   • Total nodes explored: {stats['total_nodes']}")
        print(f"   • Successful evaluations: {self.stats.successful_evaluations}")
        print(f"   • Failed evaluations: {self.stats.failed_evaluations}")
        print(f"   • Success rate: {stats['success_rate']:.1%}")
        print(f"   • LLM calls: {self.stats.llm_call_count}")
        print(f"   • Auto‑fixes applied: {self.stats.auto_fix_count}")

        if self.stats.iteration_times:
            avg_time = sum(self.stats.iteration_times) / len(self.stats.iteration_times)
            print(f"   • Average iteration time: {avg_time:.2f}s")

        print(f"\n🧬 CODE EVOLUTION:")
        print(f"   • Max generation reached: {stats['max_generation']}")
        print(f"   • Score improvement: {self.best_node.score - self.root.score:+.4f}")
        print(f"   • Relative improvement: {((self.best_node.score / self.root.score) - 1) * 100:+.1f}%")

    def get_best_code(self) -> str:
        """Get the code from the best performing node."""
        return self.best_node.code if self.best_node else ""

    def get_search_results(self) -> Dict[str, Any]:
        """Get comprehensive search results."""
        stats = self.nodes.get_statistics()

        return {
            'best_node': self.best_node.to_dict() if self.best_node else None,
            'best_code': self.get_best_code(),
            'search_stats': {
                'total_iterations': self.stats.total_iterations,
                'successful_evaluations': self.stats.successful_evaluations,
                'failed_evaluations': self.stats.failed_evaluations,
                'llm_call_count': self.stats.llm_call_count,
                'auto_fix_count': self.stats.auto_fix_count,
                'best_score_history': self.stats.best_score_history,
                'average_iteration_time': sum(self.stats.iteration_times) / len(self.stats.iteration_times) if self.stats.iteration_times else 0
            },
            'node_stats': stats,
            'task_info': {
                'domain': self.task_config.domain,
                'task_name': self.task_config.task_name,
                'evaluation_metric': self.task_config.evaluation_metric
            }
        }