"""
Enhanced LLM Worker with Multi-Phase Prompt Strategies
=====================================================

Enhanced version of the LLM worker that integrates with the complete prompt system
and supports the multi-phase architecture from the AI system graph.
"""

import os
import traceback
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass

from .llm_worker import UniversalLLMWorker, LLMResponse
from .prompts.prompt_strategies import PromptStrategyManager, SearchPhase, PromptStrategy


@dataclass
class EnhancedLLMResponse:
    """Extended response from enhanced LLM operations."""
    code: Optional[str]
    success: bool
    error_message: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    strategy_used: Optional[str] = None
    prompt_type: Optional[str] = None
    research_ideas: Optional[List[str]] = None


class MultiPhaseResults:
    """Container for multi-phase search results."""
    
    def __init__(self):
        self.preparation_results = {}
        self.research_ideas = []
        self.hybrid_strategies = []
        self.solution_analyses = []
        self.replication_attempts = []


class EnhancedLLMWorker(UniversalLLMWorker):
    """
    Enhanced LLM worker with multi-phase prompt strategies and research integration.
    
    Supports the full AI system graph workflow:
    - Phase 1: Research preparation and idea generation
    - Phase 2: Intelligent mutation with advisory prompts
    - Phase 3: Solution analysis and hybridization
    """
    
    def __init__(self, task_config, preferred_provider: str = "gemini", model_name: Optional[str] = None):
        """
        Initialize enhanced LLM worker.
        
        Args:
            task_config: TaskConfiguration instance
            preferred_provider: "gemini" or "openai"  
            model_name: Specific model name (optional)
        """
        super().__init__(preferred_provider, model_name)
        
        self.task_config = task_config
        self.prompt_manager = PromptStrategyManager(task_config, enable_research_phase=True)
        self.multi_phase_results = MultiPhaseResults()
        
        # Track performance for strategy optimization
        self.strategy_performance = {}
        self.current_search_iteration = 0
    
    def run_preparation_phase(self) -> MultiPhaseResults:
        """
        Run Phase 1 preparation including research brainstorming and strategy planning.
        
        Returns:
            MultiPhaseResults containing preparation phase outputs
        """
        print("🔬 Starting Phase 1: Research Preparation")
        
        # Get preparation strategies
        prep_results = self.prompt_manager.run_research_preparation_phase()
        self.multi_phase_results.preparation_results = prep_results
        
        # Execute research brainstorming if enabled
        if "brainstorm" in prep_results["preparation_prompts"]:
            research_ideas = self._execute_research_brainstorming(
                prep_results["preparation_prompts"]["brainstorm"]
            )
            self.multi_phase_results.research_ideas.extend(research_ideas)
            
        print(f"✅ Phase 1 complete: Generated {len(self.multi_phase_results.research_ideas)} research ideas")
        return self.multi_phase_results
    
    def generate_multi_strategy_initial_code(self) -> Dict[str, EnhancedLLMResponse]:
        """
        Generate initial code using multiple strategies as per the AI system graph.
        
        Returns:
            Dictionary mapping strategy names to LLM responses
        """
        print("🚀 Generating initial code with multiple strategies...")
        
        # Get initialization strategies
        strategy_prompts = self.prompt_manager.get_initialization_strategies()
        results = {}
        
        for strategy_name, prompt in strategy_prompts.items():
            print(f"   Executing strategy: {strategy_name}")
            
            try:
                response = self._execute_prompt(prompt, f"init_{strategy_name}")
                
                enhanced_response = EnhancedLLMResponse(
                    code=response.code,
                    success=response.success,
                    error_message=response.error_message,
                    provider=response.provider,
                    model=response.model,
                    strategy_used=strategy_name,
                    prompt_type="initialization"
                )
                
                results[strategy_name] = enhanced_response
                
            except Exception as e:
                print(f"   ❌ Strategy {strategy_name} failed: {e}")
                results[strategy_name] = EnhancedLLMResponse(
                    code=None,
                    success=False,
                    error_message=str(e),
                    strategy_used=strategy_name,
                    prompt_type="initialization"
                )
        
        print(f"✅ Generated {len([r for r in results.values() if r.success])} successful initial solutions")
        return results
    
    def generate_enhanced_mutation(
        self, 
        previous_code: str, 
        score: float,
        node_generation: int = 0,
        mutation_context: Optional[Dict[str, Any]] = None
    ) -> EnhancedLLMResponse:
        """
        Generate enhanced code mutation using intelligent prompt strategy selection.
        
        Args:
            previous_code: Code from previous iteration
            score: Performance score of previous code
            node_generation: Generation of the node being expanded
            mutation_context: Additional context for mutation
            
        Returns:
            Enhanced LLM response with strategy information
        """
        self.current_search_iteration += 1
        
        # Get optimal mutation prompt based on context
        mutation_prompt = self.prompt_manager.get_mutation_prompt(
            previous_code,
            score,
            node_generation,
            self.current_search_iteration,
            mutation_context
        )
        
        try:
            # Execute mutation
            response = self._execute_prompt(mutation_prompt, "mutation")
            
            # Determine strategy used (simplified for now)
            strategy_used = self._determine_strategy_from_prompt(mutation_prompt)
            
            enhanced_response = EnhancedLLMResponse(
                code=response.code,
                success=response.success,
                error_message=response.error_message,
                provider=response.provider,
                model=response.model,
                strategy_used=strategy_used,
                prompt_type="mutation",
                research_ideas=self.multi_phase_results.research_ideas
            )
            
            # Update strategy performance tracking
            if response.success:
                self.prompt_manager.update_strategy_performance(
                    PromptStrategy(strategy_used), score, True
                )
            
            return enhanced_response
            
        except Exception as e:
            return EnhancedLLMResponse(
                code=None,
                success=False,
                error_message=f"Enhanced mutation failed: {str(e)}",
                prompt_type="mutation"
            )
    
    def analyze_and_hybridize_solutions(self, solutions: List[Tuple[str, float]]) -> Dict[str, EnhancedLLMResponse]:
        """
        Run Phase 3 solution analysis and hybrid generation.
        
        Args:
            solutions: List of (code, score) tuples for analysis
            
        Returns:
            Dictionary containing analysis results and hybrid solutions
        """
        print("🔬 Starting Phase 3: Solution Analysis & Hybridization")
        
        if len(solutions) < 2:
            print("⚠️ Need at least 2 solutions for analysis")
            return {}
        
        results = {}
        
        # Get analysis prompts
        analysis_prompts = self.prompt_manager.analyze_solutions_for_recombination(solutions)
        
        # Execute solution analyses
        for prompt_key, prompt in analysis_prompts.items():
            if prompt_key.startswith("analysis_"):
                try:
                    response = self._execute_prompt(prompt, f"analysis_{prompt_key}")
                    
                    enhanced_response = EnhancedLLMResponse(
                        code=response.code,
                        success=response.success,
                        error_message=response.error_message,
                        provider=response.provider,
                        model=response.model,
                        strategy_used="solution_analysis",
                        prompt_type="analysis"
                    )
                    
                    results[prompt_key] = enhanced_response
                    
                    if response.success:
                        self.multi_phase_results.solution_analyses.append(response.code)
                        
                except Exception as e:
                    print(f"   ❌ Analysis {prompt_key} failed: {e}")
        
        # Generate hybrid solutions
        if "hybrid_generation" in analysis_prompts:
            try:
                hybrid_prompt = analysis_prompts["hybrid_generation"]
                response = self._execute_prompt(hybrid_prompt, "hybrid_generation")
                
                enhanced_response = EnhancedLLMResponse(
                    code=response.code,
                    success=response.success,
                    error_message=response.error_message,
                    provider=response.provider,
                    model=response.model,
                    strategy_used="hybrid_generation",
                    prompt_type="hybrid"
                )
                
                results["hybrid_solution"] = enhanced_response
                
                if response.success:
                    self.multi_phase_results.hybrid_strategies.append(response.code)
                    
            except Exception as e:
                print(f"   ❌ Hybrid generation failed: {e}")
        
        print(f"✅ Phase 3 complete: {len([r for r in results.values() if r.success])} successful analyses/hybrids")
        return results
    
    def _execute_research_brainstorming(self, brainstorm_prompt: str) -> List[str]:
        """Execute research idea brainstorming and extract ideas."""
        try:
            response = self._execute_prompt(brainstorm_prompt, "research_brainstorm")
            
            if response.success and response.code:
                # Extract research ideas from response
                # This is a simplified extraction - in practice, would use more sophisticated parsing
                ideas = self._extract_research_ideas_from_response(response.code)
                return ideas
            else:
                print("⚠️ Research brainstorming failed")
                return []
                
        except Exception as e:
            print(f"❌ Research brainstorming error: {e}")
            return []
    
    def _execute_prompt(self, prompt: str, operation_type: str) -> LLMResponse:
        """Execute a prompt using the base LLM worker."""
        try:
            if self.active_provider == "gemini":
                return self._generate_with_gemini_direct(prompt)
            elif self.active_provider == "openai":
                return self._generate_with_openai_direct(prompt)
            else:
                raise RuntimeError("No LLM provider available")
                
        except Exception as e:
            return LLMResponse(
                code=None,
                success=False,
                error_message=f"{operation_type} failed: {str(e)}"
            )
    
    def _generate_with_gemini_direct(self, prompt: str) -> LLMResponse:
        """Direct Gemini generation for enhanced prompts."""
        try:
            from google.genai import types
            
            response = self.gemini_client.models.generate_content(
                model=self.model_name or "gemini-2.5-pro",
                config=types.GenerateContentConfig(
                    temperature=0.7
                    # No max_output_tokens limit - let Gemini generate complete code
                ),
                contents=prompt
            )
            
            code = self._extract_code_from_response(response.text)
            
            return LLMResponse(
                code=code,
                success=True,
                provider="gemini",
                model=self.model_name or "gemini-2.5-pro"
            )
            
        except Exception as e:
            return LLMResponse(
                code=None,
                success=False,
                error_message=f"Gemini error: {str(e)}",
                provider="gemini"
            )
    
    def _generate_with_openai_direct(self, prompt: str) -> LLMResponse:
        """Direct OpenAI generation for enhanced prompts."""
        try:
            response = self.openai_client.chat.completions.create(
                model=self.model_name or "gpt-4-turbo-preview",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            
            code = self._extract_code_from_response(response.choices[0].message.content)
            
            return LLMResponse(
                code=code,
                success=True,
                provider="openai",
                model=self.model_name or "gpt-4-turbo-preview"
            )
            
        except Exception as e:
            return LLMResponse(
                code=None,
                success=False,
                error_message=f"OpenAI error: {str(e)}",
                provider="openai"
            )
    
    def _extract_research_ideas_from_response(self, response_text: str) -> List[str]:
        """Extract research ideas from LLM response."""
        # Simplified extraction - look for numbered lists or bullet points
        ideas = []
        lines = response_text.split('\n')
        
        for line in lines:
            line = line.strip()
            # Look for numbered items (1., 2., etc.) or bullet points
            if (line and (
                (line[0].isdigit() and '.' in line[:5]) or 
                line.startswith('•') or 
                line.startswith('-') or
                line.startswith('*')
            )):
                # Extract the idea text
                idea = line
                if '.' in line[:5]:  # Remove numbering
                    idea = line.split('.', 1)[1].strip()
                elif line.startswith(('•', '-', '*')):  # Remove bullet
                    idea = line[1:].strip()
                
                if len(idea) > 10:  # Only keep substantial ideas
                    ideas.append(idea)
        
        return ideas[:10]  # Limit to top 10 ideas
    
    def _determine_strategy_from_prompt(self, prompt: str) -> str:
        """Determine strategy type from prompt content."""
        prompt_lower = prompt.lower()
        
        if "hybrid" in prompt_lower:
            return "hybrid"
        elif "advisory" in prompt_lower or "advice" in prompt_lower:
            return "advisory"
        elif "research" in prompt_lower:
            return "research_enhanced"
        elif "guided" in prompt_lower:
            return "guided"
        else:
            return "standard"
    
    def get_multi_phase_summary(self) -> Dict[str, Any]:
        """Get comprehensive summary of multi-phase search results."""
        return {
            "preparation_phase": {
                "research_ideas_generated": len(self.multi_phase_results.research_ideas),
                "research_ideas": self.multi_phase_results.research_ideas[:5]  # Show first 5
            },
            "main_phase": {
                "current_iteration": self.current_search_iteration,
                "strategy_performance": dict(self.strategy_performance)
            },
            "analysis_phase": {
                "solutions_analyzed": len(self.multi_phase_results.solution_analyses),
                "hybrid_strategies_generated": len(self.multi_phase_results.hybrid_strategies)
            },
            "prompt_manager_summary": self.prompt_manager.get_search_phase_summary()
        }


# Backward compatibility function
def create_enhanced_llm_worker(task_config, preferred_provider: str = "gemini") -> EnhancedLLMWorker:
    """Create enhanced LLM worker with task configuration."""
    return EnhancedLLMWorker(task_config, preferred_provider)