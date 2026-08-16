"""
Database-Integrated Enhanced Universal Tree Search
=================================================

Enhanced tree search system integrated with database-driven code execution
for maximum reliability, persistence, and manual execution fallback.
"""

import math
import time
import random
from typing import List, Optional, Dict, Any, Callable, Tuple
from dataclasses import dataclass
import numpy as np

from .enhanced_search import EnhancedUniversalTreeSearch, EnhancedSearchConfiguration, EnhancedSearchStats
from .node import Node, NodeCollection
from ..task_manager import TaskConfiguration
from ..llm_worker_enhanced import EnhancedLLMWorker, MultiPhaseResults
from ..prompts.prompt_strategies import PromptStrategyManager, SearchPhase
from ..sandbox.db_universal_evaluator import DatabaseUniversalEvaluator
from ..notifications.webhook_notifier import WebhookNotifier


@dataclass
class DatabaseSearchConfiguration(EnhancedSearchConfiguration):
    """Database-enhanced search configuration."""
    db_path: str = "enhanced_search.db"
    enable_monitoring: bool = True
    wait_for_manual_completion: bool = True
    skip_auto_fixer: bool = False  # If True, skip auto-fixer and go directly to manual execution
    manual_execution_timeout: int = 300  # 5 minutes
    execution_timeout: int = 600  # 10 minutes for node code execution
    export_results_frequency: int = 10   # Export every N iterations
    
    # User feedback and code reload settings
    enable_user_feedback: bool = False
    user_feedback_timeout: int = 30
    enable_code_reload: bool = False
    code_reload_wait_time: int = 60
    
    # Adaptive C-PUCT settings (inherited from SearchConfiguration)
    use_adaptive_c_puct: bool = True  # Enable adaptive C-PUCT
    c_puct_early: float = 2.5  # Early phase (0-20% progress)
    c_puct_mid: float = 1.5    # Mid phase (20-70% progress)
    c_puct_late: float = 0.8   # Late phase (70-100% progress)


@dataclass  
class DatabaseSearchStats(EnhancedSearchStats):
    """Database-enhanced statistics tracking."""
    manual_executions_completed: int = 0
    manual_executions_pending: int = 0
    database_exports_created: int = 0
    total_auto_fixes: int = 0


