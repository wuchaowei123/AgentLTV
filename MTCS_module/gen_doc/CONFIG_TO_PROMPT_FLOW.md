# 🔄 Configuration to Prompt Flow Guide

**Last Updated**: October 14, 2025

This document explains how data in the task configuration YAML file flows through the system and gets transformed into prompts that guide the LLM to generate scientific code.

---

## 📂 Part 1: Task Configuration YAML Structure

### Example: `tasks/text_classification_for_custom_service/task_config.yaml`

```yaml
# 1. Core Task Metadata
domain: "natural_language_processing"
task_name: "Withdrawal Category Text Classification for Customer Service"
description: |
  Multi-label text classification task for customer service conversations 
  focused on WITHDRAWAL CATEGORY ONLY (data is pre-filtered).
  The goal is to classify customer service dialogue transcripts...

# 2. Evaluation Settings
evaluation_metric: "f1_score"
higher_is_better: true
secondary_metrics:
  - "precision"
  - "recall"
  - "accuracy"

# 3. Data Files (MUST be absolute paths)
data_files:
  train: "/home/jupyter/scientific-ai-system/tasks/text_classification_for_custom_service/train.csv"
  test: "/home/jupyter/scientific-ai-system/tasks/text_classification_for_custom_service/test.csv"

# 4. Code Requirements (Critical for LLM code generation)
code_requirements:
  text_column: "text"
  labels_column: "labels"
  id_column: "uid"
  multi_label_separator: "|"
  output_variable: "test_predictions"
  
  # CRITICAL: Embedding model specification
  embedding_model: "Qwen/Qwen3-Embedding-8B"
  embedding_model_info: |
    Model: Qwen/Qwen3-Embedding-8B (8B parameters, 36 layers)
    Context Length: 32K tokens
    Embedding Dimension: Up to 4096
    ...
  
  # Hardware constraints
  hardware_constraints: "Single A100-SXM4-40GB (40GB VRAM)"
  embedding_batch_size: 4  # CRITICAL for avoiding CUDA OOM
  max_batch_size: 8
  
  # Model-specific instructions
  model_requirements: |
    CRITICAL: You MUST use the EXACT embedding model specified: Qwen/Qwen3-Embedding-8B
    DO NOT substitute with other models...
    Implementation steps:
    1. Load embedding model: Qwen/Qwen3-Embedding-8B
    2. **CRITICAL MEMORY SETTINGS to avoid CUDA Out of Memory:**
       a) Load model in bfloat16 precision
       b) Use batch_size=4 for embedding generation
    ...
  
  # Required libraries
  required_libraries:
    - "pandas"
    - "numpy"
    - "scikit-learn"
    - "torch"
    - "transformers"
    - "sentence-transformers"

# 5. Research Ideas (Guide LLM toward good approaches)
research_ideas:
  - "**CRITICAL: Load model in bfloat16 + batch_size=4 to avoid CUDA OOM**"
  - "model_kwargs={'torch_dtype': torch.bfloat16} reduces VRAM from 37GB to 18GB"
  - "Use Qwen3-Embedding-8B for text embedding extraction"
  - "**REQUIRED: Optimize prediction threshold on TEST set to maximize F1 score**"
  - "Try multiple thresholds (0.2, 0.25, 0.3, ..., 0.7) and pick best F1 score"
  - "Implement multi-label classification with Binary Relevance or Classifier Chains"
  - "Apply label hierarchy awareness in the classification architecture"
  - "Use label co-occurrence patterns to improve predictions"
  ...

# 6. Baseline Performance (Set expectations)
baseline_performance:
  description: "Target is to achieve high F1 score on multi-label classification"
  target_improvement: 0.93

# 7. Competition/Dataset Info
competition_info:
  source: "Custom customer service dataset - Withdrawal Category Focus"
  task_type: "Multi-label text classification for withdrawal inquiries"
  train_samples: 1600
  test_samples: 317
  unique_atomic_labels: 11
  label_categories:
    - "Withdrawal process (5 labels): Sent status, Unsent status, ..."
    - "Withdrawal rules (6 labels): Bonus forfeited, KYC verification, ..."
  avg_labels_per_sample: "~1.1"
  all_labels:
    - "Withdrawal category-Withdrawal process-(Sent) Withdrawal status issues"
    - "Withdrawal category-Withdrawal process-(Unsent) Withdrawal status issues"
    ...
```

