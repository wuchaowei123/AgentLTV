"""
ResearchDirector: LLM-based research direction selector for forced exploration.

When evolution plateaus, this module uses an LLM to intelligently select
the most promising research direction based on:
1. Current best code and architecture
2. Recent failed attempts
3. Performance history
4. Research ideas from deep research (now from research_ideas_pool)
"""

import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Import the new research ideas pool
try:
    from ea.knowledge.research_ideas_pool import (
        RESEARCH_IDEAS,
        ResearchIdea,
        format_for_llm_selection,
        get_idea_by_id,
        get_implementation_prompt,
        get_easy_wins,
        load_task_specific_ideas,  # NEW: Load task-specific ideas
        merge_research_ideas,       # NEW: Merge generic + task-specific
    )
    RESEARCH_POOL_AVAILABLE = True
except ImportError:
    RESEARCH_POOL_AVAILABLE = False
    RESEARCH_IDEAS = []
    
    # Fallback functions if main module not available
    def load_task_specific_ideas(path): return []
    def merge_research_ideas(g, t, p=True): return g + t


@dataclass
class ResearchDirection:
    """A research direction with implementation details."""
    id: int
    name: str
    category: str
    description: str
    implementation_guide: str
    expected_benefit: str
    difficulty: str  # "easy", "medium", "hard"
    prerequisites: List[str]


