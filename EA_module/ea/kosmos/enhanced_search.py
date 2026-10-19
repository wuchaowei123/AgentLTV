"""
Enhanced ArXiv Search with LLM-based Method Extraction

The original ArxivSearch only extracts paper titles and abstracts.
This enhanced version uses an LLM to extract:
1. Specific methods/techniques mentioned in the paper
2. Key innovations and their implementation details
3. Code snippets or pseudocode when available
4. Performance improvements claimed

This provides actionable information for the evolution system.
"""

import re
import time
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

import requests

logger = logging.getLogger(__name__)


@dataclass
class ExtractedMethod:
    """A specific method/technique extracted from a paper"""
    name: str
    category: str  # 'architecture', 'loss_function', 'training', 'feature_engineering'
    description: str
    key_innovation: str
    implementation_hint: Optional[str] = None
    code_snippet: Optional[str] = None
    expected_improvement: Optional[str] = None
    paper_title: Optional[str] = None
    paper_url: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'category': self.category,
            'description': self.description,
            'key_innovation': self.key_innovation,
            'implementation_hint': self.implementation_hint,
            'code_snippet': self.code_snippet,
            'expected_improvement': self.expected_improvement,
            'paper_title': self.paper_title,
            'paper_url': self.paper_url,
        }


class EnhancedArxivSearch:
    """
    Enhanced ArXiv search that extracts specific methods from papers.
    
    Two modes:
    1. Without LLM: Uses regex/heuristics to extract method names
    2. With LLM: Uses LLM to deeply analyze abstracts and extract methods
    """
    
    ARXIV_API_URL = "https://export.arxiv.org/api/query"
    
    # Rate limiting
    _last_request_time = 0.0
    _min_request_interval = 3.0
    
    # Common CTR/ML method patterns to look for
    METHOD_PATTERNS = [
        # Architectures
        (r'\b(Transformer|BERT|GPT|T5|RoBERTa)\b', 'architecture'),
        (r'\b(attention\s+mechanism|self-attention|multi-head\s+attention)\b', 'architecture'),
        (r'\b(GRU|LSTM|RNN|BiLSTM)\b', 'architecture'),
        (r'\b(DIN|DIEN|DHAN|BST|SASRec|BERT4Rec)\b', 'architecture'),
        (r'\b(Two-Tower|two\s+tower|dual\s+encoder)\b', 'architecture'),
        (r'\b(GNN|Graph\s+Neural\s+Network|GAT|GCN)\b', 'architecture'),
        (r'\b(MIND|ComiRec|DMIN|multi-interest)\b', 'architecture'),
        (r'\b(DCN|DeepFM|Wide\s*&?\s*Deep|xDeepFM)\b', 'architecture'),
        
        # Loss functions
        (r'\b(Focal\s+Loss|focal\s+loss)\b', 'loss_function'),
        (r'\b(BCE|Binary\s+Cross\s*-?\s*Entropy)\b', 'loss_function'),
        (r'\b(Contrastive\s+Loss|InfoNCE|NT-Xent)\b', 'loss_function'),
        (r'\b(Triplet\s+Loss|margin\s+loss)\b', 'loss_function'),
        (r'\b(Cost-Sensitive|cost\s+sensitive)\b', 'loss_function'),
        
        # Training strategies
        (r'\b(Knowledge\s+Distillation|distillation)\b', 'training'),
        (r'\b(Contrastive\s+Learning|self-supervised)\b', 'training'),
        (r'\b(Meta\s*-?\s*Learning|MAML|few-shot)\b', 'training'),
        (r'\b(Curriculum\s+Learning)\b', 'training'),
        (r'\b(Mutual\s+Learning|peer\s+learning)\b', 'training'),
        (r'\b(Pre-training|fine-tuning|transfer\s+learning)\b', 'training'),
        
        # Feature engineering
        (r'\b(Feature\s+Cross|feature\s+interaction)\b', 'feature_engineering'),
        (r'\b(Embedding|embeddings)\b', 'feature_engineering'),
        (r'\b(AutoFE|automated\s+feature)\b', 'feature_engineering'),
    ]
    
    # Method name to detailed info mapping (curated knowledge)
    KNOWN_METHODS = {
        'DIN': {
            'full_name': 'Deep Interest Network',
            'description': 'Target-aware attention mechanism that dynamically weights historical behaviors relative to the candidate item.',
            'key_innovation': 'Local activation unit that computes attention between target item and each historical item.',
            'implementation_hint': 'Use attention layer: attention(target_emb, history_embs) -> weighted_sum',
        },
        'DIEN': {
            'full_name': 'Deep Interest Evolution Network',
            'description': 'Extends DIN with sequential modeling to capture temporal evolution of interests.',
            'key_innovation': 'GRU-based interest extractor + auxiliary loss for interest evolution.',
            'implementation_hint': 'Add GRU layer after embedding, use auxiliary loss on interest states.',
        },
        'DHAN': {
            'full_name': 'Deep Interest with Hierarchical Attention Network',
            'description': 'Multi-level attention over different hierarchical dimensions (recency, category, etc.).',
            'key_innovation': 'Hierarchical attention at multiple abstraction levels.',
            'implementation_hint': 'Create K attention heads for different hierarchy levels, combine with learnable weights.',
            'expected_improvement': '12-21% AUC improvement over DIN',
        },
        'Transformer': {
            'full_name': 'Transformer Encoder for Sequences',
            'description': 'Self-attention based sequence modeling for capturing long-range dependencies.',
            'key_innovation': 'Multi-head self-attention with positional encoding.',
            'implementation_hint': 'nn.TransformerEncoder with 4-8 heads, 2-3 layers.',
            'expected_improvement': '5-15% improvement on long sequences',
        },
        'MIND': {
            'full_name': 'Multi-Interest Network with Dynamic Routing',
            'description': 'Extracts multiple user interest vectors instead of single representation.',
            'key_innovation': 'Dynamic routing to cluster behaviors into K interest groups.',
            'implementation_hint': 'K interest extraction heads with orthogonality regularization.',
        },
        'Focal Loss': {
            'full_name': 'Focal Loss for Imbalanced Classification',
            'description': 'Down-weights easy negatives to focus on hard examples.',
            'key_innovation': 'Modulating factor (1-p_t)^gamma reduces loss for well-classified examples.',
            'implementation_hint': 'focal_weight = alpha * (1 - pt) ** gamma; loss = focal_weight * bce',
            'code_snippet': '''
class FocalLoss(nn.Module):
    def __init__(self, alpha=0.75, gamma=2.0):
        super().__init__()
        self.alpha, self.gamma = alpha, gamma
    
    def forward(self, logits, targets):
        bce = F.binary_cross_entropy_with_logits(logits, targets, reduction='none')
        pt = torch.exp(-bce)
        focal_weight = self.alpha * (1 - pt) ** self.gamma
        return (focal_weight * bce).mean()
''',
        },
        'Contrastive Learning': {
            'full_name': 'Self-Supervised Contrastive Learning',
            'description': 'Learn representations by maximizing similarity between augmented views.',
            'key_innovation': 'InfoNCE loss with in-batch negatives.',
            'implementation_hint': 'Create augmented views, compute similarity matrix, use cross-entropy.',
            'code_snippet': '''
class ContrastiveLoss(nn.Module):
    def __init__(self, temperature=0.1):
        super().__init__()
        self.temperature = temperature
    
    def forward(self, z1, z2):
        z1 = F.normalize(z1, dim=-1)
        z2 = F.normalize(z2, dim=-1)
        sim = torch.mm(z1, z2.t()) / self.temperature
        labels = torch.arange(z1.size(0), device=z1.device)
        return F.cross_entropy(sim, labels)
''',
        },
        'Two-Tower': {
            'full_name': 'Two-Tower Architecture',
            'description': 'Decoupled user and item encoders for efficient inference.',
            'key_innovation': 'Precompute item embeddings offline, only compute user tower in real-time.',
            'implementation_hint': 'Separate user_tower and item_tower, use dot product similarity.',
            'expected_improvement': 'Sub-10ms inference at scale',
        },
        'Cost-Sensitive': {
            'full_name': 'Cost-Sensitive Learning',
            'description': 'Weight False Negatives higher than False Positives.',
            'key_innovation': 'Asymmetric misclassification costs (FN >> FP).',
            'implementation_hint': 'cost_weight = targets * fn_weight + (1 - targets) * fp_weight',
            'code_snippet': '''
class CostSensitiveLoss(nn.Module):
    def __init__(self, fn_weight=3.0, fp_weight=1.0):
        super().__init__()
        self.fn_weight, self.fp_weight = fn_weight, fp_weight
    
    def forward(self, logits, targets):
        bce = F.binary_cross_entropy_with_logits(logits, targets, reduction='none')
        cost_weight = targets * self.fn_weight + (1 - targets) * self.fp_weight
        return (cost_weight * bce).mean()
''',
        },
    }
    
    def __init__(self, llm_client=None, verbose: bool = True):
        self.llm_client = llm_client
        self.verbose = verbose
    
    def search(
        self,
        query: str,
        max_results: int = 5,
        extract_methods: bool = True
    ) -> List[ExtractedMethod]:
        """
        Search arXiv and extract specific methods from papers.
        
        Args:
            query: Search query
            max_results: Maximum papers to fetch
            extract_methods: Whether to extract methods from abstracts
            
        Returns:
            List of ExtractedMethod objects with actionable information
        """
        if self.verbose:
            logger.info(f"📚 Enhanced arXiv search: {query[:50]}...")
        
        # Fetch papers from arXiv
        papers = self._fetch_arxiv_papers(query, max_results)
        
        if not papers:
            logger.warning("No papers found from arXiv")
            return []
        
        if self.verbose:
            logger.info(f"   Found {len(papers)} papers, extracting methods...")
        
        # Extract methods from papers
        methods = []
        for paper in papers:
            extracted = self._extract_methods_from_paper(paper)
            methods.extend(extracted)
        
        # Deduplicate by method name
        seen = set()
        unique_methods = []
        for m in methods:
            if m.name not in seen:
                seen.add(m.name)
                unique_methods.append(m)
        
        if self.verbose:
            logger.info(f"   Extracted {len(unique_methods)} unique methods")
        
        return unique_methods
    
    def _fetch_arxiv_papers(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Fetch papers from arXiv API"""
        # Build query
        query_words = query.split()[:5]
        arxiv_query = ' '.join(query_words)
        
        params = {
            'search_query': f'all:{arxiv_query}',
            'start': 0,
            'max_results': max_results,
            'sortBy': 'relevance',
            'sortOrder': 'descending'
        }
        
        # Respect rate limiting
        time_since_last = time.time() - EnhancedArxivSearch._last_request_time
        if time_since_last < EnhancedArxivSearch._min_request_interval:
            wait_time = EnhancedArxivSearch._min_request_interval - time_since_last
            time.sleep(wait_time)
        
        try:
            EnhancedArxivSearch._last_request_time = time.time()
            response = requests.get(self.ARXIV_API_URL, params=params, timeout=60)
            response.raise_for_status()
            return self._parse_arxiv_xml(response.text)
        except Exception as e:
            logger.warning(f"arXiv fetch failed: {e}")
            return []
    
    def _parse_arxiv_xml(self, xml_text: str) -> List[Dict[str, Any]]:
        """Parse arXiv XML into paper dicts"""
        import xml.etree.ElementTree as ET
        
        papers = []
        try:
            root = ET.fromstring(xml_text)
            ns = {
                'atom': 'http://www.w3.org/2005/Atom',
                'arxiv': 'http://arxiv.org/schemas/atom'
            }
            
            for entry in root.findall('atom:entry', ns):
                title = entry.find('atom:title', ns)
                summary = entry.find('atom:summary', ns)
                link = entry.find("atom:link[@type='text/html']", ns)
                
                if title is not None and summary is not None:
                    papers.append({
                        'title': title.text.strip().replace('\n', ' '),
                        'abstract': summary.text.strip().replace('\n', ' '),
                        'url': link.get('href') if link is not None else None
                    })
        except Exception as e:
            logger.warning(f"XML parse error: {e}")
        
        return papers
    
    def _extract_methods_from_paper(self, paper: Dict[str, Any]) -> List[ExtractedMethod]:
        """Extract specific methods from a paper's title and abstract"""
        methods = []
        seen_methods = set()  # Track seen method names to avoid duplicates
        text = f"{paper['title']} {paper['abstract']}"
        
        # Method 1: Pattern matching for known method names
        for pattern, category in self.METHOD_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                method_name = match if isinstance(match, str) else match[0]
                method_name = method_name.strip()
                
                # Skip if already seen
                method_key = method_name.lower()
                if method_key in seen_methods:
                    continue
                seen_methods.add(method_key)
                
                # Look up in known methods for detailed info
                known = self._lookup_known_method(method_name)
                if known:
                    methods.append(ExtractedMethod(
                        name=known.get('full_name', method_name),
                        category=category,
                        description=known.get('description', ''),
                        key_innovation=known.get('key_innovation', ''),
                        implementation_hint=known.get('implementation_hint'),
                        code_snippet=known.get('code_snippet'),
                        expected_improvement=known.get('expected_improvement'),
                        paper_title=paper['title'],
                        paper_url=paper['url'],
                    ))
                else:
                    # Create basic entry for unknown method
                    methods.append(ExtractedMethod(
                        name=method_name,
                        category=category,
                        description=self._extract_context(text, method_name),
                        key_innovation=f"Referenced in: {paper['title'][:80]}",
                        paper_title=paper['title'],
                        paper_url=paper['url'],
                    ))
        
        # Method 2: If LLM is available, use it for deeper extraction
        if self.llm_client and len(methods) < 3:
            llm_methods = self._extract_with_llm(paper)
            methods.extend(llm_methods)
        
        return methods
    
    def _lookup_known_method(self, method_name: str) -> Optional[Dict[str, Any]]:
        """Look up method in known methods database"""
        # Normalize name
        name_lower = method_name.lower().strip()
        
        for key, info in self.KNOWN_METHODS.items():
            if key.lower() in name_lower or name_lower in key.lower():
                return info
        
        return None
    
    def _extract_context(self, text: str, method_name: str, window: int = 100) -> str:
        """Extract context around method mention"""
        idx = text.lower().find(method_name.lower())
        if idx == -1:
            return ""
        
        start = max(0, idx - window)
        end = min(len(text), idx + len(method_name) + window)
        context = text[start:end]
        
        # Clean up
        if start > 0:
            context = "..." + context
        if end < len(text):
            context = context + "..."
        
        return context
    
    def _extract_with_llm(self, paper: Dict[str, Any]) -> List[ExtractedMethod]:
        """Use LLM to extract methods from paper (if available)"""
        if not self.llm_client:
            return []
        
        prompt = f"""Analyze this research paper and extract specific ML methods/techniques.

PAPER TITLE: {paper['title']}

ABSTRACT: {paper['abstract']}

Extract any specific methods mentioned. For each method, provide:
1. Method name
2. Category (architecture/loss_function/training/feature_engineering)
3. Brief description (1-2 sentences)
4. Key innovation (what makes it special)
5. Implementation hint (how to implement it)

Format as JSON array:
```json
[
  {{
    "name": "Method Name",
    "category": "architecture",
    "description": "Brief description",
    "key_innovation": "What makes it special",
    "implementation_hint": "How to implement"
  }}
]
```

If no specific methods are mentioned, return empty array: []
"""
        
        try:
            response = self.llm_client.generate(prompt)
            # Parse JSON from response
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                import json
                data = json.loads(json_match.group(1))
                return [
                    ExtractedMethod(
                        name=m['name'],
                        category=m.get('category', 'unknown'),
                        description=m.get('description', ''),
                        key_innovation=m.get('key_innovation', ''),
                        implementation_hint=m.get('implementation_hint'),
                        paper_title=paper['title'],
                        paper_url=paper['url'],
                    )
                    for m in data
                ]
        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}")
        
        return []
    
    def format_for_prompt(self, methods: List[ExtractedMethod]) -> str:
        """Format extracted methods for LLM prompt injection"""
        if not methods:
            return ""
        
        lines = [
            "",
            "═" * 60,
            "📚 EXTRACTED METHODS FROM ARXIV PAPERS",
            "═" * 60,
            "",
        ]
        
        # Group by category
        by_category = {}
        for m in methods:
            cat = m.category or 'other'
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(m)
        
        category_emoji = {
            'architecture': '🏗️',
            'loss_function': '📉',
            'training': '🎯',
            'feature_engineering': '⚙️',
            'other': '📋',
        }
        
        for category, cat_methods in by_category.items():
            emoji = category_emoji.get(category, '📋')
            lines.append(f"\n{emoji} {category.upper().replace('_', ' ')}")
            lines.append("-" * 40)
            
            for m in cat_methods:
                lines.append(f"\n### {m.name}")
                if m.description:
                    lines.append(f"**Description:** {m.description}")
                if m.key_innovation:
                    lines.append(f"**Key Innovation:** {m.key_innovation}")
                if m.implementation_hint:
                    lines.append(f"**Implementation:** {m.implementation_hint}")
                if m.expected_improvement:
                    lines.append(f"**Expected Improvement:** {m.expected_improvement}")
                if m.code_snippet:
                    lines.append(f"\n**Code:**\n```python\n{m.code_snippet.strip()}\n```")
                if m.paper_url:
                    lines.append(f"**Source:** {m.paper_url}")
                lines.append("")
        
        lines.append("═" * 60)
        lines.append("Consider implementing these methods to improve performance!")
        lines.append("═" * 60)
        
        return "\n".join(lines)


