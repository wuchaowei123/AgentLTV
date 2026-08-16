yi gai"""
AI System for Scientific Software: Complete Prompt Library

This module contains all prompt templates used in the AI system for automated
scientific software discovery. Each prompt is stored as a Python variable for
easy copy-paste usage.

Based on the paper: "An AI system to help scientists write expert-level empirical software"
"""

# =============================================================================
# 1. CORE TREE SEARCH PROMPTS
# =============================================================================

PROMPT_1_KICKSTART_TASK = """Please write the python code to work on a Kaggle competition. Use any model you like.
Kaggle competition name: Binary Classification of Machine Failures
The competition is evaluated as follows: Submissions are evaluated on area under the ROC curve between the predicted probability and the observed target.

Submission File
For each `id` in the test set, you must predict the probability of a `Machine failure`.
The file should contain a header and have the following format:

id, Machine failure
136429,0.5
136430,0.1
136431,0.9
etc.

Here are a few lines of each of the files:
file_name: sample_submission.csv
file_contents:
id, Machine failure
79996,0
100009,0
etc.
====
file_name: test.csv
file_contents:
etc.
====
file_name: train.csv
file_contents:
etc.
====
Please provide complete code that will generate the submission file in the format below:
```python
YOUR CODE
```"""

PROMPT_2_ITERATIVE_MUTATION = """You are an expert-level AI programmer. Your task is to improve a piece of Python code for a machine learning competition.

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

PROMPT_5_BRAINSTORM_RESEARCH_IDEAS = """I am developing new methods for winning single-cell batch integration competitions, as proposed by the Kaggle and extensively researched in the single-cell genomics community.

Briefly: Modelers are asked to develop a function, `eliminate_batch_effect_fn`, that transforms raw gene expression count data from multiple batches into a low-dimensional embedding or feature matrix. This transformed output should effectively remove technical variation (batch effects) while rigorously preserving biological information (e.g., cell type identity). The performance of these methods is evaluated against a suite of metrics that quantify both batch mixing and biological conservation.

This task aims to develop a SUPERHUMAN METHOD for solving this problem.

Please give me 10 highly novel and creative ideas with detailed implementation notes for the set of methods I should explore for solving this task. I aim to create the best method for solving this problem, preferably creating the best ever method."""

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

PROMPT_7_ANALYZE_SOLUTIONS = """Compare these two code solutions to the same problem of integrating single-cell batch effects. Explain the main principles that differ between the codes:

CODE 1: {code_1}
CODE 2: {code_2}"""

PROMPT_8_GENERATE_HYBRID = """We have up until now done experiments with two major types of codes, that are described in detail below. PLEASE CREATE AN ALGORITHM THAT USES THE BEST PARTS OF BOTH STRATEGIES TO CREATE A HYBRID STRATEGY THAT IS TRULY WONDERFUL AND SCORES HIGHER THAN EITHER OF THE INDIVIDUAL STRATEGIES.

{analysis_text}"""

# =============================================================================
# 4. MODEL REPLICATION PROMPTS
# =============================================================================

PROMPT_9_REPLICATE_MODEL = """Please write the python code to work on a competition.
{method}
I've already loaded the train / test files and split out the x and y parts.
Please provide a new definition for the function below, complete with imports, that will generalize well. However, do not do any cross-validation in here. Your function should expect options to be passed in via the config argument. I'll use cross-validation myself to select which of the options in the config_list generalizes best.
{method}

from typing import Any # Don't forget this!
import pandas as pd

def fit_and_predict_fn(
    train_x: pd.DataFrame,
    train_y: pd.Series,
    test_x: pd.DataFrame,
    config: dict[str, Any]) -> pd.Series:
    \"\"\"Make predictions for test_x by modeling train_x to train_y.
    Do not do any cross-validation in here.
    \"\"\"
    mean_y = np.mean(train_y)
    return pd.Series([mean_y] * len(test_x), index=test_x.index)

# These will get scored by code that I supply. You'll get back a summary
# of the performance of each of them.

config_list = [{}]

And format it like this:

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

Please provide complete, runnable Python code that addresses this scientific problem."""

UNIVERSAL_PROMPT_2_MUTATION = """You are an expert-level AI scientist and programmer. Your task is to improve a piece of Python code for a scientific computing problem.

**Scientific Domain:** {domain}
**Task:** {task_name}
**Evaluation Metric:** {evaluation_metric} ({"higher" if higher_is_better else "lower"} is better)

**Previous Code:**
```python
{previous_code}
```

**Performance of Previous Code:**
The code above achieved a {evaluation_metric} score of: {previous_score}.

**Your Goal:**
Rewrite the code to achieve a {"higher" if higher_is_better else "lower"} score. You can:
- Try different algorithms or models
- Improve data preprocessing and feature engineering
- Optimize hyperparameters
- Apply domain-specific techniques
- Use ensemble methods

