"""
Enhanced Universal Tree Search with Multi-Phase Architecture
===========================================================

Enhanced version implementing the complete AI system graph workflow:
- Phase 1: Research preparation and multi-strategy initialization
- Phase 2: Intelligent tree search with advisory prompts  
- Phase 3: Solution analysis and hybridization
"""

import math
import time
import random
from typing import List, Optional, Dict, Any, Callable, Tuple
from dataclasses import dataclass
import numpy as np

from .search import UniversalTreeSearch, SearchConfiguration, SearchStats
from .node import Node, NodeCollection
from ..task_manager import TaskConfiguration
from ..llm_worker_enhanced import EnhancedLLMWorker, MultiPhaseResults
from ..prompts.prompt_strategies import PromptStrategyManager, SearchPhase


@dataclass
class EnhancedSearchConfiguration(SearchConfiguration):
    """Enhanced search configuration with multi-phase options."""
    enable_preparation_phase: bool = True
    enable_analysis_phase: bool = True
    multi_strategy_initialization: bool = True
    max_preparation_strategies: int = 4
    hybridization_frequency: int = 10  # Every N iterations
    min_solutions_for_analysis: int = 3


@dataclass  
class EnhancedSearchStats(SearchStats):
    """Enhanced statistics tracking for multi-phase search."""
    preparation_phase_time: float = 0.0
    analysis_phase_time: float = 0.0
    strategies_attempted: Dict[str, int] = None
    research_ideas_generated: int = 0
    hybrid_solutions_created: int = 0
    
    def __post_init__(self):
        super().__post_init__()
        if self.strategies_attempted is None:
            self.strategies_attempted = {}


