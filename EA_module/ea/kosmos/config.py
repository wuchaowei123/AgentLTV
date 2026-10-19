"""
Kosmos Configuration

Defines configuration options for the Kosmos integration.
"""

from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class KosmosConfig:
    """
    Configuration for Kosmos integration.
    
    Attributes:
        enabled: Whether Kosmos analysis is enabled
        
        # Analysis settings
        analyze_threshold: Only analyze nodes with score below this threshold
        analyze_top_k: Always analyze top-k nodes regardless of threshold
        analysis_timeout: Timeout for analysis code execution (seconds)
        max_analysis_retries: Max retries if analysis code fails
        
        # Hypothesis settings
        max_hypotheses: Maximum number of hypotheses to generate
        
        # Knowledge system settings
        enable_external_search: Enable literature/web search
        plateau_threshold: Generations without improvement to trigger search
        stagnation_threshold: Unique techniques in last N gens to detect stagnation
        search_cooldown: Minimum generations between searches
        min_generations_before_search: Don't search before this generation
        periodic_search_interval: Force search every N generations
        
        # LLM settings
        llm_model: Model for hypothesis generation and analysis
        llm_temperature: Temperature for LLM calls
        
        # Safety settings
        allowed_imports: List of allowed imports for analysis code
    """
    
    # Enable/disable
    enabled: bool = True
    
    # Analysis settings
    analyze_threshold: float = 0.70  # Analyze nodes with score < 0.70
    analyze_top_k: int = 3  # Always analyze top-3 nodes
    analysis_timeout: int = 60  # 60 seconds
    max_analysis_retries: int = 1
    
    # Hypothesis settings
    max_hypotheses: int = 5
    
    # Knowledge system settings
    enable_external_search: bool = True
    plateau_threshold: int = 10  # 10 generations without improvement
    stagnation_threshold: int = 3  # < 3 unique techniques = stagnation
    search_cooldown: int = 15  # Min 15 gens between searches
    min_generations_before_search: int = 20  # Don't search before gen 20
    periodic_search_interval: int = 30  # Force search every 30 gens
    
    # LLM settings
    llm_model: str = "gemini-3-pro-preview"  # Default model for analysis
    llm_temperature: float = 0.7
    
    # Safety settings
    allowed_imports: List[str] = field(default_factory=lambda: [
        'pandas', 'numpy', 'sklearn', 'lightgbm', 'xgboost', 
        'catboost', 'json', 'warnings', 'scipy', 'shap'
    ])
    
    # Human knowledge base path
    human_kb_path: Optional[str] = None
    
    # Human guidance file path (for real-time steering)
    human_guidance_path: Optional[str] = None
    
    # Kaggle integration settings
    kaggle_competition: Optional[str] = None  # Kaggle competition slug (e.g., 'cafa-5-protein-function-prediction')
    kaggle_enabled: bool = True  # Enable/disable Kaggle notebooks & discussions search
    
    def __post_init__(self):
        """Validate configuration"""
        if self.analyze_threshold < 0 or self.analyze_threshold > 1:
            raise ValueError("analyze_threshold must be between 0 and 1")
        if self.analyze_top_k < 0:
            raise ValueError("analyze_top_k must be non-negative")
        if self.analysis_timeout < 10:
            raise ValueError("analysis_timeout must be at least 10 seconds")
        if self.max_hypotheses < 1:
            raise ValueError("max_hypotheses must be at least 1")
    
    @classmethod
    def from_dict(cls, d: dict) -> 'KosmosConfig':
        """Create config from dictionary"""
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
    
    def to_dict(self) -> dict:
        """Convert config to dictionary"""
        return {
            'enabled': self.enabled,
            'analyze_threshold': self.analyze_threshold,
            'analyze_top_k': self.analyze_top_k,
            'analysis_timeout': self.analysis_timeout,
            'max_analysis_retries': self.max_analysis_retries,
            'max_hypotheses': self.max_hypotheses,
            'enable_external_search': self.enable_external_search,
            'plateau_threshold': self.plateau_threshold,
            'stagnation_threshold': self.stagnation_threshold,
            'search_cooldown': self.search_cooldown,
            'min_generations_before_search': self.min_generations_before_search,
            'periodic_search_interval': self.periodic_search_interval,
            'llm_model': self.llm_model,
            'llm_temperature': self.llm_temperature,
            'allowed_imports': self.allowed_imports,
            'human_kb_path': self.human_kb_path,
            'human_guidance_path': self.human_guidance_path,
            'kaggle_competition': self.kaggle_competition,
            'kaggle_enabled': self.kaggle_enabled,
        }


