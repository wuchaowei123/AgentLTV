"""
Prompt Strategy Manager for Intelligent Prompt Selection
=======================================================

Manages prompt strategy selection based on search context, performance history,
and domain characteristics. Implements the multi-phase architecture from the
AI system graph.
"""

from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from .prompt_formatter import EnhancedPromptFormatter
from .prompt_library import ALL_PROMPTS


class SearchPhase(Enum):
    """Search phases as defined in the AI system graph."""
    PREPARATION = "preparation"
    MAIN_LOOP = "main_loop" 
    ANALYSIS = "analysis"


class PromptStrategy(Enum):
    """Available prompt strategies."""
    STANDARD = "standard"
    GUIDED = "guided"
    RESEARCH_ENHANCED = "research_enhanced"
    ADVISORY = "advisory"
    HYBRID = "hybrid"
    REPLICATION = "replication"


class PromptStrategyManager:
    """
    Intelligent prompt strategy manager that selects optimal prompts based on context.
    
    Implements the multi-phase architecture:
    - Phase 1: Preparation (research, recombination)
    - Phase 2: Main loop (iterative improvement) 
    - Phase 3: Analysis (solution comparison, hybridization)
    """
    
    def __init__(self, task_config, enable_research_phase: bool = True):
        """
        Initialize prompt strategy manager.
        
        Args:
            task_config: TaskConfiguration instance
            enable_research_phase: Whether to enable research preparation phase
        """
        self.task_config = task_config
        self.formatter = EnhancedPromptFormatter(task_config)
        self.enable_research_phase = enable_research_phase
        
        # Track search history for intelligent strategy selection
        self.search_history = []
        self.best_strategies = {}
        self.failed_strategies = set()
        
        # Research phase results
        self.generated_research_ideas = []
        self.analyzed_solutions = []
        self.hybrid_strategies = []
    
    def get_initialization_strategies(self) -> Dict[str, str]:
        """
        Get multiple initialization strategies for Phase 1 preparation.
        
        Returns:
            Dictionary mapping strategy names to formatted prompts
        """
        strategies = {}
        
        if self.enable_research_phase:
            # Phase 1: Preparation strategies
            strategies.update(self._get_preparation_strategies())
        
        # Standard strategies
        strategies.update(self.formatter.create_multi_strategy_prompts())
        
        return strategies
    
    def get_mutation_prompt(
        self, 
        previous_code: str, 
        previous_score: float,
        node_generation: int = 0,
        search_iteration: int = 0,
        mutation_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Get optimal mutation prompt based on search context.
        
        Args:
            previous_code: Code from previous iteration
            previous_score: Performance score of previous code  
            node_generation: Generation of the node being expanded
            search_iteration: Current search iteration
            mutation_context: Additional context for mutation strategy
            
        Returns:
            Formatted mutation prompt
        """
        # Select strategy based on context
        strategy = self._select_mutation_strategy(
            previous_score, node_generation, search_iteration, mutation_context
        )
        
        # Get appropriate prompt
        if strategy == PromptStrategy.ADVISORY:
            return self._get_advisory_mutation_prompt(previous_code, previous_score)
        elif strategy == PromptStrategy.HYBRID:
            return self._get_hybrid_mutation_prompt(previous_code, previous_score)
        elif strategy == PromptStrategy.RESEARCH_ENHANCED:
            return self._get_research_enhanced_mutation_prompt(previous_code, previous_score)
        else:
            return self._get_standard_mutation_prompt(previous_code, previous_score)
    
    def run_research_preparation_phase(self) -> Dict[str, Any]:
        """
        Run Phase 1 research preparation to generate novel ideas and strategies.
        
        Returns:
            Dictionary containing research phase results
        """
        results = {
            "research_ideas": [],
            "hybrid_strategies": [],
            "replication_methods": [],
            "preparation_prompts": {}
        }
        
        if not self.enable_research_phase:
            return results
        
        # Brainstorm research ideas (Prompt 5)
        brainstorm_prompt = self.formatter.format_research_brainstorm_prompt()
        results["preparation_prompts"]["brainstorm"] = brainstorm_prompt
        
        # Structure ideas (Prompt 6) - would be applied to LLM results
        structure_prompt = ALL_PROMPTS["structure_ideas"]
        results["preparation_prompts"]["structure"] = structure_prompt
        
        # If we have previous solutions, analyze for recombination
        if self.analyzed_solutions:
            analysis_prompt = self._create_solution_analysis_prompt()
            results["preparation_prompts"]["analysis"] = analysis_prompt
            
            hybrid_prompt = self._create_hybrid_generation_prompt()
            results["preparation_prompts"]["hybrid"] = hybrid_prompt
        
        return results
    
    def analyze_solutions_for_recombination(self, solutions: List[Tuple[str, float]]) -> Dict[str, str]:
        """
        Analyze multiple solutions for recombination (Phase 3).
        
        Args:
            solutions: List of (code, score) tuples
            
        Returns:
            Dictionary containing analysis and hybrid generation prompts
        """
        analysis_prompts = {}
        
        if len(solutions) < 2:
            return analysis_prompts
        
        # Compare pairs of solutions
        for i, (code1, score1) in enumerate(solutions):
            for j, (code2, score2) in enumerate(solutions[i+1:], i+1):
                prompt_key = f"analysis_{i}_{j}"
                analysis_prompts[prompt_key] = self.formatter.format_solution_analysis_prompt(code1, code2)
        
        # Generate hybrid strategies
        if len(solutions) >= 2:
            # Create analysis text for hybrid generation
            analysis_text = self._create_analysis_summary(solutions)
            analysis_prompts["hybrid_generation"] = self.formatter.format_hybrid_generation_prompt(analysis_text)
        
        return analysis_prompts
    
    def update_strategy_performance(self, strategy: PromptStrategy, score: float, success: bool):
        """
        Update strategy performance tracking for intelligent selection.
        
        Args:
            strategy: The strategy used
            score: Performance score achieved
            success: Whether the strategy succeeded
        """
        self.search_history.append({
            "strategy": strategy,
            "score": score,
            "success": success
        })
        
        if success:
            if strategy not in self.best_strategies:
                self.best_strategies[strategy] = []
            self.best_strategies[strategy].append(score)
        else:
            self.failed_strategies.add(strategy)
    
    def _get_preparation_strategies(self) -> Dict[str, str]:
        """Get Phase 1 preparation strategy prompts."""
        prep_strategies = {}
        
        # Research brainstorming
        prep_strategies["research_brainstorm"] = self.formatter.format_research_brainstorm_prompt()
        
        # Replication from baselines
        baseline_info = self.task_config.baseline_performance
        if baseline_info:
            for method, score in baseline_info.items():
                method_description = f"Method: {method}, Performance: {score}"
                prep_strategies[f"replicate_{method}"] = self.formatter.format_replication_prompt(method_description)
        
        return prep_strategies
    
    def _select_mutation_strategy(
        self, 
        previous_score: float, 
        node_generation: int,
        search_iteration: int,
        mutation_context: Optional[Dict[str, Any]] = None
    ) -> PromptStrategy:
        """
        Intelligently select mutation strategy based on context.
        
        Args:
            previous_score: Previous performance score
            node_generation: Generation of node being expanded
            search_iteration: Current search iteration
            mutation_context: Additional context
            
        Returns:
            Selected prompt strategy
        """
        # Early iterations: try diverse strategies
        if search_iteration < 5:
            if search_iteration % 3 == 0:
                return PromptStrategy.ADVISORY
            elif search_iteration % 3 == 1:
                return PromptStrategy.RESEARCH_ENHANCED
            else:
                return PromptStrategy.STANDARD
        
        # Mid iterations: focus on what's working
        elif search_iteration < 20:
            # Use best performing strategy from history
            if self.best_strategies:
                best_strategy = max(self.best_strategies.keys(), 
                                  key=lambda s: max(self.best_strategies[s]))
                return best_strategy
            else:
                return PromptStrategy.GUIDED
        
        # Late iterations: try hybrid approaches
        else:
            if len(self.analyzed_solutions) >= 2:
                return PromptStrategy.HYBRID
            else:
                return PromptStrategy.ADVISORY
    
    def _get_advisory_mutation_prompt(self, previous_code: str, previous_score: float) -> str:
        """Get mutation prompt with advisory guidance."""
        # Alternate between general and algorithmic advice
        advice_type = "algorithmic" if len(self.search_history) % 2 == 0 else "general"
        advisory_guidance = self.formatter.get_advisory_guidance(advice_type)
        
        return self.formatter.format_mutation_prompt(
            previous_code, 
            previous_score,
            mutation_type="advisory",
            advisory_guidance=advisory_guidance
        )
    
    def _get_hybrid_mutation_prompt(self, previous_code: str, previous_score: float) -> str:
        """Get hybrid mutation prompt."""
        research_ideas = self.generated_research_ideas or self.task_config.research_ideas
        
        return self.formatter.format_mutation_prompt(
            previous_code,
            previous_score,
            mutation_type="hybrid",
            research_ideas=research_ideas
        )
    
    def _get_research_enhanced_mutation_prompt(self, previous_code: str, previous_score: float) -> str:
        """Get research-enhanced mutation prompt."""
        research_ideas = self.generated_research_ideas or self.task_config.research_ideas
        
        return self.formatter.format_mutation_prompt(
            previous_code,
            previous_score,
            mutation_type="guided",
            research_ideas=research_ideas
        )
    
    def _get_standard_mutation_prompt(self, previous_code: str, previous_score: float) -> str:
        """Get standard mutation prompt."""
        return self.formatter.format_mutation_prompt(
            previous_code,
            previous_score,
            mutation_type="standard"
        )
    
    def _create_solution_analysis_prompt(self) -> str:
        """Create prompt for analyzing existing solutions."""
        if len(self.analyzed_solutions) < 2:
            return ""
        
        code1, code2 = self.analyzed_solutions[:2]
        return self.formatter.format_solution_analysis_prompt(code1, code2)
    
    def _create_hybrid_generation_prompt(self) -> str:
        """Create prompt for generating hybrid strategies."""
        analysis_text = "Previous solutions have shown different approaches that could be combined."
        return self.formatter.format_hybrid_generation_prompt(analysis_text)
    
    def _create_analysis_summary(self, solutions: List[Tuple[str, float]]) -> str:
        """Create summary of solutions for hybrid generation."""
        summary_parts = []
        
        for i, (code, score) in enumerate(solutions):
            summary_parts.append(f"Solution {i+1} (Score: {score:.4f}):")
            summary_parts.append(f"- Uses approach: {self._analyze_code_approach(code)}")
            summary_parts.append("")
        
        return "\n".join(summary_parts)
    
    def _analyze_code_approach(self, code: str) -> str:
        """Quick analysis of code approach for summary."""
        code_lower = code.lower()
        
        approaches = []
        if "xgboost" in code_lower or "xgb" in code_lower:
            approaches.append("XGBoost")
        if "randomforest" in code_lower:
            approaches.append("Random Forest")
        if "neural" in code_lower or "tensorflow" in code_lower or "pytorch" in code_lower:
            approaches.append("Neural Network")
        if "ensemble" in code_lower or "voting" in code_lower or "stacking" in code_lower:
            approaches.append("Ensemble")
        if "feature" in code_lower and "engineering" in code_lower:
            approaches.append("Feature Engineering")
        
        return ", ".join(approaches) if approaches else "Standard ML approach"
    
    def get_search_phase_summary(self) -> Dict[str, Any]:
        """Get summary of search progress across all phases."""
        return {
            "total_iterations": len(self.search_history),
            "successful_strategies": {str(k): len(v) for k, v in self.best_strategies.items()},
            "failed_strategies": [str(s) for s in self.failed_strategies],
            "research_ideas_generated": len(self.generated_research_ideas),
            "solutions_analyzed": len(self.analyzed_solutions),
            "best_performing_strategy": self._get_best_performing_strategy()
        }
    
    def _get_best_performing_strategy(self) -> Optional[str]:
        """Get the best performing strategy so far."""
        if not self.best_strategies:
            return None
        
        best_strategy = max(self.best_strategies.keys(),
                          key=lambda s: max(self.best_strategies[s]))
        return str(best_strategy)