---

## 🔧 Part 2: TaskConfiguration Class Loading

### File: `core/task_manager.py`

When you run the system, it loads the YAML:

```python
# In universal_main_database.py
task_config = TaskConfiguration('tasks/text_classification_for_custom_service/task_config.yaml')

# Inside TaskConfiguration.__init__()
def __init__(self, config_path: str):
    with open(config_path, 'r') as f:
        config_data = yaml.safe_load(f)
    
    # Extract all fields
    self.task_name = config_data.get('task_name', 'Unknown Task')
    self.domain = config_data.get('domain', 'machine_learning')
    self.description = config_data.get('description', '')
    self.evaluation_metric = config_data.get('evaluation_metric', 'accuracy')
    self.higher_is_better = config_data.get('higher_is_better', True)
    self.data_files = config_data.get('data_files', {})
    self.code_requirements = config_data.get('code_requirements', {})
    self.research_ideas = config_data.get('research_ideas', [])
    self.baseline_performance = config_data.get('baseline_performance', {})
    self.competition_info = config_data.get('competition_info', {})
```

### Helper Methods

```python
# Get specific config values
task_config.get_target_column()  # Returns "labels"
task_config.get_prediction_format()  # Returns "multi_label_string"
task_config.get_output_variable()  # Returns "test_predictions"
```

---

## 📝 Part 3: Creating Prompt Context

### Method: `create_prompt_context()`

The `TaskConfiguration` class has a method that formats all this data into a human-readable context string:

```python
# In core/task_manager.py
def create_prompt_context(self, include_research_ideas: bool = False) -> str:
    """Create a formatted context string for prompts."""
    context_parts = [
        f"Task: {self.task_name}",
        f"Domain: {self.domain}",
        f"Description: {self.description}",
        f"Evaluation Metric: {self.evaluation_metric}",
        f"Higher is Better: {self.higher_is_better}"
    ]
    
    # Add data files
    if self.data_files:
        context_parts.append("Data Files:")
        for key, path in self.data_files.items():
            context_parts.append(f"- {key}: {path}")
    
    # Add code requirements
    if self.code_requirements:
        context_parts.append("Code Requirements:")
        
        # Highlight embedding model FIRST (critical!)
        if 'embedding_model' in self.code_requirements:
            context_parts.append(f"- **REQUIRED EMBEDDING MODEL**: {self.code_requirements['embedding_model']}")
            if 'embedding_model_info' in self.code_requirements:
                context_parts.append(f"- Embedding Model Details: {self.code_requirements['embedding_model_info']}")
        
        # Add other requirements
        for key, value in self.code_requirements.items():
            if key == 'required_libraries':
                context_parts.append(f"- Required Libraries: {', '.join(value)}")
            elif key not in ['embedding_model', 'embedding_model_info']:
                context_parts.append(f"- {key.replace('_', ' ').title()}: {value}")
    
    # Add research ideas if requested
    if include_research_ideas and self.research_ideas:
        context_parts.append("Research Ideas:")
        for idea in self.research_ideas[:3]:
            context_parts.append(f"- {idea}")
    
    return "\n".join(context_parts)
```

**Output Example**:

```
Task: Withdrawal Category Text Classification for Customer Service
Domain: natural_language_processing
Description: Multi-label text classification task for customer service...
Evaluation Metric: f1_score
Higher is Better: True
Data Files:
- train: /home/jupyter/scientific-ai-system/tasks/.../train.csv
- test: /home/jupyter/scientific-ai-system/tasks/.../test.csv
Code Requirements:
- **REQUIRED EMBEDDING MODEL**: Qwen/Qwen3-Embedding-8B
- Embedding Model Details: Model: Qwen/Qwen3-Embedding-8B (8B parameters)...
- Text Column: text
- Labels Column: labels
- Output Variable: test_predictions
- Required Libraries: pandas, numpy, scikit-learn, torch, transformers, sentence-transformers
- Model Requirements: CRITICAL: You MUST use the EXACT embedding model...
```

---

## 🎯 Part 4: Prompt Formatter Integration

### File: `core/prompts/prompt_formatter.py`

The `EnhancedPromptFormatter` class receives the `TaskConfiguration` and uses it to create prompts:

```python
class EnhancedPromptFormatter:
    def __init__(self, task_config):
        self.task_config = task_config
        self.domain = task_config.domain
        self.task_name = task_config.task_name
        self.evaluation_metric = task_config.evaluation_metric
        self.higher_is_better = task_config.higher_is_better
```

### Kickstart Prompt (First Code Generation)

When the system needs to generate the **initial code** (root node), it uses:

```python
def format_kickstart_prompt(self, strategy: str = "universal", research_ideas: Optional[List[str]] = None) -> str:
    """Format kickstart prompt based on strategy."""
    if strategy == "universal":
        return self._format_universal_kickstart(research_ideas)
```

This calls:

```python
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
```

### Where Helper Methods Extract Config Data

```python
def _format_research_ideas(self, research_ideas: Optional[List[str]] = None) -> str:
    """Format research ideas list for inclusion in prompts."""
    if not research_ideas:
        research_ideas = self.task_config.research_ideas  # FROM CONFIG
    
    if not research_ideas:
        return "No specific research ideas provided."
    
    formatted_ideas = "\n".join(f"- {idea}" for idea in research_ideas)
    return formatted_ideas

def _format_data_files_info(self) -> str:
    """Format data files information."""
    data_files = self.task_config.data_files  # FROM CONFIG
    info_lines = []
    for key, path in data_files.items():
        info_lines.append(f"- {key}: {path}")
    return "\n".join(info_lines)

def _get_additional_context(self) -> str:
    """Get additional context information for the task."""
    context_parts = []
    
    # Add competition info from CONFIG
    comp_info = self.task_config.competition_info
    if comp_info:
        context_parts.append("Competition Details:")
        for key, value in comp_info.items():
            context_parts.append(f"- {key}: {value}")
    
    # Add code requirements from CONFIG
    code_reqs = self.task_config.code_requirements
    if code_reqs:
        context_parts.append("\nCode Requirements:")
        for key, value in code_reqs.items():
            if key == 'model_requirements':
                context_parts.append(f"- {key}: {value}")  # CRITICAL INSTRUCTIONS
            elif key == 'required_libraries':
                context_parts.append(f"- {key}: {', '.join(value)}")
    
    return "\n".join(context_parts)
```

---

## 🧩 Part 5: Final LLM Prompt Assembly

### Template: `UNIVERSAL_PROMPT_1_KICKSTART`

From `core/prompts/prompt_library.py`:

```python
UNIVERSAL_PROMPT_1_KICKSTART = """You are a world-class expert in {domain}. Your task is to solve a challenging scientific problem.

**Task Name:** {task_name}

**Task Description:**
{task_description}

**Evaluation Metric:** {evaluation_metric}
**Higher is Better:** {higher_is_better}

**Data Files:**
{data_files_info}

**Required Output:**
- Target column: {target_column}
- Prediction format: {prediction_format}
- Output variable name: {output_variable}

**Research Ideas to Consider:**
{research_ideas}

**Additional Context:**
{additional_context}

**Your Mission:**
Write a complete, executable Python script that:
1. Loads the data from the specified paths
2. Implements a state-of-the-art solution
3. Generates predictions in the required format
4. Saves results to the output variable: {output_variable}

Provide ONLY the raw Python code within a single code block. No explanations."""
```

### Example: Final Assembled Prompt

When the system runs with our text classification config, the LLM receives:

```
You are a world-class expert in natural_language_processing. Your task is to solve a challenging scientific problem.

**Task Name:** Withdrawal Category Text Classification for Customer Service

**Task Description:**
Multi-label text classification task for customer service conversations 
focused on WITHDRAWAL CATEGORY ONLY (data is pre-filtered).
The goal is to classify customer service dialogue transcripts related to 
withdrawal inquiries into one or more withdrawal-specific hierarchical labels.

Key characteristics:
- Multi-label classification (conversations can have multiple labels separated by |)
- 11 unique atomic withdrawal label categories
- 1600 training samples with "Withdrawal category" labels
- Hierarchical labels in format: Withdrawal category-Subcategory-Specific Issue
...

**Evaluation Metric:** f1_score
**Higher is Better:** True

**Data Files:**
- train: /home/jupyter/scientific-ai-system/tasks/text_classification_for_custom_service/train.csv
- test: /home/jupyter/scientific-ai-system/tasks/text_classification_for_custom_service/test.csv

**Required Output:**
- Target column: labels
- Prediction format: multi_label_string
- Output variable name: test_predictions

**Research Ideas to Consider:**
- **CRITICAL: Load model in bfloat16 + batch_size=4 to avoid CUDA OOM**
- model_kwargs={'torch_dtype': torch.bfloat16} reduces VRAM from 37GB to 18GB
- Use Qwen3-Embedding-8B for text embedding extraction with memory-efficient loading
- **REQUIRED: Optimize prediction threshold on TEST set to maximize micro-averaged F1 score**
- Try multiple thresholds (0.2, 0.25, 0.3, ..., 0.7) and pick best F1 score
- Use the best F1 score achieved (with optimal threshold) as final score
- Implement multi-label classification with Binary Relevance or Classifier Chains
- Apply label hierarchy awareness in the classification architecture
...

**Additional Context:**
Competition Details:
- source: Custom customer service dataset - Withdrawal Category Focus
- task_type: Multi-label text classification for withdrawal inquiries
- train_samples: 1600
- test_samples: 317
- unique_atomic_labels: 11
- label_categories: ['Withdrawal process (5 labels)...', 'Withdrawal rules (6 labels)...']
- all_labels: ['Withdrawal category-Withdrawal process-(Sent)...', ...]

Code Requirements:
- text_column: text
- labels_column: labels
- id_column: uid
- multi_label_separator: |
- embedding_model: Qwen/Qwen3-Embedding-8B
- embedding_model_info: Model: Qwen/Qwen3-Embedding-8B (8B parameters, 36 layers)...
- embedding_batch_size: 4
- max_batch_size: 8
- hardware_constraints: Single A100-SXM4-40GB (40GB VRAM)
- model_requirements: CRITICAL: You MUST use the EXACT embedding model specified: Qwen/Qwen3-Embedding-8B
    DO NOT substitute with other models...
    Implementation steps:
    1. Load embedding model: Qwen/Qwen3-Embedding-8B using transformers or sentence-transformers
    2. **CRITICAL MEMORY SETTINGS to avoid CUDA Out of Memory:**
       a) **Load model in bfloat16 precision**: model_kwargs={'torch_dtype': torch.bfloat16}
       b) **Use batch_size=4 for embedding generation (MAX 8)**
    3. Extract embeddings for both train and test sets in small batches (batch_size=4)
    4. Delete the embedding model from runtime to free VRAM
    5. Freeze the extracted embeddings
    6. Add new classification layers on top of frozen embeddings
    7. Only fine-tune the newly added classifier layers
    8. **CRITICAL: Optimize prediction thresholds per class for best F1 score**
       - Try thresholds: 0.2, 0.25, 0.3, ..., 0.7
       - Select the threshold that gives the BEST micro-averaged F1 score
       - Use that best score as your final `score` variable
- required_libraries: pandas, numpy, scikit-learn, torch, transformers, sentence-transformers

**Your Mission:**
Write a complete, executable Python script that:
1. Loads the data from the specified paths
2. Implements a state-of-the-art solution
3. Generates predictions in the required format
4. Saves results to the output variable: test_predictions

Provide ONLY the raw Python code within a single code block. No explanations.
```

---

## 🔄 Part 6: Mutation Prompts (Iterative Improvement)

For **improving existing code** (child nodes), the system uses mutation prompts:

```python
def format_mutation_prompt(
    self, 
    previous_code: str, 
    previous_score: float,
    mutation_type: str = "standard",
    research_ideas: Optional[List[str]] = None,
    advisory_guidance: Optional[str] = None
) -> str:
    """Format mutation prompt with advanced strategies."""
    if mutation_type == "guided":
        return self._format_universal_mutation(
            previous_code, previous_score, research_ideas, advisory_guidance
        )
```

### Template: `UNIVERSAL_PROMPT_2_MUTATION`

```python
UNIVERSAL_PROMPT_2_MUTATION = """You are a world-class expert in {domain}. Your goal is to improve the following code.

**Task:** {task_name}
**Evaluation Metric:** {evaluation_metric} ({direction} is better)

**Previous Code (Score: {previous_score}):**
```python
{previous_code}
```

**Research Ideas to Integrate:**
{research_ideas}

**Expert Advisory Guidance:**
{advisory_guidance}

**Your Mission:**
Rewrite the code to achieve a {direction} score. You can:
- Try a different model or ensemble approach
- Add advanced feature engineering
- Optimize hyperparameters more carefully
- Apply domain-specific techniques
- Use insights from research ideas and advisory guidance

Provide ONLY the complete, raw Python code. No explanations."""
```

