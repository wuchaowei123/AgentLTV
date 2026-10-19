#!/usr/bin/env python3
"""
Claude Code Fixer - Simple and Powerful

The philosophy: Instead of writing complex regex patterns and heuristics,
just send the broken code to Claude and let it fix everything.

This is the SIMPLE approach:
1. Read the file
2. Send to Claude with a well-crafted prompt
3. Get fixed code back
4. Done.

Usage:
    from ea.utils.claude_code_fixer import fix_code, fix_code_with_error
    
    # Fix any code issues
    success, fixed_code = fix_code("path/to/broken.py")
    
    # Fix with specific error message
    success, fixed_code = fix_code_with_error("path/to/broken.py", "NameError: 'deque' is not defined")
"""

import os
import sys
import json
import requests
from pathlib import Path
from typing import Optional, Tuple, Dict, Any


# Default LiteLLM configuration
DEFAULT_API_BASE = os.getenv("OPENAI_API_BASE", "")
DEFAULT_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEFAULT_MODEL = "claude-sonnet-4.5"  # Best for code


# ============================================================================
# PROMPT TEMPLATES
# ============================================================================

PROMPT_FIX_SYNTAX = """You are a Python code fixer. Fix the following Python code.

RULES:
1. Fix ALL syntax errors, indentation issues, Unicode characters
2. Add ANY missing import statements
3. DO NOT change the algorithm or logic
4. DO NOT change ML model libraries (don't replace XGBoost with LightGBM, etc.)
5. Return ONLY the complete fixed Python code
6. No explanations, no markdown, JUST CODE

```python
{code}
```

Fixed code:"""


PROMPT_FIX_WITH_ERROR = """You are a Python code fixer. The following code has an error.

ERROR MESSAGE:
{error}

CODE:
```python
{code}
```

RULES:
1. Fix the specific error shown above
2. Also fix any other syntax errors, indentation issues, Unicode characters
3. Add any missing import statements
4. DO NOT change the algorithm or logic
5. DO NOT change ML model libraries
6. Return ONLY the complete fixed Python code
7. No explanations, no markdown, JUST CODE

Fixed code:"""


PROMPT_FIX_IMPORTS_ONLY = """You are a Python import fixer. The code below has missing imports.

ERROR:
{error}

CODE:
```python
{code}
```

TASK:
1. Identify all missing imports
2. Add the correct import statements at the top
3. DO NOT change anything else
4. Return the complete code with added imports
5. No explanations, JUST CODE

Fixed code:"""


PROMPT_VALIDATE_AND_FIX = """You are a Python code validator and fixer.

CODE:
```python
{code}
```

TASK:
1. Check if the code has any issues:
   - Syntax errors
   - Indentation errors
   - Missing imports
   - Unicode characters that should be Python operators
   - Undefined variables or functions

2. If issues found, fix them ALL
3. If no issues, return the code unchanged

RULES:
- DO NOT change the algorithm or logic
- DO NOT change ML model libraries
- Return ONLY the complete code
- No explanations, JUST CODE

Result:"""


# ============================================================================
# CLAUDE API CLIENT
# ============================================================================