# Detailed research ideas from deep research
RESEARCH_DIRECTIONS: List[ResearchDirection] = [
    ResearchDirection(
        id=1,
        name="Transformer-Based Sequence Modeling",
        category="Architecture",
        description="Replace GRU-based interest extractor with Transformer encoder using multi-head self-attention.",
        implementation_guide="""
Replace the GRU-based SimpleInterestExtractor with a Transformer encoder:

```python
import torch.nn as nn
import math

class PositionalEncoding(nn.Module):
    def __init__(self, d_model, max_len=100):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer('pe', pe.unsqueeze(0))
    
    def forward(self, x):
        return x + self.pe[:, :x.size(1)]

class TransformerInterestExtractor(nn.Module):
    def __init__(self, embed_dim, num_heads=4, num_layers=2, dropout=0.2):
        super().__init__()
        self.pos_encoding = PositionalEncoding(embed_dim)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embed_dim, 
            nhead=num_heads,
            dim_feedforward=embed_dim * 4,
            dropout=dropout,
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.layer_norm = nn.LayerNorm(embed_dim)
    
    def forward(self, emb_seq):
        x = self.pos_encoding(emb_seq)
        out = self.transformer(x)
        return self.layer_norm(out)
```

Key changes:
1. Replace `SimpleInterestExtractor` with `TransformerInterestExtractor`
2. Use 4-8 attention heads
3. Add positional encoding for sequence position awareness
4. Benefits: Better long-range dependency modeling, parallel processing
""",
        expected_benefit="5-15% improvement in capturing long-range user interest patterns",
        difficulty="medium",
        prerequisites=["Basic PyTorch Transformer knowledge"]
    ),
    
    ResearchDirection(
        id=2,
        name="Enhanced Focal Loss",
        category="Loss Function",
        description="Implement Power Focal Loss to handle class imbalance while avoiding vanishing gradients.",
        implementation_guide="""
Replace standard Focal Loss with Power Focal Loss for better gradient stability:

```python
class PowerFocalLoss(nn.Module):
    '''
    Power Focal Loss: FL with additional power term to prevent vanishing gradients.
    Reference: Recent CTR papers showing FL can suffer from gradient issues.
    '''
    def __init__(self, alpha=0.75, gamma=2.0, power=1.0):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma
        self.power = power  # Additional power term for gradient stability
    
    def forward(self, logits, targets):
        bce = F.binary_cross_entropy_with_logits(logits, targets, reduction='none')
        pt = torch.exp(-bce)
        
        # Standard focal weight
        focal_weight = self.alpha * (1 - pt) ** self.gamma
        
        # Power term to prevent vanishing gradients
        power_term = (1 - pt) ** self.power + 1e-8
        
        loss = focal_weight * bce / power_term
        return loss.mean()
```

Also try Polyhedral Conic Classifier (PCC) loss which showed superiority on Criteo/Avazu:

```python
class PolyhedralConicLoss(nn.Module):
    '''Polyhedral Conic Classifier loss - SOTA for CTR on major benchmarks'''
    def __init__(self, num_cones=4, margin=0.5):
        super().__init__()
        self.num_cones = num_cones
        self.margin = margin
    
    def forward(self, logits, targets):
        # Implementation based on arXiv:2406.03892
        # Creates multiple decision boundaries (cones) for better separation
        pos_mask = targets > 0.5
        neg_mask = ~pos_mask
        
        pos_loss = F.relu(self.margin - logits[pos_mask]).mean() if pos_mask.any() else 0
        neg_loss = F.relu(self.margin + logits[neg_mask]).mean() if neg_mask.any() else 0
        
        return pos_loss + neg_loss
```
""",
        expected_benefit="Better F1 through improved handling of rare positive class",
        difficulty="easy",
        prerequisites=[]
    ),
    
    ResearchDirection(
        id=3,
        name="Multi-Interest Extraction (MIND/ComiRec)",
        category="Architecture",
        description="Extract multiple user interest vectors instead of a single representation.",
        implementation_guide="""
Implement multi-interest extraction to capture diverse user preferences:

```python
class MultiInterestExtractor(nn.Module):
    '''
    Multi-Interest Network: Extracts K different interest vectors.
    Reference: MIND, ComiRec, DMIN
    '''
    def __init__(self, hidden_dim, num_interests=4, dropout=0.2):
        super().__init__()
        self.num_interests = num_interests
        
        # K interest extraction heads
        self.interest_heads = nn.ModuleList([
            nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(hidden_dim, hidden_dim)
            ) for _ in range(num_interests)
        ])
        
        # Orthogonality regularization to ensure diverse interests
        self.ortho_weight = 0.1
    
    def forward(self, h_seq):
        # h_seq: (B, L, H)
        # Extract K interest vectors
        interests = []
        for head in self.interest_heads:
            # Pool sequence and transform
            pooled = h_seq.mean(dim=1)  # (B, H)
            interest = head(pooled)  # (B, H)
            interests.append(interest)
        
        interests = torch.stack(interests, dim=1)  # (B, K, H)
        return interests
    
    def orthogonality_loss(self, interests):
        '''Encourage diverse interests'''
        # interests: (B, K, H)
        K = interests.size(1)
        interests_norm = F.normalize(interests, dim=-1)
        sim_matrix = torch.bmm(interests_norm, interests_norm.transpose(1, 2))  # (B, K, K)
        # Penalize off-diagonal similarities
        identity = torch.eye(K, device=interests.device).unsqueeze(0)
        ortho_loss = ((sim_matrix - identity) ** 2).mean()
        return ortho_loss * self.ortho_weight


class MultiInterestAttention(nn.Module):
    '''Target-aware attention over multiple interests'''
    def __init__(self, hidden_dim, num_interests=4):
        super().__init__()
        self.attention = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1)
        )
    
    def forward(self, interests, target_emb):
        # interests: (B, K, H), target_emb: (B, H)
        K = interests.size(1)
        target_expanded = target_emb.unsqueeze(1).expand(-1, K, -1)  # (B, K, H)
        
        combined = torch.cat([interests, target_expanded], dim=-1)  # (B, K, 2H)
        scores = self.attention(combined).squeeze(-1)  # (B, K)
        weights = F.softmax(scores, dim=-1)  # (B, K)
        
        # Weighted sum of interests
        output = (interests * weights.unsqueeze(-1)).sum(dim=1)  # (B, H)
        return output
```

Integration:
1. Replace single interest vector with MultiInterestExtractor
2. Add MultiInterestAttention for target-aware aggregation
3. Add orthogonality_loss to total loss
""",
        expected_benefit="Captures diverse user preferences, 5-10% improvement on users with varied interests",
        difficulty="medium",
        prerequisites=["Understanding of attention mechanisms"]
    ),
    
    ResearchDirection(
        id=4,
        name="Contrastive Learning Pre-training",
        category="Training Strategy",
        description="Add contrastive loss to learn better user/item embeddings through self-supervision.",
        implementation_guide="""
Add contrastive learning to improve embedding quality:

```python
class ContrastiveLoss(nn.Module):
    '''
    InfoNCE-based contrastive loss for user representation learning.
    Reference: SimCLR, MoCo adapted for recommendation
    '''
    def __init__(self, temperature=0.1):
        super().__init__()
        self.temperature = temperature
    
    def forward(self, z1, z2, labels=None):
        '''
        z1, z2: Two augmented views of the same batch (B, H)
        '''
        z1 = F.normalize(z1, dim=-1)
        z2 = F.normalize(z2, dim=-1)
        
        # Compute similarity matrix
        sim = torch.mm(z1, z2.t()) / self.temperature  # (B, B)
        
        # Positive pairs are on diagonal
        labels = torch.arange(z1.size(0), device=z1.device)
        
        # Cross-entropy loss (treats each row as a classification problem)
        loss = F.cross_entropy(sim, labels)
        return loss


class SequenceAugmentor:
    '''Augmentation strategies for user behavior sequences'''
    
    @staticmethod
    def dropout_augment(seq_emb, dropout_rate=0.2):
        '''Randomly drop some positions'''
        mask = torch.rand_like(seq_emb[:, :, 0]) > dropout_rate
        return seq_emb * mask.unsqueeze(-1)
    
    @staticmethod
    def mask_augment(seq_emb, mask_rate=0.15):
        '''Replace some positions with learnable mask token'''
        mask = torch.rand(seq_emb.size(0), seq_emb.size(1), device=seq_emb.device) < mask_rate
        masked = seq_emb.clone()
        masked[mask] = 0  # Or use learnable mask embedding
        return masked
    
    @staticmethod
    def reorder_augment(seq_emb, max_shuffle=3):
        '''Slightly shuffle sequence order'''
        B, L, H = seq_emb.size()
        shuffled = seq_emb.clone()
        for i in range(B):
            # Swap a few adjacent positions
            for _ in range(max_shuffle):
                pos = torch.randint(0, L-1, (1,)).item()
                shuffled[i, pos], shuffled[i, pos+1] = shuffled[i, pos+1].clone(), shuffled[i, pos].clone()
        return shuffled


# In training loop:
def train_step_with_contrastive(model, batch, contrastive_weight=0.1):
    seq_emb = model.embed(batch['seq_ids'])
    
    # Create two augmented views
    aug1 = SequenceAugmentor.dropout_augment(seq_emb)
    aug2 = SequenceAugmentor.mask_augment(seq_emb)
    
    # Get representations
    z1 = model.extractor(aug1).mean(dim=1)  # Pool to (B, H)
    z2 = model.extractor(aug2).mean(dim=1)
    
    # Contrastive loss
    cl_loss = ContrastiveLoss()(z1, z2)
    
    # Main CTR loss
    logits = model(batch['seq_ids'], batch['target_id'], batch['dense_x'])
    ctr_loss = criterion(logits, batch['label'])
    
    total_loss = ctr_loss + contrastive_weight * cl_loss
    return total_loss
```
""",
        expected_benefit="Better generalization, especially for cold-start users, 3-8% F1 improvement",
        difficulty="medium",
        prerequisites=["Understanding of self-supervised learning"]
    ),
    
    ResearchDirection(
        id=5,
        name="Hierarchical Attention (DHAN)",
        category="Architecture",
        description="Add hierarchical attention over multiple dimensions (category, time, etc.).",
        implementation_guide="""
Implement Deep Interest with Hierarchical Attention Network (DHAN):

```python
class HierarchicalAttention(nn.Module):
    '''
    DHAN: Hierarchical attention over multiple dimensions.
    Reference: arXiv:2005.12981 - achieved 12-21% AUC improvement over DIN
    '''
    def __init__(self, hidden_dim, num_levels=3, dropout=0.2):
        super().__init__()
        self.num_levels = num_levels
        
        # Attention at each hierarchy level
        self.level_attentions = nn.ModuleList([
            nn.Sequential(
                nn.Linear(hidden_dim * 2, hidden_dim),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(hidden_dim, 1)
            ) for _ in range(num_levels)
        ])
        
        # Level combination
        self.level_combiner = nn.Sequential(
            nn.Linear(hidden_dim * num_levels, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim)
        )
    
    def forward(self, h_seq, target_emb, level_masks=None):
        '''
        h_seq: (B, L, H) - sequence hidden states
        target_emb: (B, H) - target item embedding
        level_masks: Optional dict of masks for each hierarchy level
        '''
        B, L, H = h_seq.size()
        target_expanded = target_emb.unsqueeze(1).expand(-1, L, -1)
        
        level_outputs = []
        for level_idx, attention in enumerate(self.level_attentions):
            # Compute attention scores
            combined = torch.cat([h_seq, target_expanded], dim=-1)  # (B, L, 2H)
            scores = attention(combined).squeeze(-1)  # (B, L)
            
            # Apply level-specific mask if provided
            if level_masks and level_idx in level_masks:
                scores = scores.masked_fill(~level_masks[level_idx], float('-inf'))
            
            weights = F.softmax(scores, dim=-1)  # (B, L)
            level_out = (h_seq * weights.unsqueeze(-1)).sum(dim=1)  # (B, H)
            level_outputs.append(level_out)
        
        # Combine all levels
        combined = torch.cat(level_outputs, dim=-1)  # (B, num_levels * H)
        output = self.level_combiner(combined)  # (B, H)
        return output


# Example usage with category-based hierarchy:
def create_level_masks(batch, seq_len):
    '''Create masks for different hierarchy levels'''
    # Level 0: Recent items (last 3)
    recent_mask = torch.zeros(batch_size, seq_len, dtype=torch.bool)
    recent_mask[:, -3:] = True
    
    # Level 1: Same category as target
    category_mask = batch['seq_categories'] == batch['target_category'].unsqueeze(1)
    
    # Level 2: All items (no mask)
    all_mask = torch.ones(batch_size, seq_len, dtype=torch.bool)
    
    return {0: recent_mask, 1: category_mask, 2: all_mask}
```
""",
        expected_benefit="12-21% AUC improvement over DIN (per DHAN paper)",
        difficulty="medium",
        prerequisites=["Category/metadata features available"]
    ),
    
    ResearchDirection(
        id=6,
        name="Cost-Sensitive Learning",
        category="Training Strategy",
        description="Implement asymmetric misclassification costs where FN >> FP.",
        implementation_guide="""
Implement cost-sensitive learning for the CTR task:

```python
class CostSensitiveLoss(nn.Module):
    '''
    Asymmetric loss where False Negatives (missed clicks) are more costly.
    In current market, missed clicks are extremely valuable.
    '''
    def __init__(self, fn_weight=3.0, fp_weight=1.0):
        super().__init__()
        self.fn_weight = fn_weight  # Cost of missing a click
        self.fp_weight = fp_weight  # Cost of false alarm
    
    def forward(self, logits, targets):
        probs = torch.sigmoid(logits)
        
        # False Negative loss: target=1, pred close to 0
        fn_loss = -targets * torch.log(probs + 1e-8) * self.fn_weight
        
        # False Positive loss: target=0, pred close to 1
        fp_loss = -(1 - targets) * torch.log(1 - probs + 1e-8) * self.fp_weight
        
        return (fn_loss + fp_loss).mean()


class AdaptiveCostSensitiveLoss(nn.Module):
    '''
    Adaptive cost-sensitive loss that adjusts weights based on class imbalance.
    '''
    def __init__(self, base_fn_weight=3.0, adaptive=True):
        super().__init__()
        self.base_fn_weight = base_fn_weight
        self.adaptive = adaptive
    
    def forward(self, logits, targets):
        probs = torch.sigmoid(logits)
        
        if self.adaptive:
            # Compute class ratio in batch
            pos_ratio = targets.mean()
            neg_ratio = 1 - pos_ratio
            
            # Adjust weights inversely to class frequency
            fn_weight = self.base_fn_weight * (neg_ratio / (pos_ratio + 1e-8)).clamp(max=10)
            fp_weight = 1.0
        else:
            fn_weight = self.base_fn_weight
            fp_weight = 1.0
        
        fn_loss = -targets * torch.log(probs + 1e-8) * fn_weight
        fp_loss = -(1 - targets) * torch.log(1 - probs + 1e-8) * fp_weight
        
        return (fn_loss + fp_loss).mean()


# Combined with Focal Loss:
class CostSensitiveFocalLoss(nn.Module):
    '''Best of both: Focal Loss + Cost-Sensitive weighting'''
    def __init__(self, alpha=0.75, gamma=2.0, fn_weight=3.0):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma
        self.fn_weight = fn_weight
    
    def forward(self, logits, targets):
        bce = F.binary_cross_entropy_with_logits(logits, targets, reduction='none')
        pt = torch.exp(-bce)
        
        # Focal weight
        focal_weight = self.alpha * (1 - pt) ** self.gamma
        
        # Cost-sensitive weight
        cost_weight = targets * self.fn_weight + (1 - targets) * 1.0
        
        loss = focal_weight * cost_weight * bce
        return loss.mean()
```
""",
        expected_benefit="Significant F1 improvement by reducing False Negatives",
        difficulty="easy",
        prerequisites=[]
    ),
    
    ResearchDirection(
        id=7,
        name="Two-Tower Architecture",
        category="Architecture",
        description="Implement Two-Tower model for efficient retrieval with decoupled user/item encoders.",
        implementation_guide="""
Implement Two-Tower architecture (Google's approach):

```python
class TwoTowerModel(nn.Module):
    '''
    Two-Tower Model: Separate user and item encoders.
    Reference: Google's deep retrieval systems
    
    Benefits:
    - Decoupled inference: precompute item embeddings
    - Scalable to millions of items
    - Sub-10ms inference latency
    '''
    def __init__(self, vocab_size, embed_dim=64, hidden_dim=128, dense_dim=6):
        super().__init__()
        
        # Shared embedding layer
        self.embed = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        
        # User Tower: processes behavior sequence + dense features
        self.user_tower = nn.Sequential(
            nn.Linear(embed_dim + dense_dim, hidden_dim),
            nn.ReLU(),
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, embed_dim)  # Output same dim as item
        )
        
        # Item Tower: processes target item
        self.item_tower = nn.Sequential(
            nn.Linear(embed_dim, hidden_dim),
            nn.ReLU(),
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, embed_dim)
        )
        
        # User sequence encoder (can be GRU, Transformer, etc.)
        self.seq_encoder = nn.GRU(embed_dim, embed_dim, batch_first=True)
        
        # Temperature for similarity
        self.temperature = nn.Parameter(torch.tensor(0.1))
    
    def encode_user(self, seq_ids, dense_x):
        '''Encode user from behavior sequence and dense features'''
        seq_emb = self.embed(seq_ids)  # (B, L, E)
        _, h_n = self.seq_encoder(seq_emb)  # (1, B, E)
        user_seq_repr = h_n.squeeze(0)  # (B, E)
        
        # Combine with dense features
        user_input = torch.cat([user_seq_repr, dense_x], dim=-1)  # (B, E+D)
        user_repr = self.user_tower(user_input)  # (B, E)
        return F.normalize(user_repr, dim=-1)
    
    def encode_item(self, item_ids):
        '''Encode items (can be precomputed for all items)'''
        item_emb = self.embed(item_ids)  # (B, E) or (N_items, E)
        item_repr = self.item_tower(item_emb)  # (B, E)
        return F.normalize(item_repr, dim=-1)
    
    def forward(self, seq_ids, target_ids, dense_x):
        user_repr = self.encode_user(seq_ids, dense_x)  # (B, E)
        item_repr = self.encode_item(target_ids)  # (B, E)
        
        # Dot product similarity
        logits = (user_repr * item_repr).sum(dim=-1) / self.temperature
        return logits
    
    def compute_all_scores(self, seq_ids, dense_x, all_item_reprs):
        '''Efficient scoring against all items'''
        user_repr = self.encode_user(seq_ids, dense_x)  # (B, E)
        # all_item_reprs: (N_items, E) - precomputed
        scores = torch.mm(user_repr, all_item_reprs.t())  # (B, N_items)
        return scores / self.temperature


# Training with in-batch negatives:
def two_tower_loss(model, batch, num_negatives=10):
    user_repr = model.encode_user(batch['seq_ids'], batch['dense_x'])
    
    # Positive items
    pos_item_repr = model.encode_item(batch['target_ids'])
    
    # In-batch negatives (other items in batch)
    all_item_repr = pos_item_repr  # Use batch items as negatives
    
    # Compute similarity matrix
    sim = torch.mm(user_repr, all_item_repr.t()) / model.temperature
    
    # Diagonal elements are positive pairs
    labels = torch.arange(sim.size(0), device=sim.device)
    
    return F.cross_entropy(sim, labels)
```
""",
        expected_benefit="Scalable inference, enables real-time serving at scale",
        difficulty="hard",
        prerequisites=["Understanding of retrieval systems"]
    ),
    
    ResearchDirection(
        id=8,
        name="LLM-Enhanced Feature Generation",
        category="Feature Engineering",
        description="Use LLM to generate interpretable feature rules (FeatLLM approach).",
        implementation_guide="""
Implement LLM-enhanced feature generation (FeatLLM style):

```python
# This approach uses an LLM to generate human-readable feature rules
# which are then converted to binary features for the CTR model.

# Step 1: Generate feature rules using LLM (offline)
LLM_FEATURE_RULES_PROMPT = '''
You are an expert in CTR prediction. Given the following feature descriptions,
generate interpretable rules that might predict clicks.

Available features:
- user_age_group: categorical (young, middle, senior)
- user_activity_level: numeric (0-100)
- item_category: categorical
- time_of_day: categorical (morning, afternoon, evening, night)
- day_of_week: categorical
- user_item_category_affinity: numeric (0-1)

Generate 10 interpretable rules in the format:
RULE: <condition> -> <prediction>

Example:
RULE: user_activity_level > 80 AND time_of_day == 'evening' -> high_click_prob
'''

# Step 2: Parse LLM-generated rules into features
class LLMFeatureGenerator:
    def __init__(self, rules):
        self.rules = self._parse_rules(rules)
    
    def _parse_rules(self, rules_text):
        '''Parse LLM-generated rules into executable conditions'''
        parsed = []
        for line in rules_text.split('\n'):
            if line.startswith('RULE:'):
                condition = line.split('->')[0].replace('RULE:', '').strip()
                parsed.append(condition)
        return parsed
    
    def generate_features(self, df):
        '''Apply rules to generate binary features'''
        new_features = {}
        for i, rule in enumerate(self.rules):
            try:
                # Safely evaluate rule condition
                feature_values = df.eval(rule).astype(int)
                new_features[f'llm_rule_{i}'] = feature_values
            except:
                continue
        return pd.DataFrame(new_features)


# Step 3: Integrate with CTR model
class LLMEnhancedCTRModel(nn.Module):
    def __init__(self, base_model, num_llm_features):
        super().__init__()
        self.base_model = base_model
        
        # Weighted layer for LLM-generated features
        self.llm_feature_weights = nn.Linear(num_llm_features, 1)
        
        # Combine base model output with LLM features
        self.combiner = nn.Sequential(
            nn.Linear(2, 16),
            nn.ReLU(),
            nn.Linear(16, 1)
        )
    
    def forward(self, base_inputs, llm_features):
        base_logit = self.base_model(**base_inputs)  # (B, 1)
        llm_logit = self.llm_feature_weights(llm_features)  # (B, 1)
        
        combined = torch.cat([base_logit, llm_logit], dim=-1)
        final_logit = self.combiner(combined)
        return final_logit.squeeze(-1)


# Example LLM-generated rules for CTR:
EXAMPLE_CTR_RULES = '''
RULE: emb_mean > 0.5 AND dense_activity > 0.7 -> high_click
RULE: emb_std < 0.1 AND time_since_last_click < 3600 -> high_click
RULE: category_affinity > 0.8 AND user_recency < 7 -> high_click
RULE: session_depth > 5 AND bounce_rate < 0.2 -> high_click
RULE: emb_0 * emb_1 > 0.3 -> moderate_click
'''
```
""",
        expected_benefit="Interpretable features, can discover novel patterns",
        difficulty="hard",
        prerequisites=["LLM API access", "Feature engineering infrastructure"]
    ),
    
    ResearchDirection(
        id=9,
        name="Mutual Learning (Peer Training)",
        category="Training Strategy",
        description="Train multiple peer models that learn from each other.",
        implementation_guide="""
Implement Mutual Learning for CTR models:

```python
class MutualLearningTrainer:
    '''
    Mutual Learning: Train multiple peer models that teach each other.
    Reference: Mutual Learning for Finetuning CTR Models (RecSys 2024)
    
    Benefits over Knowledge Distillation:
    - No need for pre-trained teacher
    - Peers improve together
    - 0.66% relative improvement on Criteo/Avazu
    '''
    def __init__(self, models, kl_weight=0.5):
        self.models = models  # List of peer models
        self.kl_weight = kl_weight
        self.optimizers = [torch.optim.AdamW(m.parameters(), lr=1e-4) for m in models]
    
    def train_step(self, batch):
        # Get predictions from all peers
        all_logits = []
        for model in self.models:
            model.train()
            logits = model(batch['seq_ids'], batch['target_ids'], batch['dense_x'])
            all_logits.append(logits)
        
        # Compute average soft targets (ensemble knowledge)
        with torch.no_grad():
            avg_probs = torch.stack([torch.sigmoid(l) for l in all_logits]).mean(dim=0)
        
        total_losses = []
        for i, (model, logits, optimizer) in enumerate(zip(self.models, all_logits, self.optimizers)):
            # Task loss (BCE)
            task_loss = F.binary_cross_entropy_with_logits(logits, batch['labels'])
            
            # Mutual learning loss (KL divergence from ensemble)
            probs = torch.sigmoid(logits)
            # KL(avg || current) - encourage agreement with ensemble
            ml_loss = F.kl_div(
                torch.log(probs + 1e-8),
                avg_probs,
                reduction='batchmean'
            )
            
            # Total loss
            loss = task_loss + self.kl_weight * ml_loss
            
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            total_losses.append(loss.item())
        
        return sum(total_losses) / len(total_losses)
    
    def get_ensemble_prediction(self, batch):
        '''Ensemble prediction from all peers'''
        all_probs = []
        for model in self.models:
            model.eval()
            with torch.no_grad():
                logits = model(batch['seq_ids'], batch['target_ids'], batch['dense_x'])
                probs = torch.sigmoid(logits)
                all_probs.append(probs)
        return torch.stack(all_probs).mean(dim=0)


# Usage:
def train_with_mutual_learning(train_loader, num_peers=3):
    # Create peer models with same architecture but different initialization
    models = [DIENModel(vocab_size, embed_dim, hidden_dim, dense_dim) for _ in range(num_peers)]
    
    trainer = MutualLearningTrainer(models, kl_weight=0.5)
    
    for epoch in range(num_epochs):
        for batch in train_loader:
            loss = trainer.train_step(batch)
        
        # Evaluate ensemble
        val_preds = trainer.get_ensemble_prediction(val_batch)
```
""",
        expected_benefit="0.66% relative improvement through peer learning",
        difficulty="medium",
        prerequisites=["Multiple model training infrastructure"]
    ),
    
    ResearchDirection(
        id=10,
        name="Gradient Boosting Hybrid (GBNet)",
        category="Ensemble",
        description="Combine DNN with LightGBM in an end-to-end trainable hybrid.",
        implementation_guide="""
Implement DNN + LightGBM hybrid ensemble:

```python
# Approach 1: Sequential Hybrid (DNN features -> GBM)
class DNNFeatureExtractor(nn.Module):
    '''Extract features from DNN for GBM'''
    def __init__(self, dien_model):
        super().__init__()
        self.dien = dien_model
    
    def extract_features(self, batch):
        with torch.no_grad():
            # Get intermediate representations
            seq_emb = self.dien.embed(batch['seq_ids'])
            h_seq = self.dien.extractor(seq_emb)
            
            # Various aggregations as features
            features = {
                'dnn_mean': h_seq.mean(dim=1).numpy(),
                'dnn_max': h_seq.max(dim=1)[0].numpy(),
                'dnn_last': h_seq[:, -1, :].numpy(),
            }
            
            # Get DIEN embedding
            emb = self.dien(batch['seq_ids'], batch['target_ids'], 
                          batch['dense_x'], return_embedding=True)
            features['dien_emb'] = emb.numpy()
            
        return features


def train_hybrid_model(train_df, val_df, dien_model):
    '''Train hybrid DNN + LightGBM'''
    extractor = DNNFeatureExtractor(dien_model)
    
    # Extract DNN features
    train_dnn_features = extractor.extract_features(train_df)
    val_dnn_features = extractor.extract_features(val_df)
    
    # Combine with original features
    X_train = np.hstack([
        train_df[dense_cols].values,
        train_dnn_features['dien_emb'],
        train_dnn_features['dnn_mean'],
    ])
    
    # Train LightGBM
    lgb_params = {
        'objective': 'binary',
        'metric': 'auc',
        'learning_rate': 0.05,
        'num_leaves': 63,
        'feature_fraction': 0.8,
        'bagging_fraction': 0.8,
        'bagging_freq': 5,
        'verbose': -1,
    }
    
    lgb_model = lgb.train(
        lgb_params,
        lgb.Dataset(X_train, train_df[label_col]),
        valid_sets=[lgb.Dataset(X_val, val_df[label_col])],
        num_boost_round=1000,
        callbacks=[lgb.early_stopping(50)],
    )
    
    return lgb_model


# Approach 2: Stacking with DNN prediction as feature
def stacking_hybrid(train_df, val_df, dien_model, lgb_base_model):
    '''2-stage stacking: DNN + LightGBM'''
    
    # Stage 1: Get DNN predictions
    dnn_train_preds = dien_model.predict(train_df)
    dnn_val_preds = dien_model.predict(val_df)
    
    # Stage 2: LightGBM with DNN prediction as feature
    X_train = np.column_stack([
        train_df[feature_cols].values,
        dnn_train_preds,  # DNN prediction as feature
    ])
    
    lgb_stacker = lgb.train(
        lgb_params,
        lgb.Dataset(X_train, train_df[label_col]),
        num_boost_round=500,
    )
    
    return lgb_stacker


# Approach 3: Weighted ensemble
def weighted_ensemble(dnn_preds, lgb_preds, dnn_weight=0.4):
    '''Simple weighted average'''
    return dnn_weight * dnn_preds + (1 - dnn_weight) * lgb_preds
```
""",
        expected_benefit="Combines DNN's representation power with GBM's tabular strength",
        difficulty="easy",
        prerequisites=["LightGBM installed"]
    ),
]


