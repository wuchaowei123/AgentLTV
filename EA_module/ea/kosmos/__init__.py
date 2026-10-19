"""
Kosmos Integration Module for AgentLTV

This module provides intelligent analysis and knowledge management
to enhance the evolutionary code optimization process.

Components:
- KosmosAnalyzer: Generates and ranks hypotheses about code performance
- HybridKnowledgeManager: Manages knowledge from multiple sources
- KosmosConfig: Configuration for Kosmos integration

Usage:
    from ea.kosmos import KosmosAnalyzer, HybridKnowledgeManager, KosmosConfig
    
    config = KosmosConfig(enabled=True)
    analyzer = KosmosAnalyzer(task_config, config)
    knowledge_mgr = HybridKnowledgeManager(config)
"""

from .config import KosmosConfig
from .analyzer import KosmosAnalyzer, AnalysisResult, RankedHypothesis
from .knowledge import HybridKnowledgeManager, KnowledgeBundle, NoveltySearchTrigger

__all__ = [
    'KosmosConfig',
    'KosmosAnalyzer',
    'AnalysisResult',
    'RankedHypothesis',
    'HybridKnowledgeManager',
    'KnowledgeBundle',
    'NoveltySearchTrigger',
]


