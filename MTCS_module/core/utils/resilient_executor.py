#!/usr/bin/env python3
"""
Resilient Executor - Error Recovery and Continuation System
===========================================================

Provides error recovery and continuation functionality for long-running
processes that may encounter errors during execution.
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class ExecutionState:
    """Tracks the execution state of a batch process."""
    session_id: str
    start_time: float
    current_index: int
    total_items: int
    completed_items: List[str]
    failed_items: List[Dict[str, Any]]
    results: Dict[str, Any]
    last_checkpoint: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'ExecutionState':
        """Load from dictionary."""
        return ExecutionState(**data)


class ResilientExecutor:
    """
    Resilient executor that can recover from errors and continue processing.
    
    Features:
    - Automatic checkpointing
    - Error recovery
    - Progress tracking
    - Resume from last checkpoint
    """
    
    def __init__(self, checkpoint_dir: str = "/tmp/checkpoints"):
        """
        Initialize resilient executor.
        
        Args:
            checkpoint_dir: Directory to store checkpoint files
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.state: Optional[ExecutionState] = None
    
    def execute_batch(self,
                     items: List[Any],
                     process_func: Callable,
                     session_id: str = None,
                     checkpoint_interval: int = 1,
                     continue_on_error: bool = True,
                     max_retries: int = 2) -> Dict[str, Any]:
        """
        Execute a batch of items with error recovery.
        
        Args:
            items: List of items to process
            process_func: Function to process each item
            session_id: Unique session identifier
            checkpoint_interval: Save checkpoint every N items
            continue_on_error: Whether to continue after errors
            max_retries: Maximum number of retries per item
            
        Returns:
            Dictionary with execution results
        """
        # Generate or load session
        if session_id is None:
            session_id = f"session_{int(time.time())}"
        
        # Try to load existing checkpoint
        checkpoint_file = self.checkpoint_dir / f"{session_id}.json"
        
        if checkpoint_file.exists():
            print(f"📂 Found existing checkpoint for session: {session_id}")
            print(f"   Loading state from: {checkpoint_file}")
            self.state = self._load_checkpoint(checkpoint_file)
            print(f"   ✓ Resuming from item {self.state.current_index}/{self.state.total_items}")
            print(f"   ✓ Already completed: {len(self.state.completed_items)} items")
        else:
            print(f"🆕 Starting new session: {session_id}")
            self.state = ExecutionState(
                session_id=session_id,
                start_time=time.time(),
                current_index=0,
                total_items=len(items),
                completed_items=[],
                failed_items=[],
                results={},
                last_checkpoint=time.time()
            )
        
        # Process items
        print(f"\n🚀 Processing {self.state.total_items} items...")
        print(f"   Continue on error: {continue_on_error}")
        print(f"   Checkpoint interval: {checkpoint_interval}")
        print(f"   Max retries: {max_retries}")
        
        for i in range(self.state.current_index, len(items)):
            item = items[i]
            item_id = self._get_item_id(item, i)
            
            print(f"\n{'='*60}")
            print(f"Processing item {i+1}/{len(items)}: {item_id}")
            print(f"{'='*60}")
            
            retry_count = 0
            success = False
            error_info = None
            
            while retry_count <= max_retries and not success:
                try:
                    if retry_count > 0:
                        print(f"🔄 Retry attempt {retry_count}/{max_retries}")
                    
                    result = process_func(item)
                    
                    # Store result
                    self.state.results[item_id] = result
                    self.state.completed_items.append(item_id)
                    success = True
                    
                    print(f"✅ Successfully processed: {item_id}")
                    
                except Exception as e:
                    retry_count += 1
                    error_info = {
                        'item_id': item_id,
                        'item_index': i,
                        'error': str(e),
                        'error_type': type(e).__name__,
                        'retry_count': retry_count,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    print(f"❌ Error processing {item_id}: {str(e)}")
                    
                    if retry_count <= max_retries:
                        print(f"   Will retry ({retry_count}/{max_retries})...")
                        time.sleep(1)  # Brief pause before retry
                    else:
                        print(f"   Max retries reached. {'Continuing' if continue_on_error else 'Stopping'}...")
            
            # Handle failure after all retries
            if not success:
                self.state.failed_items.append(error_info)
                
                if not continue_on_error:
                    print(f"\n⛔ Stopping execution due to error")
                    self._save_checkpoint()
                    raise RuntimeError(f"Execution stopped at item {i}: {error_info['error']}")
                else:
                    print(f"⚠️  Continuing despite failure...")
            
            # Update state
            self.state.current_index = i + 1
            
            # Checkpoint if needed
            if (i + 1) % checkpoint_interval == 0 or not success:
                self._save_checkpoint()
                print(f"💾 Checkpoint saved at item {i+1}")
        
        # Final checkpoint
        self._save_checkpoint()
        
        # Generate summary
        elapsed = time.time() - self.state.start_time
        summary = {
            'session_id': session_id,
            'total_items': self.state.total_items,
            'completed': len(self.state.completed_items),
            'failed': len(self.state.failed_items),
            'elapsed_time': elapsed,
            'results': self.state.results,
            'failed_items': self.state.failed_items
        }
        
        print(f"\n{'='*60}")
        print(f"📊 Execution Summary for {session_id}")
        print(f"{'='*60}")
        print(f"Total items: {summary['total_items']}")
        print(f"Completed: {summary['completed']}")
        print(f"Failed: {summary['failed']}")
        print(f"Success rate: {summary['completed']/summary['total_items']*100:.1f}%")
        print(f"Elapsed time: {elapsed:.1f} seconds")
        print(f"{'='*60}")
        
        return summary
    
    def _get_item_id(self, item: Any, index: int) -> str:
        """Extract or generate an ID for an item."""
        if isinstance(item, dict) and 'id' in item:
            return str(item['id'])
        elif isinstance(item, str):
            return item
        elif hasattr(item, 'name'):
            return str(item.name)
        else:
            return f"item_{index}"
    
    def _save_checkpoint(self):
        """Save current state to checkpoint file."""
        checkpoint_file = self.checkpoint_dir / f"{self.state.session_id}.json"
        self.state.last_checkpoint = time.time()
        
        with open(checkpoint_file, 'w') as f:
            json.dump(self.state.to_dict(), f, indent=2)
    
    def _load_checkpoint(self, checkpoint_file: Path) -> ExecutionState:
        """Load state from checkpoint file."""
        with open(checkpoint_file, 'r') as f:
            data = json.load(f)
        return ExecutionState.from_dict(data)
    
    def cleanup_checkpoint(self, session_id: str = None):
        """Remove checkpoint file after successful completion."""
        if session_id is None and self.state:
            session_id = self.state.session_id
        
        if session_id:
            checkpoint_file = self.checkpoint_dir / f"{session_id}.json"
            if checkpoint_file.exists():
                checkpoint_file.unlink()
                print(f"🧹 Cleaned up checkpoint: {checkpoint_file}")


# Example usage and testing
if __name__ == "__main__":
    # Example: Process a list of files
    def process_file(file_path: str) -> Dict[str, Any]:
        """Example processing function."""
        print(f"   Processing: {file_path}")
        # Simulate some work
        time.sleep(0.5)
        return {'file': file_path, 'status': 'processed'}
    
    # Test the resilient executor
    executor = ResilientExecutor()
    
    files = [f"file_{i}.txt" for i in range(10)]
    
    results = executor.execute_batch(
        items=files,
        process_func=process_file,
        session_id="test_session",
        checkpoint_interval=3,
        continue_on_error=True
    )
    
    print(f"\n✅ Final results: {len(results['results'])} items processed")