class ResearchDirector:
    """
    LLM-based research direction selector for forced exploration.
    
    When evolution plateaus, analyzes the situation and selects
    the most promising research direction based on context.
    
    Now supports:
    1. Legacy RESEARCH_DIRECTIONS (ResearchDirection dataclass)
    2. Generic research_ideas_pool (ResearchIdea dataclass)
    3. Task-specific research ideas (loaded from task directory)
    """
    
    def __init__(
        self, 
        llm_client=None, 
        directions: List[ResearchDirection] = None, 
        use_new_pool: bool = True,
        task_ideas_path: str = None  # NEW: Path to task-specific research ideas
    ):
        self.llm_client = llm_client
        self.directions = directions or RESEARCH_DIRECTIONS
        self.selection_history: List[Dict] = []
        self.use_new_pool = use_new_pool and RESEARCH_POOL_AVAILABLE
        self.task_ideas_path = task_ideas_path
        
        # Load research ideas - TASK-ONLY MODE (no generic ideas)
        self._combined_ideas = []
        
        if task_ideas_path:
            task_ideas = load_task_specific_ideas(task_ideas_path)
            if task_ideas:
                # Task-Only: Only use task-specific ideas (Option A)
                self._combined_ideas = task_ideas
                print(f"棣冩憥 ResearchDirector: Loaded {len(task_ideas)} task-specific ideas (Task-Only Mode)")
        
        # Fallback to generic ONLY if no task-specific ideas found
        if not self._combined_ideas:
            self._combined_ideas = list(RESEARCH_IDEAS)
            print(f"棣冩憥 ResearchDirector: No task-specific ideas found, using {len(RESEARCH_IDEAS)} generic ideas")
        
        if self.use_new_pool:
            # Map ideas for lookup
            self._idea_map = {idea.id: idea for idea in self._combined_ideas}
    
    def _format_directions(self) -> str:
        """Format research directions for LLM prompt."""
        lines = []
        for d in self.directions:
            lines.append(f"""
### Direction {d.id}: {d.name}
- **Category:** {d.category}
- **Difficulty:** {d.difficulty}
- **Description:** {d.description}
- **Expected Benefit:** {d.expected_benefit}
""")
        return "\n".join(lines)
    
    def _format_directions_from_pool(self, failed_approaches: List[str] = None) -> str:
        """Format research directions from the new research ideas pool."""
        if not self.use_new_pool:
            return self._format_directions()
        
        return format_for_llm_selection(
            current_approach="",  # Will be set by caller
            failed_approaches=failed_approaches or [],
            plateau_length=0,  # Will be set by caller
        )
    
    def _format_failed_approaches(self, failed: List[str]) -> str:
        """Format failed approaches for context."""
        if not failed:
            return "No previous failed attempts recorded."
        return "\n".join([f"- {f}" for f in failed[-10:]])  # Last 10
    
    def select_direction_from_pool(
        self,
        best_score: float,  # Renamed: generic metric (F1, F-max, AUC, etc.)
        plateau_length: int,
        failed_approaches: List[str],
        current_code_summary: str,
        performance_history: List[float],
        arxiv_papers: str = "",  # NEW: arXiv search results
        metric_name: str = "Score",  # NEW: Task-specific metric name
        task_description: str = "CTR prediction",  # NEW: task context for search
    ) -> Dict[str, Any]:
        """
        Select direction using the new research ideas pool + arXiv papers.
        
        This method uses:
        1. research_ideas_pool - curated ideas with code snippets
        2. arXiv paper abstracts - latest research from simple_paper_search
        
        The LLM decides which idea to implement based on ALL available information.
        """
        if not self.use_new_pool:
            return self.select_direction(
                best_score, plateau_length, failed_approaches,
                current_code_summary, performance_history
            )
        
        # Format the task-specific research ideas for LLM
        pool_prompt = format_for_llm_selection(
            current_approach=current_code_summary,
            failed_approaches=failed_approaches,
            plateau_length=plateau_length,
            ideas=self._combined_ideas,  # Task-specific ideas only
            title="TASK-SPECIFIC RESEARCH IDEAS",
        )
        
        # If no arXiv papers provided, try to fetch them
        web_search_results = ""
        if not arxiv_papers:
            search_query = f"{task_description} deep learning 2024 2025"
            
            # 1. arXiv Search
            try:
                from ea.kosmos.simple_paper_search import SimplePaperSearch
                logger.info(f"棣冩憥 Searching arXiv for: {search_query[:60]}...")
                search = SimplePaperSearch(verbose=True)
                arxiv_papers = search.search_and_format(
                    query=search_query,
                    max_results=3
                )
                if arxiv_papers:
                    logger.info(f"棣冩憥 arXiv search returned {len(arxiv_papers)} chars of content")
                else:
                    logger.warning("棣冩憥 arXiv search returned empty result")
            except Exception as e:
                logger.warning(f"棣冩憥 arXiv search failed: {e}")
                arxiv_papers = ""
            
            # 2. Gemini Web Search (with Google grounding)
            try:
                from ea.kosmos.knowledge import GeminiWebSearch
                logger.info(f"棣冨 Searching web via Gemini for: {search_query[:60]}...")
                web_search = GeminiWebSearch(verbose=True)
                web_techniques = web_search.search(
                    query=search_query,
                    max_results=3
                )
                if web_techniques:
                    web_search_results = "\n\n### Web Search Results:\n"
                    for i, tech in enumerate(web_techniques, 1):
                        web_search_results += f"\n**{i}. {tech.name}**\n{tech.description}\n"
                    logger.info(f"棣冨 Gemini web search returned {len(web_techniques)} techniques")
                else:
                    logger.info("棣冨 Gemini web search returned no results")
            except Exception as e:
                logger.warning(f"棣冨 Gemini web search failed: {e}")
        
        prompt = f"""You are a senior ML research director specializing in {task_description} optimization.

## Current Situation Analysis

**Performance Metrics:**
- Current Best {metric_name}: {best_score:.4f}
- Generations Without Improvement: {plateau_length}
- Recent Performance Trend: {performance_history[-5:] if performance_history else 'N/A'}

**Current Architecture Summary:**
{current_code_summary}

---

{pool_prompt}

---

## LATEST RESEARCH FROM ARXIV

{arxiv_papers if arxiv_papers else "(No arXiv papers available)"}

{web_search_results}

---

## YOUR DECISION

Based on:
1. The curated research ideas above
2. The latest arXiv papers
3. The current situation

Select the MOST PROMISING approach. You can either:
- Pick an idea from the RESEARCH IDEAS POOL (respond with selected_id)
- Suggest implementing a technique from the arXiv papers (respond with paper reference)

Respond with:
```json
{{
  "selected_id": "<idea_id or 'arxiv_paper_N'>",
  "reasoning": "<why this is the best choice>",
  "implementation_plan": "<specific steps to implement>"
}}
```
"""
        
        # LLM MUST make the selection - no heuristic fallback
        if self.llm_client:
            try:
                # Use query() method and access .content from QueryResult
                system_msg = "You are a senior ML research director specializing in CTR prediction optimization. Analyze the situation and select the most promising research direction."
                query_result = self.llm_client.query(msg=prompt, system_msg=system_msg)
                if query_result is None or query_result.content is None:
                    raise RuntimeError("LLM query returned None")
                response = query_result.content
                result = self._parse_pool_response(response, failed_approaches, plateau_length)
            except Exception as e:
                print(f"LLM selection from pool failed: {e}")
                print("WARNING: LLM is required for forced exploration selection!")
                print("Falling back to first available idea (LLM should decide in production)")
                result = self._fallback_selection_from_pool(failed_approaches)
        else:
            print("WARNING: No LLM client provided! LLM is required for forced exploration.")
            print("The LLM should decide which research direction to try.")
            result = self._fallback_selection_from_pool(failed_approaches)
        
        # Record selection
        self.selection_history.append({
            'best_score': best_score,
            'plateau_length': plateau_length,
            'selected': result,
            'source': 'research_ideas_pool',
        })
        
        return result
    
    def _parse_pool_response(self, response: str, failed_approaches: List[str], plateau_length: int) -> Dict[str, Any]:
        """Parse LLM response when using research ideas pool OR arXiv papers."""
        # Try to extract JSON from response
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                idea_id = data.get('selected_id', '')
                reasoning = data.get('reasoning', '')
                implementation_plan = data.get('implementation_plan', '')
                
                # Check if this is an arXiv paper selection
                if idea_id.startswith('arxiv_paper'):
                    # LLM selected a technique from arXiv papers
                    return {
                        'direction': ResearchDirection(
                            id=999,  # Special ID for arXiv-based direction
                            name=f"arXiv Research: {idea_id}",
                            category="External Research",
                            description=reasoning,
                            implementation_guide=implementation_plan,
                            expected_benefit="Based on latest arXiv research",
                            difficulty="medium",
                            prerequisites=[],
                        ),
                        'idea': None,  # No curated idea, using arXiv
                        'source': 'arxiv',
                        'reasoning': reasoning,
                        'implementation_plan': implementation_plan,
                        'full_response': response,
                    }
                
                # Otherwise, look for curated idea
                idea = get_idea_by_id(idea_id)
                if idea:
                    return {
                        'direction': self._idea_to_direction(idea),
                        'idea': idea,
                        'source': 'research_pool',
                        'reasoning': reasoning,
                        'implementation_plan': implementation_plan,
                        'full_response': response,
                    }
            except json.JSONDecodeError:
                pass
        
        # Fallback: look for idea ID in response
        for idea in RESEARCH_IDEAS:
            if idea.id in response or idea.name in response:
                return {
                    'direction': self._idea_to_direction(idea),
                    'idea': idea,
                    'source': 'research_pool',
                    'reasoning': response,
                    'implementation_plan': 'Follow implementation steps',
                    'full_response': response,
                }
        
        # Default to fallback
        return self._fallback_selection_from_pool(failed_approaches, plateau_length)
    
    def _idea_to_direction(self, idea: 'ResearchIdea') -> ResearchDirection:
        """Convert ResearchIdea to ResearchDirection for compatibility."""
        return ResearchDirection(
            id=hash(idea.id) % 100,  # Generate numeric ID
            name=idea.name,
            category=idea.category,
            description=idea.summary,
            implementation_guide=idea.code_snippet or "\n".join(idea.implementation_steps),
            expected_benefit=idea.expected_f1_gain,
            difficulty=idea.difficulty,
            prerequisites=idea.prerequisites or [],
        )
    
    def _fallback_selection_from_pool(
        self, 
        failed_approaches: List[str],
    ) -> Dict[str, Any]:
        """
        Fallback selection when LLM is not available.
        
        WARNING: This is a fallback only. LLM should make the selection!
        The LLM reads all the research ideas and decides which one to implement.
        """
        # Filter out ideas that match failed approaches
        failed_keywords = set()
        for f in (failed_approaches or []):
            failed_keywords.update(f.lower().split())
        
        available = []
        for idea in RESEARCH_IDEAS:
            name_words = set(idea.name.lower().split())
            if not name_words.intersection(failed_keywords):
                available.append(idea)
        
        if not available:
            available = list(RESEARCH_IDEAS)
        
        # Just return the first available - LLM should decide!
        idea = available[0]
        return {
            'direction': self._idea_to_direction(idea),
            'idea': idea,
            'reasoning': 'FALLBACK: LLM should decide which research direction to use!',
            'implementation_plan': '\n'.join(idea.implementation_steps),
        }
    
    def _heuristic_selection_from_pool(
        self, 
        failed_approaches: List[str],
        plateau_length: int
    ) -> Dict[str, Any]:
        """
        DEPRECATED: Use LLM selection instead.
        
        This heuristic selection is kept for backwards compatibility,
        but LLM should make the decision.
        """
        print("WARNING: Heuristic selection is deprecated. LLM should decide!")
        return self._fallback_selection_from_pool(failed_approaches)
    
    def get_forced_exploration_prompt_from_pool(self, selection: Dict[str, Any]) -> str:
        """Generate forced exploration prompt using research ideas pool."""
        idea = selection.get('idea')
        if not idea:
            return self.get_forced_exploration_prompt(selection)
        
        # Use detailed implementation prompt from pool
        implementation_prompt = get_implementation_prompt(idea.id)
        
        return f"""
閳烘柡鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫧
閳?                   棣冩瘍棣冩瘍棣冩瘍 MANDATORY FORCED EXPLORATION 棣冩瘍棣冩瘍棣冩瘍                    閳?閳烘埃鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ殕

閳跨媴绗?THE EVOLUTION HAS PLATEAUED - YOU MUST IMPLEMENT THE SPECIFIC TECHNIQUE BELOW 閳跨媴绗?
DO NOT:
閴?Do a crossover between programs
閴?Make minor tweaks to existing code
閴?Ignore this directive and do something else
閴?Just add features without changing the core architecture

YOU MUST:
閴?Implement the EXACT research idea specified below
閴?Use the provided code snippet as your starting point
閴?Make MAJOR architectural changes

================================================================================
## REQUIRED IMPLEMENTATION: [{idea.id}] {idea.name}
================================================================================

**Category:** {idea.category}
**Difficulty:** {idea.difficulty}
**Expected F1 Gain:** {idea.expected_f1_gain}

### KEY INSIGHT (UNDERSTAND THIS FIRST):
{idea.key_insight}

### WHY THIS APPROACH:
{selection.get('reasoning', idea.key_insight)}

================================================================================
## IMPLEMENTATION GUIDE - FOLLOW THIS EXACTLY
================================================================================

{implementation_prompt}

================================================================================
## MANDATORY REQUIREMENTS
================================================================================

1. 閳?REPLACE the current model architecture with the one described above
2. 閳?USE the provided code snippet - adapt it to fit the existing data pipeline
3. 閳?DO NOT just add this as an extra feature - make it the CORE approach
4. 閳?Preserve the evaluation interface (EVOLVE-BLOCK boundaries)
5. 閳?The output must still be: (val_f1, test_predictions, feature_importance)

THIS IS NOT OPTIONAL - THE SYSTEM HAS DETECTED A PLATEAU AND REQUIRES A 
FUNDAMENTALLY DIFFERENT APPROACH. IMPLEMENT THE ABOVE TECHNIQUE.
"""

    def select_direction(
        self,
        best_score: float,  # Renamed: generic metric (F1, F-max, AUC, etc.)
        plateau_length: int,
        failed_approaches: List[str],
        current_code_summary: str,
        performance_history: List[float],
        metric_name: str = "Score",  # Task-specific metric name
    ) -> Dict[str, Any]:
        """
        Use LLM to select the best research direction.
        
        Args:
            best_score: Current best score (F1, F-max, AUC, etc.)
            plateau_length: Number of generations without improvement
            failed_approaches: List of approaches that didn't work
            current_code_summary: Summary of current best code
            performance_history: Recent scores
            metric_name: Name of the metric being optimized
        
        Returns:
            Dict with selected direction and implementation guidance
        
        Note: If use_new_pool=True, this will delegate to select_direction_from_pool
        """
        # Use new pool if available
        if self.use_new_pool:
            return self.select_direction_from_pool(
                best_score, plateau_length, failed_approaches,
                current_code_summary, performance_history
            )
        
        prompt = f"""You are a senior ML research director specializing in optimization.

## Current Situation Analysis

**Performance Metrics:**
- Current Best {metric_name}: {best_score:.4f}
- Generations Without Improvement: {plateau_length}
- Recent Performance Trend: {performance_history[-5:] if performance_history else 'N/A'}

**Current Architecture Summary:**
{current_code_summary}

**Previously Failed Approaches:**
{self._format_failed_approaches(failed_approaches)}

## Available Research Directions

{self._format_directions()}

## Your Task

Analyze the situation and select the SINGLE MOST PROMISING research direction that:
1. Is likely to break the current plateau
2. Has NOT been tried before (check failed approaches)
3. Is appropriate for the current architecture
4. Has reasonable implementation difficulty

## Required Output Format (JSON):

```json
{{
    "selected_direction_id": <number 1-10>,
    "reasoning": "<detailed explanation of why this direction is best>",
    "why_others_rejected": "<brief explanation of why other top candidates were not selected>",
    "implementation_priority": "<what specific aspect to implement first>",
    "expected_f1_improvement": "<estimated improvement, e.g., '0.02-0.05'>",
    "risk_assessment": "<potential risks and how to mitigate>",
    "integration_notes": "<how to integrate with current architecture>"
}}
```

Provide your analysis and selection:
"""
        
        if self.llm_client:
            try:
                # Use query() method and access .content from QueryResult
                system_msg = "You are a senior ML research director specializing in CTR prediction optimization. Analyze the situation and select the most promising research direction."
                query_result = self.llm_client.query(msg=prompt, system_msg=system_msg)
                if query_result is None or query_result.content is None:
                    raise RuntimeError("LLM query returned None")
                response = query_result.content
                result = self._parse_llm_response(response)
            except Exception as e:
                print(f"LLM selection failed: {e}, using heuristic fallback")
                result = self._heuristic_selection(failed_approaches, plateau_length)
        else:
            result = self._heuristic_selection(failed_approaches, plateau_length)
        
        # Record selection
        self.selection_history.append({
            'best_score': best_score,
            'plateau_length': plateau_length,
            'selected': result,
        })
        
        return result
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response to extract selection."""
        # Try to extract JSON from response
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                direction_id = data.get('selected_direction_id', 1)
                direction = next((d for d in self.directions if d.id == direction_id), self.directions[0])
                
                return {
                    'direction': direction,
                    'reasoning': data.get('reasoning', ''),
                    'implementation_priority': data.get('implementation_priority', ''),
                    'expected_improvement': data.get('expected_f1_improvement', ''),
                    'risk_assessment': data.get('risk_assessment', ''),
                    'integration_notes': data.get('integration_notes', ''),
                    'full_response': response,
                }
            except json.JSONDecodeError:
                pass
        
        # Fallback: look for direction number
        for d in self.directions:
            if f"Direction {d.id}" in response or d.name in response:
                return {
                    'direction': d,
                    'reasoning': response,
                    'implementation_priority': 'See implementation guide',
                    'expected_improvement': d.expected_benefit,
                    'full_response': response,
                }
        
        # Default to first direction
        return {
            'direction': self.directions[0],
            'reasoning': 'Default selection',
            'full_response': response,
        }
    
    def _heuristic_selection(
        self, 
        failed_approaches: List[str],
        plateau_length: int
    ) -> Dict[str, Any]:
        """Fallback heuristic selection when LLM is unavailable."""
        # Filter out directions that match failed approaches
        failed_keywords = set()
        for f in failed_approaches:
            failed_keywords.update(f.lower().split())
        
        available = []
        for d in self.directions:
            name_words = set(d.name.lower().split())
            if not name_words.intersection(failed_keywords):
                available.append(d)
        
        if not available:
            available = self.directions
        
        # Prioritize by plateau length
        if plateau_length > 10:
            # Long plateau: try harder approaches
            priority_order = ['Architecture', 'Training Strategy', 'Loss Function', 'Ensemble']
        else:
            # Short plateau: try easier approaches first
            priority_order = ['Loss Function', 'Training Strategy', 'Architecture', 'Ensemble']
        
        for category in priority_order:
            for d in available:
                if d.category == category:
                    return {
                        'direction': d,
                        'reasoning': f'Heuristic selection based on plateau length ({plateau_length}) and category priority',
                        'implementation_priority': 'Follow implementation guide',
                        'expected_improvement': d.expected_benefit,
                    }
        
        return {
            'direction': available[0],
            'reasoning': 'Default heuristic selection',
        }
    
    def get_forced_exploration_prompt(self, selection: Dict[str, Any]) -> str:
        """Generate the prompt injection for forced exploration."""
        # Use new pool format if idea is available
        if 'idea' in selection and selection['idea'] is not None:
            return self.get_forced_exploration_prompt_from_pool(selection)
        
        direction = selection['direction']
        
        return f"""
