"""
Kaggle Technique Analyzer.
Uses LLM to extract research ideas from Kaggle notebooks and discussions.

This module provides:
1. KaggleTechniqueAnalyzer - Extract techniques from code/discussions
2. ExtractedTechnique - Dataclass for extracted technique info
3. Integration with ResearchIdea format

Usage:
    analyzer = KaggleTechniqueAnalyzer(llm_client)
    
    # Analyze notebook code
    techniques = analyzer.analyze_notebook(code, title, votes)
    
    # Analyze discussion
    techniques = analyzer.analyze_discussion(content, title, votes)
    
    # Convert to research ideas
    for tech in techniques:
        idea = tech.to_research_idea()
"""

import re
import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class ExtractedTechnique:
    """A technique extracted from Kaggle content."""
    name: str
    category: str  # 'architecture', 'loss_function', 'feature_engineering', 'training_strategy', 'ensemble', 'preprocessing'
    description: str
    code_snippet: Optional[str]
    source: str  # notebook slug or discussion id
    source_url: str
    votes: int
    confidence: float = 0.5  # 0.0 to 1.0
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'category': self.category,
            'description': self.description,
            'code_snippet': self.code_snippet,
            'source': self.source,
            'source_url': self.source_url,
            'votes': self.votes,
            'confidence': self.confidence,
        }
    
    def to_research_idea_dict(self) -> dict:
        """Convert to ResearchIdea-compatible dictionary."""
        return {
            'id': f"kaggle_{self.name.lower().replace(' ', '_').replace('-', '_')[:30]}",
            'name': self.name,
            'category': self.category.replace('_', ' ').title(),
            'difficulty': 'medium',  # Default
            'expected_f1_gain': f"Kaggle-validated ({self.votes} votes)",
            'summary': self.description[:100] + '...' if len(self.description) > 100 else self.description,
            'key_insight': self.description,
            'implementation_steps': [
                f"Based on Kaggle notebook/discussion: {self.source}",
                f"Source URL: {self.source_url}",
                "Review the code snippet below for implementation details",
            ],
            'code_snippet': self.code_snippet,
            'references': [f"Kaggle: {self.source_url}"],
        }
    
    def __repr__(self) -> str:
        return f"ExtractedTechnique({self.name!r}, category={self.category!r}, votes={self.votes})"


