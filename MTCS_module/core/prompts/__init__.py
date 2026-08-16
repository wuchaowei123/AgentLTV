"""
Enhanced Prompt System for Universal Scientific AI
=================================================

Complete prompt library and formatting system for advanced scientific software discovery.
"""

from .prompt_library import *
from .prompt_formatter import EnhancedPromptFormatter
from .prompt_strategies import PromptStrategyManager

__all__ = [
    'EnhancedPromptFormatter',
    'PromptStrategyManager',
    'ALL_PROMPTS',
    'CORE_PROMPTS',
    'ADVISORY_PROMPTS', 
    'RESEARCH_PROMPTS',
    'UNIVERSAL_PROMPTS'
]