class EnhancedUniversalTreeSearch(UniversalTreeSearch):
    """
    Enhanced Universal Tree Search implementing the complete AI system graph.
    
    Supports:
    - Multi-phase architecture (preparation, main loop, analysis)
    - Research idea integration and brainstorming
    - Solution analysis and hybridization
    - Intelligent prompt strategy selection
    - Multi-strategy initialization
    """
    
    def __init__(
        self,
        task_config: TaskConfiguration,
        evaluator: Callable[[str], Dict[str, Any]],
        enhanced_config: Optional[EnhancedSearchConfiguration] = None
    ):
        """
        Initialize enhanced tree search.
        
        Args:
            task_config: Task configuration
            evaluator: Code evaluation function
            enhanced_config: Enhanced search configuration
        """
        # Initialize base search with enhanced config
        base_config = enhanced_config or EnhancedSearchConfiguration()
        super().__init__(task_config, evaluator, None, base_config)
        
        # Enhanced components
        self.enhanced_config = enhanced_config or EnhancedSearchConfiguration()
        self.enhanced_llm_worker = EnhancedLLMWorker(task_config)
        self.enhanced_stats = EnhancedSearchStats()
        
        # Multi-phase results
        self.preparation_results = MultiPhaseResults()
        self.candidate_solutions = []  # For analysis phase
        self.hybrid_solutions = []
        
        # Strategy tracking
        self.initialization_strategies = {}
        self.current_phase = SearchPhase.PREPARATION
        
    def run_enhanced_search(self, max_iterations: Optional[int] = None) -> Node:
        """
        Run the complete enhanced search with all phases.
        
        Args:
            max_iterations: Maximum iterations for main loop
            
        Returns:
            Best node found across all phases
        """
        max_iter = max_iterations or self.enhanced_config.max_iterations
        
        print("🚀 Starting Enhanced Universal Tree Search")
        print("=" * 60)
        print(f"📋 Task: {self.task_config.task_name}")
        print(f"🎯 Metric: {self.task_config.evaluation_metric}")
        print(f"🔄 Max iterations: {max_iter}")
        print(f"🧪 Multi-phase: {self.enhanced_config.enable_preparation_phase}")
        print("=" * 60)
        
        total_start_time = time.time()
        
        # Phase 1: Preparation (if enabled)
        if self.enhanced_config.enable_preparation_phase:
            self._run_preparation_phase()
        
        # Phase 2: Enhanced main search loop
        self.current_phase = SearchPhase.MAIN_LOOP
        best_solution = self._run_enhanced_main_loop(max_iter)
        
        # Phase 3: Solution analysis and hybridization (if enabled)
        if self.enhanced_config.enable_analysis_phase and len(self.candidate_solutions) >= self.enhanced_config.min_solutions_for_analysis:
            self._run_analysis_phase()
            
            # Re-evaluate best solution after hybridization
            if self.hybrid_solutions:
                hybrid_best = self._evaluate_hybrid_solutions()
                if hybrid_best and hybrid_best.score > best_solution.score:
                    best_solution = hybrid_best
        
        total_time = time.time() - total_start_time
        
        # Final summary
        print("\n" + "=" * 60)
        print("🏁 ENHANCED SEARCH COMPLETED")
        print("=" * 60)
        self._print_enhanced_final_summary(total_time)
        
        return best_solution
    
    def _run_preparation_phase(self):
        """Run Phase 1: Research preparation and multi-strategy initialization."""
        print("\n🔬 PHASE 1: RESEARCH PREPARATION")
        print("-" * 40)
        
        phase_start = time.time()
        
        # Execute research preparation
        self.preparation_results = self.enhanced_llm_worker.run_preparation_phase()
        
        # Multi-strategy initialization
        if self.enhanced_config.multi_strategy_initialization:
            self._execute_multi_strategy_initialization()
        else:
            # Standard single initialization
            self._initialize_root_standard()
        
        self.enhanced_stats.preparation_phase_time = time.time() - phase_start
        self.enhanced_stats.research_ideas_generated = len(self.preparation_results.research_ideas)
        
        print(f"✅ Phase 1 completed in {self.enhanced_stats.preparation_phase_time:.1f}s")
    
    def _execute_multi_strategy_initialization(self):
        """Execute multiple initialization strategies and select the best."""
        print("🚀 Executing multi-strategy initialization...")
        
        # Generate multiple initial solutions
        init_responses = self.enhanced_llm_worker.generate_multi_strategy_initial_code()
        
        best_score = -float('inf')
        best_strategy = None
        best_code = None
        
        for strategy_name, response in init_responses.items():
            if response.success and response.code:
                # Evaluate the initial code
                print(f"   📊 Evaluating {strategy_name}...")
                
                try:
                    evaluation_result = self.evaluator(response.code)
                    score = evaluation_result.get('score', 0.0)
                    
                    self.initialization_strategies[strategy_name] = {
                        'code': response.code,
                        'score': score,
                        'evaluation': evaluation_result
                    }
                    
                    print(f"      Score: {score:.4f}")
                    
                    if score > best_score:
                        best_score = score
                        best_strategy = strategy_name
                        best_code = response.code
                        
                    # Track for candidate solutions
                    self.candidate_solutions.append((response.code, score))
                    
                    # Update stats
                    if strategy_name not in self.enhanced_stats.strategies_attempted:
                        self.enhanced_stats.strategies_attempted[strategy_name] = 0
                    self.enhanced_stats.strategies_attempted[strategy_name] += 1
                    
                except Exception as e:
                    print(f"      ❌ Evaluation failed: {e}")
        
        # Create root node from best strategy
        if best_code:
            self.root = Node(
                code=best_code,
                parent=None,
                score=best_score,
                mutation_type=f"multi_init_{best_strategy}"
            )
            self.nodes.add_node(self.root)
            self.best_node = self.root
            
            print(f"✅ Best initialization: {best_strategy} (score: {best_score:.4f})")
        else:
            print("⚠️ All initialization strategies failed, using fallback")
            self._initialize_root_standard()
    
    def _initialize_root_standard(self):
        """Fallback to standard root initialization."""
        # Use the base class method
        self._initialize_root()
    
    def _run_enhanced_main_loop(self, max_iterations: int) -> Node:
        """Run Phase 2: Enhanced main search loop with intelligent prompt strategies."""
        print(f"\n🔄 PHASE 2: ENHANCED TREE SEARCH ({max_iterations} iterations)")
        print("-" * 40)
        
        no_improvement_count = 0
        last_best_score = self.best_node.score
        
        for iteration in range(max_iterations):
            print(f"\n🔍 Iteration {iteration + 1}/{max_iterations}")
            
            # 1. Selection (same as base)
            selected_node = self.select_node()
            print(f"🎯 Selected node: {selected_node.id[:8]} (score: {selected_node.score:.4f})")
            
            # 2. Enhanced expansion with intelligent mutation
            new_node = self._expand_and_evaluate_enhanced(selected_node, iteration)
            
            if new_node is None:
                print("⚠️ Expansion failed, skipping iteration")
                continue
            
            # 3. Backpropagation
            self.backpropagate(new_node)
            
            # Track candidate solutions for analysis phase
            self.candidate_solutions.append((new_node.code, new_node.score))
            
            # Update statistics
            self.enhanced_stats.total_iterations += 1
            
            # Check for improvement
            if self.best_node.score > last_best_score + self.config.min_improvement_threshold:
                no_improvement_count = 0
                last_best_score = self.best_node.score
            else:
                no_improvement_count += 1
            
            # Periodic hybridization during search
            if (iteration + 1) % self.enhanced_config.hybridization_frequency == 0:
                self._periodic_hybridization(iteration)
            
            # Early stopping check
            if no_improvement_count >= self.config.early_stopping_patience:
                print(f"\n🛑 Early stopping: No improvement for {no_improvement_count} iterations")
                break
            
            # Progress update
            if (iteration + 1) % 5 == 0:
                self._print_enhanced_progress_summary()
        
        return self.best_node
    
    def _expand_and_evaluate_enhanced(self, parent_node: Node, iteration: int) -> Optional[Node]:
        """Enhanced expansion with intelligent prompt strategies."""
        print(f"🔄 Expanding node {parent_node.id[:8]} (score: {parent_node.score:.4f}, gen: {parent_node.genealogy.generation})")
        
        # Generate enhanced mutation
        mutation_context = {
            'iteration': iteration,
            'parent_score': parent_node.score,
            'search_history': self.enhanced_stats.strategies_attempted
        }
        
        response = self.enhanced_llm_worker.generate_enhanced_mutation(
            parent_node.code,
            parent_node.score,
            parent_node.genealogy.generation,
            mutation_context
        )
        
        if not response.success or not response.code:
            print(f"❌ Enhanced mutation failed: {response.error_message}")
            return None
        
        # Evaluate new code
        print("📊 Evaluating generated code...")
        start_time = time.time()
        evaluation_result = self.evaluator(response.code)
        evaluation_time = time.time() - start_time
        
        # Create new node with enhanced information
        new_node = Node(
            code=response.code,
            parent=parent_node,
            score=evaluation_result.get('score', 0.0),
            secondary_scores=evaluation_result.get('secondary_scores', {}),
            execution_time=evaluation_time,
            mutation_type=response.strategy_used or "enhanced_mutation",
            research_ideas_used=response.research_ideas or []
        )
        
        # Update metrics
        self._update_node_metrics(new_node, evaluation_result)
        
        # Add to collection
        self.nodes.add_node(new_node)
        
        # Check for new best
        if new_node.score > self.best_node.score:
            improvement = new_node.score - self.best_node.score
            self.best_node = new_node
            print(f"🎉 NEW BEST SCORE: {new_node.score:.4f} (+{improvement:.4f})")
            print(f"   Strategy: {response.strategy_used}")
        else:
            improvement = new_node.score - parent_node.score
            print(f"📈 Score: {new_node.score:.4f} ({improvement:+.4f} vs parent)")
        
        # Update strategy tracking
        strategy_used = response.strategy_used or "unknown"
        if strategy_used not in self.enhanced_stats.strategies_attempted:
            self.enhanced_stats.strategies_attempted[strategy_used] = 0
        self.enhanced_stats.strategies_attempted[strategy_used] += 1
        
        return new_node
    
    def _periodic_hybridization(self, iteration: int):
        """Perform periodic hybridization during the search."""
        if len(self.candidate_solutions) < 3:
            return
        
        print(f"🧬 Periodic hybridization (iteration {iteration + 1})")
        
        # Get top solutions for hybridization
        top_solutions = sorted(self.candidate_solutions, key=lambda x: x[1], reverse=True)[:3]
        
        # Generate hybrid solutions
        hybrid_results = self.enhanced_llm_worker.analyze_and_hybridize_solutions(top_solutions)
        
        for strategy_name, response in hybrid_results.items():
            if response.success and response.code and strategy_name == "hybrid_solution":
                # Evaluate hybrid solution
                try:
                    evaluation_result = self.evaluator(response.code)
                    score = evaluation_result.get('score', 0.0)
                    
                    # Create hybrid node
                    hybrid_node = Node(
                        code=response.code,
                        parent=self.best_node,  # Attach to current best
                        score=score,
                        mutation_type="periodic_hybrid",
                        research_ideas_used=response.research_ideas or []
                    )
                    
                    self.nodes.add_node(hybrid_node)
                    self.hybrid_solutions.append((response.code, score))
                    self.enhanced_stats.hybrid_solutions_created += 1
                    
                    # Check if it's a new best
                    if score > self.best_node.score:
                        self.best_node = hybrid_node
                        print(f"   🎉 Hybrid solution is new best: {score:.4f}")
                    else:
                        print(f"   📊 Hybrid score: {score:.4f}")
                        
                except Exception as e:
                    print(f"   ❌ Hybrid evaluation failed: {e}")
    
    def _run_analysis_phase(self):
        """Run Phase 3: Solution analysis and hybridization."""
        print(f"\n🔬 PHASE 3: SOLUTION ANALYSIS & HYBRIDIZATION")
        print("-" * 40)
        
        phase_start = time.time()
        
        # Get top solutions for analysis
        top_solutions = sorted(self.candidate_solutions, key=lambda x: x[1], reverse=True)[:5]
        print(f"Analyzing top {len(top_solutions)} solutions...")
        
        # Perform comprehensive analysis and hybridization
        analysis_results = self.enhanced_llm_worker.analyze_and_hybridize_solutions(top_solutions)
        
        # Process analysis results
        for strategy_name, response in analysis_results.items():
            if response.success and response.code:
                if strategy_name == "hybrid_solution":
                    self.hybrid_solutions.append((response.code, 0.0))  # Score will be evaluated
                    self.enhanced_stats.hybrid_solutions_created += 1
        
        self.enhanced_stats.analysis_phase_time = time.time() - phase_start
        print(f"✅ Phase 3 completed in {self.enhanced_stats.analysis_phase_time:.1f}s")
    
    def _evaluate_hybrid_solutions(self) -> Optional[Node]:
        """Evaluate hybrid solutions and return the best one."""
        if not self.hybrid_solutions:
            return None
        
        print("📊 Evaluating hybrid solutions...")
        best_hybrid_node = None
        best_hybrid_score = -float('inf')
        
        for i, (code, _) in enumerate(self.hybrid_solutions):
            try:
                evaluation_result = self.evaluator(code)
                score = evaluation_result.get('score', 0.0)
                
                hybrid_node = Node(
                    code=code,
                    parent=None,  # Hybrid solutions are independent
                    score=score,
                    mutation_type="final_hybrid",
                    research_ideas_used=self.preparation_results.research_ideas
                )
                
                self.nodes.add_node(hybrid_node)
                
                print(f"   Hybrid {i+1}: {score:.4f}")
                
                if score > best_hybrid_score:
                    best_hybrid_score = score
                    best_hybrid_node = hybrid_node
                    
            except Exception as e:
                print(f"   ❌ Hybrid {i+1} evaluation failed: {e}")
        
        return best_hybrid_node
    
    def _update_node_metrics(self, node: Node, evaluation_result: Dict[str, Any]):
        """Update node metrics from evaluation result."""
        if 'error_count' in evaluation_result:
            node.metrics.error_count = evaluation_result['error_count']
        if 'auto_fixes' in evaluation_result:
            node.metrics.auto_fixes = evaluation_result['auto_fixes']
        
        node.metrics.success = evaluation_result.get('success', True)
    
    def _print_enhanced_progress_summary(self):
        """Print enhanced progress summary."""
        stats = self.nodes.get_statistics()
        print(f"\n📊 Enhanced Progress Summary:")
        print(f"   • Best score: {self.best_node.score:.4f}")
        print(f"   • Total nodes: {stats['total_nodes']}")
        print(f"   • Success rate: {stats['success_rate']:.1%}")
        print(f"   • Strategies attempted: {dict(self.enhanced_stats.strategies_attempted)}")
        print(f"   • Research ideas: {self.enhanced_stats.research_ideas_generated}")
        print(f"   • Hybrid solutions: {self.enhanced_stats.hybrid_solutions_created}")
    
    def _print_enhanced_final_summary(self, total_time: float):
        """Print comprehensive final summary."""
        stats = self.nodes.get_statistics()
        llm_summary = self.enhanced_llm_worker.get_multi_phase_summary()
        
        print(f"🏆 ENHANCED SEARCH RESULTS:")
        print(f"   • Final Best Score: {self.best_node.score:.4f}")
        print(f"   • Total Runtime: {total_time:.1f}s")
        print(f"   • Best Solution Strategy: {self.best_node.genealogy.mutation_type}")
        
        if self.best_node.genealogy.research_ideas_used:
            print(f"   • Research Ideas Used: {len(self.best_node.genealogy.research_ideas_used)}")
        
        print(f"\n📈 MULTI-PHASE STATISTICS:")
        print(f"   • Phase 1 (Preparation): {self.enhanced_stats.preparation_phase_time:.1f}s")
        print(f"   • Phase 2 (Main Search): {total_time - self.enhanced_stats.preparation_phase_time - self.enhanced_stats.analysis_phase_time:.1f}s")
        print(f"   • Phase 3 (Analysis): {self.enhanced_stats.analysis_phase_time:.1f}s")
        
        print(f"\n🔬 RESEARCH & INNOVATION:")
        print(f"   • Research Ideas Generated: {self.enhanced_stats.research_ideas_generated}")
        print(f"   • Initialization Strategies: {len(self.initialization_strategies)}")
        print(f"   • Hybrid Solutions Created: {self.enhanced_stats.hybrid_solutions_created}")
        print(f"   • Candidate Solutions: {len(self.candidate_solutions)}")
        
        print(f"\n🎯 STRATEGY PERFORMANCE:")
        for strategy, count in self.enhanced_stats.strategies_attempted.items():
            print(f"   • {strategy}: {count} attempts")
    
    def get_enhanced_results(self) -> Dict[str, Any]:
        """Get comprehensive enhanced search results."""
        base_results = self.get_search_results()
        
        enhanced_results = {
            **base_results,
            "enhanced_stats": {
                "preparation_phase_time": self.enhanced_stats.preparation_phase_time,
                "analysis_phase_time": self.enhanced_stats.analysis_phase_time,
                "strategies_attempted": self.enhanced_stats.strategies_attempted,
                "research_ideas_generated": self.enhanced_stats.research_ideas_generated,
                "hybrid_solutions_created": self.enhanced_stats.hybrid_solutions_created
            },
            "multi_phase_results": {
                "initialization_strategies": {k: v['score'] for k, v in self.initialization_strategies.items()},
                "candidate_solutions_count": len(self.candidate_solutions),
                "hybrid_solutions_count": len(self.hybrid_solutions),
                "research_ideas": self.preparation_results.research_ideas[:5]  # First 5
            },
            "llm_worker_summary": self.enhanced_llm_worker.get_multi_phase_summary()
        }
        
        return enhanced_results