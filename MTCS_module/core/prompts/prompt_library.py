"""
Complete Prompt Library for Universal MTCS_module
=========================================================

Enhanced version of the original prompts.py with additional domain-agnostic templates
and improved formatting capabilities.
"""

# =============================================================================
# 1. CORE TREE SEARCH PROMPTS
# =============================================================================

PROMPT_1_KICKSTART_TASK = """Please write the python code to work on a scientific computing task.

**Task Description:**
{task_description}

**Evaluation Metric:** {evaluation_metric}
**Higher is Better:** {higher_is_better}

**Data Information:**
{data_info}

**Requirements:**
- Target column: {target_column}
- Prediction format: {prediction_format}
- Required output variable: {output_variable}

Please provide complete code that will generate results in the required format:
```python
YOUR CODE
```"""

PROMPT_2_ITERATIVE_MUTATION = """You are an expert-level AI programmer. Your task is to improve a piece of Python code for a scientific computing problem.

**Task Description:**
{task_description}

**Previous Code:**
```python
{previous_code}
```

**Performance of Previous Code:**
The code above achieved a score of: {previous_score}. A higher score is better.

**Your Goal:**
Rewrite the code to achieve a higher score. You can try a different model, add feature engineering, tune hyperparameters, or use any other strategy. The code MUST be a complete, runnable script.

Provide only the complete, raw Python code within a single code block. Do not add any explanation."""

# =============================================================================
# 2. GUIDING & ADVISORY PROMPTS
# =============================================================================

PROMPT_3_GENERAL_EXPERT_ADVICE = """Here is high level advice: Instead of putting all your effort into a single model, experiment with combining two or more models. Start with simple averaging of predictions and then explore more advanced techniques like stacking.
Try out several different types of models (e.g., gradient boosting machines, linear models, and even simpler models like logistic regression) to see how they perform.
Look for opportunities to go beyond standard preprocessing. Investigate the data for potential leaks, and consider using optimization libraries to find the best way to combine your models' predictions.
While feature engineering is a crucial skill, it's also important to recognize when it might not be the most important factor. Sometimes, the choice of model and ensembling strategy can have a bigger impact. Don't be afraid to try a more "brute-force" approach with powerful models that can handle raw data effectively."""

PROMPT_4_ADVANCED_ALGORITHMIC_ADVICE = """Given the code you are given please rewrite any library code (such as XGBoost, LightGBM, and CatBoost) by making internal algorithmic choices that produce performant training code and models that generalize well in many situations. Things you can try are alternative representations of data, using different step size algorithms, using the output of a strong learner as input to the next weak learner. If the code contains such libraries, please extract the raw code that is being used in the library and rewrite it to improve performance."""

# =============================================================================
# 3. RESEARCH & RECOMBINATION PROMPTS  
# =============================================================================

PROMPT_5_BRAINSTORM_RESEARCH_IDEAS = """I am developing new methods for solving {domain} problems, specifically for {task_name}.

**Problem Description:**
{task_description}

**Current Challenge:**
Develop a SUPERHUMAN METHOD for solving this {domain} problem with evaluation metric {evaluation_metric}.

**Current State-of-the-Art:**
{baseline_info}

Please give me 10 highly novel and creative ideas with detailed implementation notes for the set of methods I should explore for solving this task. I aim to create the best method for solving this problem, preferably creating the best ever method.

Focus on:
- Novel algorithmic approaches specific to {domain}
- Advanced feature engineering techniques
- Ensemble and hybrid strategies
- Domain-specific optimizations
- Cutting-edge research directions"""

PROMPT_6_STRUCTURE_IDEAS = """Structure the given idea into the following format:
<description>
Your description about the method goes here.
</description>
<steps>
Your list of steps to implement the method goes here.
</steps>
<notes>
Strengths and weaknesses of the idea goes here.
</notes>"""

PROMPT_6_SUMMARIZE_PAPER = """Given the following paper, please identify the main method being proposed. Then write a very short method description. This method description will be used to reproduce the method. DO NOT mention the algorithm by name.

Your output must follow this format:
<description>
Your very short description goes here.
</description>
<steps>
Your short list of steps goes here.
</steps>"""

PROMPT_7_ANALYZE_SOLUTIONS = """Compare these two code solutions to the same {domain} problem. Explain the main principles that differ between the codes:

**Solution A:**
```python
{code_1}
```

**Solution B:**
```python
{code_2}
```

**Analysis Focus:**
- Different algorithmic approaches
- Feature engineering strategies  
- Model architectures and ensembling
- Preprocessing and data handling
- Domain-specific optimizations

Provide a detailed analysis of what makes each approach unique and which aspects could be combined."""

