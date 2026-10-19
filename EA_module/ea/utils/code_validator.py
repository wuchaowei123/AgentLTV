"""
AgentLTV - Universal Code Validator
Pre-execution static analysis for catching common LLM code generation errors

FAILURE ANALYSIS FROM SC_IOS_2503 TASK:
- 42% IndentationError (8/19 failures)
- 16% Invalid decimal literal (3/19)
- 11% Invalid Unicode characters (2/19)
- 31% Missing imports / undefined names

This validator catches errors BEFORE execution, saving time and compute.
"""

import ast
import re
import subprocess
import sys
import unicodedata
from typing import Tuple, Optional, Set, List, Dict, Any
from pathlib import Path


# ============================================================================
# COMMON ML IMPORTS - Auto-detection database
# ============================================================================

COMMON_ML_CLASSES = {
    # sklearn.preprocessing
    'QuantileTransformer': 'from sklearn.preprocessing import QuantileTransformer',
    'StandardScaler': 'from sklearn.preprocessing import StandardScaler',
    'MinMaxScaler': 'from sklearn.preprocessing import MinMaxScaler',
    'RobustScaler': 'from sklearn.preprocessing import RobustScaler',
    'LabelEncoder': 'from sklearn.preprocessing import LabelEncoder',
    'OrdinalEncoder': 'from sklearn.preprocessing import OrdinalEncoder',
    'OneHotEncoder': 'from sklearn.preprocessing import OneHotEncoder',
    'PowerTransformer': 'from sklearn.preprocessing import PowerTransformer',
    'PolynomialFeatures': 'from sklearn.preprocessing import PolynomialFeatures',
    
    # sklearn.ensemble
    'RandomForestRegressor': 'from sklearn.ensemble import RandomForestRegressor',
    'RandomForestClassifier': 'from sklearn.ensemble import RandomForestClassifier',
    'GradientBoostingRegressor': 'from sklearn.ensemble import GradientBoostingRegressor',
    'GradientBoostingClassifier': 'from sklearn.ensemble import GradientBoostingClassifier',
    'HistGradientBoostingRegressor': 'from sklearn.ensemble import HistGradientBoostingRegressor',
    'HistGradientBoostingClassifier': 'from sklearn.ensemble import HistGradientBoostingClassifier',
    'AdaBoostRegressor': 'from sklearn.ensemble import AdaBoostRegressor',
    'AdaBoostClassifier': 'from sklearn.ensemble import AdaBoostClassifier',
    'ExtraTreesRegressor': 'from sklearn.ensemble import ExtraTreesRegressor',
    'ExtraTreesClassifier': 'from sklearn.ensemble import ExtraTreesClassifier',
    'BaggingRegressor': 'from sklearn.ensemble import BaggingRegressor',
    'BaggingClassifier': 'from sklearn.ensemble import BaggingClassifier',
    'StackingRegressor': 'from sklearn.ensemble import StackingRegressor',
    'StackingClassifier': 'from sklearn.ensemble import StackingClassifier',
    'VotingRegressor': 'from sklearn.ensemble import VotingRegressor',
    'VotingClassifier': 'from sklearn.ensemble import VotingClassifier',
    'IsolationForest': 'from sklearn.ensemble import IsolationForest',
    
    # sklearn.linear_model
    'LinearRegression': 'from sklearn.linear_model import LinearRegression',
    'Ridge': 'from sklearn.linear_model import Ridge',
    'RidgeCV': 'from sklearn.linear_model import RidgeCV',
    'Lasso': 'from sklearn.linear_model import Lasso',
    'LassoCV': 'from sklearn.linear_model import LassoCV',
    'ElasticNet': 'from sklearn.linear_model import ElasticNet',
    'ElasticNetCV': 'from sklearn.linear_model import ElasticNetCV',
    'LogisticRegression': 'from sklearn.linear_model import LogisticRegression',
    'SGDRegressor': 'from sklearn.linear_model import SGDRegressor',
    'SGDClassifier': 'from sklearn.linear_model import SGDClassifier',
    'HuberRegressor': 'from sklearn.linear_model import HuberRegressor',
    'RANSACRegressor': 'from sklearn.linear_model import RANSACRegressor',
    'BayesianRidge': 'from sklearn.linear_model import BayesianRidge',
    
    # sklearn.tree
    'DecisionTreeRegressor': 'from sklearn.tree import DecisionTreeRegressor',
    'DecisionTreeClassifier': 'from sklearn.tree import DecisionTreeClassifier',
    
    # sklearn.model_selection
    'KFold': 'from sklearn.model_selection import KFold',
    'StratifiedKFold': 'from sklearn.model_selection import StratifiedKFold',
    'GroupKFold': 'from sklearn.model_selection import GroupKFold',
    'TimeSeriesSplit': 'from sklearn.model_selection import TimeSeriesSplit',
    'train_test_split': 'from sklearn.model_selection import train_test_split',
    'cross_val_score': 'from sklearn.model_selection import cross_val_score',
    'cross_validate': 'from sklearn.model_selection import cross_validate',
    'GridSearchCV': 'from sklearn.model_selection import GridSearchCV',
    'RandomizedSearchCV': 'from sklearn.model_selection import RandomizedSearchCV',
    
    # sklearn.isotonic
    'IsotonicRegression': 'from sklearn.isotonic import IsotonicRegression',
    
    # sklearn.neural_network
    'MLPRegressor': 'from sklearn.neural_network import MLPRegressor',
    'MLPClassifier': 'from sklearn.neural_network import MLPClassifier',
    
    # sklearn.svm
    'SVR': 'from sklearn.svm import SVR',
    'SVC': 'from sklearn.svm import SVC',
    'LinearSVR': 'from sklearn.svm import LinearSVR',
    
    # sklearn.neighbors
    'KNeighborsRegressor': 'from sklearn.neighbors import KNeighborsRegressor',
    'KNeighborsClassifier': 'from sklearn.neighbors import KNeighborsClassifier',
    
    # sklearn.cluster
    'KMeans': 'from sklearn.cluster import KMeans',
    'DBSCAN': 'from sklearn.cluster import DBSCAN',
    
    # sklearn.decomposition
    'PCA': 'from sklearn.decomposition import PCA',
    'TruncatedSVD': 'from sklearn.decomposition import TruncatedSVD',
    
    # sklearn.feature_selection
    'SelectKBest': 'from sklearn.feature_selection import SelectKBest',
    'RFE': 'from sklearn.feature_selection import RFE',
    'VarianceThreshold': 'from sklearn.feature_selection import VarianceThreshold',
    
    # sklearn.metrics
    'mean_squared_error': 'from sklearn.metrics import mean_squared_error',
    'mean_absolute_error': 'from sklearn.metrics import mean_absolute_error',
    'r2_score': 'from sklearn.metrics import r2_score',
    'roc_auc_score': 'from sklearn.metrics import roc_auc_score',
    'accuracy_score': 'from sklearn.metrics import accuracy_score',
    
    # lightgbm
    'LGBMRegressor': 'from lightgbm import LGBMRegressor',
    'LGBMClassifier': 'from lightgbm import LGBMClassifier',
    
    # xgboost
    'XGBRegressor': 'from xgboost import XGBRegressor',
    'XGBClassifier': 'from xgboost import XGBClassifier',
    'XGBRFRegressor': 'from xgboost import XGBRFRegressor',
    'XGBRFClassifier': 'from xgboost import XGBRFClassifier',
    
    # catboost
    'CatBoostRegressor': 'from catboost import CatBoostRegressor',
    'CatBoostClassifier': 'from catboost import CatBoostClassifier',
    
    # scipy
    'spearmanr': 'from scipy.stats import spearmanr',
    'pearsonr': 'from scipy.stats import pearsonr',
    'kendalltau': 'from scipy.stats import kendalltau',
    'mannwhitneyu': 'from scipy.stats import mannwhitneyu',
    'ttest_ind': 'from scipy.stats import ttest_ind',
    'zscore': 'from scipy.stats import zscore',
    'norm': 'from scipy.stats import norm',
    
    # collections
    'Counter': 'from collections import Counter',
    'defaultdict': 'from collections import defaultdict',
    'deque': 'from collections import deque',
    'OrderedDict': 'from collections import OrderedDict',
    
    # Standard library
    'Path': 'from pathlib import Path',
    'datetime': 'from datetime import datetime',
    'timedelta': 'from datetime import timedelta',
    'date': 'from datetime import date',
    'Callable': 'from typing import Callable',
    'Optional': 'from typing import Optional',
    'List': 'from typing import List',
    'Dict': 'from typing import Dict',
    'Tuple': 'from typing import Tuple',
    'Union': 'from typing import Union',
    'Any': 'from typing import Any',
    'Set': 'from typing import Set',
    
    # PyTorch
    'DataLoader': 'from torch.utils.data import DataLoader',
    'Dataset': 'from torch.utils.data import Dataset',
    'TensorDataset': 'from torch.utils.data import TensorDataset',
    
    # imblearn
    'SMOTE': 'from imblearn.over_sampling import SMOTE',
    'RandomOverSampler': 'from imblearn.over_sampling import RandomOverSampler',
    'RandomUnderSampler': 'from imblearn.under_sampling import RandomUnderSampler',
}

