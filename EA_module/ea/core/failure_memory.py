"""
Failure Memory Module

Tracks failures across evolution runs and extracts patterns for future prompts.
This enables the system to learn from mistakes and warn LLMs about common pitfalls.
"""

import json
import re
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class FailureEntry:
    """A single failure record."""
    gen_id: int
    error_type: str
    error_msg: str
    code_snippet: str
    timestamp: float = field(default_factory=time.time)
    task_name: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, d: dict) -> 'FailureEntry':
        return cls(**d)


class FailureMemory:
    """
    Tracks failures and extracts patterns for future prompts.
    
    Features:
    1. Records failures with error type classification
    2. Detects patterns in failures (e.g., common missing imports)
    3. Generates warning prompts for LLM
    4. Persists memory to disk for cross-run learning
    """
    
    # Common error patterns for classification
    ERROR_PATTERNS = {
        'missing_import': [
            r"name '(\w+)' is not defined",
            r"NameError: name '(\w+)' is not defined",
            r"ModuleNotFoundError: No module named '(\w+)'",
        ],
        'device_mismatch': [
            r"Expected all tensors to be on the same device",
            r"cuda:\d+ and cpu",
            r"RuntimeError:.*device",
        ],
        'data_format': [
            r"No proteins with both",
            r"No valid proteins",
            r"KeyError: '[\w]+'",
            r"No data found",
        ],
        'type_error': [
            r"only integers.*are valid indices",
            r"TypeError:.*expected.*got",
            r"can't convert.*to",
        ],
        'shape_mismatch': [
            r"shape.*mismatch",
            r"size mismatch",
            r"RuntimeError: mat1 and mat2 shapes cannot be multiplied",
        ],
        'memory_error': [
            r"CUDA out of memory",
            r"MemoryError",
            r"RuntimeError: CUDA error: out of memory",
        ],
    }
    
    def __init__(
        self, 
        db_path: Optional[str] = None,
        max_entries: int = 500,
        verbose: bool = True
    ):
        """
        Initialize failure memory.
        
        Args:
            db_path: Path to JSON file for persistence. If None, uses in-memory only.
            max_entries: Maximum number of failure entries to keep.
            verbose: Print status messages.
        """
        self.db_path = Path(db_path) if db_path else None
        self.max_entries = max_entries
        self.verbose = verbose
        self.failures: List[FailureEntry] = []
        
        # Load existing failures if db_path exists
        if self.db_path and self.db_path.exists():
            self._load()
        
        if self.verbose:
            logger.info(f"🧠 FailureMemory initialized with {len(self.failures)} entries")
    
    def _load(self):
        """Load failures from disk."""
        try:
            with open(self.db_path, 'r') as f:
                data = json.load(f)
                self.failures = [FailureEntry.from_dict(d) for d in data.get('failures', [])]
        except Exception as e:
            logger.warning(f"Failed to load failure memory: {e}")
            self.failures = []
    
    def _save(self):
        """Save failures to disk."""
        if not self.db_path:
            return
        
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.db_path, 'w') as f:
                json.dump({
                    'failures': [f.to_dict() for f in self.failures[-self.max_entries:]],
                    'updated': time.time()
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save failure memory: {e}")
    
    def classify_error(self, error_msg: str) -> str:
        """Classify error message into a category."""
        for error_type, patterns in self.ERROR_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, error_msg, re.IGNORECASE):
                    return error_type
        return 'unknown'
    
    def record_failure(
        self, 
        gen_id: int, 
        error_msg: str, 
        code_snippet: str = "",
        task_name: str = ""
    ):
        """
        Record a failure for future reference.
        
        Args:
            gen_id: Generation ID where failure occurred.
            error_msg: The error message.
            code_snippet: Relevant code snippet (truncated).
            task_name: Name of the task.
        """
        error_type = self.classify_error(error_msg)
        
        entry = FailureEntry(
            gen_id=gen_id,
            error_type=error_type,
            error_msg=error_msg[:500],  # Truncate long errors
            code_snippet=code_snippet[:300] if code_snippet else "",
            task_name=task_name
        )
        
        self.failures.append(entry)
        
        # Prune if too many entries
        if len(self.failures) > self.max_entries:
            self.failures = self.failures[-self.max_entries:]
        
        self._save()
        
        if self.verbose:
            logger.info(f"🧠 Recorded failure: {error_type} at gen {gen_id}")
    
    def get_failure_stats(self) -> Dict[str, int]:
        """Get statistics about failures by type."""
        stats = defaultdict(int)
        for f in self.failures:
            stats[f.error_type] += 1
        return dict(stats)
    
    def get_recent_failures(
        self, 
        n: int = 10, 
        error_type: Optional[str] = None
    ) -> List[FailureEntry]:
        """Get recent failures, optionally filtered by type."""
        filtered = self.failures
        if error_type:
            filtered = [f for f in filtered if f.error_type == error_type]
        return filtered[-n:]
    
    def extract_missing_imports(self) -> List[str]:
        """Extract commonly missing imports from failures."""
        missing = []
        for f in self.failures:
            if f.error_type == 'missing_import':
                match = re.search(r"name '(\w+)' is not defined", f.error_msg)
                if match:
                    missing.append(match.group(1))
        return list(set(missing))
    
    def get_warning_prompt(self, max_warnings: int = 5) -> str:
        """
        Generate warning prompt from failure patterns.
        
        Returns:
            String to include in LLM mutation prompt.
        """
        if not self.failures:
            return ""
        
        # Group by error type
        by_type = defaultdict(list)
        for f in self.failures[-100:]:  # Last 100 failures
            by_type[f.error_type].append(f)
        
        warnings = []
        
        # Generate warnings for each type
        for err_type, items in sorted(by_type.items(), key=lambda x: -len(x[1])):
            count = len(items)
            recent = items[-1]  # Most recent example
            
            if err_type == 'missing_import':
                # Extract specific missing modules
                missing_modules = []
                for item in items[-5:]:
                    match = re.search(r"name '(\w+)' is not defined", item.error_msg)
                    if match:
                        missing_modules.append(match.group(1))
                if missing_modules:
                    modules_str = ', '.join(set(missing_modules))
                    warnings.append(
                        f"- MISSING IMPORTS ({count}x): Commonly forgotten: {modules_str}. "
                        f"Always include `import X` for any module X you use!"
                    )
            
            elif err_type == 'device_mismatch':
                warnings.append(
                    f"- DEVICE MISMATCH ({count}x): Tensors on different devices. "
                    f"Use `.to(DEVICE)` consistently for all tensors!"
                )
            
            elif err_type == 'data_format':
                warnings.append(
                    f"- DATA FORMAT ERROR ({count}x): e.g., '{recent.error_msg[:80]}...'. "
                    f"Check that data IDs and formats match exactly!"
                )
            
            elif err_type == 'type_error':
                warnings.append(
                    f"- TYPE ERROR ({count}x): e.g., '{recent.error_msg[:80]}...'. "
                    f"Use correct types for indices and operations!"
                )
            
            elif err_type == 'shape_mismatch':
                warnings.append(
                    f"- SHAPE MISMATCH ({count}x): Tensor shapes don't match. "
                    f"Verify input/output dimensions match!"
                )
            
            else:
                warnings.append(
                    f"- {err_type.upper()} ({count}x): {recent.error_msg[:60]}..."
                )
            
            if len(warnings) >= max_warnings:
                break
        
        if not warnings:
            return ""
        
        total_failures = len(self.failures)
        return f"""
**⚠️ AVOID THESE PATTERNS ({total_failures} total failures recorded):**
{chr(10).join(warnings)}

Learn from these past mistakes and ensure your code handles these cases correctly!
"""
    
    def get_import_checklist(self) -> str:
        """
        Generate import checklist based on commonly forgotten imports.
        
        Returns:
            String listing imports that should be included.
        """
        missing = self.extract_missing_imports()
        if not missing:
            return ""
        
        return f"""
**📦 COMMONLY FORGOTTEN IMPORTS (from {len(self.failures)} failures):**
Make sure to include these if you use them:
{chr(10).join(f'- import {m}' for m in missing[:10])}
"""


def load_task_pitfalls(pitfalls_path: str) -> str:
    """
    Load task-specific pitfalls from YAML file.
    
    Args:
        pitfalls_path: Path to task_pitfalls.yaml
        
    Returns:
        Formatted string for inclusion in prompt.
    """
    try:
        import yaml
        
        path = Path(pitfalls_path)
        if not path.exists():
            return ""
        
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        
        if not data or 'pitfalls' not in data:
            return ""
        
        lines = ["\n**📋 TASK-SPECIFIC PITFALLS (CRITICAL):**\n"]
        
        for p in data.get('pitfalls', []):
            severity = p.get('severity', 'medium').upper()
            name = p.get('name', 'Unknown')
            desc = p.get('description', '').strip()
            
            lines.append(f"[{severity}] {name}")
            # Take first 2 lines of description
            desc_lines = desc.split('\n')[:2]
            for line in desc_lines:
                if line.strip():
                    lines.append(f"    {line.strip()}")
            lines.append("")
        
        # Add data loading template if available
        if data.get('data_loading_template'):
            lines.append("**📁 RECOMMENDED DATA LOADING PATTERN:**")
            lines.append("```python")
            lines.append(data['data_loading_template'].strip())
            lines.append("```")
        
        return '\n'.join(lines)
        
    except Exception as e:
        logger.warning(f"Failed to load task pitfalls: {e}")
        return ""


# Convenience function for integration
def build_layered_prompt_additions(
    failure_memory: Optional[FailureMemory] = None,
    task_pitfalls_path: Optional[str] = None,
    max_warnings: int = 5
) -> str:
    """
    Build additional prompt content from all layers.
    
    Args:
        failure_memory: FailureMemory instance (optional)
        task_pitfalls_path: Path to task_pitfalls.yaml (optional)
        max_warnings: Maximum warnings from failure memory
        
    Returns:
        Combined string to add to mutation prompt.
    """
    parts = []
    
    # Layer 2: Task-specific pitfalls
    if task_pitfalls_path:
        pitfalls = load_task_pitfalls(task_pitfalls_path)
        if pitfalls:
            parts.append(pitfalls)
    
    # Layer 3: Dynamic failure memory
    if failure_memory:
        warnings = failure_memory.get_warning_prompt(max_warnings)
        if warnings:
            parts.append(warnings)
        
        imports = failure_memory.get_import_checklist()
        if imports:
            parts.append(imports)
    
    return '\n'.join(parts)

