"""
Code Change Detector for Manual Edits
=====================================

Detects manual code changes after execution to incorporate user improvements.
"""

import hashlib
import time
from pathlib import Path
from typing import Optional, Tuple


class CodeChangeDetector:
    """Detect manual code changes after execution."""
    
    def __init__(self, wait_time: int = 60):
        """
        Initialize change detector.
        
        Args:
            wait_time: Time to wait for manual edits (seconds)
        """
        self.wait_time = wait_time
        print(f"🔄 Code Change Detector initialized")
        print(f"   Wait time: {wait_time}s")
    
    def wait_and_check_for_changes(
        self,
        file_path: str,
        original_code: str,
        node_id: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Wait for manual edits and check if code changed.
        
        Args:
            file_path: Path to code file
            original_code: Original code content
            node_id: Node ID for display
            
        Returns:
            (changed, new_code) tuple
        """
        print(f"\n⏱️  Waiting {self.wait_time}s for manual edits to node_{node_id}.py...")
        print(f"   File: {file_path}")
        print(f"   Edit the file now if you want to improve it!")
        
        # Show countdown
        for remaining in range(self.wait_time, 0, -10):
            if remaining <= self.wait_time:
                print(f"   {remaining}s remaining...", end='\r', flush=True)
            time.sleep(min(10, remaining))
        
        print("\n   Checking for changes...                    ", flush=True)
        
        # Read current file content
        try:
            with open(file_path, 'r') as f:
                current_code = f.read()
        except Exception as e:
            print(f"   ❌ Error reading file: {e}")
            return False, None
        
        # Compare hashes
        original_hash = self._compute_hash(original_code)
        current_hash = self._compute_hash(current_code)
        
        if original_hash != current_hash:
            print(f"   ✅ Code change detected!")
            print(f"      Original: {len(original_code)} chars")
            print(f"      Updated:  {len(current_code)} chars")
            
            # Show diff summary
            self._show_diff_summary(original_code, current_code)
            
            return True, current_code
        else:
            print(f"   ℹ️  No changes detected")
            return False, None
    
    def _compute_hash(self, code: str) -> str:
        """Compute SHA256 hash of code."""
        return hashlib.sha256(code.encode()).hexdigest()
    
    def _show_diff_summary(self, original: str, updated: str):
        """Show summary of changes."""
        orig_lines = original.split('\n')
        upd_lines = updated.split('\n')
        
        lines_diff = len(upd_lines) - len(orig_lines)
        
        if lines_diff > 0:
            print(f"      +{lines_diff} lines added")
        elif lines_diff < 0:
            print(f"      {abs(lines_diff)} lines removed")
        else:
            print(f"      {len(upd_lines)} lines modified")
        
        # Show changed lines (simple diff)
        changed_count = 0
        for i, (orig_line, upd_line) in enumerate(zip(orig_lines, upd_lines)):
            if orig_line != upd_line:
                changed_count += 1
                if changed_count <= 3:  # Show first 3 changes
                    print(f"      Line {i+1}: changed")
        
        if changed_count > 3:
            print(f"      ... and {changed_count - 3} more lines changed")