class DatabaseEnhancedTreeSearch(EnhancedUniversalTreeSearch):
    """
    Database-integrated enhanced tree search.
    
    Combines the multi-phase enhanced search with database-driven execution
    for maximum reliability and comprehensive tracking.
    """
    
    def __init__(
        self,
        task_config: TaskConfiguration,
        db_config: Optional[DatabaseSearchConfiguration] = None
    ):
        """
        Initialize database-enhanced tree search.
        
        Args:
            task_config: Task configuration
            db_config: Database search configuration
        """
        # Initialize database configuration
        self.db_config = db_config or DatabaseSearchConfiguration()
        
        # Initialize webhook notifier for alerts
        self.webhook = WebhookNotifier()
        
        # Create database-integrated evaluator with Claude auto-fixer
        self.db_evaluator = DatabaseUniversalEvaluator(
            task_config, 
            self.db_config.db_path,
            self.db_config.enable_monitoring,
            self.db_config.wait_for_manual_completion,
            self.db_config.skip_auto_fixer,
            enable_user_feedback=self.db_config.enable_user_feedback,
            feedback_timeout=self.db_config.user_feedback_timeout,
            enable_code_reload=self.db_config.enable_code_reload,
            code_reload_wait_time=self.db_config.code_reload_wait_time,
            execution_timeout=self.db_config.execution_timeout
        )
        
        # Initialize enhanced search with database evaluator
        enhanced_config = EnhancedSearchConfiguration(
            c_puct=self.db_config.c_puct,
            max_iterations=self.db_config.max_iterations,
            enable_preparation_phase=self.db_config.enable_preparation_phase,
            enable_analysis_phase=self.db_config.enable_analysis_phase,
            multi_strategy_initialization=self.db_config.multi_strategy_initialization,
            max_preparation_strategies=self.db_config.max_preparation_strategies,
            hybridization_frequency=self.db_config.hybridization_frequency,
            min_solutions_for_analysis=self.db_config.min_solutions_for_analysis
        )
        
        # Initialize base enhanced search
        super().__init__(task_config, self.db_evaluator.evaluate, enhanced_config)
        
        # Replace stats with database-enhanced version
        self.db_stats = DatabaseSearchStats()
        
        # Track database integration
        self.total_manual_executions = 0
        self.pending_manual_nodes = []
        self.completed_manual_nodes = []
        
        # Session tracking for current run isolation
        import uuid
        import datetime
        self.session_id = str(uuid.uuid4())[:8]
        self.session_start_time = datetime.datetime.now()
        self.current_session_nodes = set()  # Track nodes created in this session
        
        print(f"🗄️ Database-Enhanced Tree Search initialized")
        print(f"   📊 Database: {self.db_config.db_path}")
        print(f"   🔍 Monitoring: {self.db_config.enable_monitoring}")
        print(f"   ⏳ Manual timeout: {self.db_config.manual_execution_timeout}s")
        print(f"   🆔 Session ID: {self.session_id} (started: {self.session_start_time.strftime('%H:%M:%S')})")
    
    def run_database_enhanced_search(self, max_iterations: Optional[int] = None) -> Node:
        """
        Run the complete database-enhanced search with all phases.
        
        Args:
            max_iterations: Maximum iterations for main loop
            
        Returns:
            Best node found across all phases
        """
        max_iter = max_iterations or self.db_config.max_iterations
        
        print("🚀 Starting Database-Enhanced Universal Tree Search")
        print("=" * 70)
        print(f"📋 Task: {self.task_config.task_name}")
        print(f"🎯 Metric: {self.task_config.evaluation_metric}")
        print(f"🔄 Max iterations: {max_iter}")
        print(f"🗄️ Database: {self.db_config.db_path}")
        print(f"🧪 Multi-phase: {self.enhanced_config.enable_preparation_phase}")
        print("=" * 70)
        
        total_start_time = time.time()
        
        try:
            # Phase 1: Preparation (if enabled)
            if self.enhanced_config.enable_preparation_phase:
                self._run_database_preparation_phase()
            
            # Phase 2: Enhanced main search loop with database integration
            self.current_phase = SearchPhase.MAIN_LOOP
            best_solution = self._run_database_main_loop(max_iter)
            
            # Phase 3: Solution analysis and hybridization (if enabled)
            if (self.enhanced_config.enable_analysis_phase and 
                len(self.candidate_solutions) >= self.enhanced_config.min_solutions_for_analysis):
                self._run_database_analysis_phase()
                
                # Re-evaluate best solution after hybridization
                if hasattr(self, 'hybrid_solutions') and self.hybrid_solutions:
                    hybrid_best = self._evaluate_hybrid_solutions_with_database()
                    if hybrid_best and hybrid_best.score > best_solution.score:
                        best_solution = hybrid_best
            
            total_time = time.time() - total_start_time
            
            # Final database operations
            self._finalize_database_search(total_time)
            
            return best_solution
            
        except KeyboardInterrupt:
            print("\n⚠️ Search interrupted by user")
            self._handle_search_interruption()
            raise
        except Exception as e:
            print(f"\n❌ Search error: {e}")
            self._handle_search_error(e)
            raise
    
    def _run_database_preparation_phase(self):
        """Run Phase 1 with database integration."""
        print("\n🔬 PHASE 1: RESEARCH PREPARATION (Database-Enhanced)")
        print("-" * 50)
        
        phase_start = time.time()
        
        # Execute research preparation
        self.preparation_results = self.enhanced_llm_worker.run_preparation_phase()
        
        # Multi-strategy initialization with database tracking
        if self.enhanced_config.multi_strategy_initialization:
            self._execute_database_multi_strategy_initialization()
        else:
            # Standard single initialization with database
            self._initialize_root()
        
        self.enhanced_stats.preparation_phase_time = time.time() - phase_start
        self.enhanced_stats.research_ideas_generated = len(self.preparation_results.research_ideas)
        
        print(f"✅ Phase 1 completed in {self.enhanced_stats.preparation_phase_time:.1f}s")
        
        # Check for any manual executions needed
        self._check_and_handle_manual_executions()
    
    def _execute_database_multi_strategy_initialization(self):
        """Execute multi-strategy initialization with database tracking."""
        print("🚀 Executing database-tracked multi-strategy initialization...")
        
        # Generate multiple initial solutions using database evaluator
        init_responses = self.enhanced_llm_worker.generate_multi_strategy_initial_code()
        
        best_score = -float('inf')
        best_strategy = None
        best_node_id = None
        
        for strategy_name, response in init_responses.items():
            if response.success and response.code:
                # Evaluate using database system
                print(f"   📊 Evaluating {strategy_name}...")
                
                try:
                    evaluation_result = self.db_evaluator.evaluate(
                        response.code,
                        parent_node_id=None,
                        mutation_type=f"multi_init_{strategy_name}"
                    )
                    
                    score = evaluation_result.get('score', 0.0)
                    node_id = evaluation_result.get('node_id')
                    
                    self.initialization_strategies[strategy_name] = {
                        'code': response.code,
                        'score': score,
                        'evaluation': evaluation_result,
                        'node_id': node_id
                    }
                    
                    print(f"      Score: {score:.4f} (Node: {node_id})")
                    
                    if score > best_score:
                        best_score = score
                        best_strategy = strategy_name
                        best_node_id = node_id
                        
                    # Track for candidate solutions
                    self.candidate_solutions.append((response.code, score))
                    
                    # Update database stats
                    if evaluation_result.get('auto_fixes', 0) > 0:
                        self.db_stats.total_auto_fixes += evaluation_result['auto_fixes']
                    
                except Exception as e:
                    print(f"      ❌ Evaluation failed: {e}")
        
        # Create root node from best strategy using database information
        if best_node_id:
            # Get the database node
            db_node = self.db_evaluator.db.get_node(best_node_id)
            if db_node:
                self.root = Node(
                    code=db_node.code,
                    parent=None,
                    score=db_node.score,
                    mutation_type=f"multi_init_{best_strategy}",
                    node_id=best_node_id  # Track database ID
                )
                self.nodes.add_node(self.root)
                self.best_node = self.root
                
                print(f"✅ Best initialization: {best_strategy} (score: {best_score:.4f}, node: {best_node_id})")
        else:
            print("⚠️ All initialization strategies failed, using fallback")
            self._initialize_root()
    
    def _run_database_main_loop(self, max_iterations: int) -> Node:
        """Run Phase 2 with database integration and manual execution handling."""
        print(f"\n🔄 PHASE 2: DATABASE-ENHANCED TREE SEARCH ({max_iterations} iterations)")
        print("-" * 50)
        
        no_improvement_count = 0
        last_best_score = self.best_node.score
        
        for iteration in range(max_iterations):
            print(f"\n🔍 Iteration {iteration + 1}/{max_iterations}")
            
            # 1. Selection (same as base)
            selected_node = self.select_node()
            print(f"🎯 Selected node: {selected_node.id[:8]} (score: {selected_node.score:.4f})")
            
            # 2. Enhanced expansion with database integration
            new_node = self._expand_and_evaluate_database(selected_node, iteration)
            
            if new_node is None:
                print("⚠️ Expansion failed, checking for manual executions...")
                # Enhanced manual execution handling with user approval
                if self._check_and_handle_manual_executions_with_approval():
                    print("✅ Manual executions completed, continuing search...")
                else:
                    print("⚠️ No manual executions completed, continuing to next iteration...")
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
            
            # Periodic operations
            if (iteration + 1) % self.enhanced_config.hybridization_frequency == 0:
                self._periodic_hybridization_with_database(iteration)
            
            if (iteration + 1) % self.db_config.export_results_frequency == 0:
                self._export_periodic_results(iteration)
            
            # Check for manual executions
            self._check_and_handle_manual_executions()
            
            # Early stopping check
            if no_improvement_count >= self.config.early_stopping_patience:
                print(f"\n🛑 Early stopping: No improvement for {no_improvement_count} iterations")
                break
            
            # Progress update
            if (iteration + 1) % 5 == 0:
                self._print_database_progress_summary()
        
        return self.best_node
    
    def _expand_and_evaluate_database(self, parent_node: Node, iteration: int) -> Optional[Node]:
        """Enhanced expansion with database integration."""
        print(f"🔄 Expanding node {parent_node.id[:8]} (score: {parent_node.score:.4f}, gen: {parent_node.genealogy.generation})")
        
        # Generate enhanced mutation
        mutation_context = {
            'iteration': iteration,
            'parent_score': parent_node.score,
            'search_history': self.enhanced_stats.strategies_attempted,
            'database_stats': self.db_evaluator.get_evaluation_statistics()
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
        
        # Evaluate using database system
        print("📊 Evaluating generated code...")
        start_time = time.time()
        
        evaluation_result = self.db_evaluator.evaluate(
            response.code,
            parent_node_id=getattr(parent_node, 'node_id', None),
            mutation_type=response.strategy_used or "enhanced_mutation"
        )
        
        evaluation_time = time.time() - start_time
        
        # Track node in current session
        node_id = evaluation_result.get('node_id')
        if node_id:
            self.current_session_nodes.add(node_id)
            print(f"📝 Tracking node {node_id} in session {self.session_id}")
        
        # Check if manual execution is required
        if not evaluation_result['success']:
            node_id = evaluation_result.get('node_id')
            if node_id:
                db_node = self.db_evaluator.db.get_node(node_id)
                if db_node and db_node.requires_manual_execution():
                    # Check if this node was already manually completed
                    if db_node.execution_status == 'completed' and db_node.score is not None:
                        print(f"✅ Found manually completed node {node_id} with score: {db_node.score:.4f}")
                        # Create node from manually updated database entry
                        new_node = Node(
                            code=db_node.code,
                            parent=parent_node,
                            score=db_node.score,
                            secondary_scores=db_node.secondary_scores or {},
                            execution_time=evaluation_time,
                            mutation_type=db_node.mutation_type or "manual_update",
                            node_id=node_id
                        )
                        self.nodes.add_node(new_node)
                        
                        # Check for new best
                        if new_node.score > self.best_node.score:
                            improvement = new_node.score - self.best_node.score
                            self.best_node = new_node
                            print(f"🎉 NEW BEST SCORE (from manual): {new_node.score:.4f} (+{improvement:.4f})")
                            
                            # Send webhook notification for new best score
                            self.webhook.send_best_score_alert(
                                score=new_node.score,
                                improvement=improvement,
                                node_id=new_node.id
                            )
                        
                        return new_node
                    else:
                        # Still needs manual execution
                        self.pending_manual_nodes.append(node_id)
                        print(f"🚨 Node {node_id} requires manual execution")
            return None
        
        # Create new node with enhanced information
        new_node = Node(
            code=response.code,
            parent=parent_node,
            score=evaluation_result.get('score', 0.0),
            secondary_scores=evaluation_result.get('secondary_scores', {}),
            execution_time=evaluation_time,
            mutation_type=response.strategy_used or "enhanced_mutation",
            research_ideas_used=response.research_ideas or [],
            node_id=evaluation_result.get('node_id')  # Track database ID
        )
        
        # Update metrics from database result
        if evaluation_result.get('auto_fixes', 0) > 0:
            self.db_stats.total_auto_fixes += evaluation_result['auto_fixes']
        
        # Add to collection
        self.nodes.add_node(new_node)
        
        # Check for new best
        if new_node.score > self.best_node.score:
            improvement = new_node.score - self.best_node.score
            self.best_node = new_node
            print(f"🎉 NEW BEST SCORE: {new_node.score:.4f} (+{improvement:.4f})")
            print(f"   Strategy: {response.strategy_used}")
            print(f"   Database Node: {evaluation_result.get('node_id')}")
            
            # Send webhook notification for new best score
            self.webhook.send_best_score_alert(
                score=new_node.score,
                improvement=improvement,
                node_id=evaluation_result.get('node_id', new_node.id)
            )
        else:
            improvement = new_node.score - parent_node.score
            print(f"📈 Score: {new_node.score:.4f} ({improvement:+.4f} vs parent)")
        
        # Update strategy tracking
        strategy_used = response.strategy_used or "unknown"
        if strategy_used not in self.enhanced_stats.strategies_attempted:
            self.enhanced_stats.strategies_attempted[strategy_used] = 0
        self.enhanced_stats.strategies_attempted[strategy_used] += 1
        
        return new_node
    
    def _run_database_analysis_phase(self):
        """Run Phase 3 with database integration."""
        print("\n🧪 PHASE 3: DATABASE-ENHANCED SOLUTION ANALYSIS")
        print("-" * 50)
        
        phase_start = time.time()
        
        # Run analysis using the base enhanced search logic
        if hasattr(super(), '_run_analysis_phase'):
            super()._run_analysis_phase()
        else:
            # Basic hybridization if base method not available
            self._database_basic_hybridization()
        
        self.enhanced_stats.analysis_phase_time = time.time() - phase_start
        print(f"✅ Phase 3 completed in {self.enhanced_stats.analysis_phase_time:.1f}s")
    
    def _database_basic_hybridization(self):
        """Basic hybridization with database integration."""
        print("🔬 Running database-enhanced solution hybridization...")
        
        # Get top solutions from database
        top_db_nodes = self.db_evaluator.get_best_nodes(5)
        
        if len(top_db_nodes) >= 2:
            # Create hybrid from best database solutions
            hybrid_code = f"""
# Database-Enhanced Hybrid Solution
# Combined from top {len(top_db_nodes)} database solutions

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

# Ensemble approach combining multiple strategies
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(train_df.drop(['{self.task_config.get_target_column()}'], axis=1))
X_val_scaled = scaler.transform(val_df.drop(['{self.task_config.get_target_column()}'], axis=1))

y_train = train_df['{self.task_config.get_target_column()}']

# Create ensemble of best performing approaches
rf = RandomForestClassifier(n_estimators=100, random_state=42)
lr = LogisticRegression(random_state=42, max_iter=1000)

ensemble = VotingClassifier(
    estimators=[('rf', rf), ('lr', lr)],
    voting='soft'
)

ensemble.fit(X_train_scaled, y_train)
val_predictions = ensemble.predict_proba(X_val_scaled)[:, 1]
"""
            
            # Evaluate hybrid solution
            hybrid_result = self.db_evaluator.evaluate(
                hybrid_code,
                parent_node_id=None,
                mutation_type="database_hybrid"
            )
            
            if hybrid_result['success']:
                print(f"🎉 Database hybrid solution: {hybrid_result['score']:.4f}")
                
                # Create hybrid node
                hybrid_node = Node(
                    code=hybrid_code,
                    parent=None,
                    score=hybrid_result['score'],
                    mutation_type="database_hybrid",
                    node_id=hybrid_result.get('node_id')
                )
                
                # Initialize hybrid_solutions if not exists
                if not hasattr(self, 'hybrid_solutions'):
                    self.hybrid_solutions = []
                
                self.hybrid_solutions.append(hybrid_node)
    
    def _evaluate_hybrid_solutions_with_database(self) -> Optional[Node]:
        """Evaluate hybrid solutions and return the best one."""
        if not hasattr(self, 'hybrid_solutions') or not self.hybrid_solutions:
            return None
        
        best_hybrid = None
        best_score = -float('inf')
        
        for hybrid in self.hybrid_solutions:
            # Handle both Node objects and tuples (code, score)
            if isinstance(hybrid, tuple):
                # If it's a tuple (code, score), create a Node object
                code, score = hybrid
                if score > best_score:
                    best_score = score
                    best_hybrid = Node(
                        code=code,
                        parent=None,
                        score=score,
                        mutation_type="hybrid_tuple"
                    )
            else:
                # If it's already a Node object
                if hybrid.score > best_score:
                    best_score = hybrid.score
                    best_hybrid = hybrid
        
        return best_hybrid
    
    def _periodic_hybridization_with_database(self, iteration: int):
        """Periodic hybridization with database integration."""
        print(f"\n🔄 Periodic Database Hybridization (iteration {iteration + 1})")
        
        # Get current best solutions from database
        top_nodes = self.db_evaluator.get_best_nodes(3)
        
        if len(top_nodes) >= 2:
            print(f"   🧬 Creating hybrid from {len(top_nodes)} top database solutions...")
            self._database_basic_hybridization()
    
    def _check_and_handle_manual_executions_with_approval(self) -> bool:
        """Check for and handle pending manual executions with user approval (current session only)."""
        manual_nodes = self._get_current_session_manual_nodes()
        
        if not manual_nodes:
            return False
            
        print(f"\n🚨 {len(manual_nodes)} nodes require manual execution")
        
        completed_any = False
        for node in manual_nodes:
            if node.node_id not in self.completed_manual_nodes:
                print(f"\n📊 Processing manual execution for node {node.node_id[:8]}...")
                
                # Call setup manual execution to show instructions and get user approval
                self.db_evaluator.db_executor._setup_manual_execution(node.node_id)
                
                # Wait for manual execution completion
                if self._wait_for_manual_execution_completion(node.node_id):
                    self.completed_manual_nodes.append(node.node_id)
                    self.db_stats.manual_executions_completed += 1
                    completed_any = True
                    print(f"✅ Manual execution completed for {node.node_id}")
                    
                    # Get updated score and update the search tree
                    updated_node = self.db_evaluator.db.get_node(node.node_id)
                    if updated_node and updated_node.score is not None:
                        self._update_search_tree_with_manual_result(updated_node)
                else:
                    print(f"❌ Manual execution not completed for {node.node_id}")
        
        # Update pending manual execution count
        self.db_stats.manual_executions_pending = len([n for n in manual_nodes if n.node_id not in self.completed_manual_nodes])
        return completed_any
    
    def _wait_for_manual_execution_completion(self, node_id: str) -> bool:
        """Wait for manual execution completion with enhanced database checking."""
        # Check if the node was already completed
        node = self.db_evaluator.db.get_node(node_id)
        if node and node.execution_status == 'completed':
            return True
        
        # Wait for completion with periodic database checks
        max_wait = self.db_config.manual_execution_timeout
        check_interval = 10  # Check every 10 seconds
        elapsed = 0
        
        print(f"🕐 Monitoring database for completion of node {node_id}...")
        
        while elapsed < max_wait:
            node = self.db_evaluator.db.get_node(node_id)
            if node and node.execution_status == 'completed':
                print(f"✅ Database shows node {node_id} completed with score: {node.score:.4f}")
                return True
            
            if elapsed > 0:  # Don't sleep on first check
                print(f"⏳ Still waiting... ({elapsed}/{max_wait}s elapsed)")
                time.sleep(check_interval)
            elapsed += check_interval
        
        print(f"⏰ Timeout after {max_wait}s waiting for node {node_id}")
        return False
    
    def _update_search_tree_with_manual_result(self, node):
        """Update the search tree with manually executed results."""
        # Create a new Node from the database node
        from core.controller.node import Node
        search_node = Node(
            code=node.code,
            score=node.score,
            mutation_type=node.mutation_type or "manual_update",
            node_id=node.node_id
        )
        
        # Add to our nodes collection
        self.nodes.add_node(search_node)
        
        # Update best node if this is better
        if search_node.score > self.best_node.score:
            self.best_node = search_node
            print(f"🏆 New best node from manual execution: {search_node.score:.4f}")
    
    def _get_current_session_manual_nodes(self):
        """Get manual execution nodes from current session only."""
        return self.db_evaluator.get_manual_required_nodes(session_filter=self.current_session_nodes)
    
    def _check_and_handle_manual_executions(self):
        """Check for and handle pending manual executions (current session only)."""
        manual_nodes = self._get_current_session_manual_nodes()
        
        if manual_nodes:
            print(f"\n🚨 {len(manual_nodes)} nodes require manual execution")
            
            if self.db_config.wait_for_manual_completion:
                for node in manual_nodes:
                    if node.node_id not in self.completed_manual_nodes:
                        print(f"⏳ Waiting for manual completion of node {node.node_id}...")
                        
                        if self.db_evaluator.wait_for_manual_completion(
                            node.node_id, 
                            self.db_config.manual_execution_timeout
                        ):
                            self.completed_manual_nodes.append(node.node_id)
                            self.db_stats.manual_executions_completed += 1
                            print(f"✅ Manual execution completed for {node.node_id}")
                            
                            # Get updated score and update the search tree
                            updated_node = self.db_evaluator.db.get_node(node.node_id)
                            if updated_node and updated_node.score is not None:
                                self._update_search_tree_with_manual_result(updated_node)
                        else:
                            print(f"⏰ Timeout waiting for manual execution of {node.node_id}")
        
        # Update pending manual execution count
        self.db_stats.manual_executions_pending = len(manual_nodes)
    
    def _export_periodic_results(self, iteration: int):
        """Export results periodically."""
        output_file = f"results_database/iteration_{iteration}_results.csv"
        if self.db_evaluator.export_results(output_file):
            self.db_stats.database_exports_created += 1
            print(f"📊 Results exported to: {output_file}")
    
    def _print_database_progress_summary(self):
        """Print database-enhanced progress summary."""
        stats = self.nodes.get_statistics()
        db_stats = self.db_evaluator.get_evaluation_statistics()
        
        print(f"\n📊 Database-Enhanced Progress Summary:")
        print(f"   • Best score: {self.best_node.score:.4f}")
        print(f"   • Total nodes: {stats['total_nodes']}")
        print(f"   • Database success rate: {db_stats['success_rate']:.1f}%")
        print(f"   • Manual executions: {self.db_stats.manual_executions_completed}")
        print(f"   • Auto-fixes applied: {self.db_stats.total_auto_fixes}")
        print(f"   • Strategies attempted: {dict(self.enhanced_stats.strategies_attempted)}")
    
    def _finalize_database_search(self, total_time: float):
        """Finalize database search with comprehensive reporting."""
        print("\n" + "=" * 70)
        print("🏁 DATABASE-ENHANCED SEARCH COMPLETED")
        print("=" * 70)
        
        # Print comprehensive final summary
        self._print_database_final_summary(total_time)
        
        # Export final results
        final_output = f"results_database/final_search_results.csv"
        self.db_evaluator.export_results(final_output)
        
        # Print session-specific database evaluation summary
        self.print_session_summary()
    
    def _print_database_final_summary(self, total_time: float):
        """Print comprehensive database-enhanced final summary."""
        stats = self.nodes.get_statistics()
        db_stats = self.db_evaluator.get_evaluation_statistics()
        
        print(f"🏆 DATABASE-ENHANCED SEARCH RESULTS:")
        print(f"   • Final Best Score: {self.best_node.score:.4f}")
        print(f"   • Total Runtime: {total_time:.1f}s")
        print(f"   • Best Solution Strategy: {self.best_node.genealogy.mutation_type}")
        print(f"   • Best Database Node: {getattr(self.best_node, 'node_id', 'Unknown')}")
        
        print(f"\n🗄️ DATABASE INTEGRATION STATISTICS:")
        print(f"   • Database Success Rate: {db_stats['success_rate']:.1f}%")
        print(f"   • Manual Executions Completed: {self.db_stats.manual_executions_completed}")
        print(f"   • Manual Executions Pending: {self.db_stats.manual_executions_pending}")
        print(f"   • Total Auto-fixes Applied: {self.db_stats.total_auto_fixes}")
        print(f"   • Database Exports Created: {self.db_stats.database_exports_created}")
        
        print(f"\n📈 MULTI-PHASE STATISTICS:")
        print(f"   • Phase 1 (Preparation): {self.enhanced_stats.preparation_phase_time:.1f}s")
        print(f"   • Phase 2 (Main Search): {total_time - self.enhanced_stats.preparation_phase_time - self.enhanced_stats.analysis_phase_time:.1f}s")
        print(f"   • Phase 3 (Analysis): {self.enhanced_stats.analysis_phase_time:.1f}s")
        
        if self.best_node.genealogy.research_ideas_used:
            print(f"   • Research Ideas Used: {len(self.best_node.genealogy.research_ideas_used)}")
    
    def _handle_search_interruption(self):
        """Handle search interruption gracefully."""
        print("🔄 Saving current progress to database...")
        self._export_periodic_results(-1)  # Emergency export
        print("💾 Progress saved. You can resume with the same database file.")
    
    def _handle_search_error(self, error: Exception):
        """Handle search errors with database cleanup."""
        print(f"🔄 Handling search error: {error}")
        self._export_periodic_results(-2)  # Error export
        print("💾 Progress saved before error.")
    
    def get_database_search_results(self) -> Dict[str, Any]:
        """Get comprehensive database-enhanced search results."""
        base_results = self.get_enhanced_results()
        db_stats = self.db_evaluator.get_evaluation_statistics()
        
        database_results = {
            **base_results,
            "database_enhanced_stats": {
                "manual_executions_completed": self.db_stats.manual_executions_completed,
                "manual_executions_pending": self.db_stats.manual_executions_pending,
                "total_auto_fixes": self.db_stats.total_auto_fixes,
                "database_exports_created": self.db_stats.database_exports_created,
                "database_path": self.db_config.db_path
            },
            "database_evaluation_stats": db_stats,
            "best_nodes_from_database": [
                {"node_id": node.node_id, "score": node.score, "mutation_type": node.mutation_type}
                for node in self.db_evaluator.get_best_nodes(5)
            ]
        }
        
        return database_results

    def print_session_summary(self):
        """Print summary showing only current session manual executions."""
        print("\n📊 DATABASE EVALUATION SUMMARY (Current Session)")
        print("=" * 50)
        
        # Get session-specific manual nodes
        session_manual_nodes = self._get_current_session_manual_nodes()
        
        # Print basic stats
        total_evaluations = len(self.current_session_nodes)
        manual_required = len(session_manual_nodes)
        
        print(f"📈 Session Evaluations: {total_evaluations}")
        print(f"🚨 Manual Required (Session): {manual_required}")
        
        if session_manual_nodes:
            print(f"\n🚨 {len(session_manual_nodes)} nodes require manual execution (current session)")
            for node in session_manual_nodes:
                error_msg = node.error_message or "Unknown error"
                # Truncate long error messages
                if len(error_msg) > 100:
                    error_msg = error_msg[:97] + "..."
                print(f"   - {node.node_id}: {error_msg}")
        else:
            print("✅ No manual executions required in current session")

    def _initialize_root(self):
        """Initialize root node with fresh code generation, then check for manual execution updates."""
        print("🌱 Initializing database root node...")
        
        # Initialize current_session_nodes if not exists
        if not hasattr(self, 'current_session_nodes'):
            self.current_session_nodes = set()
        
        # Check if database has existing nodes to resume from
        try:
            existing_nodes = self.db_evaluator.get_best_nodes(limit=10)
            if existing_nodes and len(existing_nodes) > 0:
                print(f"📂 Found {len(existing_nodes)} existing nodes in database!")
                print(f"✅ RESUMING from best database node instead of creating new root")
                
                # Load the best node from database as root
                best_db_node = existing_nodes[0]
                print(f"   Loading node {best_db_node.node_id} with score {best_db_node.score:.4f}")
                
                # Create a Node object from database node
                from .node import Node
                self.root = Node(
                    parent=None,
                    code=best_db_node.code or '',
                    score=best_db_node.score or 0.0
                )
                # Set additional attributes after creation
                self.root.node_id = best_db_node.node_id
                if hasattr(best_db_node, 'generation'):
                    self.root.generation = best_db_node.generation
                self.best_node = self.root
                
                # Add to current session tracking
                self.current_session_nodes.add(self.root.node_id)
                print(f"✅ Root node loaded from database: {self.root.node_id} (score: {self.root.score:.4f})")
                print(f"📊 Database has {len(existing_nodes)} nodes - search will continue from here")
                return
                
        except Exception as e:
            print(f"⚠️  Could not load from database: {e}")
            import traceback
            traceback.print_exc()
            print("Falling back to fresh root generation...")
        
        # Fallback: generate fresh initial code if database load failed
        print("🆕 Generating fresh initial code for root node...")
        super()._initialize_root()
        
        # Track root node in current session if it has a database ID
        if self.root and hasattr(self.root, 'node_id') and self.root.node_id:
            self.current_session_nodes.add(self.root.node_id)
            print(f"📝 Tracking root node {self.root.node_id} in session {self.session_id}")
        
        # After root is created, check if it needs manual execution or has been manually updated
        if self.root and hasattr(self.root, 'node_id') and self.root.node_id:
            # Check if this root node was manually updated in the database
            try:
                db_node = self.db_evaluator.db.get_node(self.root.node_id)
                if db_node and db_node.score is not None and db_node.score != self.root.score:
                    print(f"🔄 Found manual update for root node: score {db_node.score:.4f}")
                    print("✅ Updating root node with manually-provided score and code")
                    
                    # Update root node with database values
                    old_score = self.root.score
                    self.root.score = db_node.score
                    if db_node.code and db_node.code != self.root.code:
                        self.root.code = db_node.code
                        print("📝 Updated root node code from manual execution")
                    
                    # Update best node reference
                    self.best_node = self.root
                    
                    # Print corrected message to override the parent's misleading message
                    print(f"🎯 CORRECTED: Root node score is {self.root.score:.4f}, not {old_score:.4f}")
                    print(f"✅ Root node successfully initialized with manual execution score: {self.root.score:.4f}")
            except Exception as e:
                # If database lookup fails, continue with generated root
                print(f"⚠️ Could not check for manual updates: {e}")
                pass


def create_database_enhanced_search(
    task_config: TaskConfiguration,
    db_path: str = "enhanced_search.db",
    max_iterations: int = 20,
    enable_all_phases: bool = True
) -> DatabaseEnhancedTreeSearch:
    """
    Create a database-enhanced tree search system.
    
    Args:
        task_config: Task configuration
        db_path: Database file path
        max_iterations: Maximum search iterations
        enable_all_phases: Whether to enable all phases
        
    Returns:
        DatabaseEnhancedTreeSearch instance
    """
    db_config = DatabaseSearchConfiguration(
        db_path=db_path,
        max_iterations=max_iterations,
        enable_preparation_phase=enable_all_phases,
        enable_analysis_phase=enable_all_phases,
        multi_strategy_initialization=True,
        enable_monitoring=True,
        wait_for_manual_completion=False,  # Don't wait by default
        export_results_frequency=10
    )
    
    return DatabaseEnhancedTreeSearch(task_config, db_config)