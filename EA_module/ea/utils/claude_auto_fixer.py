#!/usr/bin/env python3
"""
Claude Auto Fixer for AgentLTV

Uses Claude Code to fix and run Python scripts in a single call.
Claude handles all retries, package installation, and execution internally.

This replaces the old complex auto-fixer with a simple, effective solution.

Usage in AgentLTV:
    from ea.utils.claude_auto_fixer import run_claude_fixer
    
    result = run_claude_fixer(
        script_path="/path/to/gen_X/main.py",
        output_path="/path/to/gen_X/results/output.json",
        timeout=3600,  # 1 hour for ML training
    )

CLI Usage:
    python claude_auto_fixer.py --script <path_to_script.py> --output <result.json>
"""

import argparse
import json
import os
import re
import signal
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any


# Default configuration
DEFAULT_MODEL = "claude-sonnet-4-5"  # Claude Sonnet 4.5 via LiteLLM (use hyphens not dots)
DEFAULT_TIMEOUT = 21600  # 6 hours for ML training tasks (was 1 hour, increased to prevent orphan processes)
DEFAULT_API_BASE = os.getenv("OPENAI_API_BASE", "")
DEFAULT_API_KEY = os.getenv("OPENAI_API_KEY", "")


def create_prompt(
    script_path: str,
    output_path: str,
    python_path: str,
    json_template: Optional[str] = None,
    task_description: Optional[str] = None,
) -> str:
    """Create the prompt for Claude Code."""
    
    if json_template:
        json_instruction = f"""
The result JSON MUST follow this exact template:
```json
{json_template}
```
Extract values from the script's output and fill in the template fields.
"""
    else:
        json_instruction = """
The result JSON should contain:
- "score": the main score from the script output (look for "score = X.XX" or "Composite Score: X.XX")
- "metrics": dict of metrics if present (gini, error_rate, spearman, rmse, etc.)
- "success": true/false
- "stdout": the script's full output
- "stderr": any error messages
- "execution_time": approximate execution time in seconds
- "fix_applied": true if code was modified, false otherwise
- "packages_installed": list of packages that were installed (empty list if none)
"""

    task_context = ""
    if task_description:
        task_context = f"""
TASK CONTEXT:
{task_description}
"""

    prompt = f"""You are a Python code fixer for ML/Data Science scripts. Fix and run the script EXACTLY ONCE.

闁宠法濯寸粭?CRITICAL: Before doing ANYTHING, check if the script is already running:
   pgrep -f "{script_path}" && echo "SCRIPT ALREADY RUNNING - DO NOT START ANOTHER!" && exit 0

SCRIPT: {script_path}
OUTPUT_JSON: {output_path}
PYTHON: {python_path}
{task_context}
TASK:
1. FIRST: Check if the script is already running. If yes, WAIT and monitor. DO NOT start another instance!
2. Read the script at {script_path}
3. Check for syntax errors - if found, fix them and save to {script_path}
4. Run it ONCE with: AVIA_OUTPUT_JSON={output_path} {python_path} {script_path}
5. If it fails:
   - ModuleNotFoundError 闁?Install package: {python_path} -m pip install <package>
   - ImportError 闁?Fix missing imports
   - SyntaxError 闁?Fix the syntax
   - NameError 闁?Add missing variable/import
   - Any other error 闁?Analyze and fix the code
   - Save fixed code to {script_path}
   - Run again (but ONLY if it failed, never run twice if first attempt is still running)
6. CRITICAL: After the script runs successfully, the output JSON should be at {output_path}.
   
   If the script wrote to /tmp/avia_score_output.json instead, copy it:
   cp /tmp/avia_score_output.json {output_path}
   
   OR if the script only prints the score, create the JSON:
   {python_path} -c "import json; json.dump({{'success': True, 'score': <SCORE>, 'metrics': {{}}}}, open('{output_path}', 'w'))"
   
   Replace <SCORE> with the actual score. Look for:
   - "score = 0.XXX"
   - "Final Score: 0.XXX"
   - "Composite Score: 0.XXX"
{json_instruction}

IMPORTANT RULES:
- Use {python_path} for all Python/pip commands
- Save fixed code to {script_path}
- YOU MUST create {output_path} with the score after the script runs
- DO NOT change the ML model architecture (keep LightGBM, XGBoost, etc. as-is)
- DO NOT change the algorithm logic, only fix errors
- If the script runs but produces an error score, still save the result with score 0.0
- CRITICAL: Run the script ONLY ONCE after fixing. Do NOT run it multiple times!
- If the script is already running (long training), WAIT for it to complete. Do NOT start another instance!
- If you see the script is training (printing progress), DO NOT interrupt or restart it.

Start by reading the script.
"""
    return prompt


