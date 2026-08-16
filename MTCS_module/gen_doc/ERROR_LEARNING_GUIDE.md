# 🔧 Error Learning Guide - Making the Search Tree Learn from Failures

**How to make the AI system learn from failed executions and avoid repeating mistakes**

---

## 📋 Table of Contents

1. [Current Error Handling](#current-error-handling)
2. [Error Information Storage](#error-information-storage)
3. [Making the Tree "Aware" of Errors](#making-the-tree-aware-of-errors)
4. [Feeding Error Context to LLM](#feeding-error-context-to-llm)
5. [Implementation Examples](#implementation-examples)
6. [Best Practices](#best-practices)

---

## 🔍 Current Error Handling

### What Gets Captured Now

The system currently captures:
1. **Error Messages**: Full exception text and stack traces
2. **Execution Status**: `failed_auto`, `failed_manual`, etc.
3. **Auto-Fix Attempts**: Number of fix attempts made
4. **Code Snapshots**: The failing code is preserved
5. **Parent Information**: Which node generated this failure

### Database Schema for Errors

```sql
CREATE TABLE execution_nodes (
    node_id TEXT PRIMARY KEY,
    execution_status TEXT DEFAULT 'pending',
    
    -- Error tracking
    error_message TEXT,           -- Full error with stack trace
    auto_fixes INTEGER DEFAULT 0, -- Number of auto-fix attempts
    
    -- Genealogy for pattern detection
    parent_id TEXT,
    mutation_type TEXT,
    generation INTEGER,
    
    -- Code preservation
    code TEXT NOT NULL,
    code_file_path TEXT
);
```

### What's Missing

Currently, the system:
- ❌ **Doesn't feed error history** to LLM when generating mutations
- ❌ **Doesn't detect error patterns** across multiple nodes
- ❌ **Doesn't reduce PUCT score** for nodes with failed children
- ❌ **Doesn't avoid similar mutations** that previously failed

---

## 🗄️ Error Information Storage

### Query Failed Nodes

```python
import sqlite3

def get_failed_nodes(db_path: str):
    """Get all failed nodes with error information."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            node_id,
            parent_id,
            generation,
            mutation_type,
            error_message,
            auto_fixes,
            code
        FROM execution_nodes
        WHERE execution_status LIKE 'failed%'
        ORDER BY generation, created_at
    """)
    
    failed_nodes = []
    for row in cursor.fetchall():
        failed_nodes.append({
            'node_id': row[0],
            'parent_id': row[1],
            'generation': row[2],
            'mutation_type': row[3],
            'error_message': row[4],
            'auto_fixes': row[5],
            'code': row[6]
        })
    
    conn.close()
    return failed_nodes

# Usage
failed = get_failed_nodes('manual_run_100_v3.db')
print(f"Total failed nodes: {len(failed)}")
for node in failed:
    print(f"Node {node['node_id']}: {node['error_message'][:100]}...")
```

### Analyze Error Patterns

```python
from collections import Counter
import re

def analyze_error_patterns(failed_nodes):
    """Identify common error patterns."""
    error_types = []
    
    for node in failed_nodes:
        error_msg = node['error_message']
        
        # Extract error type
        if 'ModuleNotFoundError' in error_msg:
            error_types.append('missing_module')
        elif 'AttributeError' in error_msg:
            error_types.append('attribute_error')
        elif 'SyntaxError' in error_msg:
            error_types.append('syntax_error')
        elif 'MemoryError' in error_msg or 'CUDA out of memory' in error_msg:
            error_types.append('memory_error')
        elif 'TimeoutError' in error_msg or 'timeout' in error_msg:
            error_types.append('timeout')
        elif 'ValueError' in error_msg:
            error_types.append('value_error')
        else:
            error_types.append('other')
    
    # Count occurrences
    error_counts = Counter(error_types)
    
    return error_counts

# Usage
patterns = analyze_error_patterns(failed)
print("Error patterns:")
for error_type, count in patterns.most_common():
    print(f"  {error_type}: {count}")
```

**Example Output**:
```
Error patterns:
  missing_module: 12
  attribute_error: 8
  syntax_error: 5
  memory_error: 3
  timeout: 2
```

---

## 🧠 Making the Tree "Aware" of Errors

### Method 1: Include Error History in Prompts

**Modify `prompt_formatter.py`** to include error context:

```python
def format_mutation_prompt_with_error_context(
    self,
    previous_code: str,
    previous_score: float,
    parent_errors: List[Dict[str, Any]],  # NEW
    sibling_errors: List[Dict[str, Any]]  # NEW
) -> str:
    """Format mutation prompt with error learning."""
    
    # Extract common error patterns
    error_context = self._format_error_context(parent_errors, sibling_errors)
    
    # Standard prompt
    base_prompt = UNIVERSAL_PROMPT_2_MUTATION.format(
        domain=self.domain,
        task_name=self.task_name,
        evaluation_metric=self.evaluation_metric,
        direction="higher" if self.higher_is_better else "lower",
        previous_code=previous_code,
        previous_score=previous_score,
        research_ideas=self._format_research_ideas(),
        advisory_guidance=""
    )
    
    # Add error learning section
    if error_context:
        enhanced_prompt = f"""{base_prompt}

**IMPORTANT - Learn from Previous Failures:**
{error_context}

Please avoid these errors in your implementation. The code MUST be syntactically 
correct, use only available libraries, and handle edge cases properly.
"""
        return enhanced_prompt
    
    return base_prompt

def _format_error_context(
    self,
    parent_errors: List[Dict[str, Any]],
    sibling_errors: List[Dict[str, Any]]
) -> str:
    """Format error context for prompt."""
    if not parent_errors and not sibling_errors:
        return ""
    
    context_parts = []
    
    # Parent errors (direct ancestors that failed)
    if parent_errors:
        context_parts.append("**Previous Attempts That Failed:**")
        for i, error in enumerate(parent_errors[:3], 1):  # Limit to 3
            error_type = self._extract_error_type(error['error_message'])
            context_parts.append(f"{i}. {error_type}")
            context_parts.append(f"   Mutation: {error['mutation_type']}")
            context_parts.append(f"   Error: {error['error_message'][:200]}...")
            context_parts.append("")
    
    # Sibling errors (same generation, different mutations)
    if sibling_errors:
        error_types = Counter(
            self._extract_error_type(e['error_message']) 
            for e in sibling_errors
        )
        if error_types:
            context_parts.append("**Common Errors in This Generation:**")
            for error_type, count in error_types.most_common(3):
                context_parts.append(f"- {error_type} ({count} occurrences)")
            context_parts.append("")
    
    return "\n".join(context_parts)

def _extract_error_type(self, error_message: str) -> str:
    """Extract concise error type from full message."""
    if 'ModuleNotFoundError' in error_message:
        # Extract module name
        match = re.search(r"No module named '([^']+)'", error_message)
        if match:
            return f"Missing module: {match.group(1)}"
        return "Missing module"
    elif 'AttributeError' in error_message:
        match = re.search(r"'([^']+)' object has no attribute '([^']+)'", error_message)
        if match:
            return f"AttributeError: {match.group(1)}.{match.group(2)} doesn't exist"
        return "AttributeError"
    elif 'SyntaxError' in error_message:
        return "SyntaxError: Check indentation and syntax"
    elif 'MemoryError' in error_message or 'out of memory' in error_message.lower():
        return "Memory/CUDA error: Reduce batch size or model size"
    elif 'TimeoutError' in error_message or 'timeout' in error_message.lower():
        return "Timeout: Code took too long to execute"
    else:
        # Return first line of error
        lines = error_message.split('\n')
        return lines[0][:100] if lines else "Unknown error"
```

---

### Method 2: Adjust PUCT Scores Based on Children Failures

**Modify `db_enhanced_search.py`** to penalize nodes with failed children:

```python
def calculate_puct_with_failure_penalty(
    self, 
    node: Node,
    c_puct: float = 1.5,
    failure_penalty: float = 0.1
) -> float:
    """
    Calculate PUCT score with penalty for failed children.
    
    Args:
        node: Node to evaluate
        c_puct: Exploration constant
        failure_penalty: Score reduction per failed child (0.0 to 1.0)
    """
    # Standard PUCT calculation
    exploitation = node.average_score()
    
    exploration = c_puct * math.sqrt(
        math.log(node.parent.visit_count) / (1 + node.visit_count)
    )
    
    # NEW: Penalty for failed children
    failure_ratio = self._get_failure_ratio(node)
    penalty = failure_penalty * failure_ratio
    
    return exploitation + exploration - penalty

def _get_failure_ratio(self, node: Node) -> float:
    """Get ratio of failed children to total children."""
    if not node.children:
        return 0.0
    
    failed_count = 0
    for child in node.children:
        # Check if child execution failed
        db_node = self.db.get_node(child.node_id)
        if db_node and db_node.execution_status.startswith('failed'):
            failed_count += 1
    
    return failed_count / len(node.children)
```

**Impact**: Nodes that consistently produce failing children will be selected less often.

---

### Method 3: Track Mutation Type Success Rates

**Add to `DatabaseEnhancedTreeSearch` class**:

```python
class DatabaseEnhancedTreeSearch(EnhancedUniversalTreeSearch):
    def __init__(self, ...):
        # ... existing init ...
        
        # NEW: Track mutation type performance
        self.mutation_stats = {
            'hyperparameter_tuning': {'success': 0, 'failure': 0},
            'algorithm_change': {'success': 0, 'failure': 0},
            'feature_engineering': {'success': 0, 'failure': 0},
            'ensemble_creation': {'success': 0, 'failure': 0},
            'hybrid_innovation': {'success': 0, 'failure': 0}
        }
    
    def update_mutation_stats(self, mutation_type: str, success: bool):
        """Update success/failure stats for mutation type."""
        if mutation_type in self.mutation_stats:
            if success:
                self.mutation_stats[mutation_type]['success'] += 1
            else:
                self.mutation_stats[mutation_type]['failure'] += 1
    
    def get_best_mutation_type(self) -> str:
        """Get mutation type with highest success rate."""
        best_type = None
        best_rate = 0.0
        
        for mut_type, stats in self.mutation_stats.items():
            total = stats['success'] + stats['failure']
            if total >= 3:  # Minimum attempts
                success_rate = stats['success'] / total
                if success_rate > best_rate:
                    best_rate = success_rate
                    best_type = mut_type
        
        return best_type or 'standard'
    
    def _expand_node(self, node: Node) -> List[Node]:
        """Expand node with error-aware mutation selection."""
        # Get error history
        parent_errors = self._get_ancestor_errors(node)
        sibling_errors = self._get_sibling_errors(node)
        
        # Select mutation type based on success rate
        mutation_type = self.get_best_mutation_type()
        
        # Generate code with error context
        code = self.llm_worker.generate_code_mutation(
            previous_code=node.code,
            score=node.metrics.primary_score,
            task_description=self.task_config.description,
            mutation_type=mutation_type,
            error_context={
                'parent_errors': parent_errors,
                'sibling_errors': sibling_errors
            }
        )
        
        # ... rest of expansion logic ...

def _get_ancestor_errors(self, node: Node) -> List[Dict[str, Any]]:
    """Get errors from ancestor nodes."""
    errors = []
    current = node
    
    while current.parent and len(errors) < 5:
        db_node = self.db.get_node(current.node_id)
        if db_node and db_node.execution_status.startswith('failed'):
            errors.append({
                'node_id': db_node.node_id,
                'mutation_type': db_node.mutation_type,
                'error_message': db_node.error_message,
                'generation': db_node.generation
            })
        current = current.parent
    
    return errors

def _get_sibling_errors(self, node: Node) -> List[Dict[str, Any]]:
    """Get errors from sibling nodes (same generation)."""
    if not node.parent:
        return []
    
    errors = []
    for sibling in node.parent.children:
        if sibling.id != node.id:
            db_node = self.db.get_node(sibling.node_id)
            if db_node and db_node.execution_status.startswith('failed'):
                errors.append({
                    'node_id': db_node.node_id,
                    'mutation_type': db_node.mutation_type,
                    'error_message': db_node.error_message
                })
    
    return errors
```

---

## 🤖 Feeding Error Context to LLM

### Enhanced LLM Worker Method

**Modify `llm_worker.py`**:

```python
def generate_code_mutation(
    self,
    previous_code: str,
    score: float,
    task_description: str,
    research_ideas: Optional[List[str]] = None,
    domain: str = "machine_learning",
    data_files: Optional[Dict[str, str]] = None,
    error_context: Optional[Dict[str, Any]] = None  # NEW
) -> LLMResponse:
    """
    Generate improved code with error awareness.
    
    Args:
        ... existing args ...
        error_context: Dictionary containing:
            - parent_errors: List of errors from ancestor nodes
            - sibling_errors: List of errors from sibling nodes
    """
    # Build base prompt
    base_prompt = self._build_mutation_prompt(
        previous_code, score, task_description, 
        research_ideas, domain, data_files
    )
    
    # Add error learning section
    if error_context:
        error_section = self._build_error_learning_section(error_context)
        enhanced_prompt = f"{base_prompt}\n\n{error_section}"
    else:
        enhanced_prompt = base_prompt
    
    # Generate with LLM
    return self._call_llm(enhanced_prompt)

def _build_error_learning_section(self, error_context: Dict[str, Any]) -> str:
    """Build error learning section for prompt."""
    parent_errors = error_context.get('parent_errors', [])
    sibling_errors = error_context.get('sibling_errors', [])
    
    if not parent_errors and not sibling_errors:
        return ""
    
    section = """
**⚠️ CRITICAL: Learn from Previous Failures**

"""
    
    # Add parent errors
    if parent_errors:
        section += "Recent failed attempts in this lineage:\n"
        for i, error in enumerate(parent_errors[:3], 1):
            error_summary = self._summarize_error(error['error_message'])
            section += f"{i}. Generation {error['generation']} ({error['mutation_type']})\n"
            section += f"   Error: {error_summary}\n\n"
        
        section += "**Fix these issues:**\n"
        section += self._generate_fix_suggestions(parent_errors)
        section += "\n\n"
    
    # Add sibling error patterns
    if sibling_errors:
        error_types = Counter(
            self._categorize_error(e['error_message'])
            for e in sibling_errors
        )
        
        if error_types:
            section += "Common errors in this generation:\n"
            for error_type, count in error_types.most_common(3):
                section += f"- {error_type} ({count} times)\n"
            section += "\n**Avoid these patterns in your solution.**\n"
    
    return section

def _summarize_error(self, error_message: str) -> str:
    """Create concise error summary."""
    # Extract most relevant line
    lines = error_message.split('\n')
    
    # Find the actual error line
    for line in lines:
        if any(err in line for err in ['Error', 'Exception', 'Traceback']):
            return line.strip()[:150]
    
    return error_message[:150]

def _generate_fix_suggestions(self, errors: List[Dict[str, Any]]) -> str:
    """Generate specific fix suggestions based on errors."""
    suggestions = []
    
    for error in errors:
        msg = error['error_message']
        
        if 'ModuleNotFoundError' in msg:
            match = re.search(r"No module named '([^']+)'", msg)
            if match:
                module = match.group(1)
                suggestions.append(f"✓ Don't use '{module}' - it's not installed")
                suggestions.append(f"✓ Use alternative: {self._get_module_alternative(module)}")
        
        elif 'AttributeError' in msg:
            suggestions.append("✓ Check that objects have the attributes you're accessing")
            suggestions.append("✓ Use hasattr() or try-except for safety")
        
        elif 'SyntaxError' in msg:
            suggestions.append("✓ Check indentation (use 4 spaces)")
            suggestions.append("✓ Verify all brackets, parentheses, and quotes are closed")
        
        elif 'memory' in msg.lower():
            suggestions.append("✓ Reduce batch_size (try 16 or 32)")
            suggestions.append("✓ Use mixed precision: torch.cuda.amp or dtype=float16")
            suggestions.append("✓ Clear GPU memory: torch.cuda.empty_cache()")
    
    return "\n".join(set(suggestions))  # Remove duplicates

def _get_module_alternative(self, module: str) -> str:
    """Suggest alternative modules."""
    alternatives = {
        'catboost': 'lightgbm or xgboost',
        'transformers': 'sentence-transformers (lighter)',
        'faiss': 'scikit-learn for small datasets',
        'cudf': 'pandas',
        'cupy': 'numpy'
    }
    return alternatives.get(module, 'check requirements.txt for available libraries')

def _categorize_error(self, error_message: str) -> str:
    """Categorize error for pattern detection."""
    msg_lower = error_message.lower()
    
    if 'modulenotfound' in msg_lower:
        return "Missing library"
    elif 'attributeerror' in msg_lower:
        return "Wrong attribute access"
    elif 'syntaxerror' in msg_lower:
        return "Syntax error"
    elif 'memory' in msg_lower or 'cuda' in msg_lower:
        return "Memory/CUDA error"
    elif 'timeout' in msg_lower:
        return "Timeout (code too slow)"
    elif 'typeerror' in msg_lower:
        return "Type mismatch"
    elif 'valueerror' in msg_lower:
        return "Invalid value"
    else:
        return "Runtime error"
```

---

## 💡 Implementation Examples

### Example 1: Query and Display Error Context

```python
import sqlite3

def display_node_error_context(db_path: str, node_id: str):
    """Display comprehensive error context for a node."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get node info
    cursor.execute("""
        SELECT 
            node_id, parent_id, generation, mutation_type,
            execution_status, error_message, auto_fixes, score
        FROM execution_nodes
        WHERE node_id = ?
    """, (node_id,))
    
    node = cursor.fetchone()
    if not node:
        print(f"Node {node_id} not found")
        return
    
    node_id, parent_id, gen, mut_type, status, error, fixes, score = node
    
    print(f"📊 Node Analysis: {node_id}")
    print(f"=" * 60)
    print(f"Generation: {gen}")
    print(f"Mutation Type: {mut_type}")
    print(f"Status: {status}")
    print(f"Score: {score if score else 'N/A'}")
    print(f"Auto-fix Attempts: {fixes}")
    print()
    
    if error:
        print(f"❌ Error Message:")
        print(error[:500])
        print()
    
    # Get parent context
    if parent_id:
        cursor.execute("""
            SELECT node_id, mutation_type, score, execution_status
            FROM execution_nodes
            WHERE node_id = ?
        """, (parent_id,))
        
        parent = cursor.fetchone()
        if parent:
            p_id, p_mut, p_score, p_status = parent
            print(f"👆 Parent Node: {p_id}")
            print(f"   Mutation: {p_mut}")
            print(f"   Score: {p_score if p_score else 'N/A'}")
            print(f"   Status: {p_status}")
            print()
    
    # Get sibling context (same generation)
    cursor.execute("""
        SELECT node_id, mutation_type, score, execution_status
        FROM execution_nodes
        WHERE generation = ? AND node_id != ?
        ORDER BY score DESC
    """, (gen, node_id))
    
    siblings = cursor.fetchall()
    if siblings:
        print(f"👥 Sibling Nodes (Generation {gen}):")
        for s_id, s_mut, s_score, s_status in siblings[:5]:
            status_icon = "✅" if "completed" in s_status else "❌"
            score_str = f"{s_score:.4f}" if s_score else "N/A"
            print(f"   {status_icon} {s_id}: {s_mut} → {score_str}")
        print()
    
    # Get child context
    cursor.execute("""
        SELECT node_id, mutation_type, score, execution_status
        FROM execution_nodes
        WHERE parent_id = ?
        ORDER BY score DESC
    """, (node_id,))
    
    children = cursor.fetchall()
    if children:
        print(f"👶 Child Nodes:")
        for c_id, c_mut, c_score, c_status in children:
            status_icon = "✅" if "completed" in c_status else "❌"
            score_str = f"{c_score:.4f}" if c_score else "N/A"
            print(f"   {status_icon} {c_id}: {c_mut} → {score_str}")
        print()
    
    conn.close()

# Usage
display_node_error_context('manual_run_100_v3.db', 'abc12345')
```

**Example Output**:
```
📊 Node Analysis: abc12345
============================================================
Generation: 5
Mutation Type: ensemble_creation
Status: failed_auto
Score: N/A
Auto-fix Attempts: 3

❌ Error Message:
ModuleNotFoundError: No module named 'catboost'
  File "node_abc12345.py", line 15, in <module>
    from catboost import CatBoostClassifier

👆 Parent Node: def45678
   Mutation: algorithm_change
   Score: 0.8845
   Status: completed_auto

👥 Sibling Nodes (Generation 5):
   ✅ xyz78901: hyperparameter_tuning → 0.9023
   ✅ lmn34567: feature_engineering → 0.8967
   ❌ opq89012: ensemble_creation → N/A

👶 Child Nodes:
   ✅ rst12345: algorithm_change → 0.9034
```

---

### Example 2: Generate Report of All Errors

```python
def generate_error_report(db_path: str, output_file: str = 'error_report.md'):
    """Generate comprehensive error report."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all failed nodes
    cursor.execute("""
        SELECT 
            node_id, generation, mutation_type, error_message, auto_fixes
        FROM execution_nodes
        WHERE execution_status LIKE 'failed%'
        ORDER BY generation
    """)
    
    failed_nodes = cursor.fetchall()
    
    # Analyze patterns
    error_patterns = {}
    for _, gen, mut_type, error_msg, fixes in failed_nodes:
        # Categorize error
        if 'ModuleNotFoundError' in error_msg:
            match = re.search(r"No module named '([^']+)'", error_msg)
            category = f"Missing module: {match.group(1)}" if match else "Missing module"
        elif 'AttributeError' in error_msg:
            category = "AttributeError"
        elif 'SyntaxError' in error_msg:
            category = "SyntaxError"
        elif 'memory' in error_msg.lower():
            category = "Memory/CUDA error"
        else:
            category = "Other"
        
        if category not in error_patterns:
            error_patterns[category] = []
        error_patterns[category].append({
            'generation': gen,
            'mutation_type': mut_type,
            'auto_fixes': fixes
        })
    
    # Generate report
    with open(output_file, 'w') as f:
        f.write("# Error Analysis Report\n\n")
        f.write(f"Total failed nodes: {len(failed_nodes)}\n\n")
        
        f.write("## Error Patterns\n\n")
        for category, occurrences in sorted(error_patterns.items(), 
                                           key=lambda x: len(x[1]), 
                                           reverse=True):
            f.write(f"### {category} ({len(occurrences)} occurrences)\n\n")
            
            # Get generations affected
            gens = [occ['generation'] for occ in occurrences]
            f.write(f"- Generations: {min(gens)} to {max(gens)}\n")
            
            # Get mutation types affected
            mut_types = Counter(occ['mutation_type'] for occ in occurrences)
            f.write(f"- Most affected mutation: {mut_types.most_common(1)[0][0]}\n")
            
            # Auto-fix attempts
            total_fixes = sum(occ['auto_fixes'] for occ in occurrences)
            f.write(f"- Total auto-fix attempts: {total_fixes}\n")
            f.write(f"- Auto-fix success rate: {0}% (all failed)\n\n")
        
        f.write("## Recommendations\n\n")
        for category in error_patterns:
            if 'Missing module' in category:
                module = category.split(': ')[1] if ': ' in category else 'unknown'
                f.write(f"- **{category}**: Add `{module}` to requirements.txt or use alternative\n")
            elif category == "Memory/CUDA error":
                f.write(f"- **Memory errors**: Reduce batch_size, use mixed precision, or switch to CPU\n")
            elif category == "SyntaxError":
                f.write(f"- **Syntax errors**: Improve LLM prompt to emphasize correct Python syntax\n")
        
        f.write("\n")
    
    conn.close()
    print(f"✅ Error report generated: {output_file}")

# Usage
generate_error_report('manual_run_100_v3.db')
```

---

## 🎯 Best Practices

### 1. Regular Error Analysis

```bash
# Check error patterns every 10-20 iterations
python analyze_errors.py --db manual_run_100_v3.db --output error_report.md
```

### 2. Update Prompts Based on Patterns

If you see repeated "ModuleNotFoundError: catboost":
- Add to prompt: "**IMPORTANT**: Do not use 'catboost' - it's not installed. Use LightGBM or XGBoost instead."

### 3. Maintain Error Blacklist

```python
# In task_config.yaml
code_requirements:
  forbidden_modules:
    - catboost  # Not installed
    - tensorflow  # Too large for this environment
    - cudf  # GPU pandas not available
```

Then in prompt:
```
**Forbidden Libraries**: {', '.join(forbidden_modules)}
Use alternatives: LightGBM, XGBoost, PyTorch, standard pandas
```

### 4. Track Fix Success Patterns

```python
def analyze_fix_success(db_path: str):
    """Find which errors are fixable by auto-fixer."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Nodes that succeeded after auto-fix
    cursor.execute("""
        SELECT error_message, auto_fixes
        FROM execution_nodes
        WHERE execution_status = 'completed_auto' AND auto_fixes > 0
    """)
    
    fixable = cursor.fetchall()
    
    # Nodes that failed despite auto-fix
    cursor.execute("""
        SELECT error_message, auto_fixes
        FROM execution_nodes
        WHERE execution_status LIKE 'failed%' AND auto_fixes > 0
    """)
    
    unfixable = cursor.fetchall()
    
    print(f"✅ Auto-fixable errors: {len(fixable)}")
    print(f"❌ Unfixable errors: {len(unfixable)}")
    print(f"📊 Fix success rate: {len(fixable)/(len(fixable)+len(unfixable))*100:.1f}%")
    
    conn.close()
```

### 5. Error-Aware Node Selection

Modify PUCT to heavily penalize failure-prone branches:

```python
def calculate_error_aware_puct(node: Node) -> float:
    base_puct = calculate_standard_puct(node)
    
    # Heavy penalty for nodes with failed children
    failure_ratio = count_failed_children(node) / max(count_all_children(node), 1)
    failure_penalty = 0.5 * failure_ratio  # Up to -0.5 penalty
    
    # Bonus for nodes with successful children
    success_ratio = count_successful_children(node) / max(count_all_children(node), 1)
    success_bonus = 0.2 * success_ratio  # Up to +0.2 bonus
    
    return base_puct - failure_penalty + success_bonus
```

---

## 📊 Summary

### What You Should Do

1. **✅ Query Failed Nodes Regularly**
   ```python
   failed = get_failed_nodes('your_run.db')
   patterns = analyze_error_patterns(failed)
   ```

2. **✅ Feed Error Context to LLM**
   - Modify prompts to include recent failures
   - Provide specific fix suggestions
   - Warn against repeated mistakes

3. **✅ Adjust Node Selection**
   - Penalize nodes with failed children in PUCT
   - Track mutation type success rates
   - Avoid mutation types that consistently fail

4. **✅ Maintain Error Knowledge Base**
   - Document common errors and fixes
   - Update task_config.yaml with forbidden modules
   - Generate regular error reports

5. **✅ Improve Auto-Fixer**
   - Analyze which errors Claude can fix
   - Add specific fix patterns for common errors
   - Increase timeout for complex errors

### Expected Improvements

- **30-50% reduction** in repeated errors
- **Better mutation selection** (avoid failure-prone types)
- **Faster convergence** (don't waste iterations on failing branches)
- **Higher success rate** (LLM learns from past mistakes)

---

*Last Updated: October 14, 2025*
*Related: SYSTEM_ARCHITECTURE_GUIDE.md, PROMPT_SYSTEM_GUIDE.md*