class KaggleTechniqueAnalyzer:
    """
    Extract techniques from Kaggle notebooks and discussions.
    
    Uses a combination of:
    1. Rule-based pattern matching (fast, no API calls)
    2. LLM analysis (detailed, requires API)
    
    Example:
        ```python
        from ea.llm import LLMClient
        
        llm = LLMClient(model_names=['gpt-4'])
        analyzer = KaggleTechniqueAnalyzer(llm_client=llm)
        
        # Analyze notebook
        techniques = analyzer.analyze_notebook(
            code=notebook_code,
            notebook_title="Top Scoring CAFA Solution",
            votes=150,
            source_url="https://kaggle.com/..."
        )
        
        for tech in techniques:
            print(f"Found: {tech.name} ({tech.category})")
            print(f"  {tech.description[:100]}...")
        ```
    """
    
    # Common ML technique patterns
    TECHNIQUE_PATTERNS = {
        # Loss Functions
        'Focal Loss': {
            'patterns': [r'class.*FocalLoss', r'focal.*loss', r'gamma.*alpha.*loss'],
            'category': 'loss_function',
            'description': 'Focal Loss for handling class imbalance, down-weights easy examples.'
        },
        'Label Smoothing': {
            'patterns': [r'label_smooth', r'smoothing\s*=\s*0\.\d', r'LabelSmoothingLoss'],
            'category': 'loss_function',
            'description': 'Label smoothing to prevent overconfident predictions and improve generalization.'
        },
        'Contrastive Loss': {
            'patterns': [r'ContrastiveLoss', r'InfoNCE', r'triplet.*loss', r'cosine.*similarity.*loss'],
            'category': 'loss_function',
            'description': 'Contrastive learning loss for learning discriminative representations.'
        },
        
        # Training Strategies
        'Mixup Augmentation': {
            'patterns': [r'mixup|MixUp', r'lambda.*beta.*distribution', r'mixed.*labels'],
            'category': 'training_strategy',
            'description': 'Mixup data augmentation by interpolating samples and labels.'
        },
        'Gradient Accumulation': {
            'patterns': [r'accumulation_steps', r'gradient.*accum', r'accum.*grad'],
            'category': 'training_strategy',
            'description': 'Gradient accumulation for training with effectively larger batch sizes.'
        },
        'Cosine Annealing': {
            'patterns': [r'CosineAnnealing', r'cosine.*schedule', r'T_max'],
            'category': 'training_strategy',
            'description': 'Cosine annealing learning rate schedule for smooth convergence.'
        },
        'Warmup Schedule': {
            'patterns': [r'warmup', r'linear.*warmup', r'warmup_steps'],
            'category': 'training_strategy',
            'description': 'Learning rate warmup to stabilize early training.'
        },
        'Early Stopping': {
            'patterns': [r'EarlyStopping', r'early_stop', r'patience\s*='],
            'category': 'training_strategy',
            'description': 'Early stopping to prevent overfitting.'
        },
        
        # Architecture Components
        'Multi-Head Attention': {
            'patterns': [r'MultiheadAttention', r'num_heads', r'self.*attention'],
            'category': 'architecture',
            'description': 'Multi-head self-attention mechanism for capturing dependencies.'
        },
        'Residual Connection': {
            'patterns': [r'x\s*\+\s*', r'residual', r'skip.*connection', r'ResNet'],
            'category': 'architecture',
            'description': 'Residual connections for deeper networks and gradient flow.'
        },
        'Layer Normalization': {
            'patterns': [r'LayerNorm', r'layer.*norm', r'nn\.LayerNorm'],
            'category': 'architecture',
            'description': 'Layer normalization for training stability.'
        },
        'Dropout Regularization': {
            'patterns': [r'nn\.Dropout', r'dropout.*rate', r'Dropout\('],
            'category': 'architecture',
            'description': 'Dropout for regularization and preventing overfitting.'
        },
        'Batch Normalization': {
            'patterns': [r'BatchNorm', r'nn\.BatchNorm', r'batch.*norm'],
            'category': 'architecture',
            'description': 'Batch normalization for faster training and regularization.'
        },
        
        # Ensemble Methods
        'Cross-Validation': {
            'patterns': [r'KFold', r'cross.*val', r'n_splits', r'StratifiedKFold'],
            'category': 'ensemble',
            'description': 'K-fold cross-validation for robust model evaluation.'
        },
        'Multi-Seed Ensemble': {
            'patterns': [r'seed.*\[.*\]', r'random.*seeds', r'ensemble.*seed'],
            'category': 'ensemble',
            'description': 'Training with multiple random seeds and averaging predictions.'
        },
        'Model Stacking': {
            'patterns': [r'stacking', r'meta.*model', r'blend.*prediction'],
            'category': 'ensemble',
            'description': 'Stacking multiple models with a meta-learner.'
        },
        
        # Feature Engineering
        'Target Encoding': {
            'patterns': [r'TargetEncoder', r'target.*encoding', r'mean.*encoding'],
            'category': 'feature_engineering',
            'description': 'Target encoding for categorical features.'
        },
        'Feature Scaling': {
            'patterns': [r'StandardScaler', r'MinMaxScaler', r'RobustScaler'],
            'category': 'preprocessing',
            'description': 'Feature scaling for numerical stability.'
        },
        
        # Domain-Specific (Protein/Biology)
        'ESM-2 Embeddings': {
            'patterns': [r'esm2', r'ESM.*embed', r'protein.*language.*model'],
            'category': 'feature_engineering',
            'description': 'Using ESM-2 pre-trained protein embeddings as features.'
        },
        'GO Hierarchy': {
            'patterns': [r'GO.*hierarchy', r'go.*basic.*obo', r'ontology.*graph'],
            'category': 'architecture',
            'description': 'Leveraging Gene Ontology hierarchy structure.'
        },
        'IA Weighting': {
            'patterns': [r'IA.*weight', r'information.*accretion', r'ia_weights'],
            'category': 'loss_function',
            'description': 'Information Accretion weighting for GO term specificity.'
        },
    }
    
    def __init__(self, llm_client=None, use_llm: bool = True):
        """
        Initialize analyzer.
        
        Args:
            llm_client: LLM client for detailed analysis (optional)
            use_llm: Whether to use LLM for analysis (requires llm_client)
        """
        self.llm = llm_client
        self.use_llm = use_llm and llm_client is not None
        
        if self.use_llm:
            logger.info("鉁?KaggleTechniqueAnalyzer initialized with LLM support")
        else:
            logger.info("馃摑 KaggleTechniqueAnalyzer initialized (rule-based only)")
    
    def analyze_notebook(
        self,
        code: str,
        notebook_title: str,
        votes: int,
        source_url: str = ''
    ) -> List[ExtractedTechnique]:
        """
        Extract techniques from notebook code.
        
        Args:
            code: Notebook Python code
            notebook_title: Notebook title for context
            votes: Vote count (proxy for quality)
            source_url: URL of the notebook
        
        Returns:
            List of extracted techniques
        """
        techniques = []
        
        # Step 1: Rule-based extraction (fast)
        rule_based = self._rule_based_extraction(code, notebook_title, votes, source_url)
        techniques.extend(rule_based)
        
        # Step 2: LLM-based extraction (detailed)
        if self.use_llm and len(code) > 100:
            llm_based = self._llm_notebook_analysis(code, notebook_title, votes, source_url)
            
            # Merge, avoiding duplicates
            existing_names = {t.name.lower() for t in techniques}
            for t in llm_based:
                if t.name.lower() not in existing_names:
                    techniques.append(t)
                    existing_names.add(t.name.lower())
        
        logger.info(f"馃搳 Extracted {len(techniques)} techniques from '{notebook_title}'")
        return techniques
    
    def analyze_discussion(
        self,
        content: str,
        title: str,
        votes: int,
        source_url: str = ''
    ) -> List[ExtractedTechnique]:
        """
        Extract insights from discussion thread.
        
        Args:
            content: Discussion content text
            title: Discussion title
            votes: Vote count
            source_url: URL of the discussion
        
        Returns:
            List of extracted techniques
        """
        if not content:
            return []
        
        techniques = []
        
        # Rule-based extraction on discussion text
        rule_based = self._rule_based_extraction(content, title, votes, source_url)
        techniques.extend(rule_based)
        
        # LLM analysis for discussions
        if self.use_llm:
            llm_based = self._llm_discussion_analysis(content, title, votes, source_url)
            
            existing_names = {t.name.lower() for t in techniques}
            for t in llm_based:
                if t.name.lower() not in existing_names:
                    techniques.append(t)
        
        logger.info(f"馃挰 Extracted {len(techniques)} insights from discussion '{title}'")
        return techniques
    
    def _rule_based_extraction(
        self,
        text: str,
        source_name: str,
        votes: int,
        source_url: str
    ) -> List[ExtractedTechnique]:
        """Simple rule-based technique extraction using patterns."""
        techniques = []
        
        for name, info in self.TECHNIQUE_PATTERNS.items():
            for pattern in info['patterns']:
                if re.search(pattern, text, re.IGNORECASE):
                    # Extract code snippet around the match
                    match = re.search(
                        f'(.{{0,300}}{pattern}.{{0,300}})',
                        text,
                        re.IGNORECASE | re.DOTALL
                    )
                    snippet = match.group(1).strip() if match else None
                    
                    # Clean up snippet
                    if snippet:
                        snippet = self._clean_code_snippet(snippet)
                    
                    techniques.append(ExtractedTechnique(
                        name=name,
                        category=info['category'],
                        description=info['description'],
                        code_snippet=snippet,
                        source=source_name,
                        source_url=source_url,
                        votes=votes,
                        confidence=0.7  # Rule-based has decent confidence
                    ))
                    break  # Only add once per technique
        
        return techniques
    
    def _clean_code_snippet(self, snippet: str) -> str:
        """Clean and format code snippet."""
        # Remove excessive whitespace
        lines = snippet.split('\n')
        lines = [line.rstrip() for line in lines if line.strip()]
        
        # Limit length
        if len(lines) > 15:
            lines = lines[:15] + ['# ... (truncated)']
        
        return '\n'.join(lines)
    
    def _llm_notebook_analysis(
        self,
        code: str,
        title: str,
        votes: int,
        source_url: str
    ) -> List[ExtractedTechnique]:
        """Use LLM to analyze notebook code."""
        if not self.llm:
            return []
        
        # Truncate code for LLM context
        code_truncated = code[:15000] if len(code) > 15000 else code
        
        prompt = f'''Analyze this Kaggle notebook code and extract key ML/DL techniques.

NOTEBOOK TITLE: {title}
VOTES: {votes}

CODE:
```python
{code_truncated}
```

For EACH distinct technique found, provide:
1. name: Short descriptive name
2. category: One of [architecture, loss_function, feature_engineering, training_strategy, ensemble, preprocessing]
3. description: 2-3 sentence explanation of what it does and why it works
4. code_snippet: The most relevant code (max 15 lines)

Focus on techniques that contribute to model performance.
Skip basic imports and boilerplate.

Return as JSON array:
[{{"name": "...", "category": "...", "description": "...", "code_snippet": "..."}}]

Return ONLY the JSON array, no other text.
'''
        
        try:
            response = self.llm.query(prompt)
            return self._parse_llm_response(response, title, votes, source_url)
        except Exception as e:
            logger.error(f"LLM notebook analysis failed: {e}")
            return []
    
    def _llm_discussion_analysis(
        self,
        content: str,
        title: str,
        votes: int,
        source_url: str
    ) -> List[ExtractedTechnique]:
        """Use LLM to analyze discussion content."""
        if not self.llm:
            return []
        
        # Truncate content
        content_truncated = content[:8000] if len(content) > 8000 else content
        
        prompt = f'''Analyze this Kaggle discussion and extract actionable ML insights.

DISCUSSION TITLE: {title}
VOTES: {votes}

CONTENT:
{content_truncated}

Extract practical techniques or insights that could improve model performance.
For each insight, provide:
1. name: Short descriptive name
2. category: One of [architecture, loss_function, feature_engineering, training_strategy, ensemble, preprocessing, insight]
3. description: 2-3 sentence explanation
4. code_snippet: Example code if mentioned (or null)

Return as JSON array:
[{{"name": "...", "category": "...", "description": "...", "code_snippet": null}}]

Return ONLY the JSON array, no other text.
'''
        
        try:
            response = self.llm.query(prompt)
            return self._parse_llm_response(response, title, votes, source_url)
        except Exception as e:
            logger.error(f"LLM discussion analysis failed: {e}")
            return []
    
    def _parse_llm_response(
        self,
        response: str,
        source: str,
        votes: int,
        source_url: str
    ) -> List[ExtractedTechnique]:
        """Parse LLM JSON response into techniques."""
        try:
            # Find JSON array in response
            start = response.find('[')
            end = response.rfind(']') + 1
            if start == -1 or end == 0:
                logger.warning("No JSON array found in LLM response")
                return []
            
            data = json.loads(response[start:end])
            
            techniques = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                
                name = item.get('name', '')
                if not name:
                    continue
                
                techniques.append(ExtractedTechnique(
                    name=name,
                    category=item.get('category', 'other'),
                    description=item.get('description', ''),
                    code_snippet=item.get('code_snippet'),
                    source=source,
                    source_url=source_url,
                    votes=votes,
                    confidence=0.8  # LLM has higher confidence
                ))
            
            return techniques
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return []
    
    def get_top_techniques(
        self,
        techniques: List[ExtractedTechnique],
        n: int = 10
    ) -> List[ExtractedTechnique]:
        """
        Get top N techniques by votes and confidence.
        
        Args:
            techniques: List of extracted techniques
            n: Number of top techniques to return
        
        Returns:
            Sorted list of top techniques
        """
        # Score = votes * confidence
        scored = [(t, t.votes * t.confidence) for t in techniques]
        scored.sort(key=lambda x: x[1], reverse=True)
        
        return [t for t, _ in scored[:n]]


