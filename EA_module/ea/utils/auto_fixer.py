#!/usr/bin/env python3
"""
EAFramework Auto Fixer
Universal auto-fixing and safe code execution for EAFramework

Features:
1. Pre-execution validation with static analysis (NEW!)
2. Auto-fix common LLM errors: Unicode, indentation, missing imports
3. Auto-fix code errors using Claude via LiteLLM
4. Auto-install missing packages
5. Safe execution of LLM-generated analysis code (for Kosmos)
6. Model change validation (prevents auto-fixer from changing ML models)

ERROR ANALYSIS (from real evolution runs):
- 42% IndentationError - LLM generates wrong indentation
- 16% Invalid decimal literal - LLM writes '1e' or '0.'
- 11% Invalid Unicode characters - LLM uses 閳?instead of ==
- 31% Missing imports - LLM forgets import statements

This auto-fixer addresses ALL these common failure modes.
"""

import subprocess
import os
import sys
import time
import re
import ast
import json
import tempfile
from pathlib import Path
from typing import Optional, Tuple, Set, Dict, Any, Callable, List
import requests

# Import the new code validator
try:
    from ea.utils.code_validator import CodeValidator, validate_and_fix
except ImportError:
    # Fallback if running standalone
    try:
        from code_validator import CodeValidator, validate_and_fix
    except ImportError:
        CodeValidator = None
        validate_and_fix = None

# Package name mapping for common packages
PACKAGE_NAME_MAPPING = {
    'bs4': 'beautifulsoup4',
    'cv2': 'opencv-python',
    'PIL': 'pillow',
    'yaml': 'pyyaml',
    'sklearn': 'scikit-learn',
    'imblearn': 'imbalanced-learn',
    'lgb': 'lightgbm',
    'xgb': 'xgboost',
}


