"""
LLM-Based Paper Analyzer for Deep Method Extraction

Uses LLM to:
1. Read paper abstracts (or full text if available)
2. Extract specific methods/techniques with implementation details
3. Generate actionable code snippets
4. Identify expected improvements

This provides much richer extraction than simple pattern matching.
"""

import re
import json
import time
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ExtractedTechnique:
    """A technique extracted by LLM from a paper"""
    name: str
    category: str  # architecture, loss_function, training, feature_engineering
    what_it_does: str
    why_it_works: str
    how_to_implement: str
    code_snippet: Optional[str] = None
    expected_improvement: Optional[str] = None
    paper_title: Optional[str] = None
    paper_url: Optional[str] = None
    confidence: float = 0.8
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'category': self.category,
            'what_it_does': self.what_it_does,
            'why_it_works': self.why_it_works,
            'how_to_implement': self.how_to_implement,
            'code_snippet': self.code_snippet,
            'expected_improvement': self.expected_improvement,
            'paper_title': self.paper_title,
            'paper_url': self.paper_url,
            'confidence': self.confidence,
        }


class LLMPaperAnalyzer:
    """
    Uses LLM to deeply analyze papers and extract actionable methods.
    
    The key difference from pattern matching:
    - Pattern matching: "Found 'Transformer' in text" 鈫?lookup predefined info
    - LLM analysis: "Read the paper, understand the method, generate implementation"
    """
    
    # Prompt template for method extraction (GENERIC - works for any ML task)
    EXTRACTION_PROMPT = '''You are an expert ML researcher analyzing a research paper.

TASK DOMAIN: {domain}

PAPER TITLE: {title}

PAPER ABSTRACT:
{abstract}

YOUR TASK:
Extract ALL specific ML methods, techniques, or algorithms mentioned in this paper that could be implemented to improve model performance. For EACH method, provide:

1. **Name**: The method/technique name (e.g., "Transformer Encoder", "Focal Loss", "Contrastive Learning")
2. **Category**: One of:
   - architecture: Neural network architectures, layers, modules
   - loss_function: Loss functions, objectives, regularization terms
   - training: Training strategies, optimization techniques, learning schedules
   - feature_engineering: Feature processing, embedding methods, data augmentation
   - ensemble: Ensemble methods, model combination strategies
   - preprocessing: Data preprocessing, normalization, handling imbalance
3. **What it does**: 1-2 sentences explaining what the method does
4. **Why it works**: The key insight or intuition that makes this method effective
5. **How to implement**: Specific implementation steps (3-5 bullet points)
6. **Code snippet**: Python/PyTorch code implementing the core idea (if possible)
7. **Expected improvement**: Quantified improvement if mentioned (e.g., "5-10% improvement on metric X")

IMPORTANT:
- Extract CONCRETE, IMPLEMENTABLE methods - not vague concepts
- Include specific implementation details (hyperparameters, layer sizes, etc.)
- Focus on methods that could generalize to similar tasks
- If no clear methods are extractable, return empty list

OUTPUT FORMAT (JSON):
```json
[
  {{
    "name": "Method Name",
    "category": "architecture",
    "what_it_does": "Brief description of what it does",
    "why_it_works": "Key insight that makes it effective",
    "how_to_implement": [
      "Step 1: ...",
      "Step 2: ...",
      "Step 3: ..."
    ],
    "code_snippet": "# Python/PyTorch implementation\\nclass MethodName(nn.Module):\\n    ...",
    "expected_improvement": "X% improvement on Y metric"
  }}
]
```

Extract methods now:'''

    # Prompt for generating code from method description (GENERIC)
    CODE_GENERATION_PROMPT = '''You are an expert Python/PyTorch developer.

Generate a complete, working implementation for this ML method:

METHOD NAME: {name}
DESCRIPTION: {description}
KEY INSIGHT: {insight}
TASK CONTEXT: {task_context}

Requirements:
1. Use Python with PyTorch (torch, torch.nn, torch.nn.functional) or scikit-learn as appropriate
2. Include proper class/function structure with docstrings
3. Add comments explaining key parts of the implementation
4. Make it modular and easy to integrate into existing code
5. Include type hints where helpful
6. Handle edge cases appropriately

Generate the code:

```python
'''

    def __init__(self, llm_client=None, verbose: bool = True):
        """
        Initialize the analyzer.
        
        Args:
            llm_client: LLM client with .query() or .generate() method
                       Can be from ea.llm.LLMClient or any compatible client
            verbose: Whether to print progress
        """
        self.llm_client = llm_client
        self.verbose = verbose
        self._cache = {}  # Cache extracted methods
    
    def analyze_paper(
        self,
        title: str,
        abstract: str,
        url: Optional[str] = None,
        domain: str = "machine learning and deep learning"
    ) -> List[ExtractedTechnique]:
        """
        Analyze a paper and extract methods using LLM.
        
        Args:
            title: Paper title
            abstract: Paper abstract (or full text)
            url: Paper URL
            domain: Domain context for better extraction
            
        Returns:
            List of ExtractedTechnique objects
        """
        if not self.llm_client:
            logger.warning("No LLM client provided, cannot analyze paper")
            return []
        
        # Check cache
        cache_key = f"{title[:50]}_{hash(abstract)}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        if self.verbose:
            logger.info(f"馃敩 Analyzing paper: {title[:60]}...")
        
        # Build prompt
        prompt = self.EXTRACTION_PROMPT.format(
            domain=domain,
            title=title,
            abstract=abstract
        )
        
        try:
            # Query LLM
            response = self._query_llm(prompt)
            
            if not response:
                return []
            
            # Parse response
            techniques = self._parse_extraction_response(response, title, url)
            
            # Generate code for methods without code snippets
            for tech in techniques:
                if not tech.code_snippet:
                    tech.code_snippet = self._generate_code(tech)
            
            # Cache results
            self._cache[cache_key] = techniques
            
            if self.verbose:
                logger.info(f"   Extracted {len(techniques)} techniques")
            
            return techniques
            
        except Exception as e:
            logger.warning(f"Error analyzing paper: {e}")
            return []
    
    def _query_llm(self, prompt: str) -> Optional[str]:
        """Query the LLM client"""
        try:
            # Try different LLM client interfaces
            if hasattr(self.llm_client, 'query'):
                # ea.llm.LLMClient style
                response = self.llm_client.query(msg=prompt)
                return response.content if response else None
            elif hasattr(self.llm_client, 'generate'):
                # Simple generate interface
                return self.llm_client.generate(prompt)
            elif hasattr(self.llm_client, 'chat'):
                # OpenAI-style
                response = self.llm_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.choices[0].message.content
            elif callable(self.llm_client):
                # Direct callable
                return self.llm_client(prompt)
            else:
                logger.warning(f"Unknown LLM client type: {type(self.llm_client)}")
                return None
        except Exception as e:
            logger.warning(f"LLM query failed: {e}")
            return None
    
    def _parse_extraction_response(
        self,
        response: str,
        paper_title: str,
        paper_url: Optional[str]
    ) -> List[ExtractedTechnique]:
        """Parse LLM response into ExtractedTechnique objects"""
        techniques = []
        
        # Try to extract JSON from response
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                if isinstance(data, list):
                    for item in data:
                        tech = ExtractedTechnique(
                            name=item.get('name', 'Unknown'),
                            category=item.get('category', 'unknown'),
                            what_it_does=item.get('what_it_does', ''),
                            why_it_works=item.get('why_it_works', ''),
                            how_to_implement='\n'.join(item.get('how_to_implement', [])) if isinstance(item.get('how_to_implement'), list) else item.get('how_to_implement', ''),
                            code_snippet=item.get('code_snippet'),
                            expected_improvement=item.get('expected_improvement'),
                            paper_title=paper_title,
                            paper_url=paper_url,
                        )
                        techniques.append(tech)
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse error: {e}")
        
        # Fallback: try to parse as plain text
        if not techniques:
            techniques = self._parse_plain_text_response(response, paper_title, paper_url)
        
        return techniques
    
    def _parse_plain_text_response(
        self,
        response: str,
        paper_title: str,
        paper_url: Optional[str]
    ) -> List[ExtractedTechnique]:
        """Fallback parser for non-JSON responses"""
        techniques = []
        
        # Look for method sections
        method_pattern = r'\*\*(?:Name|Method):\*\*\s*(.+?)(?=\*\*(?:Name|Method):|$)'
        matches = re.findall(method_pattern, response, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            # Extract fields
            name_match = re.search(r'(?:^|\n)(.+?)(?:\n|$)', match)
            desc_match = re.search(r'\*\*What.*?:\*\*\s*(.+?)(?=\*\*|$)', match, re.DOTALL)
            
            if name_match:
                tech = ExtractedTechnique(
                    name=name_match.group(1).strip(),
                    category='unknown',
                    what_it_does=desc_match.group(1).strip() if desc_match else '',
                    why_it_works='',
                    how_to_implement='',
                    paper_title=paper_title,
                    paper_url=paper_url,
                )
                techniques.append(tech)
        
        return techniques
    
    def _generate_code(self, tech: ExtractedTechnique, task_context: str = "general ML task") -> Optional[str]:
        """Generate code snippet for a technique using LLM"""
        if not self.llm_client:
            return None
        
        prompt = self.CODE_GENERATION_PROMPT.format(
            name=tech.name,
            description=tech.what_it_does,
            insight=tech.why_it_works,
            task_context=task_context
        )
        
        try:
            response = self._query_llm(prompt)
            if response:
                # Extract code from response
                code_match = re.search(r'```python\s*(.*?)\s*```', response, re.DOTALL)
                if code_match:
                    return code_match.group(1).strip()
                # If no code block, try to find class definition
                class_match = re.search(r'(class\s+\w+.*?)(?=\n\n|\Z)', response, re.DOTALL)
                if class_match:
                    return class_match.group(1).strip()
        except Exception as e:
            logger.warning(f"Code generation failed: {e}")
        
        return None
    
    def analyze_multiple_papers(
        self,
        papers: List[Dict[str, Any]],
        domain: str = "CTR prediction"
    ) -> List[ExtractedTechnique]:
        """
        Analyze multiple papers and combine results.
        
        Args:
            papers: List of dicts with 'title', 'abstract', 'url' keys
            domain: Domain context
            
        Returns:
            Combined list of unique techniques
        """
        all_techniques = []
        seen_names = set()
        
        for paper in papers:
            techniques = self.analyze_paper(
                title=paper.get('title', ''),
                abstract=paper.get('abstract', ''),
                url=paper.get('url'),
                domain=domain
            )
            
            for tech in techniques:
                # Deduplicate by name
                name_key = tech.name.lower().strip()
                if name_key not in seen_names:
                    seen_names.add(name_key)
                    all_techniques.append(tech)
            
            # Rate limiting
            time.sleep(1)
        
        return all_techniques
    
    def format_for_prompt(self, techniques: List[ExtractedTechnique]) -> str:
        """Format extracted techniques for LLM prompt injection"""
        if not techniques:
            return ""
        
        lines = [
            "",
            "鈺? * 60,
            "馃敩 LLM-EXTRACTED METHODS FROM RESEARCH PAPERS",
            "鈺? * 60,
            "",
        ]
        
        # Group by category
        by_category = {}
        for tech in techniques:
            cat = tech.category or 'other'
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(tech)
        
        category_emoji = {
            'architecture': '馃彈锔?,
            'loss_function': '馃搲',
            'training': '馃幆',
            'feature_engineering': '鈿欙笍',
            'other': '馃搵',
        }
        
        for category, cat_techs in by_category.items():
            emoji = category_emoji.get(category, '馃搵')
            lines.append(f"\n{emoji} {category.upper().replace('_', ' ')}")
            lines.append("-" * 40)
            
            for tech in cat_techs:
                lines.append(f"\n### {tech.name}")
                if tech.what_it_does:
                    lines.append(f"**What it does:** {tech.what_it_does}")
                if tech.why_it_works:
                    lines.append(f"**Why it works:** {tech.why_it_works}")
                if tech.how_to_implement:
                    lines.append(f"**How to implement:**")
                    lines.append(tech.how_to_implement)
                if tech.expected_improvement:
                    lines.append(f"**Expected improvement:** {tech.expected_improvement}")
                if tech.code_snippet:
                    lines.append(f"\n**Code:**")
                    lines.append(f"```python\n{tech.code_snippet}\n```")
                if tech.paper_url:
                    lines.append(f"**Source:** {tech.paper_url}")
                lines.append("")
        
        lines.append("鈺? * 60)
        lines.append("Implement these methods to improve your model!")
        lines.append("鈺? * 60)
        
        return "\n".join(lines)


# ============================================================================
# Demo with mock LLM
# ============================================================================

class MockLLMClient:
    """Mock LLM client for testing without API calls"""
    
    def generate(self, prompt: str) -> str:
        """Return a mock response"""
        if "Extract methods" in prompt or "EXTRACTION" in prompt.upper():
            return '''Based on the paper, I extracted the following methods:

```json
[
  {
    "name": "Disentangled Self-Attention",
    "category": "architecture",
    "what_it_does": "Separates user behavior representation into multiple disentangled components, each capturing different aspects of user interest.",
    "why_it_works": "By disentangling representations, the model can capture diverse user interests without interference, leading to more accurate predictions.",
    "how_to_implement": [
      "1. Create K attention heads for K interest aspects",
      "2. Apply orthogonality constraint between heads",
      "3. Use separate query projections for each aspect",
      "4. Aggregate with target-aware attention"
    ],
    "code_snippet": "class DisentangledAttention(nn.Module):\\n    def __init__(self, d_model, n_aspects=4):\\n        super().__init__()\\n        self.aspects = nn.ModuleList([\\n            nn.MultiheadAttention(d_model, 4) for _ in range(n_aspects)\\n        ])\\n    \\n    def forward(self, x):\\n        outputs = [attn(x, x, x)[0] for attn in self.aspects]\\n        return torch.stack(outputs, dim=1).mean(dim=1)",
    "expected_improvement": "2-5% AUC improvement over standard attention"
  },
  {
    "name": "Auxiliary Interest Loss",
    "category": "loss_function",
    "what_it_does": "Adds auxiliary supervision to intermediate interest representations to ensure they capture meaningful patterns.",
    "why_it_works": "Direct supervision on interest states prevents gradient vanishing and ensures each interest component is informative.",
    "how_to_implement": [
      "1. Add prediction head on each interest state",
      "2. Compute auxiliary BCE loss",
      "3. Weight auxiliary loss (typically 0.1-0.5)",
      "4. Add to main CTR loss"
    ],
    "code_snippet": "aux_loss = sum(F.binary_cross_entropy_with_logits(\\n    self.aux_head(h), labels) for h in interest_states) * 0.2",
    "expected_improvement": "1-3% F1 improvement"
  }
]
```'''
        elif "Generate" in prompt and "code" in prompt.lower():
            return '''```python
class DisentangledSelfAttention(nn.Module):
    """
    Disentangled Self-Attention for CTR Prediction
    
    Separates user behavior into K disentangled aspects,
    each capturing different interest dimensions.
    """
    def __init__(self, d_model: int, n_aspects: int = 4, n_heads: int = 4, dropout: float = 0.1):
        super().__init__()
        self.n_aspects = n_aspects
        
        # Separate attention for each aspect
        self.aspect_attentions = nn.ModuleList([
            nn.MultiheadAttention(d_model, n_heads, dropout=dropout, batch_first=True)
            for _ in range(n_aspects)
        ])
        
        # Orthogonality projection
        self.ortho_proj = nn.Linear(d_model * n_aspects, d_model)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, seq_len, d_model)
        aspect_outputs = []
        
        for attn in self.aspect_attentions:
            out, _ = attn(x, x, x)
            aspect_outputs.append(out.mean(dim=1))  # Pool sequence
        
        # Concatenate and project
        combined = torch.cat(aspect_outputs, dim=-1)
        return self.ortho_proj(combined)
    
    def orthogonality_loss(self, aspects: List[torch.Tensor]) -> torch.Tensor:
        """Encourage orthogonal aspect representations"""
        stacked = torch.stack(aspects, dim=1)  # (B, K, H)
        stacked = F.normalize(stacked, dim=-1)
        sim = torch.bmm(stacked, stacked.transpose(1, 2))
        identity = torch.eye(self.n_aspects, device=sim.device)
        return ((sim - identity) ** 2).mean()
```'''
        else:
            return "No relevant methods found."


def test_llm_paper_analyzer():
    """Test the LLM paper analyzer"""
    print("=" * 70)
    print("LLM PAPER ANALYZER TEST")
    print("=" * 70)
    
    # Use mock LLM for testing
    mock_llm = MockLLMClient()
    analyzer = LLMPaperAnalyzer(llm_client=mock_llm, verbose=True)
    
    # Test paper
    test_paper = {
        'title': 'Disentangled Self-Attentive Neural Networks for Click-Through Rate Prediction',
        'abstract': '''Click-Through Rate (CTR) prediction is crucial for recommendation systems. 
        We propose a disentangled self-attention mechanism that separates user behavior 
        representations into multiple orthogonal components, each capturing different aspects 
        of user interest. Our method achieves 2-5% AUC improvement over baselines on 
        Criteo and Avazu datasets. We also introduce an auxiliary interest loss to 
        provide direct supervision on intermediate representations.''',
        'url': 'https://arxiv.org/abs/example'
    }
    
    print(f"\n馃搫 Analyzing paper: {test_paper['title'][:60]}...")
    print("-" * 70)
    
    techniques = analyzer.analyze_paper(
        title=test_paper['title'],
        abstract=test_paper['abstract'],
        url=test_paper['url']
    )
    
    print(f"\n鉁?Extracted {len(techniques)} techniques:\n")
    
    for tech in techniques:
        print(f"馃搶 {tech.name} [{tech.category}]")
        print(f"   What: {tech.what_it_does[:80]}...")
        print(f"   Why: {tech.why_it_works[:80]}...")
        if tech.expected_improvement:
            print(f"   Expected: {tech.expected_improvement}")
        if tech.code_snippet:
            print(f"   Code: {len(tech.code_snippet)} chars")
        print()
    
    print("=" * 70)
    print("FORMATTED OUTPUT FOR LLM PROMPT:")
    print("=" * 70)
    formatted = analyzer.format_for_prompt(techniques)
    print(formatted[:3000])
    if len(formatted) > 3000:
        print(f"\n... [{len(formatted) - 3000} more chars]")


if __name__ == "__main__":
    test_llm_paper_analyzer()

