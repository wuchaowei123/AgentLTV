"""
Claude Code Programmatic Auto-Fixer
====================================

Uses Claude Code CLI's programmatic mode (--print with --output-format json)
to automatically fix and run Python code in an iterative loop.

This mimics the interactive Claude Code session workflow:
1. Run code → Get error
2. Ask Claude to fix → Apply fix  
3. Run code again → Repeat until success
"""

import subprocess
import json
import os
import time
import re
from pathlib import Path
from typing import Tuple, Optional, Dict, Any


class ClaudeCodeProgrammaticFixer:
    """Auto-fixer using Claude Code CLI's programmatic JSON mode"""
    
    def __init__(self, max_attempts: int = 5):
        """
        Initialize the programmatic auto-fixer.
        
        Args:
            max_attempts: Maximum number of fix attempts
        """
        self.max_attempts = max_attempts
        self.api_base = os.getenv("ANTHROPIC_BASE_URL", "http://litellm.aviagames.net")
        self.auth_token = os.getenv("ANTHROPIC_AUTH_TOKEN", "sk-1gcvcMUA8g8aNy7y_FRfXg")
        self.model = os.getenv("ANTHROPIC_MODEL", "gpt-5")
        
        # Set environment variables for Claude Code CLI
        os.environ["ANTHROPIC_BASE_URL"] = self.api_base
        os.environ["ANTHROPIC_AUTH_TOKEN"] = self.auth_token
        os.environ["ANTHROPIC_MODEL"] = self.model
        os.environ["ANTHROPIC_DEFAULT_HAIKU_MODEL"] = self.model
        os.environ["CLAUDE_CODE_SUBAGENT_MODEL"] = self.model
        
        print("✅ Claude Code Programmatic Auto Fixer initialized")
        print(f"   API Base: {self.api_base}")
        print(f"   Model: {self.model}")
        print(f"   Max attempts: {max_attempts}")
        print(f"   Claude CLI timeout: 240 seconds (4 minutes)")
        print(f"   Timeout retries: 2")
    
    def run_code(self, file_path: str, run_timeout: int = 600, conda_env: str = "pytorch") -> Tuple[bool, str, str]:
        """
        Run Python code and capture output/error.
        
        Args:
            file_path: Path to Python file
            run_timeout: Timeout in seconds
            conda_env: Conda environment name
            
        Returns:
            Tuple of (success, stdout, stderr)
        """
        # Get absolute path and working directory
        abs_path = Path(file_path).resolve()
        work_dir = abs_path.parent
        file_name = abs_path.name
        
        cmd = f"""
        source ~/.bashrc && \
        conda activate {conda_env} && \
        cd {work_dir} && \
        timeout {run_timeout} python {file_name} 2>&1
        """
        
        try:
            result = subprocess.run(
                ["bash", "-c", cmd],
                capture_output=True,
                text=True,
                timeout=run_timeout + 5  # Extra buffer
            )
            
            output = result.stdout + result.stderr
            success = result.returncode == 0
            
            return success, output, ""
            
        except subprocess.TimeoutExpired:
            return False, "", f"Timeout after {run_timeout} seconds"
        except Exception as e:
            return False, "", f"Execution error: {e}"
    
    def ask_claude_code(self, prompt: str, timeout: int = 240, max_retries: int = 2) -> Optional[Dict[str, Any]]:
        """
        Ask Claude Code CLI programmatically with JSON output.
        
        Args:
            prompt: Question/instruction for Claude
            timeout: Timeout for Claude request (default: 240 seconds)
            max_retries: Number of retries on timeout (default: 2)
            
        Returns:
            Dict with Claude's response or None on error
        """
        # Retry logic for timeouts
        for retry_attempt in range(max_retries + 1):
            if retry_attempt > 0:
                print(f"   🔄 Retry {retry_attempt}/{max_retries}...")
                time.sleep(2)  # Brief delay before retry
            
            cmd = [
                "bash", "-c",
                f"""
                source ~/.bashrc && \
                cd {Path.cwd()} && \
                timeout {timeout} claude -p \
                --output-format json \
                --dangerously-skip-permissions \
                --model {self.model} \
                "{prompt}" 2>&1
                """
            ]
            
            try:
                start_time = time.time()
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout + 5
                )
                duration = time.time() - start_time
                
                if result.returncode == 124:
                    # Timeout - try retry if available
                    print(f"   ⏱️  Claude Code CLI timed out after {timeout}s (attempt {retry_attempt + 1}/{max_retries + 1})")
                    if retry_attempt < max_retries:
                        continue  # Retry
                    else:
                        return None  # All retries exhausted
                
                if result.returncode != 0:
                    print(f"   ❌ Claude Code CLI failed (exit code: {result.returncode})")
                    print(f"   Error: {result.stderr[:500]}")
                    return None
                
                # Parse JSON response
                try:
                    response = json.loads(result.stdout)
                    print(f"   ✓ Claude response received in {duration:.1f} seconds")
                    print(f"   📊 Turns: {response.get('num_turns', 'N/A')}")
                    if retry_attempt > 0:
                        print(f"   ✅ Succeeded after {retry_attempt} retry(ies)")
                    return response
                except json.JSONDecodeError as e:
                    print(f"   ❌ Failed to parse JSON response: {e}")
                    print(f"   Raw output: {result.stdout[:500]}")
                    return None
                    
            except subprocess.TimeoutExpired:
                print(f"   ⏱️  Process timed out after {timeout + 5}s (attempt {retry_attempt + 1}/{max_retries + 1})")
                if retry_attempt < max_retries:
                    continue  # Retry
                else:
                    return None  # All retries exhausted
            except Exception as e:
                print(f"   ❌ Error calling Claude Code CLI: {e}")
                return None
        
        return None  # Should not reach here
    
    def extract_error_info(self, output: str) -> str:
        """Extract concise error information from output"""
        lines = output.split('\n')
        
        # Find traceback
        error_lines = []
        in_traceback = False
        
        for line in lines:
            if 'Traceback (most recent call last):' in line:
                in_traceback = True
            if in_traceback:
                error_lines.append(line)
        
        if error_lines:
            # Return last 20 lines of traceback
            return '\n'.join(error_lines[-20:])
        else:
            # Return last 10 lines if no traceback
            return '\n'.join(lines[-10:])
    
    def try_auto_install_package(self, error_output: str) -> bool:
        """
        Detect ModuleNotFoundError and auto-install the missing package.
        
        Args:
            error_output: Error message from code execution
            
        Returns:
            True if a package was installed, False otherwise
        """
        # Check for ModuleNotFoundError
        if 'ModuleNotFoundError' not in error_output and 'No module named' not in error_output:
            return False
        
        # Extract module name
        import re
        match = re.search(r"No module named ['\"]([^'\"]+)['\"]", error_output)
        if not match:
            return False
        
        module_name = match.group(1)
        print(f"   📦 Detected missing module: {module_name}")
        
        # Map common module names to pip package names
        module_to_package = {
            'iterstrat': 'iterative-stratification',
            'skmultilearn': 'scikit-multilearn',
            'cv2': 'opencv-python',
            'sklearn': 'scikit-learn',
            'PIL': 'Pillow',
        }
        
        # Get the base module name (e.g., 'iterstrat' from 'iterstrat.ml_stratifiers')
        base_module = module_name.split('.')[0]
        package_name = module_to_package.get(base_module, base_module)
        
        print(f"   🔧 Attempting to install: {package_name}")
        
        try:
            import subprocess
            result = subprocess.run(
                ['pip', 'install', package_name],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                print(f"   ✅ Successfully installed {package_name}")
                return True
            else:
                print(f"   ❌ Failed to install {package_name}: {result.stderr[:200]}")
                return False
                
        except Exception as e:
            print(f"   ❌ Error during installation: {e}")
            return False
    
    def auto_fix_and_run(self, file_path: str, run_timeout: int = 600) -> Tuple[bool, str]:
        """
        Automatically fix and run code iteratively using Claude Code CLI.
        
        This mimics the interactive Claude Code workflow:
        1. Run code
        2. If error → Ask Claude to fix
        3. Run again → Repeat until success or max attempts
        
        Args:
            file_path: Path to Python file
            run_timeout: Timeout for each code run
            
        Returns:
            Tuple of (success, final_output)
        """
        abs_path = Path(file_path).resolve()
        
        print("=" * 70)
        print("🚀 STARTING PROGRAMMATIC AUTO-FIX-AND-RUN WORKFLOW")
        print("=" * 70)
        print(f"📁 File: {abs_path}")
        print(f"🔢 Max attempts: {self.max_attempts}")
        print(f"⏱️  Run timeout: {run_timeout} seconds")
        print(f"🤖 Model: {self.model}")
        print("=" * 70)
        print()
        
        all_output = []
        
        for attempt in range(1, self.max_attempts + 1):
            print("─" * 70)
            print(f"📍 ATTEMPT {attempt}/{self.max_attempts}")
            print("─" * 70)
            print()
            
            # Run the code
            print(f"🔄 Running {abs_path.name}...")
            success, output, error = self.run_code(str(abs_path), run_timeout=run_timeout)
            all_output.append(output)
            
            if success:
                print()
                print("=" * 70)
                print("✅ SUCCESS! CODE EXECUTED WITHOUT ERRORS!")
                print("=" * 70)
                print()
                print("📊 Final output (last 50 lines):")
                print('\n'.join(output.split('\n')[-50:]))
                print()
                return True, '\n\n'.join(all_output)
            
            print(f"❌ EXECUTION FAILED")
            error_info = self.extract_error_info(output)
            print(f"   Error:\n{error_info[:500]}")
            print()
            
            # Try to auto-install missing packages first
            if self.try_auto_install_package(output):
                print(f"   🔄 Package installed, re-running code...")
                print()
                # Re-run immediately after installing package
                success, output, error = self.run_code(str(abs_path), run_timeout=run_timeout)
                all_output.append(output)
                
                if success:
                    print()
                    print("=" * 70)
                    print("✅ SUCCESS AFTER AUTO-INSTALL!")
                    print("=" * 70)
                    print()
                    print("📊 Final output (last 50 lines):")
                    print('\n'.join(output.split('\n')[-50:]))
                    print()
                    return True, '\n\n'.join(all_output)
                else:
                    print(f"   ⚠️  Still failing after package install, will ask Claude for fix")
                    error_info = self.extract_error_info(output)
            
            # If not last attempt, ask Claude to fix
            if attempt < self.max_attempts:
                print(f"🤖 Asking Claude Code CLI to fix the error...")
                
                # Construct prompt for Claude
                prompt = f"""Please read {abs_path} and fix the error. The code failed with this error:

{error_info}

Please update the file to fix this error.""".replace('"', '\\"')  # Escape quotes for bash
                
                print(f"   📝 Prompt length: {len(prompt)} characters")
                
                response = self.ask_claude_code(prompt, timeout=120)
                
                if not response:
                    print(f"   ❌ Failed to get Claude response, skipping to next attempt...")
                    continue
                
                if response.get('is_error'):
                    print(f"   ❌ Claude returned error: {response.get('result', 'Unknown error')}")
                    continue
                
                result_text = response.get('result', '')
                print(f"   💡 Claude's response (first 300 chars):")
                print(f"      {result_text[:300]}...")
                print()
                print("   ✅ Claude has updated the file")
                print()
                
                # Small delay before next attempt
                time.sleep(1)
            else:
                print()
                print("😞 Max attempts reached without success")
        
        print()
        print("=" * 70)
        print("❌ FAILED TO FIX CODE AFTER ALL ATTEMPTS")
        print("=" * 70)
        return False, '\n\n'.join(all_output)


def test_programmatic_fixer():
    """Test the programmatic fixer on the test broken code"""
    fixer = ClaudeCodeProgrammaticFixer(max_attempts=5)
    
    test_file = Path.cwd() / "test_broken_code.py"
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return
    
    success, output = fixer.auto_fix_and_run(str(test_file), run_timeout=60)
    
    if success:
        print("🎉 Test passed!")
    else:
        print("❌ Test failed")
    
    return success


if __name__ == "__main__":
    test_programmatic_fixer()

