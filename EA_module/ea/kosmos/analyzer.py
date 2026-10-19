"""
Kosmos Analyzer

Universal analyzer for EAFramework that:
1. Generates hypotheses about why code achieved its performance
2. Generates analysis code to rank hypotheses by evidence
3. Returns all ranked hypotheses for mutation guidance
"""

import os
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import requests

from .config import KosmosConfig
from ..utils.auto_fixer import EAAutoFixer


@dataclass
class RankedHypothesis:
    """A hypothesis with evidence-based ranking"""
    hypothesis: str
    score: float  # 0.0 to 1.0, higher = more evidence
    evidence: str
    recommendation: str
    hypothesis_type: str = "general"
    
    def to_dict(self) -> dict:
        return {
            'hypothesis': self.hypothesis,
            'score': self.score,
            'evidence': self.evidence,
            'recommendation': self.recommendation,
            'type': self.hypothesis_type
        }


@dataclass
class AnalysisResult:
    """Result of Kosmos analysis"""
    hypotheses: List[RankedHypothesis]
    recommendations: List[str]
    raw_analysis: Optional[Dict[str, Any]] = None
    success: bool = True
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'hypotheses': [h.to_dict() for h in self.hypotheses],
            'recommendations': self.recommendations,
            'raw_analysis': self.raw_analysis,
            'success': self.success,
            'error': self.error
        }


