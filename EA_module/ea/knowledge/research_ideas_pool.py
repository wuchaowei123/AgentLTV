"""
Research Ideas Pool for CTR Prediction (2024-2025 SOTA)

This module provides a structured pool of research ideas derived from
comprehensive deep research on CTR prediction. Each idea is formatted
for easy LLM consumption and selection.

The ideas are categorized and ranked by:
1. Expected F1 improvement
2. Implementation difficulty
3. Compatibility with current architecture
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ResearchIdea:
    """A single research idea with implementation guidance."""
    id: str
    name: str
    category: str
    difficulty: str  # "easy", "medium", "hard"
    expected_f1_gain: str  # e.g., "3-8%", "5-15%"
    summary: str  # One-line summary
    key_insight: str  # Why this works
    implementation_steps: List[str]
    code_snippet: Optional[str] = None
    references: Optional[List[str]] = None
    prerequisites: Optional[List[str]] = None
    risks: Optional[List[str]] = None


# ============================================================================
# RESEARCH IDEAS POOL
# ============================================================================

RESEARCH_IDEAS: List[ResearchIdea] = [
    
    # =========================================================================
    # CATEGORY 1: ARCHITECTURE IMPROVEMENTS
    # =========================================================================
    
    ResearchIdea(
        id="arch_transformer",
        name="Transformer-Based Sequence Modeling",
        category="Architecture",
        difficulty="medium",
        expected_f1_gain="5-15%",
        summary="Replace GRU with Transformer encoder for better long-range dependency modeling.",
        key_insight="Transformers excel at capturing non-local dependencies in long sequences through self-attention, outperforming RNN/GRU on datasets with strong temporal correlation.",
        implementation_steps=[
            "1. Add PositionalEncoding module for sequence position awareness",
            "2. Replace GRU-based interest extractor with TransformerEncoder",
            "3. Use 4-8 attention heads with 2-3 encoder layers",
            "4. Add LayerNorm for training stability",
            "5. Keep embedding dimension same as current DIEN (48-64)",
        ],
        code_snippet='''
class TransformerInterestExtractor(nn.Module):
    def __init__(self, embed_dim=64, num_heads=4, num_layers=2, dropout=0.2):
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
''',
        references=["SASRec", "BERT4Rec", "BST (Behavior Sequence Transformer)"],
        prerequisites=["PyTorch Transformer modules"],
        risks=["Higher memory usage", "Slower training on short sequences"],
    ),
    
    ResearchIdea(
        id="arch_multi_interest",
        name="Multi-Interest Extraction (MIND/ComiRec)",
        category="Architecture",
        difficulty="medium",
        expected_f1_gain="5-10%",
        summary="Extract multiple user interest vectors instead of single representation.",
        key_insight="Users have diverse preferences. A single vector cannot capture all interests. Multi-interest networks extract K orthogonal interest vectors for better personalization.",
        implementation_steps=[
            "1. Create K interest extraction heads (K=4 recommended)",
            "2. Add orthogonality regularization to ensure diverse interests",
            "3. Implement target-aware attention to aggregate interests",
            "4. Add orthogonality_loss to total training loss",
        ],
        code_snippet='''
class MultiInterestExtractor(nn.Module):
    def __init__(self, hidden_dim, num_interests=4, dropout=0.2):
        super().__init__()
        self.num_interests = num_interests
        self.interest_heads = nn.ModuleList([
            nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(hidden_dim, hidden_dim)
            ) for _ in range(num_interests)
        ])
    
    def forward(self, h_seq):
        interests = []
        for head in self.interest_heads:
            pooled = h_seq.mean(dim=1)
            interest = head(pooled)
            interests.append(interest)
        return torch.stack(interests, dim=1)  # (B, K, H)
''',
        references=["MIND", "ComiRec", "DMIN"],
    ),
    
    ResearchIdea(
        id="arch_hierarchical_attention",
        name="Hierarchical Attention (DHAN)",
        category="Architecture",
        difficulty="medium",
        expected_f1_gain="12-21% AUC improvement",
        summary="Add multi-level attention over different dimensions (recency, category, etc.).",
        key_insight="User interests are hierarchical and multi-dimensional. DHAN attends to different hierarchical abstractions (recent items, same-category items, all items) for comprehensive interest modeling.",
        implementation_steps=[
            "1. Define hierarchy levels (e.g., recent, same-category, all)",
            "2. Create attention module for each level",
            "3. Combine level outputs with learnable weights",
            "4. Integrate with existing DIEN architecture",
        ],
        references=["DHAN paper: arXiv:2005.12981"],
    ),
    
    ResearchIdea(
        id="arch_two_tower",
        name="Two-Tower Architecture",
        category="Architecture",
        difficulty="hard",
        expected_f1_gain="Scalability + slight accuracy gain",
        summary="Decouple user and item encoders for efficient inference.",
        key_insight="Google's approach: precompute item embeddings offline, only compute user tower in real-time. Enables sub-10ms inference at scale.",
        implementation_steps=[
            "1. Create separate user_tower and item_tower networks",
            "2. User tower: processes behavior sequence + dense features",
            "3. Item tower: processes target item features",
            "4. Use dot product similarity with temperature scaling",
            "5. Train with in-batch negatives",
        ],
        references=["Google Deep Retrieval", "YouTube recommendations"],
        risks=["Requires architectural refactoring"],
    ),
    
    # =========================================================================
    # CATEGORY 2: LOSS FUNCTIONS
    # =========================================================================
    
    ResearchIdea(
        id="loss_power_focal",
        name="Power Focal Loss",
        category="Loss Function",
        difficulty="easy",
        expected_f1_gain="3-5%",
        summary="Enhanced Focal Loss with power term to prevent vanishing gradients.",
        key_insight="Standard Focal Loss can suffer from vanishing gradients on hard examples. Power term ensures stable optimization.",
        implementation_steps=[
            "1. Replace BCE/Focal Loss with PowerFocalLoss",
            "2. Set alpha=0.75, gamma=2.0, power=1.0",
            "3. Monitor gradient magnitudes during training",
        ],
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
    ),
    
    ResearchIdea(
        id="loss_cost_sensitive",
        name="Cost-Sensitive Learning",
        category="Loss Function",
        difficulty="easy",
        expected_f1_gain="5-10%",
        summary="Weight False Negatives higher than False Positives.",
        key_insight="In CTR, missing a click (FN) is more costly than false alarm (FP). Asymmetric weighting improves recall without sacrificing precision.",
        implementation_steps=[
            "1. Define FN_weight=3.0 (missed clicks are 3x more costly)",
            "2. Implement CostSensitiveLoss",
            "3. Combine with Focal Loss for best results",
        ],
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
    ),
    
    ResearchIdea(
        id="loss_polyhedral_conic",
        name="Polyhedral Conic Classifier (PCC)",
        category="Loss Function",
        difficulty="medium",
        expected_f1_gain="SOTA on Criteo/Avazu",
        summary="Novel loss function that creates multiple decision boundaries.",
        key_insight="PCC creates polyhedral decision boundaries instead of single hyperplane, better separating imbalanced classes.",
        implementation_steps=[
            "1. Implement PCC loss with num_cones=4",
            "2. Use margin-based separation",
            "3. Replace final sigmoid with PCC classifier",
        ],
        references=["arXiv:2406.03892"],
    ),
    
    # =========================================================================
    # CATEGORY 3: TRAINING STRATEGIES
    # =========================================================================
    
    ResearchIdea(
        id="train_contrastive",
        name="Contrastive Learning Pre-training",
        category="Training Strategy",
        difficulty="medium",
        expected_f1_gain="3-8%",
        summary="Add self-supervised contrastive loss for better embeddings.",
        key_insight="Contrastive learning creates robust representations by maximizing similarity between augmented views of same user while repelling different users.",
        implementation_steps=[
            "1. Create sequence augmentation (dropout, mask, reorder)",
            "2. Implement InfoNCE contrastive loss",
            "3. Add contrastive_loss to total loss with weight 0.1",
            "4. Train jointly with CTR loss",
        ],
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
''',
        references=["SimCLR", "MoCo for recommendations"],
    ),
    
    ResearchIdea(
        id="train_mutual_learning",
        name="Mutual Learning (Peer Training)",
        category="Training Strategy",
        difficulty="medium",
        expected_f1_gain="0.66% relative improvement",
        summary="Train multiple peer models that learn from each other.",
        key_insight="Instead of teacher-student distillation, train multiple models simultaneously. They refine each other's representations through knowledge exchange.",
        implementation_steps=[
            "1. Create 3 peer models with same architecture",
            "2. Train jointly with KL divergence between peers",
            "3. Use ensemble prediction at inference",
        ],
        references=["RecSys 2024: Mutual Learning for CTR"],
    ),
    
    ResearchIdea(
        id="train_threshold_optimization",
        name="F1-Max Threshold Search",
        category="Training Strategy",
        difficulty="easy",
        expected_f1_gain="2-5%",
        summary="Search for optimal classification threshold on validation set.",
        key_insight="Deep learning outputs are poorly calibrated. Optimal threshold is rarely 0.5. Search thresholds 0.2-0.65 to maximize F1.",
        implementation_steps=[
            "1. After training, get predictions on validation set",
            "2. Search thresholds from 0.2 to 0.65 in 0.01 steps",
            "3. Select threshold that maximizes F1",
            "4. Use this threshold at inference",
        ],
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
    ),
    
    # =========================================================================
    # CATEGORY 4: ENSEMBLE METHODS
    # =========================================================================
    
    ResearchIdea(
        id="ensemble_dnn_gbm",
        name="DNN + Gradient Boosting Hybrid",
        category="Ensemble",
        difficulty="easy",
        expected_f1_gain="3-5%",
        summary="Combine DNN embeddings with LightGBM for best of both worlds.",
        key_insight="DNNs excel at sequence modeling, GBMs excel at tabular features. Hybrid captures both.",
        implementation_steps=[
            "1. Extract DIEN embeddings as features",
            "2. Combine with original dense features",
            "3. Train LightGBM on combined features",
            "4. Optionally stack with DNN prediction as feature",
        ],
        code_snippet='''
# Two-stage stacking
dnn_preds = dien_model.predict(X)
X_combined = np.column_stack([X_original, dien_embeddings, dnn_preds])
lgb_model = lgb.train(params, lgb.Dataset(X_combined, y))
''',
    ),
    
    ResearchIdea(
        id="ensemble_multi_seed",
        name="Multi-Seed Ensemble",
        category="Ensemble",
        difficulty="easy",
        expected_f1_gain="1-3%",
        summary="Train same model with different random seeds and average predictions.",
        key_insight="Reduces variance, improves generalization. Simple but effective.",
        implementation_steps=[
            "1. Train 5 models with seeds [42, 2023, 777, 1337, 999]",
            "2. Average predictions at inference",
            "3. Optionally use weighted average based on validation F1",
        ],
    ),
    
    # =========================================================================
    # CATEGORY 5: FEATURE ENGINEERING
    # =========================================================================
    
    ResearchIdea(
        id="feat_llm_rules",
        name="LLM-Generated Feature Rules",
        category="Feature Engineering",
        difficulty="hard",
        expected_f1_gain="Novel pattern discovery",
        summary="Use LLM to generate interpretable feature rules.",
        key_insight="LLMs can infer human-readable rules from feature descriptions. These rules become binary features for transparent prediction.",
        implementation_steps=[
            "1. Describe available features to LLM",
            "2. Ask LLM to generate interpretable rules",
            "3. Convert rules to binary features",
            "4. Add to feature set for LightGBM",
        ],
        references=["FeatLLM: arXiv:2404.09491"],
    ),
    
    ResearchIdea(
        id="feat_behavior_hierarchy",
        name="Hierarchical Behavior Features",
        category="Feature Engineering",
        difficulty="medium",
        expected_f1_gain="3-5%",
        summary="Create features at multiple time scales (recent, weekly, monthly).",
        key_insight="User behavior has different patterns at different time scales. Capture all of them.",
        implementation_steps=[
            "1. Create rolling features: 3-day, 7-day, 30-day",
            "2. Add velocity features (rate of change)",
            "3. Add acceleration features (change in velocity)",
            "4. Create ratio features (recent/historical)",
        ],
    ),
    
    ResearchIdea(
        id="feat_cross_interactions",
        name="Automated Cross-Feature Interactions",
        category="Feature Engineering",
        difficulty="medium",
        expected_f1_gain="2-4%",
        summary="Automatically discover high-order feature interactions.",
        key_insight="Manual feature crossing is labor-intensive. AutoFE discovers optimal interactions.",
        implementation_steps=[
            "1. Identify top features by importance",
            "2. Create pairwise interactions (multiply, divide, subtract)",
            "3. Use feature selection to keep useful ones",
            "4. Add to LightGBM feature set",
        ],
    ),
]


# ============================================================================
# TASK-SPECIFIC IDEAS LOADER
# ============================================================================

def load_task_specific_ideas(task_ideas_path: str) -> List[ResearchIdea]:
    """
    Load task-specific research ideas from a Python file.
    
    The file should define a list called TASK_RESEARCH_IDEAS or a similar
    naming convention (e.g., CAFA_RESEARCH_IDEAS for CAFA tasks).
    
    Args:
        task_ideas_path: Path to the task-specific research ideas Python file
    
    Returns:
        List of ResearchIdea objects from the task file
    """
    import importlib.util
    from pathlib import Path
    
    path = Path(task_ideas_path)
    if not path.exists():
        print(f"Task research ideas file not found: {task_ideas_path}")
        return []
    
    try:
        # Load the module dynamically
        spec = importlib.util.spec_from_file_location("task_research_ideas", path)
        if spec is None or spec.loader is None:
            print(f"Could not load spec for: {task_ideas_path}")
            return []
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Try common naming patterns for task-specific ideas
        task_ideas = []
        for attr_name in dir(module):
            if attr_name.endswith('_RESEARCH_IDEAS') or attr_name == 'TASK_RESEARCH_IDEAS':
                potential_ideas = getattr(module, attr_name, None)
                if isinstance(potential_ideas, list) and len(potential_ideas) > 0:
                    # Verify they're ResearchIdea objects or similar
                    if hasattr(potential_ideas[0], 'id') and hasattr(potential_ideas[0], 'name'):
                        task_ideas = potential_ideas
                        print(f"Loaded {len(task_ideas)} task-specific research ideas from {attr_name}")
                        break
        
        return task_ideas
    except Exception as e:
        print(f"Error loading task-specific research ideas from {task_ideas_path}: {e}")
        return []


def merge_research_ideas(
    generic_ideas: List[ResearchIdea],
    task_ideas: List[ResearchIdea],
    task_priority: bool = True
) -> List[ResearchIdea]:
    """
    Merge generic and task-specific research ideas.
    
    Args:
        generic_ideas: Generic research ideas pool
        task_ideas: Task-specific research ideas
        task_priority: If True, task-specific ideas come first
    
    Returns:
        Merged list of research ideas
    """
    if task_priority:
        return task_ideas + generic_ideas
    else:
        return generic_ideas + task_ideas


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_ideas_by_category(category: str) -> List[ResearchIdea]:
    """Get all ideas in a specific category."""
    return [idea for idea in RESEARCH_IDEAS if idea.category == category]


def get_ideas_by_difficulty(difficulty: str) -> List[ResearchIdea]:
    """Get all ideas with a specific difficulty level."""
    return [idea for idea in RESEARCH_IDEAS if idea.difficulty == difficulty]


def get_easy_wins() -> List[ResearchIdea]:
    """Get easy-to-implement ideas with good expected gains."""
    return [idea for idea in RESEARCH_IDEAS if idea.difficulty == "easy"]


def format_for_llm_selection(
    current_approach: str = "",
    failed_approaches: List[str] = None,
    plateau_length: int = 0,
    ideas: List[ResearchIdea] = None,  # NEW: Custom ideas list (allows task-specific)
    title: str = "RESEARCH IDEAS POOL",  # NEW: Customizable title
) -> str:
    """
    Format research ideas for LLM to select from.
    
    Args:
        current_approach: Description of current best approach
        failed_approaches: List of previously tried approaches
        plateau_length: Number of generations without improvement
        ideas: Custom list of research ideas (defaults to RESEARCH_IDEAS if not provided)
        title: Custom title for the ideas pool
    
    Returns:
        Formatted string for LLM prompt
    """
    failed_approaches = failed_approaches or []
    
    # Use provided ideas or default to global RESEARCH_IDEAS
    ideas_to_format = ideas if ideas is not None else RESEARCH_IDEAS
    
    # Group by category
    categories = {}
    for idea in ideas_to_format:
        if idea.category not in categories:
            categories[idea.category] = []
        categories[idea.category].append(idea)
    
    lines = [
        f"# 馃敩 {title}",
        "",
        "Select ONE idea to implement based on:",
        f"- Current plateau length: {plateau_length} generations",
        f"- Current approach: {current_approach or 'Unknown'}",
        f"- Previously tried: {', '.join(failed_approaches) if failed_approaches else 'None'}",
        "",
        "---",
        "",
    ]
    
    for category, ideas in categories.items():
        lines.append(f"## {category.upper()}")
        lines.append("")
        
        for idea in ideas:
            # Skip if already tried
            if any(idea.name.lower() in f.lower() for f in failed_approaches):
                continue
            
            lines.append(f"### [{idea.id}] {idea.name}")
            lines.append(f"**Difficulty:** {idea.difficulty} | **Expected Gain:** {idea.expected_f1_gain}")
            lines.append(f"**Summary:** {idea.summary}")
            lines.append(f"**Key Insight:** {idea.key_insight}")
            lines.append("")
            lines.append("**Implementation Steps:**")
            for step in idea.implementation_steps:
                lines.append(f"  {step}")
            
            if idea.code_snippet:
                lines.append("")
                lines.append("**Code Snippet:**")
                lines.append("```python")
                lines.append(idea.code_snippet.strip())
                lines.append("```")
            
            lines.append("")
            lines.append("---")
            lines.append("")
    
    lines.append("")
    lines.append("# YOUR TASK")
    lines.append("")
    lines.append("1. Analyze the current situation")
    lines.append("2. Select the MOST PROMISING idea that:")
    lines.append("   - Has NOT been tried before")
    lines.append("   - Is appropriate for the current architecture")
    lines.append("   - Has reasonable difficulty for the expected gain")
    lines.append("")
    lines.append("3. Respond with:")
    lines.append("```json")
    lines.append('{')
    lines.append('  "selected_id": "<idea_id>",')
    lines.append('  "reasoning": "<why this idea is best for current situation>",')
    lines.append('  "implementation_plan": "<specific steps to implement>"')
    lines.append('}')
    lines.append("```")
    
    return "\n".join(lines)


def get_idea_by_id(idea_id: str) -> Optional[ResearchIdea]:
    """Get a specific idea by its ID."""
    for idea in RESEARCH_IDEAS:
        if idea.id == idea_id:
            return idea
    return None


def get_implementation_prompt(idea_id: str) -> str:
    """Get a detailed implementation prompt for a specific idea."""
    idea = get_idea_by_id(idea_id)
    if not idea:
        return f"Unknown idea ID: {idea_id}"
    
    lines = [
        f"# IMPLEMENT: {idea.name}",
        "",
        f"**Category:** {idea.category}",
        f"**Difficulty:** {idea.difficulty}",
        f"**Expected F1 Gain:** {idea.expected_f1_gain}",
        "",
        "## Key Insight",
        idea.key_insight,
        "",
        "## Implementation Steps",
    ]
    
    for step in idea.implementation_steps:
        lines.append(step)
    
    if idea.code_snippet:
        lines.append("")
        lines.append("## Reference Code")
        lines.append("```python")
        lines.append(idea.code_snippet.strip())
        lines.append("```")
    
    if idea.risks:
        lines.append("")
        lines.append("## Risks to Consider")
        for risk in idea.risks:
            lines.append(f"- {risk}")
    
    lines.append("")
    lines.append("## Requirements")
    lines.append("1. Implement the core idea following the steps above")
    lines.append("2. Preserve the existing evaluation interface")
    lines.append("3. Ensure the code compiles and runs correctly")
    lines.append("4. Focus on the EVOLVE-BLOCK region only")
    
    return "\n".join(lines)