def run_claude_fixer(
    script_path: str,
    output_path: str,
    model: str = DEFAULT_MODEL,
    timeout: int = DEFAULT_TIMEOUT,
    json_template: Optional[str] = None,
    task_description: Optional[str] = None,
    verbose: bool = True,
    api_base: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run Claude Code to fix and execute a Python script.
    
    Args:
        script_path: Path to the Python script to fix and run
        output_path: Path where to save the result JSON
        model: Claude model to use
        timeout: Timeout in seconds for Claude Code
        json_template: Optional JSON template for output format
        task_description: Optional description of what the script does
        verbose: Enable verbose output
        api_base: LiteLLM API base URL (uses env var if not provided)
        api_key: API key (uses env var if not provided)
        
    Returns:
        Dict with result including score, metrics, success status
    """
    
    script_path = os.path.abspath(script_path)
    output_path = os.path.abspath(output_path)
    python_path = sys.executable
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Set up environment for Claude Code to use LiteLLM
    env = os.environ.copy()
    env['ANTHROPIC_BASE_URL'] = api_base or os.getenv('ANTHROPIC_BASE_URL', DEFAULT_API_BASE)
    env['ANTHROPIC_AUTH_TOKEN'] = api_key or os.getenv('ANTHROPIC_AUTH_TOKEN', DEFAULT_API_KEY)
    
    # Set output path for scripts that use AVIA_OUTPUT_JSON env var
    env['AVIA_OUTPUT_JSON'] = output_path
    
    # Create the prompt
    prompt = create_prompt(
        script_path=script_path,
        output_path=output_path,
        python_path=python_path,
        json_template=json_template,
        task_description=task_description,
    )
    
    if verbose:
        print(f"妫ｅ啯鏆?Claude Auto Fixer", file=sys.stderr)
        print(f"   Script: {script_path}", file=sys.stderr)
        print(f"   Output: {output_path}", file=sys.stderr)
        print(f"   Python: {python_path}", file=sys.stderr)
        print(f"   Model: {model}", file=sys.stderr)
        print(f"   Timeout: {timeout}s", file=sys.stderr)
        print(f"妫ｅ喚妯?Calling Claude Code...", file=sys.stderr)
    
    start_time = datetime.now()
    
    try:
        # Call Claude Code using Popen with process group for proper cleanup
        # This ensures all child processes (including spawned main.py) are killed on timeout
        process = subprocess.Popen(
            [
                "claude",
                "-p",  # Print mode (non-interactive)
                "--model", model,
                "--dangerously-skip-permissions",
                prompt,
            ],
            cwd=os.path.dirname(script_path),
            stdin=subprocess.DEVNULL,  # Prevent stdin read errors
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            # Create a new process group so we can kill all children on timeout
            start_new_session=True,
        )
        
        try:
            stdout, stderr = process.communicate(timeout=timeout)
            returncode = process.returncode
        except subprocess.TimeoutExpired:
            # Kill the entire process group (includes all children like main.py)
            if verbose:
                print(f"闁?Timeout reached, killing process tree (PGID: {process.pid})...", file=sys.stderr)
            try:
                # Kill the entire process group
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass  # Already dead
            process.wait()
            raise  # Re-raise to be caught by outer handler
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        # Create a result object similar to subprocess.run result
        class Result:
            pass
        result = Result()
        result.stdout = stdout
        result.stderr = stderr
        result.returncode = returncode
        
        if verbose:
            print(f"闁?Claude Code completed in {elapsed:.1f}s", file=sys.stderr)
            print(f"   Exit code: {result.returncode}", file=sys.stderr)
        
        # Parse Claude's output (text, not JSON)
        claude_result = {"raw_output": result.stdout[:5000] if result.stdout else ""}
        
        # Check if output JSON was created by Claude
        if os.path.exists(output_path):
            if verbose:
                print(f"妫ｅ啯鎯?Result JSON saved by Claude: {output_path}", file=sys.stderr)
            with open(output_path, 'r') as f:
                final_result = json.load(f)
                final_result['execution_time'] = elapsed
                final_result['success'] = True
                # Re-save with execution time
                with open(output_path, 'w') as f2:
                    json.dump(final_result, f2, indent=2)
                return final_result
        
        # Check if the script wrote to its default location
        # Only use if it was modified AFTER we started running
        default_output = "/tmp/avia_score_output.json"
        if os.path.exists(default_output):
            default_mtime = os.path.getmtime(default_output)
            start_timestamp = start_time.timestamp()
            
            if default_mtime > start_timestamp:
                # File was created/modified during our run
                if verbose:
                    print(f"妫ｅ啯鎯?Found fresh script output at {default_output}, copying...", file=sys.stderr)
                import shutil
                shutil.copy(default_output, output_path)
                with open(output_path, 'r') as f:
                    final_result = json.load(f)
                    final_result['execution_time'] = elapsed
                    final_result['success'] = True
                    with open(output_path, 'w') as f2:
                        json.dump(final_result, f2, indent=2)
                    return final_result
            else:
                if verbose:
                    print(f"闁宠法濯寸粭? Found {default_output} but it's stale (from before our run)", file=sys.stderr)
        
        # Otherwise, try to extract from output
            # Claude didn't save the JSON, try to extract from output
            if verbose:
                print(f"闁宠法濯寸粭? Claude did not save result JSON, creating fallback", file=sys.stderr)
            
            stdout = result.stdout or ""
            stderr = result.stderr or ""
            combined = stdout + stderr
            
            # Try to extract score from output
            extracted_score = None
            score_patterns = [
                r'score["\s:=]+([0-9]+\.[0-9]+)',
                r'Composite Score[:\s]+([0-9]+\.[0-9]+)',
                r'"score"[:\s]+([0-9]+\.[0-9]+)',
                r'Final Score[:\s]+([0-9]+\.[0-9]+)',
            ]
            for pattern in score_patterns:
                match = re.search(pattern, combined, re.IGNORECASE)
                if match:
                    try:
                        extracted_score = float(match.group(1))
                        if verbose:
                            print(f"妫ｅ啯鎯?Extracted score from output: {extracted_score}", file=sys.stderr)
                        break
                    except ValueError:
                        pass
            
            # Determine success based on:
            # 1. Claude Code exit code
            # 2. Whether we found a valid score
            # 3. Whether there were critical errors
            has_critical_error = any(err in combined.lower() for err in [
                'syntaxerror', 'indentationerror', 'nameerror', 
                'modulenotfounderror', 'importerror', 'traceback'
            ])
            
            is_success = (
                result.returncode == 0 and 
                extracted_score is not None and
                extracted_score > 0 and
                not has_critical_error
            )
            
            fallback_result = {
                "success": is_success,
                "score": extracted_score,
                "metrics": {},
                "claude_output": claude_result,
                "stdout": stdout[:5000],
                "stderr": stderr[:2000],
                "execution_time": elapsed,
                "fix_applied": "fix" in combined.lower() or "fixed" in combined.lower(),
                "packages_installed": [],
            }
            
            if not is_success and not extracted_score:
                fallback_result["error"] = "Could not extract score from output"
            
            with open(output_path, 'w') as f:
                json.dump(fallback_result, f, indent=2)
            return fallback_result
            
    except subprocess.TimeoutExpired:
        elapsed = (datetime.now() - start_time).total_seconds()
        if verbose:
            print(f"闁?Claude Code timed out after {timeout}s", file=sys.stderr)
        
        error_result = {
            "success": False,
            "score": 0.0,
            "metrics": {},
            "error": f"Claude Code timed out after {timeout} seconds",
            "execution_time": elapsed,
        }
        with open(output_path, 'w') as f:
            json.dump(error_result, f, indent=2)
        return error_result
        
    except FileNotFoundError:
        elapsed = (datetime.now() - start_time).total_seconds()
        if verbose:
            print(f"闁?Claude Code CLI not found. Install with: npm install -g @anthropic-ai/claude-code", file=sys.stderr)
        
        error_result = {
            "success": False,
            "score": 0.0,
            "metrics": {},
            "error": "Claude Code CLI not installed. Run: npm install -g @anthropic-ai/claude-code",
            "execution_time": elapsed,
        }
        with open(output_path, 'w') as f:
            json.dump(error_result, f, indent=2)
        return error_result
        
    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        if verbose:
            print(f"闁?Error: {e}", file=sys.stderr)
        
        error_result = {
            "success": False,
            "score": 0.0,
            "metrics": {},
            "error": str(e),
            "execution_time": elapsed,
        }
        with open(output_path, 'w') as f:
            json.dump(error_result, f, indent=2)
        return error_result


def run_and_evaluate(
    program_path: str,
    results_dir: str,
    timeout: int = DEFAULT_TIMEOUT,
    task_description: Optional[str] = None,
    json_template: Optional[str] = None,
) -> Dict[str, Any]:
    """
    AgentLTV-compatible interface for running and evaluating programs.
    
    This is designed to be a drop-in replacement for the old evaluation flow.
    
    Args:
        program_path: Path to the program (main.py) to evaluate
        results_dir: Directory to save results
        timeout: Timeout in seconds
        task_description: Description of the task
        json_template: JSON template for output
        
    Returns:
        Dict with combined_score, public metrics, private metrics
    """
    
    output_path = os.path.join(results_dir, "output.json")
    
    # Run Claude fixer
    result = run_claude_fixer(
        script_path=program_path,
        output_path=output_path,
        timeout=timeout,
        task_description=task_description,
        json_template=json_template,
    )
    
    # Convert to AgentLTV format
    score = result.get("score", 0.0) or 0.0
    metrics = result.get("metrics", {})
    
    ea_result = {
        "combined_score": score,
        "public": {
            "composite_score": score,
            **metrics,
        },
        "private": {
            **metrics,
        },
        "elapsed_time": result.get("execution_time", 0),
    }
    
    if not result.get("success", False):
        ea_result["public"]["error"] = result.get("error", "Unknown error")
    
    # Save metrics.json for AgentLTV
    metrics_path = os.path.join(results_dir, "metrics.json")
    with open(metrics_path, 'w') as f:
        json.dump(ea_result, f, indent=2)
    
    return ea_result


def main():
    parser = argparse.ArgumentParser(
        description="Claude Auto Fixer for AgentLTV - Fix and run Python scripts using Claude Code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--script", "-s",
        required=True,
        help="Path to the Python script to fix and run",
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Path where to save the result.json",
    )
    parser.add_argument(
        "--timeout", "-t",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Timeout in seconds for Claude Code (default: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Claude model to use (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--json-template",
        help="JSON template for output format. Can be a file path or JSON string.",
    )
    parser.add_argument(
        "--task-description",
        help="Description of what the script does (helps Claude understand context)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=True,
        help="Enable verbose output (default: True)",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Disable verbose output",
    )
    
    args = parser.parse_args()
    
    # Load JSON template if provided
    json_template = None
    if args.json_template:
        if os.path.exists(args.json_template):
            with open(args.json_template, 'r') as f:
                json_template = f.read().strip()
        else:
            json_template = args.json_template
    
    # Run the fixer
    result = run_claude_fixer(
        script_path=args.script,
        output_path=args.output,
        model=args.model,
        timeout=args.timeout,
        json_template=json_template,
        task_description=args.task_description,
        verbose=not args.quiet,
    )
    
    # Print summary
    success = result.get("success", False)
    if success:
        print(f"闁?SUCCESS")
        score = result.get("score")
        if score is not None:
            print(f"   Score: {score}")
        metrics = result.get("metrics", {})
        if metrics:
            print(f"   Metrics: {metrics}")
    else:
        print(f"闁?FAILED")
        error = result.get("error", "Unknown error")
        print(f"   Error: {str(error)[:200]}")
    
    print(f"   Result saved to: {args.output}")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