# Module alias mappings
ALIAS_IMPORTS = {
    'lgb': 'import lightgbm as lgb',
    'xgb': 'import xgboost as xgb',
    'cb': 'import catboost as cb',
    'pd': 'import pandas as pd',
    'np': 'import numpy as np',
    'torch': 'import torch',
    'F': 'import torch.nn.functional as F',
    'nn': 'from torch import nn',
    'tf': 'import tensorflow as tf',
    'sns': 'import seaborn as sns',
    'plt': 'import matplotlib.pyplot as plt',
    'scipy': 'import scipy',
    'gc': 'import gc',
    'json': 'import json',
    're': 'import re',
    'os': 'import os',
    'sys': 'import sys',
    'warnings': 'import warnings',
    'joblib': 'import joblib',
    'pickle': 'import pickle',
    'math': 'import math',
    'random': 'import random',
    'time': 'import time',
}

# Unicode replacements for common LLM errors
UNICODE_REPLACEMENTS = {
    '閳?: '==',          # APPROXIMATELY EQUAL TO
    '閳?: '!=',          # NOT EQUAL TO
    '閳?: '<=',          # LESS-THAN OR EQUAL TO
    '閳?: '>=',          # GREATER-THAN OR EQUAL TO
    '鑴?: '*',           # MULTIPLICATION SIGN
    '姊?: '/',           # DIVISION SIGN
    '閳?: '-',           # MINUS SIGN (different from hyphen!)
    '閳?: '-',           # EN DASH
    '閳?: '-',           # EM DASH
    '"': '"',           # LEFT DOUBLE QUOTATION MARK
    '"': '"',           # RIGHT DOUBLE QUOTATION MARK
    ''': "'",           # LEFT SINGLE QUOTATION MARK
    ''': "'",           # RIGHT SINGLE QUOTATION MARK
    '閳?: '...',         # HORIZONTAL ELLIPSIS
    '閳?: '->',          # RIGHTWARDS ARROW
    '閳?: '<-',          # LEFTWARDS ARROW
    '璺?: '*',           # MIDDLE DOT
    '閳?: 'float("inf")',# INFINITY
    '浼?: 'alpha',       # GREEK SMALL LETTER ALPHA
    '灏?: 'beta',        # GREEK SMALL LETTER BETA
    '绾?: 'gamma',       # GREEK SMALL LETTER GAMMA
    '浣?: 'lambda_',     # GREEK SMALL LETTER LAMBDA (reserved word!)
    '娓?: 'mu',          # GREEK SMALL LETTER MU
    '锜?: 'sigma',       # GREEK SMALL LETTER SIGMA
    '钄?: 'epsilon',     # GREEK SMALL LETTER EPSILON
    '\u00a0': ' ',      # NON-BREAKING SPACE
    '\u2003': ' ',      # EM SPACE
    '\u2002': ' ',      # EN SPACE
    '\u200b': '',       # ZERO WIDTH SPACE
    '\ufeff': '',       # BYTE ORDER MARK
}


