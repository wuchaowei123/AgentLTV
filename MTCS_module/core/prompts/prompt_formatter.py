"""
Enhanced Prompt Formatter for Dynamic Prompt Generation
======================================================

Intelligent prompt formatting system that dynamically selects and formats
prompts based on context, search phase, and domain requirements.
"""

from typing import Dict, Any, List, Optional
from .prompt_library import *


class EnhancedPromptFormatter:
    """Enhanced prompt formatter with context-aware prompt selection and formatting."""
    
    def __init__(self, task_config):
        """
        Initialize with task configuration.
        
        Args:
            task_config: TaskConfiguration instance
        """
        self.task_config = task_config
        self.domain = task_config.domain
        self.task_name = task_config.task_name
        self.evaluation_metric = task_config.evaluation_metric
        self.higher_is_better = task_config.higher_is_better
        
    def format_kickstart_prompt(self, strategy: str = "universal", research_ideas: Optional[List[str]] = None) -> str:
        """
        Format kickstart prompt based on strategy.
        
        Args:
            strategy: "basic", "universal", "guided", or "research_enhanced"
            research_ideas: Optional research ideas to include
            
        Returns:
            Formatted prompt string
        """
        if strategy == "universal" or strategy == "guided":
            return self._format_universal_kickstart(research_ideas)
        elif strategy == "research_enhanced":
            return self._format_research_enhanced_kickstart(research_ideas)
        else:
            return self._format_basic_kickstart()
    
    def format_mutation_prompt(
        self, 
        previous_code: str, 
        previous_score: float,
        mutation_type: str = "standard",
        research_ideas: Optional[List[str]] = None,
        advisory_guidance: Optional[str] = None
    ) -> str:
        """
        Format mutation prompt with advanced strategies.
        
        Args:
            previous_code: Code from previous iteration
            previous_score: Performance score of previous code
            mutation_type: "standard", "guided", "advisory", or "hybrid"
            research_ideas: Research ideas to incorporate
            advisory_guidance: Expert advisory guidance
            
        Returns:
            Formatted mutation prompt
        """
        if mutation_type == "guided" or mutation_type == "advisory":
            return self._format_universal_mutation(
                previous_code, previous_score, research_ideas, advisory_guidance
            )
        elif mutation_type == "hybrid":
            return self._format_hybrid_mutation(previous_code, previous_score, research_ideas)
        else:
            return self._format_standard_mutation(previous_code, previous_score)
    
    def format_research_brainstorm_prompt(self, baseline_info: Optional[str] = None) -> str:
        """Format research idea brainstorming prompt."""
        return PROMPT_5_BRAINSTORM_RESEARCH_IDEAS.format(
            domain=self.domain,
            task_name=self.task_name,
            task_description=self.task_config.description,
            evaluation_metric=self.evaluation_metric,
            baseline_info=baseline_info or self._get_baseline_info()
        )
    
    def format_solution_analysis_prompt(self, code_1: str, code_2: str) -> str:
        """Format solution comparison and analysis prompt."""
        return PROMPT_7_ANALYZE_SOLUTIONS.format(
            domain=self.domain,
            code_1=code_1,
            code_2=code_2
        )
    
    def format_hybrid_generation_prompt(self, analysis_text: str) -> str:
        """Format hybrid solution generation prompt."""
        return PROMPT_8_GENERATE_HYBRID.format(
            domain=self.domain,
            analysis_text=analysis_text
        )
    
    def format_replication_prompt(self, method_description: str) -> str:
        """Format model replication prompt."""
        return PROMPT_9_REPLICATE_MODEL.format(
            domain=self.domain,
            method=method_description,
            task_description=self.task_config.description
        )
    
    def get_advisory_guidance(self, advice_type: str = "general") -> str:
        """
        Get advisory guidance for incorporation into mutation prompts.
        
        Args:
            advice_type: "general" or "algorithmic"
            
        Returns:
            Advisory guidance text
        """
        if advice_type == "algorithmic":
            return PROMPT_4_ADVANCED_ALGORITHMIC_ADVICE
        else:
            return PROMPT_3_GENERAL_EXPERT_ADVICE
    
    def _format_universal_kickstart(self, research_ideas: Optional[List[str]] = None) -> str:
        """Format universal kickstart prompt."""
        research_ideas_text = self._format_research_ideas(research_ideas)
        
        return UNIVERSAL_PROMPT_1_KICKSTART.format(
            domain=self.domain,
            task_name=self.task_name,
            task_description=self.task_config.description,
            evaluation_metric=self.evaluation_metric,
            higher_is_better=self.higher_is_better,
            data_files_info=self._format_data_files_info(),
            target_column=self.task_config.get_target_column(),
            prediction_format=self.task_config.get_prediction_format(),
            output_variable=self.task_config.get_output_variable(),
            research_ideas=research_ideas_text,
            additional_context=self._get_additional_context()
        )
    
    def _format_research_enhanced_kickstart(self, research_ideas: Optional[List[str]] = None) -> str:
        """Format research-enhanced kickstart prompt with domain-specific insights."""
        base_prompt = self._format_universal_kickstart(research_ideas)
        
        # Add domain-specific research context
        domain_context = self._get_domain_specific_context()
        
        enhanced_prompt = f"""{base_prompt}

**Domain-Specific Research Context:**
{domain_context}

**Advanced Techniques to Consider:**
- State-of-the-art methods in {self.domain}
- Recent breakthroughs and novel approaches
- Cross-domain technique adaptation
- Performance optimization strategies specific to {self.evaluation_metric}

Focus on implementing cutting-edge techniques that push beyond standard approaches."""
        
        return enhanced_prompt
    
    def _format_basic_kickstart(self) -> str:
        """Format basic kickstart prompt."""
        return PROMPT_1_KICKSTART_TASK.format(
            task_description=self.task_config.description,
            evaluation_metric=self.evaluation_metric,
            higher_is_better=self.higher_is_better,
            data_info=self._format_data_files_info(),
            target_column=self.task_config.get_target_column(),
            prediction_format=self.task_config.get_prediction_format(),
            output_variable=self.task_config.get_output_variable()
        )
    
    def _format_universal_mutation(
        self, 
        previous_code: str, 
        previous_score: float,
        research_ideas: Optional[List[str]] = None,
        advisory_guidance: Optional[str] = None
    ) -> str:
        """Format universal mutation prompt with advisory guidance."""
        research_ideas_text = self._format_research_ideas(research_ideas)
        advisory_text = advisory_guidance or ""
        
        direction = "higher" if self.higher_is_better else "lower"
        return UNIVERSAL_PROMPT_2_MUTATION.format(
            domain=self.domain,
            task_name=self.task_name,
            evaluation_metric=self.evaluation_metric,
            direction=direction,
            previous_code=previous_code,
            previous_score=previous_score,
            research_ideas=research_ideas_text,
            advisory_guidance=advisory_text
        )
    
    def _format_hybrid_mutation(
        self, 
        previous_code: str, 
        previous_score: float,
        research_ideas: Optional[List[str]] = None
    ) -> str:
        """Format mutation prompt specifically for hybrid approach generation."""
        research_ideas_text = self._format_research_ideas(research_ideas)
        direction = "higher" if self.higher_is_better else "lower"
        
        hybrid_prompt = f"""You are an expert-level AI scientist specializing in {self.domain}. Your task is to create a HYBRID APPROACH that combines multiple strategies to improve upon the previous solution.

**Task:** {self.task_name}
**Domain:** {self.domain}
**Evaluation Metric:** {self.evaluation_metric} ({direction} is better)

**Previous Code (Score: {previous_score}):**
```python
{previous_code}
```

**Your Mission:**
Create a hybrid solution that combines:
1. The strengths of the previous approach
2. Novel techniques from {self.domain} research
3. Advanced ensemble or multi-model strategies
4. Domain-specific optimizations

**Research Ideas to Integrate:**
{research_ideas_text}

**Hybrid Strategy Guidelines:**
- Combine multiple algorithms or approaches
- Use ensemble techniques (stacking, blending, voting)
- Integrate different feature engineering strategies
- Apply multi-level optimization
- Create synergies between different methodologies

Provide only the complete, raw Python code within a single code block. The hybrid approach should significantly outperform the previous solution."""
        
        return hybrid_prompt
    
    def _format_standard_mutation(self, previous_code: str, previous_score: float) -> str:
        """Format standard mutation prompt."""
        return PROMPT_2_ITERATIVE_MUTATION.format(
            task_description=self.task_config.description,
            previous_code=previous_code,
            previous_score=previous_score
        )
    
    def _format_research_ideas(self, research_ideas: Optional[List[str]] = None) -> str:
        """Format research ideas list for inclusion in prompts."""
        if not research_ideas:
            research_ideas = self.task_config.research_ideas
        
        if not research_ideas:
            return "No specific research ideas provided."
        
        formatted_ideas = "\n".join(f"- {idea}" for idea in research_ideas)
        return formatted_ideas
    
    def _format_data_files_info(self) -> str:
        """Format data files information."""
        data_files = self.task_config.data_files
        if not data_files:
            return "Data files not specified."
        
        info_lines = []
        for key, path in data_files.items():
            info_lines.append(f"- {key}: {path}")
        
        return "\n".join(info_lines)
    
    def _get_baseline_info(self) -> str:
        """Get baseline performance information."""
        baseline_perf = self.task_config.baseline_performance
        if not baseline_perf:
            return "No baseline performance information available."
        
        info_lines = []
        for method, score in baseline_perf.items():
            info_lines.append(f"- {method}: {score}")
        
        return "\n".join(info_lines)
    
    def _get_additional_context(self) -> str:
        """Get additional context information for the task."""
        context_parts = []
        
        # Add competition info if available
        comp_info = self.task_config.competition_info
        if comp_info:
            context_parts.append("Competition Details:")
            for key, value in comp_info.items():
                context_parts.append(f"- {key}: {value}")
        
        # Add code requirements
        code_reqs = self.task_config.code_requirements
        if code_reqs:
            context_parts.append("\nCode Requirements:")
            for key, value in code_reqs.items():
                if key not in ['target_column', 'prediction_format', 'output_variable']:
                    context_parts.append(f"- {key}: {value}")
        
        return "\n".join(context_parts) if context_parts else "No additional context available."
    
    def _get_domain_specific_context(self) -> str:
        """Get domain-specific research context."""
        domain_contexts = {
            "machine_learning": """
- Advanced ensemble methods (stacking, blending, meta-learning)
- Neural architecture search and AutoML techniques
- Feature selection and dimensionality reduction
- Hyperparameter optimization (Bayesian, genetic algorithms)
- Transfer learning and pre-trained model adaptation
            """,
            "bioinformatics": """
- Single-cell analysis techniques (scRNA-seq, spatial transcriptomics)
- Genomic sequence analysis and motif discovery
- Protein structure prediction and molecular dynamics
- Phylogenetic analysis and evolutionary modeling
- Multi-omics integration strategies
            """,
            "geospatial": """
- Remote sensing and satellite image analysis
- Geographic information systems (GIS) and spatial statistics
- Computer vision for aerial/satellite imagery
- Temporal analysis of geographic data
- Multi-spectral and hyperspectral image processing
            """,
            "time_series": """
- Deep learning for temporal modeling (LSTM, Transformers)
- Seasonal decomposition and trend analysis
- Multi-variate time series forecasting
- Anomaly detection in temporal data
- Frequency domain analysis and spectral methods
            """,
        }
        
        return domain_contexts.get(self.domain, f"Domain-specific techniques for {self.domain} problems.")
    
    def create_multi_strategy_prompts(self) -> Dict[str, str]:
        """
        Create multiple initialization prompts for different strategies.
        
        Returns:
            Dictionary mapping strategy names to formatted prompts
        """
        strategies = {}
        
        # Standard approach
        strategies["standard"] = self.format_kickstart_prompt("universal")
        
        # Research-guided approach
        strategies["research_guided"] = self.format_kickstart_prompt("research_enhanced")
        
        # Replication approach (if baseline exists)
        baseline_perf = self.task_config.baseline_performance
        if baseline_perf:
            # Use the first baseline method for replication
            first_method = next(iter(baseline_perf.keys()))
            first_score = baseline_perf[first_method]
            method_description = f"Method: {first_method}, Performance: {first_score}"
            strategies["replication"] = self.format_replication_prompt(method_description)
        
        return strategies
    
    def format_mutation_prompt_with_user_feedback(
        self,
        previous_code: str,
        previous_score: float,
        user_feedback_list: list,
        mutation_type: str = "standard",
        research_ideas: Optional[List[str]] = None,
        advisory_guidance: Optional[str] = None
    ) -> str:
        """
        Format mutation prompt with user feedback incorporated.
        
        Args:
            previous_code: Code from previous iteration
            previous_score: Performance score of previous code
            user_feedback_list: List of UserFeedback objects
            mutation_type: Type of mutation
            research_ideas: Research ideas to incorporate
            advisory_guidance: Expert advisory guidance
            
        Returns:
            Formatted mutation prompt with feedback
        """
        # Get base prompt
        base_prompt = self.format_mutation_prompt(
            previous_code,
            previous_score,
            mutation_type,
            research_ideas,
            advisory_guidance
        )
        
        # Add user feedback section if available
        if user_feedback_list:
            feedback_section = self._build_user_feedback_section(user_feedback_list)
            enhanced_prompt = f"{base_prompt}\n\n{feedback_section}"
        else:
            enhanced_prompt = base_prompt
        
        return enhanced_prompt
    
    def _build_user_feedback_section(self, feedback_list: list) -> str:
        """
        Build user feedback section for prompt.
        
        Args:
            feedback_list: List of UserFeedback objects (from core.utils.user_feedback_collector)
            
        Returns:
            Formatted feedback section
        """
        if not feedback_list:
            return ""
        
        section = """
**👤 USER FEEDBACK - CRITICAL ADVICE**

The human expert has provided the following feedback on previous solutions 
in this lineage. You MUST address these concerns in your improved solution:

"""
        
        # Sort by priority (highest first)
        sorted_feedback = sorted(
            feedback_list, 
            key=lambda f: f.priority, 
            reverse=True
        )
        
        for i, feedback in enumerate(sorted_feedback, 1):
            priority_stars = "⭐" * feedback.priority
            section += f"{i}. [{feedback.feedback_type.upper()}] {priority_stars}\n"
            section += f"   \"{feedback.feedback_text}\"\n\n"
        
        section += """
**Your Task:**
Address ALL the above feedback points in your solution. Specifically:
"""
        
        # Generate specific action items based on feedback type
        action_items = set()
        for feedback in sorted_feedback:
            if feedback.feedback_type == 'performance':
                action_items.add("- Optimize for speed: reduce batch size, use faster models, enable GPU")
            elif feedback.feedback_type == 'accuracy':
                action_items.add("- Improve accuracy: try better models, ensemble, feature engineering")
            elif feedback.feedback_type == 'approach':
                action_items.add("- Revise approach: consider different algorithms or methodologies")
        
        section += "\n".join(action_items)
        section += "\n"
        
        return section