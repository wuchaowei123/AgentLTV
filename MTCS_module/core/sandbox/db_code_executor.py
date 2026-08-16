"""
Database-Driven Code Executor
============================

Executes code with database tracking, automatic result storage, and manual execution fallback.
"""

import os
import subprocess
import tempfile
import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from ..database.db_manager import DatabaseManager
from ..database.models import ExecutionNode
from ..notifications.webhook_notifier import WebhookNotifier
from ..utils.user_feedback_collector import UserFeedbackCollector
from ..utils.code_change_detector import CodeChangeDetector


class DatabaseCodeExecutor:
    """Database-driven code executor with manual fallback support."""
    
    def __init__(self, task_config, db_path: str = "execution_tracking.db", 
                 wait_for_manual: bool = False, skip_auto_fixer: bool = False,
                 enable_user_feedback: bool = False, feedback_timeout: int = 30,
                 enable_code_reload: bool = False, code_reload_wait_time: int = 60, execution_timeout: int = 600):
        """
        Initialize database code executor.
        
        Args:
            task_config: TaskConfiguration instance
            db_path: Path to SQLite database
            wait_for_manual: Whether to always trigger manual execution on failures
            skip_auto_fixer: If True, skip auto-fixer entirely and go directly to manual execution
            enable_user_feedback: Whether to enable user feedback collection
            feedback_timeout: Timeout for user feedback input (seconds)
            enable_code_reload: Whether to enable code reload after execution
            code_reload_wait_time: Time to wait for manual code edits (seconds)
            execution_timeout: Timeout for node code execution (seconds)
        """
        self.task_config = task_config
        self.db = DatabaseManager(db_path)
        self.wait_for_manual = wait_for_manual
        self.skip_auto_fixer = skip_auto_fixer
        self.db_path = db_path
        self.enable_user_feedback = enable_user_feedback
        self.enable_code_reload = enable_code_reload
        self.execution_timeout = execution_timeout
        
        # Setup execution directory
        self.exe_dir = Path("core/sandbox/exe_code")
        self.exe_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize webhook notifier
        self.webhook = WebhookNotifier()
        if self.webhook.enabled:
            print("📱 Webhook notifications enabled for manual execution alerts")
        
        # Setup results directory
        self.results_dir = Path("core/sandbox/results")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if auto_code_fixer is available
        auto_fixer_path = Path.cwd() / "auto_code_fixer"
        if not auto_fixer_path.exists():
            print(f"⚠️ auto_code_fixer not found at {auto_fixer_path}")
            raise RuntimeError("auto_code_fixer directory not found")
        else:
            print(f"✅ Using Gemini Code Programmatic auto_code_fixer (Gemini 2.0 Flash) for intelligent code execution")
        
        # Initialize user feedback collector
        if enable_user_feedback:
            self.feedback_collector = UserFeedbackCollector(
                self.db, 
                enable_feedback=True, 
                timeout=feedback_timeout
            )
        else:
            self.feedback_collector = None
        
        # Initialize code change detector
        if enable_code_reload:
            self.code_change_detector = CodeChangeDetector(
                wait_time=code_reload_wait_time
            )
        else:
            self.code_change_detector = None
        
        print(f"✅ Database Code Executor initialized")
        print(f"   📁 Execution directory: {self.exe_dir}")
        print(f"   🗄️ Database: {db_path}")
        if enable_user_feedback:
            print(f"   💬 User feedback: enabled (timeout: {feedback_timeout}s)")
        if enable_code_reload:
            print(f"   🔄 Code reload: enabled (wait: {code_reload_wait_time}s)")
    
    def create_execution_node(self, code: str, parent_id: Optional[str] = None, 
                            mutation_type: str = "unknown") -> str:
        """
        Create a new execution node in the database.
        
        Args:
            code: Python code to execute
            parent_id: Optional parent node ID
            mutation_type: Type of mutation used to generate this code
            
        Returns:
            Node ID for the created node
        """
        node_id = str(uuid.uuid4())[:8]  # Short UUID for readability
        
        # Determine generation
        generation = 0
        if parent_id:
            parent_node = self.db.get_node(parent_id)
            if parent_node:
                generation = parent_node.generation + 1
        
        # Create code file path
        code_file_path = str(self.exe_dir / f"node_{node_id}.py")
        
        # Create execution node
        node = ExecutionNode(
            node_id=node_id,
            parent_id=parent_id,
            generation=generation,
            mutation_type=mutation_type,
            code=code,
            code_file_path=code_file_path,
            execution_status='pending'
        )
        
        # Save to database
        if self.db.insert_node(node):
            # Save code to file
            self._save_code_to_file(node_id, code)
            print(f"✅ Created execution node: {node_id}")
            return node_id
        else:
            raise RuntimeError(f"Failed to create execution node: {node_id}")
    
    def execute_node(self, node_id: str, timeout: int = None) -> Dict[str, Any]:
        """
        Execute a node's code and store results.
        
        Args:
            node_id: ID of node to execute
            timeout: Execution timeout in seconds (uses self.execution_timeout if None)
            
        Returns:
            Execution result dictionary
        """
        node = self.db.get_node(node_id)
        if not node:
            raise ValueError(f"Node not found: {node_id}")
        
        # Use provided timeout or default
        if timeout is None:
            timeout = self.execution_timeout
        
        print(f"🔄 Executing node: {node_id} (timeout: {timeout}s)")
        
        # Update status to executing
        self.db.update_execution_status(node_id, 'executing')
        
        try:
            # Prepare code for execution
            wrapped_code = self._wrap_code_for_domain(node.code, node_id)
            
            # Check if we should skip automatic execution entirely and go directly to manual
            if self.skip_auto_fixer:
                print("🚨 Skip auto-fixer mode enabled - going directly to manual execution")
                print("   ℹ️  Skipping both direct execution and auto-fixer attempts")
                
                # Save the WRAPPED code to file for manual execution (includes evaluation wrapper)
                code_file = Path.cwd() / self.exe_dir / f"node_{node_id}.py"
                with open(code_file, 'w') as f:
                    f.write(f"# Execution Node: {node_id}\n")
                    f.write(f"# Generated: {datetime.now().isoformat()}\n\n")
                    f.write(wrapped_code)  # Save wrapped code with evaluation wrapper
                print(f"💾 Saved wrapped code (with evaluation wrapper) to: {code_file}")
                
                # Check if this node was already manually executed
                existing_node = self.db.get_node(node_id)
                if existing_node and existing_node.score is not None and existing_node.execution_status == 'completed':
                    print(f"✅ Found existing manual execution result: score = {existing_node.score:.4f}")
                    result = {
                        'success': True,
                        'score': existing_node.score,
                        'predictions': existing_node.predictions,
                        'output': '',
                        'error': None,
                        'auto_fixes': 0,
                        'error_count': 0,
                        'node_id': node_id,
                        'secondary_scores': existing_node.secondary_scores or {}
                    }
                else:
                    # No manual execution yet, trigger manual execution workflow
                    if self.wait_for_manual:
                        # Mark node as requiring manual execution and send webhook
                        self.db.update_execution_status(node_id, 'manual_required', "Manual execution requested (skip-auto-fixer mode)")
                        self._setup_manual_execution(node_id)
                        
                        # After user types 'yes', immediately get result from database
                        # (JSON processing already happened in _wait_for_user_approval)
                        updated_node = self.db.get_node(node_id)
                        
                        if updated_node and updated_node.score is not None and updated_node.execution_status == 'completed':
                            print(f"✅ Retrieved manual execution result: score = {updated_node.score:.4f}")
                            result = {
                                'success': True,
                                'score': updated_node.score,
                                'predictions': updated_node.predictions,
                                'output': '',
                                'error': None,
                                'auto_fixes': 0,
                                'error_count': 0,
                                'node_id': node_id,
                                'secondary_scores': updated_node.secondary_scores or {}
                            }
                        else:
                            print(f"⚠️  No score found after manual execution - continuing with score=0")
                            result = {
                                'success': False,
                                'score': 0.0,
                                'predictions': None,
                                'output': '',
                                'error': 'Manual execution not completed',
                                'auto_fixes': 0,
                                'error_count': 0,
                                'node_id': node_id
                            }
                    else:
                        # Not waiting for manual, just return failure
                        result = {
                            'success': False,
                            'score': 0.0,
                            'predictions': None,
                            'output': '',
                            'error': 'Auto-fixer skipped - manual execution requested',
                            'auto_fixes': 0,
                            'error_count': 0,
                            'node_id': node_id
                        }
            else:
                # Normal flow: Try direct execution first (without auto-fixer)
                print("🚀 STEP 1: Trying direct execution first...")
                direct_result = self._try_direct_execution(wrapped_code, node_id, timeout)
                
                if direct_result['success'] and direct_result.get('score', 0) > 0:
                    print(f"✅ Direct execution succeeded! Score: {direct_result['score']:.4f}")
                    print("   ℹ️  Skipping auto-fixer (not needed)")
                    result = direct_result
                else:
                    # Direct execution failed, proceed to auto-fixer
                    if direct_result.get('error'):
                        print(f"❌ Direct execution failed: {direct_result['error'][:200]}")
                    else:
                        print(f"⚠️  Direct execution completed but no score found")
                    print("🔧 STEP 2: Proceeding to auto-fixer...\n")
                    
                    # Execute with auto code fixer
                    result = self._execute_with_auto_code_fixer(wrapped_code, node_id, timeout)
            
            if result['success']:
                # Store successful result
                self.db.update_execution_result(
                    node_id,
                    result['score'],
                    result.get('secondary_scores'),
                    result.get('predictions'),
                    result.get('auto_fixes', 0)
                )
                print(f"✅ Node {node_id} completed: score = {result['score']:.4f}")
                
                # NEW: Collect user feedback if enabled
                if self.feedback_collector:
                    code_lines = node.code.split('\n')
                    code_snippet = '\n'.join(code_lines[:10])
                    execution_time = result.get('execution_time', 0)
                    
                    feedback = self.feedback_collector.collect_feedback(
                        node_id=node_id,
                        score=result['score'],
                        execution_time=execution_time,
                        code_snippet=code_snippet
                    )
                    
                    if feedback:
                        result['user_feedback'] = feedback.feedback_text
                        result['user_feedback_priority'] = feedback.priority
                
                # NEW: Check for manual code edits if enabled
                if self.code_change_detector:
                    code_file_path = str(Path.cwd() / self.exe_dir / f"node_{node_id}.py")
                    original_code = wrapped_code  # Use wrapped code
                    
                    changed, new_code = self.code_change_detector.wait_and_check_for_changes(
                        file_path=code_file_path,
                        original_code=original_code,
                        node_id=node_id
                    )
                    
                    if changed and new_code:
                        # Update code in database
                        self.db.update_node(
                            node_id=node_id,
                            code=new_code
                        )
                        
                        # Mark as manually edited
                        result['manually_edited'] = True
                        result['original_code'] = original_code
                        result['updated_code'] = new_code
                        
                        print(f"   ✅ Code updated with manual edits")
                        
                        # Optionally re-execute if code might affect score
                        if self._code_might_affect_score(original_code, new_code):
                            print(f"   🔄 Re-executing with updated code...")
                            
                            # Re-execute
                            rerun_result = self._execute_code_file(code_file_path, timeout)
                            
                            if rerun_result['success'] and rerun_result.get('score'):
                                old_score = result['score']
                                new_score = rerun_result['score']
                                
                                # Update with new result
                                self.db.update_execution_result(
                                    node_id,
                                    new_score,
                                    rerun_result.get('secondary_scores'),
                                    rerun_result.get('predictions'),
                                    result.get('auto_fixes', 0)
                                )
                                
                                result['score'] = new_score
                                result['predictions'] = rerun_result.get('predictions')
                                
                                improvement = new_score - old_score
                                if improvement > 0:
                                    print(f"   🎉 Manual edit improved score: {old_score:.4f} → {new_score:.4f} (+{improvement:.4f})")
                                else:
                                    print(f"   ℹ️  New score: {old_score:.4f} → {new_score:.4f} ({improvement:.4f})")
            else:
                # Handle failure
                self._handle_execution_failure(node_id, result['error'])
            
            return result
            
        except Exception as e:
            error_msg = f"Execution error: {str(e)}"
            self._handle_execution_failure(node_id, error_msg)
            return {
                'success': False,
                'score': 0.0,
                'error': error_msg,
                'node_id': node_id
            }
    
    def _wrap_code_for_domain(self, code: str, node_id: str) -> str:
        """Execute code directly without data injection - LLM generates complete self-contained code."""
        # Use _manual.json for consistent filename that wait_for_manual_completion can find
        result_file = f"/tmp/ai_result_{node_id}_manual.json"
        
        # Only add result saving wrapper - no data injection
        eval_wrapper = self._create_evaluation_wrapper(
            self.task_config.evaluation_metric,
            self.task_config.higher_is_better,
            result_file
        )
        
        wrapped_code = f"""
# User generated code (complete and self-contained)
{code}

# Evaluation and result saving
{eval_wrapper}
"""
        return wrapped_code
    
    def _create_data_preparation_code(self, timestamp: int) -> str:
        """Create code to load data for the domain."""
        train_file = f"/tmp/train_data_{timestamp}.csv"
        val_file = f"/tmp/val_data_{timestamp}.csv"
        
        # Save data to temporary files
        try:
            train_df = self.task_config.load_data('train')
            val_df = self.task_config.load_data('validation')
            
            train_df.to_csv(train_file, index=False)
            val_df.to_csv(val_file, index=False)
            
        except Exception as e:
            print(f"⚠️ Failed to prepare data files: {e}")
            # Create dummy data fallback
            return f"""
import pandas as pd
import numpy as np

print("🔧 Creating dummy data for testing...")
np.random.seed(42)
train_df = pd.DataFrame({{
    'feature1': np.random.randn(100),
    'feature2': np.random.randn(100),
    'target': np.random.randint(0, 2, 100)
}})
val_df = pd.DataFrame({{
    'feature1': np.random.randn(50),
    'feature2': np.random.randn(50),
    'target': np.random.randint(0, 2, 50)
}})
"""
        
        return f"""
import pandas as pd

# Load data from temporary files
train_df = pd.read_csv('{train_file}')
val_df = pd.read_csv('{val_file}')

print(f"✅ Loaded data: {{len(train_df)}} train, {{len(val_df)}} validation samples")
"""
    
    def _create_evaluation_wrapper(self, metric: str, higher_is_better: bool, result_file: str) -> str:
        """Create evaluation code for the domain."""
        output_var = self.task_config.get_output_variable()
        return f"""
# Save results to JSON (for AI system to collect)
try:
    if '{output_var}' not in locals():
        raise ValueError("{output_var} not defined by generated code")
    
    # Check if user code already calculated score
    # Try multiple variable names that might contain the score
    score_candidates = [
        'score',
        '{metric.lower()}_score',
        'f1_score_value',
        'f1',
        'micro_f1',
        'final_score',
        'test_f1',
        'f1_micro'
    ]
    
    final_score = None
    for candidate in score_candidates:
        if candidate in locals():
            final_score = locals()[candidate]
            print(f"📊 Using score from variable '{{candidate}}': {{final_score:.4f}}")
            break
    
    if final_score is None:
        # Try to find any variable containing 'f1' or 'score'
        for var_name in list(locals().keys()):
            if ('f1' in var_name.lower() or 'score' in var_name.lower()) and \
               isinstance(locals()[var_name], (int, float)):
                final_score = locals()[var_name]
                print(f"📊 Found score in variable '{{var_name}}': {{final_score:.4f}}")
                break
    
    if final_score is None:
        print("⚠️  No score variable found - setting to 0.0")
        print("   Hint: Set 'score = f1_score(...)' in your code")
        final_score = 0.0
    
    # Save results
    import json
    result_data = {{
        'score': float(final_score),
        'predictions': {output_var}.tolist() if hasattr({output_var}, 'tolist') else (
            list({output_var}) if hasattr({output_var}, '__iter__') and not isinstance({output_var}, (str, dict)) else {output_var}
        ),
        'metric': '{metric}',
        'higher_is_better': {higher_is_better},
        'success': True
    }}
    
    with open('{result_file}', 'w') as f:
        json.dump(result_data, f)
    
    print(f"✅ Results saved to: {result_file}")
    
except Exception as e:
    # Save error result
    import json
    result_data = {{
        'score': 0.0,
        'error': str(e),
        'success': False
    }}
    
    with open('{result_file}', 'w') as f:
        json.dump(result_data, f)
    
    print(f"❌ Result saving error: {{e}}")
    raise e
"""
    
    def _try_direct_execution(self, code: str, node_id: str, timeout: int) -> Dict[str, Any]:
        """
        Try direct execution without auto-fixer (fast path).
        
        Args:
            code: Code to execute
            node_id: Node ID
            timeout: Execution timeout
            
        Returns:
            Result dictionary with success status, score, etc.
        """
        # Save code to file
        code_file = Path.cwd() / self.exe_dir / f"node_{node_id}.py"
        with open(code_file, 'w') as f:
            f.write(code)
        
        try:
            # Run code directly with subprocess
            cmd = f'source ~/.bashrc && conda activate pytorch && timeout {timeout} python {code_file}'
            
            result = subprocess.run(
                ['bash', '-c', cmd],
                capture_output=True,
                text=True,
                timeout=timeout + 10
            )
            
            output = result.stdout + result.stderr
            
            # Wait for result file to be written
            time.sleep(0.5)
            
            # Try to extract score from result file
            score, predictions, file_success = self._extract_results_from_file(node_id)
            
            # Check if execution was successful
            if result.returncode == 0 and score > 0:
                return {
                    'success': True,
                    'score': score,
                    'predictions': predictions,
                    'output': output,
                    'error': None,
                    'auto_fixes': 0,
                    'error_count': 0,
                    'node_id': node_id
                }
            else:
                # Execution failed or no score
                error_msg = output if result.returncode != 0 else "No score found in output"
                return {
                    'success': False,
                    'score': score,  # might be 0
                    'predictions': predictions,
                    'output': output,
                    'error': error_msg,
                    'auto_fixes': 0,
                    'error_count': 1,
                    'node_id': node_id
                }
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'score': 0.0,
                'predictions': None,
                'output': '',
                'error': f'Timeout after {timeout} seconds',
                'auto_fixes': 0,
                'error_count': 1,
                'node_id': node_id
            }
        except Exception as e:
            return {
                'success': False,
                'score': 0.0,
                'predictions': None,
                'output': '',
                'error': f'Direct execution error: {str(e)}',
                'auto_fixes': 0,
                'error_count': 1,
                'node_id': node_id
            }
    
    def _execute_with_auto_code_fixer(self, code: str, node_id: str, timeout: int) -> Dict[str, Any]:
        """Execute code using Claude Code CLI auto_code_fixer with intelligent error fixing."""
        # Save code to file with absolute path
        code_file = Path.cwd() / self.exe_dir / f"node_{node_id}.py"
        with open(code_file, 'w') as f:
            f.write(code)
        
        try:
            # Import the Claude Code CLI auto code fixer
            import sys
            auto_fixer_path = Path.cwd() / "auto_code_fixer"
            if str(auto_fixer_path) not in sys.path:
                sys.path.insert(0, str(auto_fixer_path))
            
            from gemini_code_programmatic_fixer import GeminiCodeProgrammaticFixer
            fixer = GeminiCodeProgrammaticFixer(max_attempts=3)  # Allow up to 3 fix attempts
            print("✅ Using Gemini Code Programmatic auto_code_fixer (Gemini 2.0 Flash)")
            
            print(f"🤖 Executing code with auto-fixer: {code_file}")
            
            # Execute with auto-fixing capability
            success, final_output = fixer.auto_fix_and_run(str(code_file), run_timeout=timeout)
            
            # Parse output and error from final_output
            if success:
                output = final_output
                error_output = ""
                # Count auto fixes from the final output
                auto_fixes = final_output.count("✅ Fix applied successfully!") if final_output else 0
            else:
                output = final_output[:2000] if final_output else ""  # Limit output size
                error_output = "Code execution failed after auto-fixing attempts"
                auto_fixes = final_output.count("✅ Fix applied successfully!") if final_output else 0
            
            error_count = 0 if success else 1
            
            # Wait a moment for the result file to be written
            import time
            time.sleep(0.5)
            
            # Extract results from the result file
            score, predictions, file_success = self._extract_results_from_file(node_id)
            
            # If no score from file but code succeeded, try parsing from output
            if score == 0.0 and success:
                # Try to extract score from output
                import re
                score_match = re.search(r'[Ff]inal score:\s*([\d.]+)', output)
                if score_match:
                    extracted_score = float(score_match.group(1))
                    score = extracted_score
                    print(f"📊 Extracted score from output: {score:.4f}")
            
            print(f"📊 Auto-fixer completed: success={success}, score={score:.4f}, auto_fixes={auto_fixes}")
            
            return {
                'success': success and (file_success or score > 0.0),
                'score': score,
                'predictions': predictions,
                'output': output,
                'error': error_output or '',
                'auto_fixes': auto_fixes,
                'error_count': error_count,
                'node_id': node_id
            }
            
        except subprocess.TimeoutExpired as e:
            error_message = f'Execution timed out after {timeout} seconds'
            print(f"❌ Node {node_id} execution timed out after {timeout}s")
            print(f"   This suggests the ML task is computationally intensive")
            print(f"   Consider optimizing the generated code or increasing timeout further")
            
            # Update database with timeout status
            self.db.update_execution_status(node_id, 'failed', error_message)
            
            return {
                'success': False,
                'score': 0.0,
                'predictions': None,
                'output': '',
                'error': error_message,
                'auto_fixes': 0,
                'error_count': 1,
                'node_id': node_id
            }
        except Exception as e:
            return {
                'success': False,
                'score': 0.0,
                'predictions': None,
                'output': '',
                'error': f'Auto-fixer execution failed: {str(e)}',
                'auto_fixes': 0,
                'error_count': 1,
                'node_id': node_id
            }
    
    def _extract_results_from_file(self, node_id: str) -> tuple:
        """Extract results from the temporary result file."""
        try:
            # Look for result files with this node_id with retry logic
            import glob
            import time
            pattern = f"/tmp/ai_result_{node_id}_*.json"
            
            # Retry a few times in case the file is still being written
            for attempt in range(3):
                result_files = glob.glob(pattern)
                if result_files:
                    break
                time.sleep(0.2)  # Wait 200ms between attempts
            
            if not result_files:
                print(f"⚠️ No result file found for node {node_id} after retries")
                print(f"   Pattern searched: {pattern}")
                # List files that might be related for debugging
                all_ai_results = glob.glob("/tmp/ai_result_*.json")
                recent_files = [f for f in all_ai_results if node_id in f]
                if recent_files:
                    print(f"   Found related files: {recent_files}")
                return 0.0, None, False
            
            # Use the most recent result file
            result_file = max(result_files, key=os.path.getctime)
            
            with open(result_file, 'r') as f:
                result_data = json.load(f)
            
            score = result_data.get('score', 0.0)
            predictions = result_data.get('predictions', None)
            success = result_data.get('success', False)
            
            # Clean up result file
            try:
                os.unlink(result_file)
            except:
                pass
            
            return score, predictions, success
            
        except Exception as e:
            print(f"❌ Failed to extract results for node {node_id}: {e}")
            return 0.0, None, False
    
    def _handle_execution_failure(self, node_id: str, error_message: str):
        """Handle execution failure - decide between retry or manual execution."""
        print(f"❌ Node {node_id} execution failed: {error_message}")
        
        # Check if manual execution is always required (user flag)
        if self.wait_for_manual:
            print(f"🚨 Manual execution mode enabled - triggering manual intervention")
            self.db.update_execution_status(node_id, 'manual_required', error_message)
            self._setup_manual_execution(node_id)
            return
        
        # Otherwise, check if this is a severe error requiring manual intervention
        severe_errors = [
            "timeout", "import error", "module not found", 
            "syntax error", "indentation error", "memory error"
        ]
        
        error_lower = error_message.lower()
        requires_manual = any(severe in error_lower for severe in severe_errors)
        
        if requires_manual:
            # Mark for manual execution
            self.db.update_execution_status(node_id, 'manual_required', error_message)
            self._setup_manual_execution(node_id)
        else:
            # Mark as failed for potential retry
            self.db.update_execution_status(node_id, 'failed', error_message)
    
    def _setup_manual_execution(self, node_id: str):
        """Setup manual execution for a node."""
        node = self.db.get_node(node_id)
        if not node:
            return
        
        print(f"\n🚨 AUTOMATIC EXECUTION FAILED - MANUAL INTERVENTION REQUIRED")
        print("=" * 80)
        print(f"🆔 Node ID: {node_id}")
        print(f"📁 Generated Script Location: {node.code_file_path}")
        print(f"❌ Auto-Execution Error: {node.error_message}")
        print("=" * 80)
        
        # Send webhook notification
        abs_code_path = Path(node.code_file_path).resolve()
        self.webhook.send_manual_execution_alert(
            node_id=node_id,
            code_file=str(abs_code_path),
            error_message=node.error_message or "Unknown error",
            db_path=self.db_path,
            project_dir="/home/jupyter/scientific-ai-system"
        )
        
        print(f"\n📋 MANUAL EXECUTION INSTRUCTIONS:")
        print(f"  ┌─ Step 1: Navigate to Project Directory")
        print(f"  │   cd /home/jupyter/scientific-ai-system")
        print(f"  │")
        print(f"  ├─ Step 2: Activate Environment") 
        print(f"  │   conda activate pytorch")
        print(f"  │")
        print(f"  ├─ Step 3: Fix and Run the Generated Script")
        print(f"  │   nano {abs_code_path}")
        print(f"  │   python {abs_code_path}")
        print(f"  │")
        print(f"  └─ Step 4: Update Score in Database (Copy & Run This Command)")
        print(f"")
        print(f"      python manual_update_result.py \\")
        print(f"        --node-id {node_id} \\")
        print(f"        --score <YOUR_SCORE> \\")
        print(f"        --success \\")
        print(f"        --code-file {abs_code_path} \\")
        print(f"        --db {self.db.db_path}")
        print(f"")
        print(f"      ⚠️  Just replace <YOUR_SCORE> with the actual score!")
        print(f"")
        print(f"💡 EXAMPLE: If your script achieved F1 score of 0.8542:")
        print(f"      python manual_update_result.py --node-id {node_id} --score 0.8542 --success --code-file {abs_code_path} --db {self.db.db_path}")
        print("=" * 80)
        
        # Wait for user approval before continuing
        self._wait_for_user_approval(node_id)
    
    def _wait_for_user_approval(self, node_id: str):
        """Wait for user approval before continuing execution."""
        print(f"\n🚨 WAITING FOR USER APPROVAL")
        print("=" * 50)
        print(f"⏸️  System execution is PAUSED for node {node_id}")
        print(f"📝 Please complete the manual execution steps above")
        print(f"✅ Type 'yes' when ready to continue: ", end="", flush=True)
        
        while True:
            try:
                user_input = input().strip().lower()
                if user_input == 'yes':
                    print(f"✅ User approved! Continuing execution...")
                    
                    # Check for JSON result file immediately (no waiting)
                    json_result_file = Path(f"/tmp/ai_result_{node_id}_manual.json")
                    if json_result_file.exists():
                        print(f"✅ Found JSON result file: {json_result_file}")
                        success = self._process_manual_json_result(node_id, json_result_file)
                        if success:
                            updated_node = self.db.get_node(node_id)
                            if updated_node and updated_node.score is not None:
                                print(f"📊 Updated score from JSON: {updated_node.score:.4f}")
                    else:
                        # Check database as fallback
                        updated_node = self.db.get_node(node_id)
                        if updated_node and updated_node.score is not None:
                            print(f"📊 Found score in database: {updated_node.score:.4f}")
                        else:
                            print(f"⚠️  No JSON file or database score found - continuing anyway")
                    
                    break
                else:
                    print(f"❌ Please type 'yes' to continue (you entered: '{user_input}'): ", end="", flush=True)
            except KeyboardInterrupt:
                print(f"\n⚠️ Keyboard interrupt detected. Type 'yes' to continue or Ctrl+C again to exit: ", end="", flush=True)
            except EOFError:
                print(f"\n⚠️ Input ended. Assuming 'yes' to continue...")
                break
    
    def _save_code_to_file(self, node_id: str, code: str):
        """Save code to execution file."""
        code_file = self.exe_dir / f"node_{node_id}.py"
        with open(code_file, 'w') as f:
            f.write(f"# Execution Node: {node_id}\n")
            f.write(f"# Generated: {datetime.now().isoformat()}\n\n")
            f.write(code)
        
        # Update database with file path
        self.db.update_node(node_id, {'code_file_path': str(code_file)})
    
    def get_execution_queue_status(self) -> Dict[str, Any]:
        """Get current execution queue status."""
        pending = len(self.db.get_pending_nodes())
        executing = len(self.db.get_nodes_by_status('executing'))
        manual_required = len(self.db.get_manual_required_nodes())
        completed = len(self.db.get_completed_nodes())
        failed = len(self.db.get_failed_nodes())
        
        return {
            'pending': pending,
            'executing': executing,
            'manual_required': manual_required,
            'completed': completed,
            'failed': failed,
            'total': pending + executing + manual_required + completed + failed
        }
    
    def wait_for_manual_completion(self, node_id: str, check_interval: int = 5, max_wait: int = 86400) -> bool:
        """
        Wait for manual execution completion.
        First checks for JSON result file, then checks database.
        
        Args:
            node_id: ID of node to wait for
            check_interval: How often to check (seconds)
            max_wait: Maximum time to wait (seconds)
            
        Returns:
            True if completed, False if timeout
        """
        elapsed = 0
        json_result_file = Path(f"/tmp/ai_result_{node_id}_manual.json")
        
        while elapsed < max_wait:
            # First, check for JSON result file
            if json_result_file.exists():
                print(f"✅ Found JSON result file: {json_result_file}")
                success = self._process_manual_json_result(node_id, json_result_file)
                if success:
                    return True
            
            # Then check database (for manual_update_result.py updates)
            node = self.db.get_node(node_id)
            if node and node.execution_status == 'completed':
                print(f"✅ Manual execution completed for node {node_id} (via database)")
                return True
            
            time.sleep(check_interval)
            elapsed += check_interval
        
        print(f"⏰ Timeout waiting for manual execution of node {node_id}")
        return False
    
    def _process_manual_json_result(self, node_id: str, json_file: Path) -> bool:
        """
        Process JSON result file from manual execution.
        
        Args:
            node_id: Node ID
            json_file: Path to JSON result file
            
        Returns:
            True if successfully processed
        """
        try:
            with open(json_file, 'r') as f:
                result_data = json.load(f)
            
            score = result_data.get('score', 0.0)
            success = result_data.get('success', False)
            predictions = result_data.get('predictions')
            error = result_data.get('error')
            secondary_scores = result_data.get('secondary_scores', {})
            
            if not success:
                print(f"❌ JSON result indicates failure: {error}")
                self.db.update_execution_status(node_id, 'failed', error or "Manual execution failed")
                return False
            
            # Update database with result
            print(f"📊 Updating node {node_id} with score from JSON: {score:.4f}")
            update_success = self.db.update_execution_result(
                node_id,
                score,
                secondary_scores,
                predictions,
                0  # auto_fixes = 0 for manual execution
            )
            
            if update_success:
                print(f"✅ Successfully updated node {node_id} from JSON result")
                # Clean up JSON file
                json_file.unlink()
                return True
            else:
                print(f"❌ Failed to update database for node {node_id}")
                return False
                
        except Exception as e:
            print(f"❌ Error processing JSON result file: {e}")
            return False
    
    def _execute_code_file(self, file_path: str, timeout: int = 600) -> Dict[str, Any]:
        """
        Execute a code file and return result.
        
        Args:
            file_path: Path to Python file to execute
            timeout: Execution timeout in seconds
            
        Returns:
            Execution result dictionary
        """
        try:
            # Run the code file
            cmd = f'source ~/.bashrc && conda activate pytorch && timeout {timeout} python {file_path}'
            
            result = subprocess.run(
                ['bash', '-c', cmd],
                capture_output=True,
                text=True,
                timeout=timeout + 10
            )
            
            output = result.stdout + result.stderr
            success = result.returncode == 0
            
            if not success:
                return {
                    'success': False,
                    'score': 0.0,
                    'output': output,
                    'error': f"Exit code: {result.returncode}"
                }
            
            # Try to extract score from output
            score = self._extract_score_from_output(output)
            
            return {
                'success': True if score is not None else False,
                'score': score or 0.0,
                'output': output,
                'error': None if score is not None else "Could not extract score from output"
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'score': 0.0,
                'output': '',
                'error': f"Timeout after {timeout} seconds"
            }
        except Exception as e:
            return {
                'success': False,
                'score': 0.0,
                'output': '',
                'error': f"Execution error: {e}"
            }
    
    def _extract_score_from_output(self, output: str) -> Optional[float]:
        """Extract score from execution output."""
        import re
        
        # Try different patterns
        patterns = [
            r'Final\s+score[:\s]+([0-9.]+)',
            r'score[:\s]+([0-9.]+)',
            r'F1[:\s]+([0-9.]+)',
            r'Accuracy[:\s]+([0-9.]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        
        return None