**Research Ideas to Consider:**
{research_ideas}

The code MUST be a complete, runnable script that produces the required output format.

Provide only the complete, raw Python code within a single code block. Do not add any explanation."""

# =============================================================================
# 6. EXAMPLE STRUCTURED CONTENT
# =============================================================================

EXAMPLE_BBKNN_SUMMARY = """<description>
This method performs batch correction by modifying the neighborhood graph construction
step. For each cell, its nearest neighbors are identified independently within each batch, rather
than across the entire combined dataset. The resulting batch-specific neighbor lists for each
cell are then merged to create a single, integrated graph. This approach assumes that shared
cell types exist across batches and that biological differences are greater than technical batch
effects.
</description>

<steps>
1. For each cell, iterate through every batch in the dataset.
2. Find the k-nearest neighbors for the cell from within the current batch, based on a given
   distance metric (e.g., Euclidean distance in PCA space).
3. After iterating through all batches, merge the identified neighbor sets for the cell into a
   single neighborhood.
4. Repeat for all cells to construct a batch-corrected neighborhood graph.
</steps>"""

# =============================================================================
# 7. UTILITY FUNCTIONS FOR PROMPT FORMATTING
# =============================================================================

def format_universal_kickstart(domain, task_name, task_description, evaluation_metric, 
                              higher_is_better, data_files_info, target_column, 
                              prediction_format, output_variable, research_ideas):
    """Format the universal kickstart prompt with task-specific information."""
    return UNIVERSAL_PROMPT_1_KICKSTART.format(
        domain=domain,
        task_name=task_name,
        task_description=task_description,
        evaluation_metric=evaluation_metric,
        higher_is_better=higher_is_better,
        data_files_info=data_files_info,
        target_column=target_column,
        prediction_format=prediction_format,
        output_variable=output_variable,
        research_ideas=research_ideas
    )

def format_universal_mutation(domain, task_name, evaluation_metric, higher_is_better,
                             previous_code, previous_score, research_ideas):
    """Format the universal mutation prompt with task-specific information."""
    return UNIVERSAL_PROMPT_2_MUTATION.format(
        domain=domain,
        task_name=task_name,
        evaluation_metric=evaluation_metric,
        higher_is_better="higher" if higher_is_better else "lower",
        previous_code=previous_code,
        previous_score=previous_score,
        research_ideas=research_ideas
    )

def format_iterative_mutation(task_description, previous_code, previous_score):
    """Format the iterative mutation prompt with specific code and score."""
    return PROMPT_2_ITERATIVE_MUTATION.format(
        task_description=task_description,
        previous_code=previous_code,
        previous_score=previous_score
    )

def format_analyze_solutions(code_1, code_2):
    """Format the solution analysis prompt with two code solutions."""
    return PROMPT_7_ANALYZE_SOLUTIONS.format(
        code_1=code_1,
        code_2=code_2
    )

def format_generate_hybrid(analysis_text):
    """Format the hybrid generation prompt with analysis results."""
    return PROMPT_8_GENERATE_HYBRID.format(
        analysis_text=analysis_text
    )

def format_replicate_model(method):
    """Format the model replication prompt with method description."""
    return PROMPT_9_REPLICATE_MODEL.format(
        method=method
    )

# =============================================================================
# 8. PROMPT COLLECTIONS BY USE CASE
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

# =============================================================================
# 9. USAGE EXAMPLES
# =============================================================================

if __name__ == "__main__":
    # Example 1: Using a basic prompt
    print("=== PROMPT 1: KICKSTART TASK ===")
    print(PROMPT_1_KICKSTART_TASK)
    print("\n" + "="*50 + "\n")
    
    # Example 2: Using a formatted prompt
    print("=== FORMATTED MUTATION PROMPT ===")
    example_mutation = format_iterative_mutation(
        task_description="Binary Classification of Machine Failures",
        previous_code="# Simple logistic regression baseline",
        previous_score="0.85"
    )
    print(example_mutation)
    print("\n" + "="*50 + "\n")
    
    # Example 3: Universal prompt formatting
    print("=== UNIVERSAL KICKSTART PROMPT ===")
    universal_example = format_universal_kickstart(
        domain="Machine Learning",
        task_name="Binary Classification of Machine Failures",
        task_description="Predict machine failure probability based on sensor readings",
        evaluation_metric="AUC",
        higher_is_better=True,
        data_files_info="train.csv, test.csv, validation.csv",
        target_column="Machine failure",
        prediction_format="probabilities",
        output_variable="val_predictions",
        research_ideas="Use ensemble methods, apply feature engineering"
    )
    print(universal_example)