# Convenience function
def get_technique_analyzer(llm_client=None) -> KaggleTechniqueAnalyzer:
    """Get a KaggleTechniqueAnalyzer instance."""
    return KaggleTechniqueAnalyzer(llm_client=llm_client)


if __name__ == "__main__":
    # Test the analyzer
    logging.basicConfig(level=logging.INFO)
    
    print("\n=== Testing Kaggle Technique Analyzer ===\n")
    
    # Test code
    test_code = '''
import torch
import torch.nn as nn
import numpy as np
from torch.optim.lr_scheduler import CosineAnnealingLR

class FocalLoss(nn.Module):
    def __init__(self, alpha=0.75, gamma=2.0):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma
    
    def forward(self, logits, targets):
        bce = F.binary_cross_entropy_with_logits(logits, targets, reduction='none')
        pt = torch.exp(-bce)
        focal_weight = self.alpha * (1 - pt) ** self.gamma
        return (focal_weight * bce).mean()

class ResidualBlock(nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(dim, dim),
            nn.LayerNorm(dim),
            nn.ReLU(),
            nn.Dropout(0.3)
        )
    
    def forward(self, x):
        return x + self.net(x)  # Residual connection

# Training with cosine annealing
optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
scheduler = CosineAnnealingLR(optimizer, T_max=50)

# Multi-seed ensemble
SEEDS = [42, 2023, 777, 1337, 999]
'''
    
    analyzer = KaggleTechniqueAnalyzer(llm_client=None)
    
    techniques = analyzer.analyze_notebook(
        code=test_code,
        notebook_title="Test Notebook",
        votes=100,
        source_url="https://kaggle.com/test"
    )
    
    print(f"Found {len(techniques)} techniques:\n")
    for i, tech in enumerate(techniques, 1):
        print(f"{i}. {tech.name} ({tech.category})")
        print(f"   {tech.description}")
        if tech.code_snippet:
            print(f"   Code: {tech.code_snippet[:100]}...")
        print()