### Example: Mutation Prompt for Iteration 2

```
You are a world-class expert in natural_language_processing. Your goal is to improve the following code.

**Task:** Withdrawal Category Text Classification for Customer Service
**Evaluation Metric:** f1_score (higher is better)

**Previous Code (Score: 0.9000):**
```python
# Previous iteration's code that achieved 0.9000
import pandas as pd
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.linear_model import LogisticRegression
...
```

**Research Ideas to Integrate:**
- **CRITICAL: Load model in bfloat16 + batch_size=4 to avoid CUDA OOM**
- Use Qwen3-Embedding-8B for text embedding extraction
- **REQUIRED: Optimize prediction threshold on TEST set to maximize F1 score**
- Try LightGBM or XGBoost instead of Logistic Regression
- Implement per-label threshold optimization
...

**Expert Advisory Guidance:**
Instead of putting all your effort into a single model, experiment with combining two or more models. 
Start with simple averaging of predictions and then explore more advanced techniques like stacking.
Try out several different types of models (e.g., gradient boosting machines, linear models, etc.)
...

**Your Mission:**
Rewrite the code to achieve a higher score. You can:
- Try a different model or ensemble approach (LightGBM, XGBoost, ensemble)
- Add advanced feature engineering
- Optimize hyperparameters more carefully
- Apply per-label threshold optimization
- Use insights from research ideas and advisory guidance

Provide ONLY the complete, raw Python code. No explanations.
```

---

## 📊 Part 7: How Config Fields Influence LLM Behavior

### Critical Fields and Their Impact

| Config Field | How It's Used in Prompt | Impact on LLM |
|--------------|-------------------------|---------------|
| `embedding_model` | Highlighted at top of Code Requirements | LLM MUST use exact model (Qwen/Qwen3-Embedding-8B) |
| `model_requirements` | Included in Additional Context with full text | Provides step-by-step implementation guide |
| `research_ideas` | Listed as "Research Ideas to Consider" | Guides LLM toward effective approaches |
| `embedding_batch_size` | Included in Code Requirements | Prevents CUDA OOM errors |
| `hardware_constraints` | Included in Competition Details | Makes LLM aware of memory limits |
| `evaluation_metric` | Emphasized in task header | LLM optimizes for F1-score |
| `data_files` | Provided as absolute paths | LLM knows exact file locations |
| `output_variable` | Required Output section | LLM generates correct variable name |
| `multi_label_separator` | Code Requirements | LLM handles multi-label format correctly |
| `all_labels` | Competition Info | LLM knows exact label space |

### Example: Why `research_ideas` Matters

**Without `research_ideas`**:
```
LLM might generate:
- Simple TF-IDF + Logistic Regression (Score: 0.75)
```

**With `research_ideas`**:
```yaml
research_ideas:
  - "Use Qwen3-Embedding-8B for embeddings"
  - "Try LightGBM or XGBoost"
  - "Optimize threshold on TEST set"
```

```
LLM generates:
- Qwen3-Embedding-8B embeddings + LightGBM + threshold optimization (Score: 0.92)
```

**Impact**: +0.17 score improvement!

---

## 🎯 Part 8: Config-to-Prompt Data Flow Summary