class CuratedKnowledgeBase:
    """
    Curated knowledge from deep research on CTR prediction.
    
    This provides reliable, detailed method information that may not
    be extractable from arXiv abstracts alone.
    """
    
    METHODS = [
        ExtractedMethod(
            name="Transformer-Based Sequence Modeling",
            category="architecture",
            description="Replace GRU/LSTM with Transformer encoder for better long-range dependency modeling in user behavior sequences.",
            key_innovation="Self-attention captures non-local dependencies. Positional encoding provides sequence awareness. Multi-head attention enables parallel processing.",
            implementation_hint="Use nn.TransformerEncoder with 4-8 heads, 2-3 layers. Add PositionalEncoding module. Keep embed_dim same as current (48-64).",
            code_snippet='''
class TransformerInterestExtractor(nn.Module):
    def __init__(self, embed_dim=64, num_heads=4, num_layers=2, dropout=0.2):
        super().__init__()
        self.pos_encoding = PositionalEncoding(embed_dim)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embed_dim, nhead=num_heads,
            dim_feedforward=embed_dim * 4, dropout=dropout, batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.layer_norm = nn.LayerNorm(embed_dim)
    
    def forward(self, emb_seq):
        x = self.pos_encoding(emb_seq)
        out = self.transformer(x)
        return self.layer_norm(out)
''',
            expected_improvement="5-15% improvement on long sequences (SASRec, BERT4Rec, BST papers)",
        ),
        ExtractedMethod(
            name="Power Focal Loss",
            category="loss_function",
            description="Enhanced Focal Loss with power term to prevent vanishing gradients on hard examples in imbalanced CTR data.",
            key_innovation="Standard Focal Loss (1-pt)^gamma can cause vanishing gradients. Power term ensures stable optimization.",
            implementation_hint="Replace BCE with PowerFocalLoss. Set alpha=0.75, gamma=2.0, power=1.0. Monitor gradient magnitudes.",
            code_snippet='''
class PowerFocalLoss(nn.Module):
    def __init__(self, alpha=0.75, gamma=2.0, power=1.0):
        super().__init__()
        self.alpha, self.gamma, self.power = alpha, gamma, power
    
    def forward(self, logits, targets):
        bce = F.binary_cross_entropy_with_logits(logits, targets, reduction='none')
        pt = torch.exp(-bce)
        focal_weight = self.alpha * (1 - pt) ** self.gamma
        power_term = (1 - pt) ** self.power + 1e-8
        return (focal_weight * bce / power_term).mean()
''',
            expected_improvement="3-5% F1 improvement over standard Focal Loss",
        ),
        ExtractedMethod(
            name="Cost-Sensitive Learning",
            category="loss_function",
            description="Weight False Negatives (missed clicks) higher than False Positives. In CTR, missing a click is more costly than a false alarm.",
            key_innovation="Asymmetric misclassification costs. FN_weight=3.0 means missed clicks are 3x more costly than false positives.",
            implementation_hint="Combine with Focal Loss. cost_weight = targets * fn_weight + (1 - targets) * 1.0",
            code_snippet='''
class CostSensitiveFocalLoss(nn.Module):
    def __init__(self, alpha=0.75, gamma=2.0, fn_weight=3.0):
        super().__init__()
        self.alpha, self.gamma, self.fn_weight = alpha, gamma, fn_weight
    
    def forward(self, logits, targets):
        bce = F.binary_cross_entropy_with_logits(logits, targets, reduction='none')
        pt = torch.exp(-bce)
        focal_weight = self.alpha * (1 - pt) ** self.gamma
        cost_weight = targets * self.fn_weight + (1 - targets) * 1.0
        return (focal_weight * cost_weight * bce).mean()
''',
            expected_improvement="5-10% F1 improvement through better recall",
        ),
        ExtractedMethod(
            name="Multi-Interest Extraction (MIND/ComiRec)",
            category="architecture",
            description="Extract K orthogonal user interest vectors instead of single representation. Users have diverse preferences that one vector cannot capture.",
            key_innovation="K interest extraction heads with orthogonality regularization ensure diverse interest capture. Target-aware attention aggregates interests.",
            implementation_hint="Create K=4 interest heads. Add orthogonality_loss to training. Use target attention for final aggregation.",
            code_snippet='''
class MultiInterestExtractor(nn.Module):
    def __init__(self, hidden_dim, num_interests=4, dropout=0.2):
        super().__init__()
        self.num_interests = num_interests
        self.interest_heads = nn.ModuleList([
            nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim), nn.ReLU(),
                nn.Dropout(dropout), nn.Linear(hidden_dim, hidden_dim)
            ) for _ in range(num_interests)
        ])
    
    def forward(self, h_seq):
        interests = []
        for head in self.interest_heads:
            pooled = h_seq.mean(dim=1)
            interest = head(pooled)
            interests.append(interest)
        return torch.stack(interests, dim=1)  # (B, K, H)
    
    def orthogonality_loss(self, interests):
        K = interests.size(1)
        interests_norm = F.normalize(interests, dim=-1)
        sim = torch.bmm(interests_norm, interests_norm.transpose(1, 2))
        identity = torch.eye(K, device=interests.device).unsqueeze(0)
        return ((sim - identity) ** 2).mean() * 0.1
''',
            expected_improvement="5-10% improvement on users with diverse interests (MIND, ComiRec papers)",
        ),
        ExtractedMethod(
            name="Hierarchical Attention (DHAN)",
            category="architecture",
            description="Multi-level attention over different dimensions: recency, category, all items. Captures hierarchical user interest structure.",
            key_innovation="Attends to different hierarchical abstractions simultaneously. Combines level outputs with learnable weights.",
            implementation_hint="Create 3 attention levels: recent (last 3), same-category, all. Combine with MLP.",
            code_snippet='''
class HierarchicalAttention(nn.Module):
    def __init__(self, hidden_dim, num_levels=3, dropout=0.2):
        super().__init__()
        self.level_attentions = nn.ModuleList([
            nn.Sequential(
                nn.Linear(hidden_dim * 2, hidden_dim), nn.ReLU(),
                nn.Dropout(dropout), nn.Linear(hidden_dim, 1)
            ) for _ in range(num_levels)
        ])
        self.combiner = nn.Linear(hidden_dim * num_levels, hidden_dim)
    
    def forward(self, h_seq, target_emb):
        B, L, H = h_seq.size()
        target_exp = target_emb.unsqueeze(1).expand(-1, L, -1)
        
        level_outputs = []
        for attention in self.level_attentions:
            combined = torch.cat([h_seq, target_exp], dim=-1)
            scores = attention(combined).squeeze(-1)
            weights = F.softmax(scores, dim=-1)
            level_out = (h_seq * weights.unsqueeze(-1)).sum(dim=1)
            level_outputs.append(level_out)
        
        return self.combiner(torch.cat(level_outputs, dim=-1))
''',
            expected_improvement="12-21% AUC improvement over DIN (DHAN paper arXiv:2005.12981)",
        ),
        ExtractedMethod(
            name="Contrastive Learning Pre-training",
            category="training",
            description="Add self-supervised contrastive loss for better embeddings. Maximizes similarity between augmented views of same user.",
            key_innovation="InfoNCE loss with sequence augmentation (dropout, mask, reorder). Creates robust representations.",
            implementation_hint="Add contrastive_loss with weight 0.1 to total loss. Create 2 augmented views per sample.",
            code_snippet='''
class ContrastiveLoss(nn.Module):
    def __init__(self, temperature=0.1):
        super().__init__()
        self.temperature = temperature
    
    def forward(self, z1, z2):
        z1 = F.normalize(z1, dim=-1)
        z2 = F.normalize(z2, dim=-1)
        sim = torch.mm(z1, z2.t()) / self.temperature
        labels = torch.arange(z1.size(0), device=z1.device)
        return F.cross_entropy(sim, labels)

def augment_sequence(seq_emb, dropout_rate=0.2):
    mask = torch.rand_like(seq_emb[:, :, 0]) > dropout_rate
    return seq_emb * mask.unsqueeze(-1)
''',
            expected_improvement="3-8% F1 improvement, especially for cold-start users",
        ),
        ExtractedMethod(
            name="F1-Max Threshold Search",
            category="training",
            description="Search for optimal classification threshold on validation set. Deep learning outputs are poorly calibrated, optimal threshold is rarely 0.5.",
            key_innovation="Post-training threshold optimization. Search 0.2-0.65 in 0.01 steps to maximize F1.",
            implementation_hint="After training, predict on val set. Search thresholds. Use best threshold at inference.",
            code_snippet='''
def find_optimal_threshold(y_true, y_pred_proba):
    best_f1, best_threshold = 0, 0.5
    for t in np.arange(0.2, 0.65, 0.01):
        y_pred = (y_pred_proba > t).astype(int)
        f1 = f1_score(y_true, y_pred)
        if f1 > best_f1:
            best_f1, best_threshold = f1, t
    return best_threshold, best_f1
''',
            expected_improvement="2-5% F1 improvement with zero training cost",
        ),
        ExtractedMethod(
            name="DNN + LightGBM Hybrid Ensemble",
            category="training",
            description="Combine DNN embeddings with LightGBM for best of both worlds. DNNs excel at sequences, GBMs excel at tabular features.",
            key_innovation="Extract DIEN embeddings as features, combine with original dense features, train LightGBM on combined.",
            implementation_hint="Two-stage: 1) Get DNN embeddings/predictions, 2) Stack with original features for GBM.",
            code_snippet='''
# Two-stage stacking
dnn_embeddings = dien_model.get_embeddings(X)  # (N, embed_dim)
dnn_preds = dien_model.predict(X)  # (N,)

X_combined = np.column_stack([
    X_original_dense,  # Original dense features
    dnn_embeddings,    # DNN learned representations
    dnn_preds,         # DNN prediction as feature
])

lgb_params = {'objective': 'binary', 'metric': 'auc', 'learning_rate': 0.05}
lgb_model = lgb.train(lgb_params, lgb.Dataset(X_combined, y))
''',
            expected_improvement="3-5% F1 improvement through complementary strengths",
        ),
    ]
    
    @classmethod
    def get_all_methods(cls) -> List[ExtractedMethod]:
        """Get all curated methods"""
        return cls.METHODS.copy()
    
    @classmethod
    def get_methods_by_category(cls, category: str) -> List[ExtractedMethod]:
        """Get methods by category"""
        return [m for m in cls.METHODS if m.category == category]