棣冩瘍 **FORCED EXPLORATION MODE** 棣冩瘍

The evolution has plateaued. You MUST implement the following research direction:

## Selected Direction: {direction.name}
**Category:** {direction.category}
**Difficulty:** {direction.difficulty}

### Why This Direction:
{selection.get('reasoning', direction.description)}

### Implementation Priority:
{selection.get('implementation_priority', 'Follow the guide below')}

### Expected Improvement:
{selection.get('expected_improvement', direction.expected_benefit)}

### Implementation Guide:
{direction.implementation_guide}

---

**IMPORTANT:** 
- You MUST make significant changes following this direction
- Do NOT make minor tweaks - implement the core idea
- The code must compile and run correctly
- Preserve the existing evaluation interface
"""
    
    def save_history(self, path: str):
        """Save selection history for analysis."""
        with open(path, 'w') as f:
            json.dump(self.selection_history, f, indent=2, default=str)


# Convenience function for integration
def get_forced_exploration_guidance(
    llm_client,
    best_score: float,  # Renamed: generic metric (F1, F-max, AUC, etc.)
    plateau_length: int,
    failed_approaches: List[str],
    current_code_summary: str,
    performance_history: List[float],
    metric_name: str = "Score",  # Task-specific metric name
) -> str:
    """
    Get forced exploration guidance when evolution plateaus.
    
    Returns a prompt injection string to force the LLM to try a new direction.
    """
    director = ResearchDirector(llm_client)
    selection = director.select_direction(
        best_score=best_score,
        plateau_length=plateau_length,
        failed_approaches=failed_approaches,
        current_code_summary=current_code_summary,
        performance_history=performance_history,
        metric_name=metric_name,
    )
    return director.get_forced_exploration_prompt(selection)