PROMPT_8_GENERATE_HYBRID = """We have experimented with multiple strategies for solving this {domain} problem. PLEASE CREATE AN ALGORITHM THAT USES THE BEST PARTS OF ALL STRATEGIES TO CREATE A HYBRID STRATEGY THAT IS TRULY WONDERFUL AND SCORES HIGHER THAN ANY OF THE INDIVIDUAL STRATEGIES.

**Previous Solutions Analysis:**
{analysis_text}

**Your Task:**
Create a comprehensive hybrid approach that intelligently combines:
1. The best algorithmic insights from each solution
2. Complementary feature engineering techniques
3. Optimal ensemble strategies
4. Domain-specific optimizations

The hybrid should be more than the sum of its parts - it should create synergies between different approaches."""

# =============================================================================
# 4. MODEL REPLICATION PROMPTS
# =============================================================================

PROMPT_9_REPLICATE_MODEL = """Please write the python code to work on a {domain} problem.

**Method to Replicate:**
{method}

**Task Context:**
{task_description}

I've already loaded the train / test files and split out the x and y parts.
Please provide a new definition for the function below, complete with imports, that will generalize well. However, do not do any cross-validation in here. Your function should expect options to be passed in via the config argument. I'll use cross-validation myself to select which of the options in the config_list generalizes best.

from typing import Any
import pandas as pd

def fit_and_predict_fn(
    train_x: pd.DataFrame,
    train_y: pd.Series,
    test_x: pd.DataFrame,
    config: dict[str, Any]) -> pd.Series:
    \"\"\"Make predictions for test_x by modeling train_x to train_y.
    Do not do any cross-validation in here.
    \"\"\"
    # YOUR IMPLEMENTATION HERE
    mean_y = train_y.mean()
    return pd.Series([mean_y] * len(test_x), index=test_x.index)

# These will get scored by code that I supply. You'll get back a summary
# of the performance of each of them.

config_list = [{{}}]

Format your response as:
# YOUR CODE
# YOUR config_list"""

# =============================================================================
# 5. UNIVERSAL TEMPLATES (Domain-Agnostic Versions)
# =============================================================================

UNIVERSAL_PROMPT_1_KICKSTART = """Please write Python code to solve the following scientific task:

**Domain:** {domain}
**Task:** {task_name}
**Description:** {task_description}

**Evaluation Metric:** {evaluation_metric}
**Higher is Better:** {higher_is_better}

**Data Files:**
{data_files_info}

**Requirements:**
- Target column: {target_column}
- Prediction format: {prediction_format}
- Required output variable: {output_variable}

**Research Ideas to Consider:**
{research_ideas}

**Additional Context:**
{additional_context}

Please provide complete, runnable Python code that addresses this scientific problem."""

UNIVERSAL_PROMPT_2_MUTATION = """You are an expert-level AI scientist and programmer. Your task is to improve a piece of Python code for a scientific computing problem.

**Scientific Domain:** {domain}
**Task:** {task_name}
**Evaluation Metric:** {evaluation_metric} ({direction} is better)

**Previous Code:**
```python
{previous_code}
```

**Performance of Previous Code:**
The code above achieved a {evaluation_metric} score of: {previous_score}.

**Your Goal:**
Rewrite the code to achieve a {direction} score. You can:
- Try different algorithms or models
- Improve data preprocessing and feature engineering
- Optimize hyperparameters
- Apply domain-specific techniques
- Use ensemble methods

**Research Ideas to Consider:**
{research_ideas}

**Advisory Guidance:**
{advisory_guidance}

The code MUST be a complete, runnable script that produces the required output format.

Provide only the complete, raw Python code within a single code block. Do not add any explanation."""

# =============================================================================
# 6. PROMPT COLLECTIONS BY USE CASE  
# =============================================================================

CORE_PROMPTS = {
    "kickstart": PROMPT_1_KICKSTART_TASK,
    "mutation": PROMPT_2_ITERATIVE_MUTATION,
}

ADVISORY_PROMPTS = {
    "general_advice": PROMPT_3_GENERAL_EXPERT_ADVICE,
    "algorithmic_advice": PROMPT_4_ADVANCED_ALGORITHMIC_ADVICE,
}

RESEARCH_PROMPTS = {
    "brainstorm": PROMPT_5_BRAINSTORM_RESEARCH_IDEAS,
    "structure_ideas": PROMPT_6_STRUCTURE_IDEAS,
    "summarize_paper": PROMPT_6_SUMMARIZE_PAPER,
    "analyze_solutions": PROMPT_7_ANALYZE_SOLUTIONS,
    "generate_hybrid": PROMPT_8_GENERATE_HYBRID,
}

REPLICATION_PROMPTS = {
    "replicate_model": PROMPT_9_REPLICATE_MODEL,
}

UNIVERSAL_PROMPTS = {
    "universal_kickstart": UNIVERSAL_PROMPT_1_KICKSTART,
    "universal_mutation": UNIVERSAL_PROMPT_2_MUTATION,
}

ALL_PROMPTS = {
    **CORE_PROMPTS,
    **ADVISORY_PROMPTS,
    **RESEARCH_PROMPTS,
    **REPLICATION_PROMPTS,
    **UNIVERSAL_PROMPTS,
}