class KosmosAnalyzer:
    """
    Universal analyzer for EAFramework.
    
    Works with ANY task by reading task description from config.
    Generates hypotheses and ranks them using LLM-generated analysis code.
    """
    
    def __init__(
        self, 
        task_config: dict,
        kosmos_config: Optional[KosmosConfig] = None,
        auto_fixer: Optional[EAAutoFixer] = None,
        verbose: bool = True
    ):
        """
        Initialize analyzer.
        
        Args:
            task_config: Task configuration dict with 'description', 'metric', etc.
            kosmos_config: Kosmos configuration
            auto_fixer: Auto-fixer for executing analysis code
            verbose: Print status messages
        """
        self.task_config = task_config
        self.config = kosmos_config or KosmosConfig()
        self.auto_fixer = auto_fixer or EAAutoFixer(verbose=verbose)
        self.verbose = verbose
        
        # Extract task info
        self.task_description = task_config.get('description', 'ML optimization task')
        self.metric_name = task_config.get('metric', 'score')
        self.higher_is_better = task_config.get('higher_is_better', True)
        
        # LLM configuration
        self.api_base = os.getenv('OPENAI_API_BASE', '')
        self.api_key = os.getenv('OPENAI_API_KEY', '')
        self.model = self.config.llm_model
        
        if self.verbose:
            print(f"棣冩暕 KosmosAnalyzer initialized")
            print(f"   Task: {self.task_description[:50]}...")
            print(f"   Metric: {self.metric_name}")
            print(f"   Model: {self.model}")
    
    def analyze_node(
        self,
        code: str,
        metrics: Dict[str, Any],
        predictions: Optional[Any] = None,
        feature_importance: Optional[Dict[str, float]] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> AnalysisResult:
        """
        Analyze a node's performance and generate ranked hypotheses.
        
        Args:
            code: The evolved code
            metrics: Performance metrics (F1, precision, recall, etc.)
            predictions: Optional predictions array
            feature_importance: Optional feature importance dict
            additional_context: Optional additional context for analysis
            
        Returns:
            AnalysisResult with ranked hypotheses
        """
        if self.verbose:
            print(f"\n棣冩暕 Analyzing node (metric: {metrics.get('combined_score', 'N/A')})")
        
        try:
            # Step 1: Generate hypotheses
            hypotheses = self._generate_hypotheses(code, metrics, feature_importance)
            
            if not hypotheses:
                return AnalysisResult(
                    hypotheses=[],
                    recommendations=["Unable to generate hypotheses"],
                    success=False,
                    error="No hypotheses generated"
                )
            
            # Step 2: Generate analysis code to rank hypotheses
            analysis_code = self._generate_analysis_code(
                hypotheses, metrics, feature_importance, additional_context
            )
            
            # Step 3: Execute analysis code
            success, raw_results, error = self.auto_fixer.execute_analysis_code(
                analysis_code,
                timeout=self.config.analysis_timeout,
                max_retries=self.config.max_analysis_retries,
                allowed_imports=self.config.allowed_imports
            )
            
            # Step 4: Rank hypotheses based on analysis
            if success and raw_results:
                ranked = self._rank_hypotheses(hypotheses, raw_results)
            else:
                # Fallback: return hypotheses with default scores
                if self.verbose:
                    print(f"閳跨媴绗? Analysis failed, using default ranking")
                ranked = [
                    RankedHypothesis(
                        hypothesis=h,
                        score=0.5,
                        evidence="Analysis failed - default score",
                        recommendation="Investigate this hypothesis",
                        hypothesis_type="unranked"
                    )
                    for h in hypotheses
                ]
            
            # Step 5: Generate recommendations
            recommendations = self._generate_recommendations(ranked)
            
            return AnalysisResult(
                hypotheses=ranked,
                recommendations=recommendations,
                raw_analysis=raw_results,
                success=True
            )
            
        except Exception as e:
            if self.verbose:
                print(f"閴?Analysis error: {e}")
            return AnalysisResult(
                hypotheses=[],
                recommendations=[],
                success=False,
                error=str(e)
            )
    
    def _generate_hypotheses(
        self,
        code: str,
        metrics: Dict[str, Any],
        feature_importance: Optional[Dict[str, float]] = None
    ) -> List[str]:
        """Generate hypotheses about why the code achieved its performance"""
        
        # Build prompt
        prompt = f"""Analyze this ML code and its performance metrics.
Generate {self.config.max_hypotheses} hypotheses about why it achieved this performance.

TASK: {self.task_description}
METRIC: {self.metric_name} = {metrics.get('combined_score', 'N/A')}

ADDITIONAL METRICS:
{json.dumps({k: v for k, v in metrics.items() if k != 'combined_score'}, indent=2)}

CODE (excerpt):
```python
{code[:3000]}
```
"""
        
        if feature_importance:
            top_features = sorted(
                feature_importance.items(), 
                key=lambda x: -x[1]
            )[:10]
            prompt += f"""
TOP FEATURES BY IMPORTANCE:
{json.dumps(dict(top_features), indent=2)}
"""
        
        prompt += """
Generate hypotheses about:
1. Why the model achieves this level of performance
2. What might be limiting further improvement
3. Potential issues or opportunities

Return as JSON array of strings (hypotheses only, no explanations):
["hypothesis 1", "hypothesis 2", ...]
"""
        
        try:
            response = self._call_llm(prompt)
            
            # Parse JSON response
            if response:
                # Find JSON array in response
                start = response.find('[')
                end = response.rfind(']') + 1
                if start != -1 and end > start:
                    hypotheses = json.loads(response[start:end])
                    if isinstance(hypotheses, list):
                        return hypotheses[:self.config.max_hypotheses]
            
            return []
            
        except Exception as e:
            if self.verbose:
                print(f"閴?Error generating hypotheses: {e}")
            return []
    
    def _generate_analysis_code(
        self,
        hypotheses: List[str],
        metrics: Dict[str, Any],
        feature_importance: Optional[Dict[str, float]] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate Python code to score each hypothesis based on evidence"""
        
        prompt = f"""Generate Python code to analyze and SCORE each hypothesis.

TASK: {self.task_description}

METRICS AVAILABLE:
{json.dumps(metrics, indent=2)}

HYPOTHESES TO SCORE:
{json.dumps(hypotheses, indent=2)}
"""
        
        if feature_importance:
            prompt += f"""
FEATURE IMPORTANCE (top 10):
{json.dumps(dict(sorted(feature_importance.items(), key=lambda x: -x[1])[:10]), indent=2)}
"""
        
        prompt += """
Generate Python code that:
1. Analyzes the available metrics to score each hypothesis
2. Assigns a score from 0.0 to 1.0 based on evidence strength
3. Provides evidence string explaining the score
4. Outputs JSON to stdout with format:
   {
     "scores": [
       {"hypothesis": "...", "score": 0.85, "evidence": "...", "recommendation": "..."},
       ...
     ]
   }

REQUIREMENTS:
- Use ONLY the metrics provided (no external data)
- Score based on how well the metrics support each hypothesis
- Higher score = stronger evidence
- Include actionable recommendations
- Output MUST be valid JSON

Return ONLY the Python code, no explanations.
```python
"""
        
        try:
            response = self._call_llm(prompt)
            
            if response:
                # Extract code from markdown
                if '```python' in response:
                    start = response.find('```python') + 9
                    end = response.find('```', start)
                    if end != -1:
                        return response[start:end].strip()
                elif '```' in response:
                    start = response.find('```') + 3
                    end = response.find('```', start)
                    if end != -1:
                        return response[start:end].strip()
                return response.strip()
            
            # Fallback: simple analysis code
            return self._get_fallback_analysis_code(hypotheses, metrics)
            
        except Exception as e:
            if self.verbose:
                print(f"閴?Error generating analysis code: {e}")
            return self._get_fallback_analysis_code(hypotheses, metrics)
    
    def _get_fallback_analysis_code(
        self, 
        hypotheses: List[str], 
        metrics: Dict[str, Any]
    ) -> str:
        """Fallback analysis code if LLM fails"""
        return f'''
import json

# Fallback analysis - assign default scores
hypotheses = {json.dumps(hypotheses)}
metrics = {json.dumps(metrics)}

scores = []
for i, h in enumerate(hypotheses):
    scores.append({{
        "hypothesis": h,
        "score": 0.5,  # Default score
        "evidence": "Default analysis - LLM generation failed",
        "recommendation": "Investigate this hypothesis manually"
    }})

print(json.dumps({{"scores": scores}}, indent=2))
'''
    
    def _rank_hypotheses(
        self,
        hypotheses: List[str],
        analysis_results: Dict[str, Any]
    ) -> List[RankedHypothesis]:
        """Rank hypotheses based on analysis results"""
        
        ranked = []
        
        scores_data = analysis_results.get('scores', [])
        
        # Create lookup by hypothesis text
        score_lookup = {
            s.get('hypothesis', ''): s 
            for s in scores_data
        }
        
        for h in hypotheses:
            score_data = score_lookup.get(h, {})
            
            ranked.append(RankedHypothesis(
                hypothesis=h,
                score=float(score_data.get('score', 0.5)),
                evidence=score_data.get('evidence', 'No evidence provided'),
                recommendation=score_data.get('recommendation', 'No recommendation'),
                hypothesis_type=score_data.get('type', 'general')
            ))
        
        # Sort by score (highest first)
        ranked.sort(key=lambda x: -x.score)
        
        return ranked
    
    def _generate_recommendations(
        self,
        ranked_hypotheses: List[RankedHypothesis]
    ) -> List[str]:
        """Generate actionable recommendations from ranked hypotheses"""
        
        recommendations = []
        
        for h in ranked_hypotheses[:3]:  # Top 3 hypotheses
            if h.score >= 0.7:
                prefix = "HIGH PRIORITY"
            elif h.score >= 0.5:
                prefix = "MEDIUM PRIORITY"
            else:
                prefix = "LOW PRIORITY"
            
            recommendations.append(f"[{prefix}] {h.recommendation}")
        
        return recommendations
    
    def _call_llm(self, prompt: str) -> Optional[str]:
        """Call LLM API"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': self.model,
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 32000,  # No restrictive limit
                'temperature': self.config.llm_temperature
            }
            
            response = requests.post(
                f'{self.api_base}/chat/completions',
                headers=headers,
                json=payload,
                timeout=120
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'choices' in data and len(data['choices']) > 0:
                    return data['choices'][0]['message']['content'].strip()
            
            if self.verbose:
                print(f"閴?LLM call failed: {response.status_code}")
            return None
            
        except Exception as e:
            if self.verbose:
                print(f"閴?LLM error: {e}")
            return None
    
    def format_for_mutation_prompt(
        self,
        analysis_result: AnalysisResult
    ) -> str:
        """Format analysis result for inclusion in mutation prompt"""
        
        if not analysis_result.success or not analysis_result.hypotheses:
            return ""
        
        lines = [
            "",
            "閳? * 60,
            "棣冩暕 KOSMOS ANALYSIS (Evidence-Based)",
            "閳? * 60,
            "",
            "RANKED HYPOTHESES (by evidence strength):",
        ]
        
        for i, h in enumerate(analysis_result.hypotheses[:5], 1):
            confidence = "HIGH" if h.score >= 0.7 else "MED" if h.score >= 0.5 else "LOW"
            lines.append(f"")
            lines.append(f"{i}. [{confidence} {h.score:.2f}] {h.hypothesis}")
            lines.append(f"   Evidence: {h.evidence[:100]}")
            lines.append(f"   閳?{h.recommendation}")
        
        if analysis_result.recommendations:
            lines.append("")
            lines.append("TOP RECOMMENDATIONS:")
            for rec in analysis_result.recommendations[:3]:
                lines.append(f"閳?{rec}")
        
        lines.append("")
        lines.append("Focus on HIGH-ranked hypotheses first!")
        lines.append("閳? * 60)
        
        return "\n".join(lines)