class EAAutoFixer:
    """
    Universal auto-fixer for EAFramework.
    
    Capabilities:
    1. PRE-EXECUTION VALIDATION - Catch errors before running (saves time!)
    2. AUTO-FIX COMMON LLM ERRORS:
       - Unicode characters (閳?閳?==)
       - Indentation issues
       - Missing imports
       - Incomplete decimal literals
    3. Fix broken code using Claude via LiteLLM
    4. Auto-install missing packages
    5. Execute LLM-generated analysis code safely (for Kosmos integration)
    6. Validate fixes to prevent model changes
    """
    
    def __init__(
        self, 
        max_fix_attempts: int = 2, 
        execution_timeout: int = 600, 
        auto_install: bool = True,
        verbose: bool = True,
        enable_pre_validation: bool = True,
        enable_static_fixes: bool = True
    ):
        """
        Initialize auto-fixer
        
        Args:
            max_fix_attempts: Maximum number of fix attempts per error
            execution_timeout: Timeout for code execution in seconds
            auto_install: Auto-install missing packages
            verbose: Print status messages
            enable_pre_validation: Run static analysis before execution
            enable_static_fixes: Apply static fixes (unicode, imports, indentation)
        """
        self.max_fix_attempts = max_fix_attempts
        self.execution_timeout = execution_timeout
        self.auto_install = auto_install
        self.verbose = verbose
        self.enable_pre_validation = enable_pre_validation
        self.enable_static_fixes = enable_static_fixes
        
        # Initialize code validator if available
        self.code_validator = None
        if CodeValidator and enable_pre_validation:
            self.code_validator = CodeValidator(
                auto_suggest_imports=True,
                auto_fix_unicode=enable_static_fixes,
                auto_fix_indentation=enable_static_fixes,
                verbose=verbose
            )
        
        # LiteLLM configuration for Claude
        self.api_base = os.getenv('OPENAI_API_BASE', '')
        self.api_key = os.getenv('OPENAI_API_KEY', '')
        self.model = os.getenv('AUTOFIXER_MODEL', 'claude-sonnet-4-5')  # Best for code fixing (note: hyphen not dot!)
        
        if self.verbose:
            print(f"棣冩暋 EAAutoFixer initialized")
            print(f"   Max fix attempts: {self.max_fix_attempts}")
            print(f"   Execution timeout: {self.execution_timeout}s")
            print(f"   Auto-install packages: {self.auto_install}")
            print(f"   Pre-validation: {self.enable_pre_validation}")
            print(f"   Static fixes: {self.enable_static_fixes}")
            print(f"   Fix model: {self.model}")
    
    # =========================================================================
    # PRE-EXECUTION VALIDATION (NEW!)
    # =========================================================================
    
    def pre_validate_and_fix(self, program_path: str) -> Tuple[bool, Optional[str], bool]:
        """
        Validate code and apply static fixes BEFORE execution.
        This catches most common LLM errors without needing to run the code.
        
        Args:
            program_path: Path to program file
            
        Returns:
            (is_valid, error_message, was_fixed)
        """
        if not self.code_validator:
            return True, None, False
        
        if self.verbose:
            print(f"\n棣冩敵 Pre-validating: {program_path}")
        
        is_valid, error, fixed_code = self.code_validator.validate(program_path)
        
        if is_valid:
            if fixed_code:
                # Apply the fixes
                try:
                    with open(program_path, 'w', encoding='utf-8') as f:
                        f.write(fixed_code)
                    if self.verbose:
                        print(f"閴?Static fixes applied and saved")
                    return True, None, True
                except Exception as e:
                    if self.verbose:
                        print(f"閳跨媴绗? Could not save fixes: {e}")
                    return True, None, False
            else:
                if self.verbose:
                    print(f"閴?Pre-validation passed (no fixes needed)")
                return True, None, False
        else:
            if self.verbose:
                print(f"閴?Pre-validation failed: {error}")
            return False, error, False
    
    # =========================================================================
    # PACKAGE INSTALLATION
    # =========================================================================
    
    def _install_package(self, package_name: str) -> bool:
        """Auto-install missing package"""
        pip_package = PACKAGE_NAME_MAPPING.get(package_name, package_name)
        
        if self.verbose:
            print(f"棣冩憹 Auto-installing: {package_name}")
            if pip_package != package_name:
                print(f"   (pip: {pip_package})")
        
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", pip_package],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                if self.verbose:
                    print(f"閴?Installed {pip_package}")
                return True
            else:
                if self.verbose:
                    print(f"閴?Failed to install {pip_package}")
                return False
        except Exception as e:
            if self.verbose:
                print(f"閴?Error installing: {e}")
            return False
    
    # =========================================================================
    # CODE VALIDATION
    # =========================================================================
    
    def _strip_markdown_fences(self, code: str) -> str:
        """
        Strip markdown code fences from LLM output.
        Handles ```python and ``` at start/end of code.
        """
        if not code:
            return code
            
        code = code.strip()
        
        # Check if code is wrapped in markdown fences
        if code.startswith('```python'):
            # Find the end of the opening fence line
            newline_idx = code.find('\n')
            if newline_idx != -1:
                code = code[newline_idx + 1:]
            else:
                code = code[9:]  # Just skip ```python
        elif code.startswith('```'):
            newline_idx = code.find('\n')
            if newline_idx != -1:
                code = code[newline_idx + 1:]
            else:
                code = code[3:]  # Just skip ```
        
        # Remove closing fence
        if code.rstrip().endswith('```'):
            code = code.rstrip()
            code = code[:-3].rstrip()
        
        return code
    
    def _extract_ml_imports(self, code: str) -> Set[str]:
        """Extract ML library imports from code (lightgbm, xgboost, catboost, etc.)"""
        ml_libs = set()
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        lib_name = alias.name.split('.')[0]
                        if lib_name in {'lightgbm', 'xgboost', 'catboost', 'sklearn', 'torch', 'tensorflow'}:
                            ml_libs.add(lib_name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        lib_name = node.module.split('.')[0]
                        if lib_name in {'lightgbm', 'xgboost', 'catboost', 'sklearn', 'torch', 'tensorflow'}:
                            ml_libs.add(lib_name)
        except:
            pass
        return ml_libs
    
    def _validate_fix(self, original_code: str, fixed_code: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that the fix didn't inappropriately change ML models.
        Returns (is_valid, reason_if_invalid)
        
        ALLOW: catboost閳姡ightgbm if code was using lgb (fixing import mismatch)
        REJECT: xgboost閳姡ightgbm if code was using xgb (changing working model)
        """
        original_libs = self._extract_ml_imports(original_code)
        fixed_libs = self._extract_ml_imports(fixed_code)
        
        removed_libs = original_libs - fixed_libs
        added_libs = fixed_libs - original_libs
        
        if removed_libs and added_libs:
            # Check if original code was actually using the NEW library
            for added_lib in added_libs:
                lib_aliases = {
                    'lightgbm': ['lgb.', 'LGBMClassifier', 'LGBMRegressor'],
                    'xgboost': ['xgb.', 'XGBClassifier', 'XGBRegressor'],
                    'catboost': ['cb.', 'CatBoostClassifier', 'CatBoostRegressor'],
                }
                
                if added_lib in lib_aliases:
                    for pattern in lib_aliases[added_lib]:
                        if pattern in original_code:
                            if self.verbose:
                                print(f"   閳╃櫢绗? Detected import mismatch fix: {removed_libs}閳姾added_libs}")
                                print(f"      Code was using {added_lib} syntax, fixing import")
                            return True, None
            
            return False, f"閳跨媴绗? Auto-fixer changed model library! Removed: {removed_libs}, Added: {added_libs}"
        
        elif removed_libs:
            return False, f"閳跨媴绗? Auto-fixer removed ML library: {removed_libs}"
        
        return True, None
    
    # =========================================================================
    # CODE FIXING
    # =========================================================================
    
    def _fix_code_with_claude(self, code: str, error_msg: str) -> Optional[str]:
        """Use Claude to fix code"""
        try:
            prompt = f"""I have Python code that is producing an error. Please fix it with MINIMAL changes.

Original code:
```python
{code}
```

Error:
```
{error_msg}
```

CRITICAL REQUIREMENTS:
1. Make MINIMAL changes - ONLY fix the specific error
2. DO NOT change machine learning model libraries (e.g., don't replace XGBoost with LightGBM)
3. DO NOT refactor or simplify working code
4. ONLY fix: syntax errors, wrong imports, wrong parameter names/usage
5. If it's an import mismatch, fix the import - DON'T change the model
6. If it's a parameter error, fix the parameter - DON'T change the model
7. Maintain the exact same function signatures and return values
8. Keep the EVOLVE-BLOCK structure if present
9. Return ONLY the complete fixed Python code
10. No explanations, just code

Fixed code:"""
            
            if self.verbose:
                print("棣冾樆 Asking Claude to fix code...")
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': self.model,
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 8192,
                'temperature': 0.3
            }
            
            response = requests.post(
                f'{self.api_base}/chat/completions',
                headers=headers,
                json=payload,
                timeout=180
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if 'choices' in data and len(data['choices']) > 0:
                    fixed_code = data['choices'][0]['message']['content'].strip()
                else:
                    if self.verbose:
                        print(f"閴?Unexpected response format")
                    return None
                
                # Extract code from markdown if present
                fixed_code = self._strip_markdown_fences(fixed_code)
                return fixed_code
            else:
                if self.verbose:
                    print(f"閴?API call failed: {response.status_code}")
                return None
                
        except Exception as e:
            if self.verbose:
                print(f"閴?Error during fix: {e}")
            return None
    
    # =========================================================================
    # STANDALONE CODE FIXING (without execution)
    # =========================================================================
    
    def fix_code_with_error(
        self, 
        program_path: str, 
        error_msg: str,
        fix_hint: str = ""
    ) -> Tuple[bool, Optional[str]]:
        """
        Fix code based on an error message, without executing.
        Returns (success, path_to_fixed_code)
        
        Args:
            program_path: Path to the original program
            error_msg: Error message describing the problem
            fix_hint: Optional hint for how to fix the code
        
        Returns:
            (success, fixed_path) - fixed_path is None if fix failed
        """
        if self.verbose:
            print(f"\n棣冩暋 Fixing code based on error...")
            print(f"   Error: {error_msg[:200]}")
        
        try:
            with open(program_path, 'r', encoding='utf-8') as f:
                code = f.read()
        except Exception as e:
            if self.verbose:
                print(f"閴?Cannot read file: {e}")
            return False, None
        
        # Construct fix prompt with hint
        fix_prompt = error_msg
        if fix_hint:
            fix_prompt = f"{error_msg}\n\nHINT: {fix_hint}"
        
        fixed_code = self._fix_code_with_claude(code, fix_prompt)
        
        if not fixed_code:
            if self.verbose:
                print("閴?Could not get fix from Claude")
            return False, None
        
        # Validate the fix
        is_valid, validation_error = self._validate_fix(code, fixed_code)
        if not is_valid:
            if self.verbose:
                print(f"閴?Fix validation failed: {validation_error}")
            return False, None
        
        # Write fixed code to new file
        fixed_path = f"{program_path}.fixed"
        try:
            with open(fixed_path, 'w', encoding='utf-8') as f:
                f.write(fixed_code)
            if self.verbose:
                print(f"閴?Fixed code saved to: {fixed_path}")
            return True, fixed_path
        except Exception as e:
            if self.verbose:
                print(f"閴?Cannot write fixed code: {e}")
            return False, None
    
    # =========================================================================
    # CODE EXECUTION WITH AUTO-FIX
    # =========================================================================
    
    def try_fix_and_execute(
        self,
        program_path: str,
        execute_fn: Callable[[str], Tuple[bool, Optional[dict], Optional[str]]],
        max_total_attempts: int = 3
    ) -> Tuple[bool, Optional[dict], Optional[str]]:
        """
        Try to fix and execute code
        
        Args:
            program_path: Path to program file
            execute_fn: Function to execute program (should return (success, metrics, error_msg))
            max_total_attempts: Maximum total attempts (including fixes)
        
        Returns:
            (success, metrics, error_msg)
        """
        if self.verbose:
            print(f"\n棣冩畬 Executing with auto-fix: {program_path}")
            print("=" * 70)
        
        # STEP 0: Pre-validation with static fixes (NEW!)
        if self.enable_pre_validation:
            is_valid, pre_error, was_fixed = self.pre_validate_and_fix(program_path)
            if not is_valid:
                # Try to fix with Claude if static analysis found errors
                if self.verbose:
                    print(f"閳跨媴绗? Pre-validation failed, trying Claude fix...")
                
                try:
                    with open(program_path, 'r', encoding='utf-8') as f:
                        code = f.read()
                    
                    fixed_code = self._fix_code_with_claude(code, pre_error)
                    if fixed_code:
                        # Validate the fix
                        is_valid_fix, validation_error = self._validate_fix(code, fixed_code)
                        if is_valid_fix:
                            with open(program_path, 'w', encoding='utf-8') as f:
                                f.write(fixed_code)
                            if self.verbose:
                                print(f"閴?Claude fix applied (pre-validation)")
                        else:
                            if self.verbose:
                                print(f"閴?Claude fix rejected: {validation_error}")
                            return False, None, pre_error
                    else:
                        return False, None, pre_error
                except Exception as e:
                    if self.verbose:
                        print(f"閴?Pre-fix failed: {e}")
                    return False, None, pre_error
        
        for attempt in range(1, max_total_attempts + 1):
            if self.verbose:
                print(f"\n棣冩惙 Attempt {attempt}/{max_total_attempts}")
            
            success, metrics, error_msg = execute_fn(program_path)
            
            if success:
                if self.verbose:
                    print("閴?Execution successful!")
                return True, metrics, None
            
            if self.verbose:
                print(f"閴?Execution failed")
                if error_msg:
                    print(f"   Error: {error_msg[:200]}")
            
            if attempt >= max_total_attempts:
                if self.verbose:
                    print(f"閴?Max attempts reached")
                return False, None, error_msg
            
            # Try auto-install for missing packages
            if self.auto_install and error_msg and "No module named" in error_msg:
                match = re.search(r"No module named '(\w+)'", error_msg)
                if match:
                    missing_pkg = match.group(1)
                    if self._install_package(missing_pkg):
                        if self.verbose:
                            print(f"棣冩敡 Retrying after package installation...")
                        continue
            
            # Try to fix with Claude
            if attempt < max_total_attempts and error_msg:
                if self.verbose:
                    print(f"\n棣冩暋 Attempting to fix code...")
                
                try:
                    with open(program_path, 'r', encoding='utf-8') as f:
                        code = f.read()
                except Exception as e:
                    if self.verbose:
                        print(f"閴?Cannot read file: {e}")
                    return False, None, error_msg
                
                fixed_code = self._fix_code_with_claude(code, error_msg)
                
                if fixed_code:
                    is_valid, validation_error = self._validate_fix(code, fixed_code)
                    
                    if not is_valid:
                        if self.verbose:
                            print(f"閴?Fix validation failed: {validation_error}")
                            print(f"   Rejecting this fix to prevent downgrade.")
                        error_msg = f"{error_msg} (Auto-fixer tried to change model, rejected)"
                        continue
                    
                    # Backup original
                    backup_path = f"{program_path}.backup_{int(time.time())}"
                    try:
                        os.rename(program_path, backup_path)
                        if self.verbose:
                            print(f"棣冩惂 Backup: {backup_path}")
                    except Exception as e:
                        if self.verbose:
                            print(f"閳跨媴绗? Cannot backup: {e}")
                    
                    # Write fixed code
                    try:
                        with open(program_path, 'w', encoding='utf-8') as f:
                            f.write(fixed_code)
                        if self.verbose:
                            print("閴佸骏绗? Fixed code saved")
                            print("閴?Fix validation passed - no model changes detected")
                    except Exception as e:
                        if self.verbose:
                            print(f"閴?Cannot write fixed code: {e}")
                        return False, None, error_msg
                else:
                    if self.verbose:
                        print("閴?Cannot get fix from Claude")
                    return False, None, error_msg
        
        return False, None, error_msg
    
    # =========================================================================
    # ANALYSIS CODE EXECUTION (FOR KOSMOS)
    # =========================================================================
    
    def execute_analysis_code(
        self,
        analysis_code: str,
        timeout: int = 60,
        max_retries: int = 1,
        allowed_imports: Optional[list] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Execute LLM-generated analysis code safely.
        Used by Kosmos to run hypothesis ranking code.
        
        Args:
            analysis_code: Python code to execute
            timeout: Maximum execution time in seconds
            max_retries: Number of retries with auto-fix if code fails
            allowed_imports: Optional list of allowed import modules
            
        Returns:
            (success, json_result, error_msg)
        """
        if self.verbose:
            print(f"\n棣冩暕 Executing analysis code (timeout: {timeout}s)")
        
        # Validate code safety
        if allowed_imports:
            valid, error = self._validate_analysis_code(analysis_code, allowed_imports)
            if not valid:
                return False, None, f"Code validation failed: {error}"
        
        for attempt in range(max_retries + 1):
            if attempt > 0 and self.verbose:
                print(f"   Retry {attempt}/{max_retries}")
            
            # Write to temp file
            try:
                with tempfile.NamedTemporaryFile(
                    mode='w', 
                    suffix='.py', 
                    delete=False,
                    encoding='utf-8'
                ) as f:
                    f.write(analysis_code)
                    temp_path = f.name
            except Exception as e:
                return False, None, f"Failed to write temp file: {e}"
            
            try:
                # Execute with timeout
                result = subprocess.run(
                    [sys.executable, temp_path],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    env={**os.environ, 'PYTHONUNBUFFERED': '1'}
                )
                
                if result.returncode == 0:
                    # Parse JSON output
                    try:
                        # Try to find JSON in output
                        stdout = result.stdout.strip()
                        
                        # Handle case where JSON is embedded in other output
                        json_start = stdout.find('{')
                        json_end = stdout.rfind('}') + 1
                        
                        if json_start != -1 and json_end > json_start:
                            json_str = stdout[json_start:json_end]
                            output = json.loads(json_str)
                            if self.verbose:
                                print("閴?Analysis code executed successfully")
                            return True, output, None
                        else:
                            # Try parsing entire output as JSON
                            output = json.loads(stdout)
                            if self.verbose:
                                print("閴?Analysis code executed successfully")
                            return True, output, None
                            
                    except json.JSONDecodeError as e:
                        error_msg = f"Invalid JSON output: {result.stdout[:500]}"
                        if attempt < max_retries:
                            # Try to fix the code
                            fixed_code = self._fix_analysis_code(analysis_code, error_msg)
                            if fixed_code:
                                analysis_code = fixed_code
                                continue
                        return False, None, error_msg
                else:
                    error_msg = result.stderr or result.stdout
                    if attempt < max_retries:
                        # Try to fix the code
                        fixed_code = self._fix_analysis_code(analysis_code, error_msg)
                        if fixed_code:
                            analysis_code = fixed_code
                            continue
                    return False, None, error_msg
                    
            except subprocess.TimeoutExpired:
                return False, None, f"Analysis timed out after {timeout}s"
            except Exception as e:
                return False, None, f"Execution error: {str(e)}"
            finally:
                # Cleanup temp file
                try:
                    os.unlink(temp_path)
                except:
                    pass
        
        return False, None, "Max retries exceeded"
    
    def _validate_analysis_code(
        self, 
        code: str, 
        allowed_imports: list
    ) -> Tuple[bool, Optional[str]]:
        """Validate analysis code for safety"""
        
        # Check for dangerous patterns
        dangerous_patterns = [
            'os.system', 'subprocess.', 'eval(', 'exec(',
            '__import__', 'shutil.', 'open(', '.write(',
            'rm ', 'sudo', 'chmod', 'requests.', 'urllib',
            'socket.', 'paramiko', 'fabric'
        ]
        
        for pattern in dangerous_patterns:
            if pattern in code:
                return False, f"Dangerous pattern detected: {pattern}"
        
        # Check imports
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module = alias.name.split('.')[0]
                        if module not in allowed_imports and module not in ['json', 'warnings']:
                            return False, f"Import not allowed: {module}"
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module = node.module.split('.')[0]
                        if module not in allowed_imports and module not in ['json', 'warnings']:
                            return False, f"Import not allowed: {module}"
        except SyntaxError as e:
            return False, f"Syntax error: {e}"
        
        return True, None
    
    def _fix_analysis_code(self, code: str, error_msg: str) -> Optional[str]:
        """Fix analysis code using Claude"""
        try:
            prompt = f"""I have Python analysis code that failed. Please fix it.

Code:
```python
{code}
```

Error:
```
{error_msg}
```

REQUIREMENTS:
1. Fix the specific error
2. Ensure output is valid JSON printed to stdout
3. Keep the analysis logic intact
4. Return ONLY the fixed Python code

Fixed code:"""
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': self.model,
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 32000,  # No restrictive limit
                'temperature': 0.3
            }
            
            response = requests.post(
                f'{self.api_base}/chat/completions',
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'choices' in data and len(data['choices']) > 0:
                    fixed_code = data['choices'][0]['message']['content'].strip()
                    
                    # Extract code from markdown
                    fixed_code = self._strip_markdown_fences(fixed_code)
                    return fixed_code
            
            return None
            
        except Exception as e:
            if self.verbose:
                print(f"閴?Error fixing analysis code: {e}")
            return None


def wrap_execution_with_autofixer(
    program_path: str,
    original_execute_fn: Callable[[str], Tuple[bool, Optional[dict], Optional[str]]],
    enable_autofixer: bool = True,
    max_fix_attempts: int = 2,
    enable_pre_validation: bool = True,
    enable_static_fixes: bool = True,
    verbose: bool = True
) -> Tuple[bool, Optional[dict], Optional[str]]:
    """
    Wrapper function to add auto-fixing to any execution function
    
    Args:
        program_path: Path to program
        original_execute_fn: Original execution function
        enable_autofixer: Whether to enable auto-fixing
        max_fix_attempts: Max fix attempts
        enable_pre_validation: Run static analysis before execution (catches 60%+ of errors!)
        enable_static_fixes: Apply static fixes (unicode, imports, indentation)
        verbose: Print status messages
    
    Returns:
        (success, metrics, error_msg)
    """
    if not enable_autofixer:
        return original_execute_fn(program_path)
    
    fixer = EAAutoFixer(
        max_fix_attempts=max_fix_attempts,
        enable_pre_validation=enable_pre_validation,
        enable_static_fixes=enable_static_fixes,
        verbose=verbose
    )
    return fixer.try_fix_and_execute(
        program_path,
        original_execute_fn,
        max_total_attempts=max_fix_attempts + 1
    )


def validate_code_before_execution(program_path: str, auto_fix: bool = True, verbose: bool = True) -> Tuple[bool, Optional[str]]:
    """
    Convenience function to validate code before execution.
    Can be called independently of the auto-fixer.
    
    Args:
        program_path: Path to program file
        auto_fix: Whether to apply auto-fixes (unicode, indentation, imports)
        verbose: Print status messages
        
    Returns:
        (is_valid, error_message)
    """
    if validate_and_fix is None:
        # Code validator not available, skip validation
        return True, None
    
    is_valid, error, fixed_code = validate_and_fix(program_path, verbose=verbose)
    
    if is_valid and fixed_code and auto_fix:
        try:
            with open(program_path, 'w', encoding='utf-8') as f:
                f.write(fixed_code)
        except Exception as e:
            if verbose:
                print(f"閳跨媴绗? Could not save fixes: {e}")
    
    return is_valid, error


if __name__ == "__main__":
    print("EAAutoFixer - Test Mode")
    print("=" * 70)
    
    if len(sys.argv) < 2:
        print("Usage: python auto_fixer.py <python_file>")
        print("       python auto_fixer.py --test-analysis")
        sys.exit(1)
    
    if sys.argv[1] == "--test-analysis":
        # Test analysis code execution
        test_code = '''
import json
import numpy as np

# Simple analysis
results = {
    "hypothesis_1": {"score": 0.85, "evidence": "High correlation"},
    "hypothesis_2": {"score": 0.60, "evidence": "Moderate support"},
    "best_threshold": 0.6
}

print(json.dumps(results, indent=2))
'''
        fixer = EAAutoFixer()
        success, result, error = fixer.execute_analysis_code(
            test_code,
            timeout=30,
            allowed_imports=['json', 'numpy', 'pandas', 'sklearn']
        )
        
        if success:
            print("\n棣冨竴 Analysis test passed!")
            print(f"Result: {result}")
        else:
            print(f"\n棣冩Д Analysis test failed: {error}")
    else:
        file_path = sys.argv[1]
        
        def test_execute(path):
            try:
                result = subprocess.run(
                    [sys.executable, path],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode == 0:
                    return True, {'score': 1.0}, None
                else:
                    return False, None, result.stderr
            except Exception as e:
                return False, None, str(e)
        
        fixer = EAAutoFixer()
        success, metrics, error = fixer.try_fix_and_execute(file_path, test_execute)
        
        if success:
            print("\n棣冨竴 Success!")
            print(f"Metrics: {metrics}")
        else:
            print("\n棣冩Д Failed")
            if error:
                print(f"Error: {error}")

