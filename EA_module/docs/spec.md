# AgentLTV Specification & Lessons Learned

## LLM Configuration Guidelines

### Max Tokens Setting

**Issue Date:** 2026-01-07

**Problem:** 
LLM output was being truncated when generating full code rewrites for large files.

**Root Cause:**
`max_tokens=16384` was insufficient for files >40KB. A 51KB Python file needs approximately 13,000+ tokens just for the original code, and the LLM generates additional tokens for formatting, code modifications, and explanations.

**Symptoms:**
- Incomplete Python code (e.g., `opt.` instead of `opt.zero_grad()`)
- `SyntaxError: invalid syntax` at unexpected lines (not line 1)
- Generated file significantly smaller than original

**Solution:**
```python
# In run_evo.py
max_tokens=65536,  # Large enough for full code rewrites (51KB+ files need ~20K+ tokens)
```

**Calculation:**
- Average: ~4 characters per token
- 51KB file = ~13,000 tokens
- With modifications + formatting: ~20,000-25,000 tokens
- Safety margin: 65536 tokens (64K)

---

## Markdown Fence Issues

**Issue Date:** 2026-01-07

**Problem:**
LLM outputs sometimes include markdown code fences (` ```python ... ``` `) which cause Python SyntaxError when the file is executed.

**Root Cause:**
1. `extract_between()` fails when input has NO markdown fences
2. AutoFixer may re-introduce markdown fences

**Solution:**
1. Modified `apply_full.py` to handle both cases:
   - If input HAS fences: extract code between them
   - If input has NO fences: use code directly
2. Modified `auto_fixer.py` with `_strip_markdown_fences()` helper

**Detection:**
```python
# Check first line of main.py
with open('main.py', 'r') as f:
    first_line = f.readline().strip()
if first_line.startswith('```'):
    print("MARKDOWN FENCE ISSUE!")
```

---

## Evolution Task Configuration Checklist

When setting up a new evolution task:

1. **File Size Check:**
   - If source file > 30KB, set `max_tokens` to at least 65536
   - Calculate: `file_size_bytes / 4 * 2` as minimum

2. **Markdown Handling:**
   - Ensure `apply_full.py` has the fence-stripping code
   - Verify AutoFixer has `_strip_markdown_fences()` method

3. **EVOLVE-BLOCK Markers:**
   - Always include markers in the initial code
   - Format: `# EVOLVE-BLOCK-START: SECTION_NAME`

4. **Timeout Settings:**
   - For files > 50KB with full rewrites: `execution_timeout >= 45 minutes`

---

## Quick Debug Commands

```bash
# Check if main.py has markdown fences
head -1 results_*/gen_*/main.py

# Check file size comparison
wc -l results_*/gen_*/original.py results_*/gen_*/main.py

# Check for truncation
tail -10 results_*/gen_*/main.py
```






