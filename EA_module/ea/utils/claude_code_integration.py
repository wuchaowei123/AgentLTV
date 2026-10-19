#!/usr/bin/env python3
"""
Claude Code Integration for AgentLTV

This module integrates Anthropic's Claude Code CLI tool with AgentLTV.
Claude Code is an agentic coding tool that can understand codebases and fix code.

Configuration:
    Set environment variables:
    - ANTHROPIC_BASE_URL: LiteLLM proxy URL (e.g., http://your-proxy-server:port)
    - ANTHROPIC_AUTH_TOKEN: LiteLLM API key

Usage:
    from ea.utils.claude_code_integration import ClaudeCodeFixer
    
    fixer = ClaudeCodeFixer()
    success, fixed_code = fixer.fix_file("/path/to/broken.py", error="NameError: 'deque' is not defined")
"""

import os
import subprocess
import sys
import re
import tempfile
from pathlib import Path
from typing import Optional, Tuple, Dict, Any


class ClaudeCodeFixer:
    """
    Wrapper for Claude Code CLI to fix Python code.
    Uses the -p (print) mode for non-interactive execution.
    """
    
    # Default LiteLLM configuration
    DEFAULT_API_BASE = os.getenv("OPENAI_API_BASE", "")
    DEFAULT_API_KEY = os.getenv("OPENAI_API_KEY", "")
    DEFAULT_MODEL = "claude-sonnet-4.5"
    
    # Prompt templates
    PROMPT_FIX_SYNTAX = """Fix ALL issues in the Python code at {file_path}:
- Fix syntax errors
- Fix indentation errors
- Replace Unicode characters (闁愁喖鐗冮崯?=, 闁愁喓鍊愰崯?=, etc.)
- Fix incomplete decimals (1e闁?e0)
- Add missing imports

DO NOT change the algorithm or ML model libraries.
Return ONLY the complete fixed Python code, no explanations."""

    PROMPT_FIX_WITH_ERROR = """Fix the Python code at {file_path}.

ERROR: {error}

Fix the specific error and also:
- Fix any syntax errors
- Fix indentation issues  
- Replace Unicode characters with valid Python
- Add missing imports

DO NOT change the algorithm or ML model libraries.
Return ONLY the complete fixed Python code, no explanations."""

    def __init__(
        self,
        api_base: str = None,
        api_key: str = None,
        model: str = None,
        timeout: int = 300,
        verbose: bool = True
    ):
        """
        Initialize Claude Code integration.
        
        Args:
            api_base: LiteLLM API base URL
            api_key: API key
            model: Model to use
            timeout: Command timeout in seconds
            verbose: Print status messages
        """
        self.api_base = api_base or os.getenv('ANTHROPIC_BASE_URL', self.DEFAULT_API_BASE)
        self.api_key = api_key or os.getenv('ANTHROPIC_AUTH_TOKEN', self.DEFAULT_API_KEY)
        self.model = model or os.getenv('CLAUDE_CODE_MODEL', self.DEFAULT_MODEL)
        self.timeout = timeout
        self.verbose = verbose
        
        # Check if claude command is available
        self.claude_available = self._check_claude_installed()
        
        if self.verbose:
            print(f"妫ｅ啯鏆?Claude Code Integration initialized")
            print(f"   Model: {self.model}")
            print(f"   API Base: {self.api_base}")
            print(f"   Claude CLI available: {self.claude_available}")
    
    def _check_claude_installed(self) -> bool:
        """Check if Claude Code CLI is installed."""
        try:
            result = subprocess.run(
                ['claude', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _run_claude(self, prompt: str, cwd: str = None) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Run Claude Code with a prompt.
        
        Returns:
            (success, output, error)
        """
        if not self.claude_available:
            return False, None, "Claude Code CLI not installed"
        
        # Set up environment
        env = os.environ.copy()
        env['ANTHROPIC_BASE_URL'] = self.api_base
        env['ANTHROPIC_AUTH_TOKEN'] = self.api_key
        
        cmd = [
            'claude',
            '-p',  # Print mode (non-interactive)
            '--model', self.model,
            '--dangerously-skip-permissions',  # Skip permission checks
            prompt
        ]
        
        try:
            if self.verbose:
                print(f"妫ｅ喚妯?Running Claude Code...")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=cwd,
                env=env
            )
            
            if result.returncode == 0:
                return True, result.stdout.strip(), None
            else:
                return False, None, result.stderr or result.stdout
                
        except subprocess.TimeoutExpired:
            return False, None, f"Claude Code timed out after {self.timeout}s"
        except Exception as e:
            return False, None, str(e)
    
    def _extract_code(self, response: str) -> str:
        """Extract Python code from Claude's response."""
        # Try to find code block
        if '```python' in response:
            start = response.find('```python') + 9
            end = response.find('```', start)
            if end != -1:
                return response[start:end].strip()
        
        if '```' in response:
            start = response.find('```') + 3
            # Skip language identifier
            newline = response.find('\n', start)
            if newline != -1 and newline - start < 20:
                start = newline + 1
            end = response.find('```', start)
            if end != -1:
                return response[start:end].strip()
        
        # No markdown, return as-is
        return response.strip()
    
    def fix_code(self, code: str, error: str = None) -> Tuple[bool, Optional[str]]:
        """
        Fix Python code string.
        
        Args:
            code: Python code to fix
            error: Optional error message
            
        Returns:
            (success, fixed_code)
        """
        # Write code to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = f.name
        
        try:
            success, fixed_code = self.fix_file(temp_path, error=error, save=False)
            return success, fixed_code
        finally:
            try:
                os.unlink(temp_path)
            except:
                pass
    
    def fix_file(
        self,
        file_path: str,
        error: str = None,
        save: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """
        Fix a Python file.
        
        Args:
            file_path: Path to Python file
            error: Optional error message for targeted fix
            save: Whether to save the fixed code back to the file
            
        Returns:
            (success, fixed_code)
        """
        file_path = str(Path(file_path).resolve())
        
        # Check file exists
        if not os.path.exists(file_path):
            if self.verbose:
                print(f"闁?File not found: {file_path}")
            return False, None
        
        # Build prompt
        if error:
            prompt = self.PROMPT_FIX_WITH_ERROR.format(file_path=file_path, error=error)
        else:
            prompt = self.PROMPT_FIX_SYNTAX.format(file_path=file_path)
        
        # Run Claude Code
        success, output, err = self._run_claude(prompt, cwd=os.path.dirname(file_path))
        
        if not success:
            if self.verbose:
                print(f"闁?Claude Code failed: {err}")
            return False, None
        
        # Extract code from response
        fixed_code = self._extract_code(output)
        
        if not fixed_code:
            if self.verbose:
                print(f"闁?No code in response")
            return False, None
        
        # Validate syntax
        try:
            compile(fixed_code, '<string>', 'exec')
        except SyntaxError as e:
            if self.verbose:
                print(f"闁宠法濯寸粭? Fixed code still has syntax error: {e}")
            # Return anyway, let caller decide
        
        if self.verbose:
            print(f"闁?Code fixed successfully ({len(fixed_code)} chars)")
        
        # Save if requested
        if save:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_code)
                if self.verbose:
                    print(f"闁?Saved to {file_path}")
            except Exception as e:
                if self.verbose:
                    print(f"闁宠法濯寸粭? Could not save: {e}")
        
        return True, fixed_code
    
    def validate_and_fix(
        self,
        file_path: str,
        save: bool = True
    ) -> Tuple[bool, Optional[str], bool]:
        """
        Validate code and fix if needed.
        
        Returns:
            (is_valid, fixed_code, was_fixed)
        """
        file_path = str(Path(file_path).resolve())
        
        # First check if code has syntax errors
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            compile(code, file_path, 'exec')
            # No syntax errors, return as-is
            return True, code, False
        except SyntaxError as e:
            error = f"SyntaxError: {e.msg} at line {e.lineno}"
            if self.verbose:
                print(f"妫ｅ啯鏁?Found syntax error: {error}")
        except Exception as e:
            error = str(e)
        
        # Fix the code
        success, fixed_code = self.fix_file(file_path, error=error, save=save)
        
        return success, fixed_code, success


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def fix_file_with_claude_code(
    file_path: str,
    error: str = None,
    save: bool = True,
    verbose: bool = True
) -> Tuple[bool, Optional[str]]:
    """
    Fix a Python file using Claude Code.
    
    Args:
        file_path: Path to Python file
        error: Optional error message
        save: Whether to save the fixed code
        verbose: Print status messages
        
    Returns:
        (success, fixed_code)
    """
    fixer = ClaudeCodeFixer(verbose=verbose)
    return fixer.fix_file(file_path, error=error, save=save)


def fix_code_with_claude_code(
    code: str,
    error: str = None,
    verbose: bool = True
) -> Tuple[bool, Optional[str]]:
    """
    Fix Python code string using Claude Code.
    
    Args:
        code: Python code to fix
        error: Optional error message
        verbose: Print status messages
        
    Returns:
        (success, fixed_code)
    """
    fixer = ClaudeCodeFixer(verbose=verbose)
    return fixer.fix_code(code, error=error)


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Fix Python code with Claude Code')
    parser.add_argument('file', help='Python file to fix')
    parser.add_argument('--error', '-e', help='Error message for targeted fix')
    parser.add_argument('--no-save', action='store_true', help='Do not save fixed code')
    parser.add_argument('--quiet', '-q', action='store_true', help='Quiet mode')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Claude Code Integration for AgentLTV")
    print("=" * 60)
    
    fixer = ClaudeCodeFixer(verbose=not args.quiet)
    success, fixed_code = fixer.fix_file(
        args.file,
        error=args.error,
        save=not args.no_save
    )
    
    if success:
        print("\n闁?Code fixed successfully!")
        if args.no_save and fixed_code:
            print("\n" + "=" * 60)
            print("FIXED CODE:")
            print("=" * 60)
            print(fixed_code[:1000] + "..." if len(fixed_code) > 1000 else fixed_code)
    else:
        print("\n闁?Failed to fix code")
        sys.exit(1)



















