"""
Adaptive Patch Selection for AgentLTV

Dynamically adjusts patch type probabilities based on evolution progress:
- Exploits (more DIFF) when making progress
- Explores (more FULL) when stuck
- Uses meta-insights to guide exploration direction
"""

import logging
from typing import List, Optional, Dict, Any
from collections import defaultdict

logger = logging.getLogger(__name__)


class AdaptivePatchSelector:
    """
    Uses evolution progress to dynamically adjust patch type probabilities.
    
    Patch types:
    - DIFF: Targeted SEARCH/REPLACE changes (exploitation)
    - FULL: Complete rewrite with 5 variants (exploration)
    - CROSS: Combine two programs (hybrid)
    """
    
    def __init__(
        self,
        base_probs: List[float] = None,
        stagnation_thresholds: Dict[str, int] = None,
        verbose: bool = True
    ):
        """
        Initialize adaptive patch selector.
        
        Args:
            base_probs: Base probabilities [diff, full, cross]. Default [0.4, 0.3, 0.3]
            stagnation_thresholds: Dict with 'mild', 'moderate', 'severe' thresholds
            verbose: Print status messages
        """
        self.base_probs = base_probs or [0.4, 0.3, 0.3]
        self.stagnation_thresholds = stagnation_thresholds or {
            'mild': 3,      # 3 generations without improvement
            'moderate': 7,  # 7 generations
            'severe': 15    # 15 generations
        }
        self.verbose = verbose
        
        # State tracking
        self.generations_since_improvement = 0
        self.last_best_score = 0.0
        self.current_probs = self.base_probs.copy()
        
        # History for analysis
        self.history = []
        
        if self.verbose:
            logger.info(f"棣冨箟 AdaptivePatchSelector initialized")
            logger.info(f"   Base probs: diff={self.base_probs[0]:.0%}, full={self.base_probs[1]:.0%}, cross={self.base_probs[2]:.0%}")
    
    def update(self, current_best_score: float, generation: int = None):
        """
        Update state after each generation.
        
        Args:
            current_best_score: Current best score in the population
            generation: Optional generation number for logging
        """
        improved = current_best_score > self.last_best_score
        
        if improved:
            if self.verbose and self.generations_since_improvement > 0:
                logger.info(f"棣冨箚 Improvement detected! Score: {self.last_best_score:.4f} 閳?{current_best_score:.4f}")
                logger.info(f"   Resetting stagnation counter (was {self.generations_since_improvement})")
            
            self.generations_since_improvement = 0
            self.last_best_score = current_best_score
        else:
            self.generations_since_improvement += 1
            if self.verbose and self.generations_since_improvement % 5 == 0:
                logger.info(f"閳?No improvement for {self.generations_since_improvement} generations")
        
        # Record history
        self.history.append({
            'generation': generation,
            'best_score': current_best_score,
            'improved': improved,
            'stagnation': self.generations_since_improvement
        })
    
    def get_probs(self, meta_recommendation: Optional[Dict[str, Any]] = None) -> List[float]:
        """
        Get adaptive patch probabilities based on current state.
        
        Args:
            meta_recommendation: Optional recommendation from meta-summarizer
                Expected format: {
                    'patch_strategy': {
                        'force_type': 'full',  # Optional: force specific type
                        'exploration_boost': 0.3  # Optional: boost exploration
                    }
                }
        
        Returns:
            [diff_prob, full_prob, cross_prob]
        """
        # Check if meta-summarizer has specific recommendation
        if meta_recommendation and 'patch_strategy' in meta_recommendation:
            strategy = meta_recommendation['patch_strategy']
            
            # Check for forced type
            if strategy.get('force_type'):
                forced_type = strategy['force_type']
                if forced_type == 'full':
                    probs = [0.1, 0.7, 0.2]
                elif forced_type == 'cross':
                    probs = [0.1, 0.2, 0.7]
                elif forced_type == 'diff':
                    probs = [0.7, 0.15, 0.15]
                else:
                    probs = self.base_probs.copy()
                
                if self.verbose:
                    logger.info(f"棣冨箟 Meta-forced patch type: {forced_type}")
                    logger.info(f"   Probs: diff={probs[0]:.0%}, full={probs[1]:.0%}, cross={probs[2]:.0%}")
                
                self.current_probs = probs
                return probs
            
            # Check for exploration boost
            if strategy.get('exploration_boost'):
                boost = strategy['exploration_boost']
                # Increase FULL probability, decrease DIFF
                probs = [
                    max(0.1, self.base_probs[0] - boost),
                    min(0.7, self.base_probs[1] + boost),
                    self.base_probs[2]
                ]
                # Normalize
                total = sum(probs)
                probs = [p / total for p in probs]
                
                if self.verbose:
                    logger.info(f"棣冨箟 Meta exploration boost: +{boost:.0%}")
                    logger.info(f"   Probs: diff={probs[0]:.0%}, full={probs[1]:.0%}, cross={probs[2]:.0%}")
                
                self.current_probs = probs
                return probs
        
        # Adaptive based on stagnation level
        stag = self.generations_since_improvement
        
        if stag < self.stagnation_thresholds['mild']:
            # Recent improvement: exploit with DIFF
            probs = [0.5, 0.25, 0.25]
            level = "EXPLOITING"
        
        elif stag < self.stagnation_thresholds['moderate']:
            # Mild stagnation: balanced exploration
            probs = [0.33, 0.34, 0.33]
            level = "BALANCED"
        
        elif stag < self.stagnation_thresholds['severe']:
            # Moderate stagnation: increase FULL for new approaches
            probs = [0.2, 0.5, 0.3]
            level = "EXPLORING"
        
        else:
            # Severe stagnation: maximum exploration
            probs = [0.1, 0.6, 0.3]
            level = "MAX_EXPLORATION"
        
        if self.verbose and probs != self.current_probs:
            logger.info(f"棣冨箟 Adaptive patch selection: {level}")
            logger.info(f"   Stagnation: {stag} generations")
            logger.info(f"   Probs: diff={probs[0]:.0%}, full={probs[1]:.0%}, cross={probs[2]:.0%}")
        
        self.current_probs = probs
        return probs
    
    def get_full_variant_recommendation(self) -> Optional[str]:
        """
        Get recommended FULL patch variant based on stagnation.
        
        Returns:
            Variant name: 'default', 'different_algorithm', 'motivated', 
                         'structural', 'parametric', or None
        """
        stag = self.generations_since_improvement
        
        if stag >= self.stagnation_thresholds['severe']:
            # Force "completely different algorithm" variant
            return 'different_algorithm'
        elif stag >= self.stagnation_thresholds['moderate']:
            # Prefer structural or motivated variants
            return 'structural'
        
        return None  # Use random selection
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status for logging/debugging."""
        return {
            'generations_since_improvement': self.generations_since_improvement,
            'last_best_score': self.last_best_score,
            'current_probs': self.current_probs,
            'stagnation_level': self._get_stagnation_level(),
            'recommended_full_variant': self.get_full_variant_recommendation()
        }
    
    def _get_stagnation_level(self) -> str:
        """Get human-readable stagnation level."""
        stag = self.generations_since_improvement
        
        if stag < self.stagnation_thresholds['mild']:
            return 'none'
        elif stag < self.stagnation_thresholds['moderate']:
            return 'mild'
        elif stag < self.stagnation_thresholds['severe']:
            return 'moderate'
        else:
            return 'severe'


def create_adaptive_selector(config: Dict[str, Any] = None) -> AdaptivePatchSelector:
    """
    Factory function to create AdaptivePatchSelector from config.
    
    Args:
        config: Optional configuration dict with:
            - base_probs: [diff, full, cross]
            - stagnation_thresholds: {mild, moderate, severe}
            - verbose: bool
    
    Returns:
        Configured AdaptivePatchSelector
    """
    if config is None:
        return AdaptivePatchSelector()
    
    return AdaptivePatchSelector(
        base_probs=config.get('base_probs'),
        stagnation_thresholds=config.get('stagnation_thresholds'),
        verbose=config.get('verbose', True)
    )