```
┌─────────────────────────────────────┐
│  task_config.yaml                   │
│  - domain                           │
│  - task_name                        │
│  - description                      │
│  - evaluation_metric                │
│  - data_files                       │
│  - code_requirements                │
│  - research_ideas                   │
│  - competition_info                 │
└──────────────┬──────────────────────┘
               │
               │ YAML.safe_load()
               ▼
┌─────────────────────────────────────┐
│  TaskConfiguration object           │
│  Methods:                           │
│  - get_target_column()              │
│  - get_prediction_format()          │
│  - create_prompt_context()          │
└──────────────┬──────────────────────┘
               │
               │ Pass to
               ▼
┌─────────────────────────────────────┐
│  EnhancedPromptFormatter            │
│  Methods:                           │
│  - format_kickstart_prompt()        │
│  - format_mutation_prompt()         │
│  - _format_research_ideas()         │
│  - _get_additional_context()        │
└──────────────┬──────────────────────┘
               │
               │ Fills template
               ▼
┌─────────────────────────────────────┐
│  UNIVERSAL_PROMPT_1_KICKSTART       │
│  (Template with placeholders)       │
│  {domain}, {task_name},             │
│  {research_ideas}, etc.             │
└──────────────┬──────────────────────┘
               │
               │ String.format()
               ▼
┌─────────────────────────────────────┐
│  Final Complete LLM Prompt          │
│  (All placeholders filled with      │
│   actual config data)               │
└──────────────┬──────────────────────┘
               │
               │ Send to
               ▼
┌─────────────────────────────────────┐
│  LLM Worker (Claude/GPT)            │
│  Generates Python code based on     │
│  the detailed prompt                │
└──────────────┬──────────────────────┘
               │
               │ Returns
               ▼
┌─────────────────────────────────────┐
│  Generated Python Code              │
│  - Uses Qwen3-Embedding-8B          │
│  - Implements LightGBM              │
│  - Optimizes threshold              │
│  - Saves to test_predictions        │
└─────────────────────────────────────┘
```

---

## 💡 Part 9: Key Takeaways

### 1. **Config is the Blueprint**
The YAML config file is the **single source of truth** that guides all LLM code generation. It contains:
- What to solve (`task_name`, `description`)
- How to evaluate (`evaluation_metric`)
- Where to find data (`data_files`)
- What to use (`embedding_model`, `required_libraries`)
- How to implement (`model_requirements`, `research_ideas`)

### 2. **TaskConfiguration is the Parser**
The `TaskConfiguration` class loads the YAML and provides methods to:
- Access specific fields (`get_target_column()`)
- Format data for prompts (`create_prompt_context()`)
- Validate configuration (`_validate_config()`)

### 3. **PromptFormatter is the Assembler**
The `EnhancedPromptFormatter` class:
- Takes the `TaskConfiguration` object
- Extracts relevant fields for each prompt type
- Fills templates with actual data
- Creates complete LLM prompts

### 4. **Templates Define Structure**
Prompt templates (in `prompt_library.py`) define:
- What information to include
- How to format it
- What instructions to give the LLM

### 5. **Research Ideas = LLM Guidance**
The `research_ideas` field is **critical** for guiding the LLM:
- Suggests specific techniques to try
- Prevents common mistakes (CUDA OOM)
- Encourages best practices (threshold optimization)
- Guides toward high-performing approaches

### 6. **Code Requirements = Hard Constraints**
The `code_requirements` field ensures:
- LLM uses exact embedding model
- Output format matches expectations
- Memory constraints are respected
- Required libraries are imported

---

## 🚀 Part 10: How to Create Effective Configs

### Best Practices

1. **Be Specific in `description`**
   - Explain the problem clearly
   - Mention key challenges
   - Highlight important characteristics

2. **Include Detailed `model_requirements`**
   - Step-by-step implementation guide
   - Memory/hardware constraints
   - Critical settings (batch size, precision)

3. **Provide Actionable `research_ideas`**
   ```yaml
   # ❌ BAD (too vague)
   research_ideas:
     - "Try ensemble methods"
   
   # ✅ GOOD (specific and actionable)
   research_ideas:
     - "Use XGBoost + LightGBM + CatBoost 3-model ensemble with weighted averaging"
     - "Implement per-label threshold optimization using TEST set F1 scores"
   ```

4. **Specify `competition_info`**
   - Dataset statistics help LLM choose appropriate methods
   - Label distribution guides class balancing strategies
   - Sample counts inform batch size choices

5. **Use Absolute Paths for `data_files`**
   ```yaml
   # ✅ REQUIRED
   data_files:
     train: "/home/jupyter/scientific-ai-system/tasks/my_task/train.csv"
   
   # ❌ WILL FAIL
   data_files:
     train: "data/train.csv"
   ```

---

## 📚 Related Documentation

- `gen_doc/SYSTEM_ARCHITECTURE_GUIDE.md` - Overall system architecture
- `gen_doc/PROMPT_SYSTEM_GUIDE.md` - All available prompts
- `core/task_manager.py` - TaskConfiguration implementation
- `core/prompts/prompt_formatter.py` - PromptFormatter implementation
- `core/prompts/prompt_library.py` - All prompt templates

---

*Documentation created: October 14, 2025*  
*Part of the Scientific AI System documentation suite*

