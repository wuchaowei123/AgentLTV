"""
Universal MTCS_module - Core Components
==============================================

Core components for automated scientific software discovery using
LLM + Tree Search across any scorable task.
"""

from .task_manager import TaskConfiguration, load_task_configuration
from .llm_worker import UniversalLLMWorker, generate_code_mutation, generate_initial_code

__all__ = [
    'TaskConfiguration',
    'load_task_configuration', 
    'UniversalLLMWorker',
    'generate_code_mutation',
    'generate_initial_code'
]