class CodeValidator:
    """
    Universal code validator for AgentLTV.
    Performs static analysis to catch common LLM code generation errors.
    """
    
    def __init__(
        self, 
        auto_suggest_imports: bool = True,
        auto_fix_unicode: bool = True,
        auto_fix_indentation: bool = True,
        verbose: bool = True
    ):
        """
        Args:
            auto_suggest_imports: Suggest missing imports when detected
            auto_fix_unicode: Automatically fix Unicode errors
            auto_fix_indentation: Attempt to fix indentation errors
            verbose: Print status messages
        """
        self.auto_suggest_imports = auto_suggest_imports
        self.auto_fix_unicode = auto_fix_unicode
        self.auto_fix_indentation = auto_fix_indentation
        self.verbose = verbose
    
    def validate(self, code_path: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate code for syntax, imports, and semantic errors.
        
        Returns:
            (is_valid, error_message, fixed_code_if_applicable)
        """
        try:
            with open(code_path, 'r', encoding='utf-8') as f:
                code = f.read()
        except Exception as e:
            return False, f"Failed to read file: {e}", None
        
        original_code = code
        fixes_applied = []
        
        # 1. Fix Unicode characters (pre-processing)
        if self.auto_fix_unicode:
            code, unicode_fixes = self._fix_unicode(code)
            if unicode_fixes:
                fixes_applied.extend(unicode_fixes)
        
        # 2. Fix incomplete decimal literals
        code, decimal_fixes = self._fix_incomplete_decimals(code)
        if decimal_fixes:
            fixes_applied.extend(decimal_fixes)
        
        # 3. Syntax check
        is_valid, error = self._check_syntax(code, code_path)
        if not is_valid:
            # Try indentation fix
            if 'IndentationError' in str(error) and self.auto_fix_indentation:
                fixed_code = self._try_fix_indentation(code)
                if fixed_code:
                    is_valid, error = self._check_syntax_string(fixed_code)
                    if is_valid:
                        code = fixed_code
                        fixes_applied.append("Fixed indentation")
                    else:
                        return False, f"Syntax Error: {error}", None
                else:
                    return False, f"Syntax Error: {error}", None
            else:
                return False, f"Syntax Error: {error}", None
        
        # 4. Import/usage consistency check
        is_valid, error, import_fixes = self._check_import_usage_consistency(code)
        if not is_valid:
            if import_fixes:
                code = self._apply_import_fixes(code, import_fixes)
                fixes_applied.append(f"Added imports: {import_fixes}")
            else:
                return False, f"Import Error: {error}", None
        
        # 5. Check for undefined names (CRITICAL - catches missing imports!)
        is_valid, error, undefined_fixes = self._check_undefined_names(code)
        if not is_valid:
            if undefined_fixes:
                code = self._apply_import_fixes(code, undefined_fixes)
                fixes_applied.append(f"Added missing imports: {undefined_fixes}")
            else:
                return False, f"Undefined Name: {error}", None
        
        # 6. Final syntax check after fixes
        if fixes_applied:
            is_valid, error = self._check_syntax_string(code)
            if not is_valid:
                return False, f"Syntax Error after fixes: {error}", None
        
        # Return fixed code if we made changes
        if fixes_applied and code != original_code:
            if self.verbose:
                print(f"閴?Applied {len(fixes_applied)} auto-fixes:")
                for fix in fixes_applied:
                    print(f"   - {fix}")
            return True, None, code
        
        return True, None, None
    
    def _fix_unicode(self, code: str) -> Tuple[str, List[str]]:
        """Fix Unicode characters that cause Python syntax errors."""
        fixes = []
        original_code = code
        
        for unicode_char, replacement in UNICODE_REPLACEMENTS.items():
            if unicode_char in code:
                count = code.count(unicode_char)
                code = code.replace(unicode_char, replacement)
                fixes.append(f"Replaced {repr(unicode_char)} 鑴?{count}")
        
        # Also check for any remaining non-ASCII characters that might cause issues
        suspicious_chars = set()
        for i, char in enumerate(code):
            if ord(char) > 127 and char not in '\n\r\t':
                # Check if it's in a string or comment
                line_start = code.rfind('\n', 0, i) + 1
                line_end = code.find('\n', i)
                if line_end == -1:
                    line_end = len(code)
                line = code[line_start:line_end]
                
                # Simple heuristic: if not in string/comment, it's suspicious
                in_string = (line.count('"') % 2 == 1) or (line.count("'") % 2 == 1)
                in_comment = '#' in line[:i - line_start]
                
                if not in_string and not in_comment:
                    suspicious_chars.add(char)
        
        if suspicious_chars and self.verbose:
            print(f"閳跨媴绗? Suspicious non-ASCII chars found: {suspicious_chars}")
        
        return code, fixes
    
    def _fix_incomplete_decimals(self, code: str) -> Tuple[str, List[str]]:
        """Fix incomplete decimal literals like '1e' or '0.'"""
        fixes = []
        
        # Pattern: number followed by 'e' or 'E' not followed by a digit or sign
        pattern1 = r'(\d+)[eE](?![+-]?\d)'
        matches = list(re.finditer(pattern1, code))
        for match in reversed(matches):  # Reverse to maintain indices
            fix = match.group(1) + 'e0'
            code = code[:match.start()] + fix + code[match.end():]
            fixes.append(f"Fixed incomplete exponent at pos {match.start()}")
        
        # Pattern: decimal point at end of number (not followed by digit)
        pattern2 = r'(\d+)\.(?!\d)'
        matches = list(re.finditer(pattern2, code))
        for match in reversed(matches):
            # Only fix if it's not a method call (e.g., "1.method()")
            if match.end() < len(code) and code[match.end()].isalpha():
                continue
            fix = match.group(1) + '.0'
            code = code[:match.start()] + fix + code[match.end():]
            fixes.append(f"Fixed incomplete decimal at pos {match.start()}")
        
        return code, fixes
    
    def _try_fix_indentation(self, code: str) -> Optional[str]:
        """Attempt to fix indentation errors."""
        lines = code.split('\n')
        fixed_lines = []
        
        # First pass: normalize all indentation to spaces
        for line in lines:
            # Replace tabs with 4 spaces
            if line.startswith('\t'):
                spaces = 0
                i = 0
                while i < len(line) and line[i] == '\t':
                    spaces += 4
                    i += 1
                line = ' ' * spaces + line[i:]
            fixed_lines.append(line)
        
        # Second pass: try to fix inconsistent indentation
        # This is a simple heuristic approach
        result_lines = []
        indent_stack = [0]  # Stack of indent levels
        
        for i, line in enumerate(fixed_lines):
            stripped = line.lstrip()
            if not stripped or stripped.startswith('#'):
                result_lines.append(line)
                continue
            
            current_indent = len(line) - len(stripped)
            
            # If line ends with ':', next line should be indented more
            # If current indent is weird, try to fix it
            
            if indent_stack and current_indent > 0:
                expected = indent_stack[-1]
                
                # Allow multiples of 4
                if current_indent % 4 != 0:
                    # Round to nearest multiple of 4
                    fixed_indent = round(current_indent / 4) * 4
                    line = ' ' * fixed_indent + stripped
                    current_indent = fixed_indent
            
            result_lines.append(line)
            
            # Update indent stack
            if stripped.endswith(':'):
                indent_stack.append(current_indent + 4)
            elif current_indent < indent_stack[-1]:
                while indent_stack and current_indent < indent_stack[-1]:
                    indent_stack.pop()
        
        fixed_code = '\n'.join(result_lines)
        
        # Verify the fix worked
        try:
            ast.parse(fixed_code)
            return fixed_code
        except SyntaxError:
            # Fix didn't work, try more aggressive approach
            return self._aggressive_indentation_fix(code)
    
    def _aggressive_indentation_fix(self, code: str) -> Optional[str]:
        """More aggressive indentation fix using autopep8 if available."""
        try:
            import autopep8
            fixed = autopep8.fix_code(code, options={'aggressive': 2})
            ast.parse(fixed)
            return fixed
        except ImportError:
            pass
        except:
            pass
        
        # Try using Python's tabnanny
        try:
            import tabnanny
            import io
            # Just return None if we can't fix it
            return None
        except:
            return None
    
    def _check_syntax(self, code: str, filename: str) -> Tuple[bool, Optional[str]]:
        """Check for Python syntax errors."""
        # First try AST parsing (faster)
        try:
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            return False, f"Line {e.lineno}: {e.msg}"
    
    def _check_syntax_string(self, code: str) -> Tuple[bool, Optional[str]]:
        """Check syntax of code string."""
        try:
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            return False, f"Line {e.lineno}: {e.msg}"
    
    def _check_import_usage_consistency(self, code: str) -> Tuple[bool, Optional[str], List[str]]:
        """Check if imports match their usage in code."""
        try:
            tree = ast.parse(code)
        except:
            return True, None, []
        
        # Extract defined names from imports
        defined_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name.split('.')[0]
                    defined_names.add(name)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name != '*':
                        name = alias.asname if alias.asname else alias.name
                        defined_names.add(name)
        
        # Check for missing module aliases
        missing_imports = []
        
        for alias, import_stmt in ALIAS_IMPORTS.items():
            if alias in defined_names:
                continue
            
            # Check if alias is used
            pattern = rf'\b{alias}\.'
            if re.search(pattern, code):
                missing_imports.append(import_stmt)
        
        if missing_imports:
            return False, f"Missing imports for used aliases", missing_imports
        
        return True, None, []
    
    def _check_undefined_names(self, code: str) -> Tuple[bool, Optional[str], List[str]]:
        """Check for undefined names in the code using AST analysis."""
        try:
            tree = ast.parse(code)
        except:
            return True, None, []
        
        # Collect all defined names
        defined_names = set()
        
        # 1. Imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    defined_names.add(name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name == '*':
                        continue
                    name = alias.asname if alias.asname else alias.name
                    defined_names.add(name)
        
        # 2. Function and class definitions
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defined_names.add(node.name)
        
        # 3. Variable assignments
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        defined_names.add(target.id)
            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name):
                    defined_names.add(node.target.id)
        
        # Add Python builtins
        builtins = {
            'True', 'False', 'None', 'self', 'cls',
            'print', 'len', 'range', 'str', 'int', 'float', 'list', 'dict', 'set', 'tuple',
            'bool', 'bytes', 'bytearray', 'complex', 'frozenset', 'object', 'slice',
            'sum', 'max', 'min', 'abs', 'round', 'sorted', 'enumerate', 'zip', 'filter', 'map',
            'open', 'type', 'isinstance', 'issubclass', 'hasattr', 'getattr', 'setattr', 'delattr',
            'callable', 'iter', 'next', 'reversed', 'all', 'any', 'bin', 'hex', 'oct',
            'repr', 'ascii', 'chr', 'ord', 'format', 'id', 'hash', 'dir', 'vars', 'locals', 'globals',
            'staticmethod', 'classmethod', 'property', 'super', 'input',
            'Exception', 'BaseException', 'ValueError', 'TypeError', 'KeyError', 'AttributeError',
            'RuntimeError', 'IndexError', 'OSError', 'IOError', 'FileNotFoundError',
            'ImportError', 'ModuleNotFoundError', 'StopIteration', 'AssertionError',
            'ZeroDivisionError', 'OverflowError', 'MemoryError', 'RecursionError',
            'NotImplementedError', 'NameError', 'UnboundLocalError',
        }
        defined_names |= builtins
        
        # Collect used class names
        missing_imports = []
        undefined_classes = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                name = node.id
                
                # Check if it's a class name (TitleCase) and not defined
                if name[0].isupper() and not name.isupper() and name not in defined_names:
                    if name in COMMON_ML_CLASSES:
                        undefined_classes.add(name)
                        missing_imports.append(COMMON_ML_CLASSES[name])
        
        if undefined_classes:
            error_msg = f"Undefined names: {undefined_classes}"
            if self.auto_suggest_imports:
                error_msg += f"\nSuggested imports: {missing_imports[:5]}"
            return False, error_msg, list(set(missing_imports))
        
        return True, None, []
    
    def _apply_import_fixes(self, code: str, imports: List[str]) -> str:
        """Add missing imports to the beginning of the code."""
        if not imports:
            return code
        
        # Find the best place to insert imports
        lines = code.split('\n')
        insert_index = 0
        
        # Skip shebang, encoding declarations, docstrings
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('#!') or stripped.startswith('# -*-'):
                insert_index = i + 1
            elif stripped.startswith('"""') or stripped.startswith("'''"):
                # Skip docstring
                if stripped.count('"""') == 2 or stripped.count("'''") == 2:
                    insert_index = i + 1
                else:
                    # Multi-line docstring
                    for j in range(i + 1, len(lines)):
                        if '"""' in lines[j] or "'''" in lines[j]:
                            insert_index = j + 1
                            break
            elif stripped.startswith('import ') or stripped.startswith('from '):
                insert_index = i
                break
            elif stripped and not stripped.startswith('#'):
                # First non-comment, non-empty line
                insert_index = i
                break
        
        # Remove duplicates while preserving order
        unique_imports = []
        seen = set()
        for imp in imports:
            if imp not in seen:
                seen.add(imp)
                unique_imports.append(imp)
        
        # Insert imports
        import_block = '\n'.join(unique_imports)
        lines.insert(insert_index, import_block + '\n')
        
        return '\n'.join(lines)
    
    def _extract_imports(self, code: str) -> List[str]:
        """Extract all import statements as strings."""
        imports = []
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.asname:
                            imports.append(f"import {alias.name} as {alias.asname}")
                        else:
                            imports.append(f"import {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    for alias in node.names:
                        if alias.asname:
                            imports.append(f"from {module} import {alias.name} as {alias.asname}")
                        else:
                            imports.append(f"from {module} import {alias.name}")
        except:
            pass
        return imports


def validate_and_fix(code_path: str, verbose: bool = True) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Convenience function to validate and optionally fix code.
    
    Returns:
        (is_valid, error_message, fixed_code)
    """
    validator = CodeValidator(
        auto_suggest_imports=True,
        auto_fix_unicode=True,
        auto_fix_indentation=True,
        verbose=verbose
    )
    return validator.validate(code_path)


def quick_validate(code_path: str) -> Tuple[bool, Optional[str]]:
    """Quick validation without auto-fix."""
    validator = CodeValidator(
        auto_suggest_imports=True,
        auto_fix_unicode=False,
        auto_fix_indentation=False,
        verbose=False
    )
    is_valid, error, _ = validator.validate(code_path)
    return is_valid, error


# ============================================================================
# CLI Interface
# ============================================================================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='AgentLTV Code Validator')
    parser.add_argument('file', help='Python file to validate')
    parser.add_argument('--fix', action='store_true', help='Apply auto-fixes')
    parser.add_argument('--quiet', action='store_true', help='Quiet mode')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("AgentLTV - Universal Code Validator")
    print("=" * 60)
    
    validator = CodeValidator(
        auto_suggest_imports=True,
        auto_fix_unicode=args.fix,
        auto_fix_indentation=args.fix,
        verbose=not args.quiet
    )
    
    is_valid, error, fixed_code = validator.validate(args.file)
    
    if is_valid:
        print(f"\n閴?{args.file} is valid")
        if fixed_code and args.fix:
            # Write fixed code
            with open(args.file, 'w') as f:
                f.write(fixed_code)
            print(f"閴?Auto-fixes applied and saved")
        sys.exit(0)
    else:
        print(f"\n閴?{args.file} has errors:")
        print(f"   {error}")
        sys.exit(1)



















