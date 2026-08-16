"""
Database-Integrated Universal Code Evaluator
===========================================

Enhanced version of UniversalCodeEvaluator that uses the database-driven execution system
for reliable code execution with manual fallback capabilities.
"""

import os
import time
from typing import Dict, Any, Optional, Callable
from pathlib import Path

from .db_code_executor import DatabaseCodeExecutor
from ..database.db_manager import DatabaseManager


class DatabaseUniversalEvaluator:
    """
    Database-integrated universal code evaluator.
    
    Combines the domain-agnostic evaluation capabilities of UniversalCodeEvaluator
    with the reliability and persistence of the database-driven execution system.
    """
    
    def __init__(self, task_config, db_path: str = "execution_tracking.db", 
                 enable_monitoring: bool = True, wait_for_manual: bool = False, skip_auto_fixer: bool = False,
                 enable_user_feedback: bool = False, feedback_timeout: int = 30,
                 enable_code_reload: bool = False, code_reload_wait_time: int = 60, execution_timeout: int = 600):
        """
        Initialize database-integrated evaluator.
        
        Args:
            task_config: TaskConfiguration instance
            db_path: Path to SQLite database file
            enable_monitoring: Whether to enable execution monitoring
            wait_for_manual: Whether to always trigger manual execution on failures
            skip_auto_fixer: If True, skip auto-fixer entirely and go directly to manual execution
            enable_user_feedback: Whether to enable user feedback collection
            feedback_timeout: Timeout for user feedback input (seconds)
            enable_code_reload: Whether to enable code reload after execution
            execution_timeout: Timeout for node code execution (seconds)
            code_reload_wait_time: Time to wait for manual code edits (seconds)
        """
        # Initialize base evaluator (but don't load data yet)
        self.task_config = task_config
        self.domain = task_config.domain
        self.db_path = db_path
        self.enable_monitoring = enable_monitoring
        self.wait_for_manual = wait_for_manual
        self.skip_auto_fixer = skip_auto_fixer
        
        # Initialize database-driven executor
        self.db_executor = DatabaseCodeExecutor(
            task_config, db_path, wait_for_manual, skip_auto_fixer,
            enable_user_feedback, feedback_timeout,
            enable_code_reload, code_reload_wait_time, execution_timeout
        )
        self.db = self.db_executor.db
        
        # Track evaluation statistics
        self.evaluation_stats = {
            'total_evaluations': 0,
            'successful_evaluations': 0,
            'failed_evaluations': 0,
            'manual_executions_required': 0,
            'auto_fixes_applied': 0
        }
        
        # Load data using the enhanced task config
        self._load_evaluation_data()
        
        print(f"✅ Database-integrated evaluator initialized")
        print(f"   🗄️ Database: {db_path}")
        print(f"   📊 Monitoring: {'enabled' if enable_monitoring else 'disabled'}")
    
    def _load_evaluation_data(self):
        """Load evaluation data (placeholder - actual data loading handled by LLM-generated code)."""
        # Data loading is handled by the LLM-generated code itself
        # This is just a placeholder to satisfy the initialization
        pass
    
    def evaluate(self, code: str, parent_node_id: Optional[str] = None, 
                mutation_type: str = "unknown") -> Dict[str, Any]:
        """
        Evaluate code using database-driven execution system.
        
        Args:
            code: Python code to evaluate
            parent_node_id: Optional parent node ID for tree structure
            mutation_type: Type of mutation used to generate this code
            
        Returns:
            Evaluation result dictionary with enhanced database tracking
        """
        self.evaluation_stats['total_evaluations'] += 1
        
        try:
            # Create execution node in database
            node_id = self.db_executor.create_execution_node(
                code=code,
                parent_id=parent_node_id,
                mutation_type=mutation_type
            )
            
            if self.enable_monitoring:
                print(f"🔄 Evaluating node {node_id} ({mutation_type})")
            
            # Execute using database system
            result = self.db_executor.execute_node(node_id)
            
            # Update statistics
            if result['success']:
                self.evaluation_stats['successful_evaluations'] += 1
                self.evaluation_stats['auto_fixes_applied'] += result.get('auto_fixes', 0)
            else:
                self.evaluation_stats['failed_evaluations'] += 1
                
                # Check if manual execution is required
                node = self.db.get_node(node_id)
                if node and node.requires_manual_execution():
                    self.evaluation_stats['manual_executions_required'] += 1
                    self._notify_manual_execution_required(node_id, result.get('error', 'Unknown error'))
            
            # Enhance result with database information
            enhanced_result = self._enhance_result(result, node_id)
            
            if self.enable_monitoring and result['success']:
                print(f"✅ Node {node_id}: {enhanced_result['score']:.4f}")
            elif self.enable_monitoring:
                print(f"❌ Node {node_id}: {result.get('error', 'Unknown error')[:50]}...")
            
            return enhanced_result
            
        except Exception as e:
            self.evaluation_stats['failed_evaluations'] += 1
            error_msg = f"Database evaluation error: {str(e)}"
            
            if self.enable_monitoring:
                print(f"❌ Evaluation failed: {error_msg}")
            
            return {
                'success': False,
                'score': 0.0,
                'error': error_msg,
                'predictions': None,
                'auto_fixes': 0,
                'error_count': 1,
                'node_id': None,
                'execution_time': 0.0
            }
    
    def _enhance_result(self, result: Dict[str, Any], node_id: str) -> Dict[str, Any]:
        """Enhance execution result with additional database information."""
        enhanced_result = result.copy()
        
        # Add database-specific information
        enhanced_result['node_id'] = node_id
        enhanced_result['db_path'] = self.db_path
        
        # Get additional node information from database
        node = self.db.get_node(node_id)
        if node:
            enhanced_result['generation'] = node.generation
            enhanced_result['mutation_type'] = node.mutation_type
            enhanced_result['execution_duration'] = node.execution_duration
            enhanced_result['created_at'] = node.created_at.isoformat() if node.created_at else None
            
            # Add secondary scores if available
            if node.secondary_scores:
                enhanced_result['secondary_scores'] = node.secondary_scores
        
        return enhanced_result
    
    def _notify_manual_execution_required(self, node_id: str, error_message: str):
        """Notify about manual execution requirement."""
        node = self.db.get_node(node_id)
        if not node:
            return
        
        print(f"\n🚨 MANUAL EXECUTION REQUIRED")
        print("=" * 50)
        print(f"📁 Node ID: {node_id}")
        print(f"🔧 Error: {error_message}")
        print(f"📄 Code file: {node.code_file_path}")
        print(f"🔬 Mutation: {node.mutation_type}")
        print(f"\n📋 Manual Execution Instructions:")
        print(f"  1. cd /home/jupyter/MTCS_module")
        print(f"  2. conda activate pytorch")
        print(f"  3. nano {node.code_file_path}  # Fix the code")
        print(f"  4. python {node.code_file_path}")
        print(f"")
        print(f"  5. Update Score (Copy & Run - just replace <YOUR_SCORE>):")
        print(f"")
        abs_code_path = Path(node.code_file_path).resolve()
        print(f"     python manual_update_result.py \\")
        print(f"       --node-id {node_id} \\")
        print(f"       --score <YOUR_SCORE> \\")
        print(f"       --success \\")
        print(f"       --code-file {abs_code_path} \\")
        print(f"       --db {self.db.db_path}")
        print("=" * 50)
    
    def wait_for_manual_completion(self, node_id: str, max_wait: int = 300) -> bool:
        """
        Wait for manual execution completion.
        
        Args:
            node_id: ID of node to wait for
            max_wait: Maximum time to wait in seconds
            
        Returns:
            True if completed, False if timeout
        """
        return self.db_executor.wait_for_manual_completion(node_id, max_wait=max_wait)
    
    def get_execution_queue_status(self) -> Dict[str, Any]:
        """Get current execution queue status."""
        return self.db_executor.get_execution_queue_status()
    
    def get_evaluation_statistics(self) -> Dict[str, Any]:
        """Get comprehensive evaluation statistics."""
        db_stats = self.db.get_execution_statistics()
        
        combined_stats = {
            'evaluation_stats': self.evaluation_stats,
            'database_stats': db_stats,
            'success_rate': (self.evaluation_stats['successful_evaluations'] / 
                           max(self.evaluation_stats['total_evaluations'], 1)) * 100,
            'manual_execution_rate': (self.evaluation_stats['manual_executions_required'] / 
                                    max(self.evaluation_stats['total_evaluations'], 1)) * 100,
            'auto_fix_rate': (self.evaluation_stats['auto_fixes_applied'] / 
                            max(self.evaluation_stats['successful_evaluations'], 1))
        }
        
        return combined_stats
    
    def get_best_nodes(self, limit: int = 10) -> list:
        """Get best performing nodes from database."""
        return self.db.get_best_nodes(limit)
    
    def get_failed_nodes(self) -> list:
        """Get nodes that failed execution."""
        return self.db.get_failed_nodes()
    
    def get_manual_required_nodes(self, session_filter=None) -> list:
        """Get nodes requiring manual execution."""
        all_manual_nodes = self.db.get_manual_required_nodes()
        if session_filter:
            # Filter to only nodes in the provided session set
            return [node for node in all_manual_nodes if node.node_id in session_filter]
        return all_manual_nodes
    
    def export_results(self, output_file: str) -> bool:
        """Export all execution results to CSV."""
        return self.db.export_results(output_file)
    
    def print_evaluation_summary(self):
        """Print comprehensive evaluation summary."""
        stats = self.get_evaluation_statistics()
        
        print("\n📊 DATABASE EVALUATION SUMMARY")
        print("=" * 50)
        print(f"📈 Total Evaluations: {stats['evaluation_stats']['total_evaluations']}")
        print(f"✅ Successful: {stats['evaluation_stats']['successful_evaluations']}")
        print(f"❌ Failed: {stats['evaluation_stats']['failed_evaluations']}")
        print(f"🔧 Manual Required: {stats['evaluation_stats']['manual_executions_required']}")
        print(f"🛠️ Auto-fixes Applied: {stats['evaluation_stats']['auto_fixes_applied']}")
        print(f"📊 Success Rate: {stats['success_rate']:.1f}%")
        print(f"🚨 Manual Rate: {stats['manual_execution_rate']:.1f}%")
        
        if stats['database_stats']['best_score']:
            print(f"🏆 Best Score: {stats['database_stats']['best_score']:.4f}")
        
        # Show pending manual executions (all nodes by default)
        manual_nodes = self.get_manual_required_nodes()
        if manual_nodes:
            print(f"\n🚨 {len(manual_nodes)} nodes require manual execution")
            for node in manual_nodes[:3]:  # Show first 3
                print(f"   - {node.node_id}: {node.error_message}")
    
    def wait_for_manual_completion(self, node_id: str, max_wait: int = 300) -> bool:
        """
        Wait for manual execution completion.
        
        Args:
            node_id: ID of node to wait for
            max_wait: Maximum time to wait in seconds
            
        Returns:
            True if completed, False if timeout
        """
        import time
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            node = self.db.get_node(node_id)
            if node and node.execution_status in ['completed', 'failed']:
                return node.execution_status == 'completed'
            time.sleep(5)  # Check every 5 seconds
        
        return False
    
    def export_results(self, output_file: str) -> bool:
        """Export all execution results to CSV."""
        try:
            import pandas as pd
            from pathlib import Path
            
            # Create output directory
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            
            # Get all nodes from database
            all_nodes = self.db.get_all_nodes()
            
            if not all_nodes:
                print(f"⚠️ No nodes to export")
                return False
            
            # Convert to DataFrame
            data = []
            for node in all_nodes:
                data.append({
                    'node_id': node.node_id,
                    'parent_id': node.parent_id,
                    'generation': node.generation,
                    'mutation_type': node.mutation_type,
                    'execution_status': node.execution_status,
                    'score': node.score,
                    'execution_duration': node.execution_duration,
                    'auto_fixes': node.auto_fixes,
                    'error_message': node.error_message,
                    'created_at': node.created_at,
                    'updated_at': node.updated_at
                })
            
            df = pd.DataFrame(data)
            df.to_csv(output_file, index=False)
            print(f"📊 Exported {len(data)} execution records to {output_file}")
            return True
            
        except Exception as e:
            print(f"❌ Export failed: {e}")
            return False
    
    def cleanup_old_executions(self, days: int = 7) -> int:
        """Clean up old execution records."""
        return self.db.cleanup_old_nodes(days)


def create_database_evaluator(task_config, db_path: str = "execution_tracking.db") -> DatabaseUniversalEvaluator:
    """
    Create a database-integrated universal evaluator.
    
    Args:
        task_config: TaskConfiguration instance
        db_path: Path to database file
        
    Returns:
        DatabaseUniversalEvaluator instance
    """
    return DatabaseUniversalEvaluator(task_config, db_path)