def test_enhanced_search():
    """Test the enhanced search with curated knowledge"""
    print("=" * 70)
    print("ENHANCED ARXIV SEARCH + CURATED KNOWLEDGE TEST")
    print("=" * 70)
    
    search = EnhancedArxivSearch(verbose=True)
    
    # Get arXiv methods
    query = "CTR prediction deep learning attention"
    arxiv_methods = search.search(query, max_results=5)
    print(f"\n📚 ArXiv Methods: {len(arxiv_methods)}")
    
    # Get curated methods
    curated_methods = CuratedKnowledgeBase.get_all_methods()
    print(f"📖 Curated Methods: {len(curated_methods)}")
    
    # Combine (curated first for reliability)
    all_methods = curated_methods + arxiv_methods
    
    print(f"\n✅ Total Methods Available: {len(all_methods)}\n")
    print("-" * 70)
    
    for m in all_methods[:5]:  # Show first 5
        print(f"\n📌 {m.name} [{m.category}]")
        if m.description:
            print(f"   {m.description[:100]}...")
        if m.expected_improvement:
            print(f"   Expected: {m.expected_improvement}")
        if m.code_snippet:
            print(f"   Has Code: Yes")
    
    print("\n" + "=" * 70)
    print("FORMATTED OUTPUT FOR LLM PROMPT:")
    print("=" * 70)
    formatted = search.format_for_prompt(all_methods[:5])
    print(formatted[:4000])
    if len(formatted) > 4000:
        print(f"\n... [{len(formatted) - 4000} more chars]")


if __name__ == "__main__":
    test_enhanced_search()