class ClaudeCodeFixer:
    """
    Simple Claude-based code fixer.
    Just send code to Claude, get fixed code back.
    """
    
    def __init__(
        self,
        api_base: str = None,
        api_key: str = None,
        model: str = None,
        timeout: int = 180,
        max_tokens: int = 16000,
        temperature: float = 0.1,
        verbose: bool = True
    ):
        """
        Initialize the Claude code fixer.
        
        Args:
            api_base: LiteLLM API base URL
            api_key: API key
            model: Model to use (default: claude-sonnet-4.5)
            timeout: Request timeout in seconds
            max_tokens: Maximum tokens in response
            temperature: Model temperature (lower = more deterministic)
            verbose: Print status messages
        """
        self.api_base = api_base or os.getenv('OPENAI_API_BASE', DEFAULT_API_BASE)
        self.api_key = api_key or os.getenv('OPENAI_API_KEY', DEFAULT_API_KEY)
        self.model = model or os.getenv('CLAUDE_FIXER_MODEL', DEFAULT_MODEL)
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.verbose = verbose
        
        if self.verbose:
            print(f"棣冩暋 Claude Code Fixer initialized")
            print(f"   Model: {self.model}")
            print(f"   API: {self.api_base}")
    
    def _call_claude(self, prompt: str) -> Optional[str]:
        """Call Claude via LiteLLM and return the response."""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': self.model,
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': self.max_tokens,
                'temperature': self.temperature
            }
            
            if self.verbose:
                print(f"棣冾樆 Sending to Claude ({self.model})...")
            
            response = requests.post(
                f'{self.api_base}/chat/completions',
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if 'choices' in data and len(data['choices']) > 0:
                    content = data['choices'][0]['message']['content'].strip()
                    
                    # Extract code from markdown if present
                    content = self._extract_code(content)
                    
                    if self.verbose:
                        print(f"閴?Got response ({len(content)} chars)")
                    
                    return content
                else:
                    if self.verbose:
                        print(f"閴?Unexpected response format")
                    return None
            else:
                if self.verbose:
                    print(f"閴?API error: {response.status_code}")
                    print(f"   Response: {response.text[:500]}")
                return None
                
        except requests.exceptions.Timeout:
            if self.verbose:
                print(f"閴?Request timed out after {self.timeout}s")
            return None
        except Exception as e:
            if self.verbose:
                print(f"閴?Error: {e}")
            return None
    
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
            # Skip language identifier if present
            newline = response.find('\n', start)
            if newline != -1 and newline - start < 20:
                start = newline + 1
            end = response.find('```', start)
            if end != -1:
                return response[start:end].strip()
        
        # No markdown, return as-is
        return response.strip()
    
    def fix(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        Fix Python code (general fix for any issues).
        
        Args:
            code: Python code to fix
            
        Returns:
            (success, fixed_code)
        """
        prompt = PROMPT_FIX_SYNTAX.format(code=code)
        fixed_code = self._call_claude(prompt)
        
        if fixed_code:
            return True, fixed_code
        return False, None
    
    def fix_with_error(self, code: str, error: str) -> Tuple[bool, Optional[str]]:
        """
        Fix Python code with a specific error message.
        
        Args:
            code: Python code to fix
            error: Error message
            
        Returns:
            (success, fixed_code)
        """
        prompt = PROMPT_FIX_WITH_ERROR.format(code=code, error=error)
        fixed_code = self._call_claude(prompt)
        
        if fixed_code:
            return True, fixed_code
        return False, None
    
    def fix_imports(self, code: str, error: str) -> Tuple[bool, Optional[str]]:
        """
        Fix only import statements.
        
        Args:
            code: Python code
            error: Import error message
            
        Returns:
            (success, fixed_code)
        """
        prompt = PROMPT_FIX_IMPORTS_ONLY.format(code=code, error=error)
        fixed_code = self._call_claude(prompt)
        
        if fixed_code:
            return True, fixed_code
        return False, None
    
    def validate_and_fix(self, code: str) -> Tuple[bool, Optional[str], bool]:
        """
        Validate code and fix if needed.
        
        Args:
            code: Python code to validate
            
        Returns:
            (is_valid, fixed_code_if_changed, was_fixed)
        """
        prompt = PROMPT_VALIDATE_AND_FIX.format(code=code)
        result = self._call_claude(prompt)
        
        if result:
            # Check if code was changed
            was_fixed = result.strip() != code.strip()
            return True, result, was_fixed
        return False, None, False
    
    def fix_file(self, file_path: str, save: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Fix a Python file.
        
        Args:
            file_path: Path to Python file
            save: Whether to save the fixed code back to the file
            
        Returns:
            (success, fixed_code)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
        except Exception as e:
            if self.verbose:
                print(f"閴?Cannot read file: {e}")
            return False, None
        
        success, fixed_code = self.fix(code)
        
        if success and save:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_code)
                if self.verbose:
                    print(f"閴?Fixed code saved to {file_path}")
            except Exception as e:
                if self.verbose:
                    print(f"閳跨媴绗? Cannot save file: {e}")
        
        return success, fixed_code
    
    def fix_file_with_error(
        self, 
        file_path: str, 
        error: str, 
        save: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """
        Fix a Python file with a specific error message.
        
        Args:
            file_path: Path to Python file
            error: Error message
            save: Whether to save the fixed code
            
        Returns:
            (success, fixed_code)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
        except Exception as e:
            if self.verbose:
                print(f"閴?Cannot read file: {e}")
            return False, None
        
        success, fixed_code = self.fix_with_error(code, error)
        
        if success and save:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_code)
                if self.verbose:
                    print(f"閴?Fixed code saved to {file_path}")
            except Exception as e:
                if self.verbose:
                    print(f"閳跨媴绗? Cannot save file: {e}")
        
        return success, fixed_code


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def fix_code(code_or_path: str, save: bool = True, verbose: bool = True) -> Tuple[bool, Optional[str]]:
    """
    Fix Python code or file.
    
    Args:
        code_or_path: Either Python code string or path to file
        save: If path provided, save the fixed code
        verbose: Print status messages
        
    Returns:
        (success, fixed_code)
    """
    fixer = ClaudeCodeFixer(verbose=verbose)
    
    # Check if it's a file path
    if os.path.isfile(code_or_path):
        return fixer.fix_file(code_or_path, save=save)
    else:
        return fixer.fix(code_or_path)


def fix_code_with_error(
    code_or_path: str, 
    error: str, 
    save: bool = True, 
    verbose: bool = True
) -> Tuple[bool, Optional[str]]:
    """
    Fix Python code or file with a specific error message.
    
    Args:
        code_or_path: Either Python code string or path to file
        error: Error message
        save: If path provided, save the fixed code
        verbose: Print status messages
        
    Returns:
        (success, fixed_code)
    """
    fixer = ClaudeCodeFixer(verbose=verbose)
    
    # Check if it's a file path
    if os.path.isfile(code_or_path):
        return fixer.fix_file_with_error(code_or_path, error, save=save)
    else:
        return fixer.fix_with_error(code_or_path, error)


# ============================================================================
# CLI INTERFACE
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Claude Code Fixer - Fix Python code with AI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Fix a file
    python claude_code_fixer.py broken.py
    
    # Fix with error message
    python claude_code_fixer.py broken.py --error "NameError: 'deque' is not defined"
    
    # Don't save, just print
    python claude_code_fixer.py broken.py --no-save
    
    # Use different model
    python claude_code_fixer.py broken.py --model gpt-5.1-2025-11-13
"""
    )
    
    parser.add_argument('file', help='Python file to fix')
    parser.add_argument('--error', '-e', help='Error message for targeted fix')
    parser.add_argument('--no-save', action='store_true', help='Do not save fixed code')
    parser.add_argument('--model', '-m', default=DEFAULT_MODEL, help='Model to use')
    parser.add_argument('--quiet', '-q', action='store_true', help='Quiet mode')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Claude Code Fixer")
    print("=" * 60)
    
    fixer = ClaudeCodeFixer(
        model=args.model,
        verbose=not args.quiet
    )
    
    if args.error:
        success, fixed_code = fixer.fix_file_with_error(
            args.file, 
            args.error, 
            save=not args.no_save
        )
    else:
        success, fixed_code = fixer.fix_file(
            args.file, 
            save=not args.no_save
        )
    
    if success:
        print("\n閴?Code fixed successfully!")
        if args.no_save and fixed_code:
            print("\n" + "=" * 60)
            print("FIXED CODE:")
            print("=" * 60)
            print(fixed_code)
    else:
        print("\n閴?Failed to fix code")
        sys.exit(1)



















