Of course. Here is a comprehensive Markdown file that organizes all the prompts and necessary information, as requested. This file is designed to be a complete reference for anyone looking to understand or implement the prompt engineering aspect of this AI system.

You can save this directly as a `.md` file (e.g., `ai_system_prompts.md`).

---

# AI System for Scientific Software: Complete Prompt Library

This document contains a comprehensive collection of all prompt templates and informational content used in the AI system described in the paper "An AI system to help scientists write expert-level empirical software."

## Table of Contents

1.  [Core Tree Search Prompts](#1-core-tree-search-prompts)
    *   [Prompt 1: Kick-starting a Task (Root Node Generation)](#prompt-1-kick-starting-a-task-root-node-generation)
    *   [Prompt 2: Iterative Code Mutation (Main Loop)](#prompt-2-iterative-code-mutation-main-loop)
2.  [Guiding & Advisory Prompts](#2-guiding--advisory-prompts)
    *   [Prompt 3: Guiding with General Expert Advice](#prompt-3-guiding-with-general-expert-advice)
    *   [Prompt 4: Guiding with Advanced Algorithmic Advice](#prompt-4-guiding-with-advanced-algorithmic-advice)
3.  [Research & Recombination Prompts](#3-research--recombination-prompts)
    *   [Prompt 5: Brainstorming Novel Research Ideas ("Deep Research")](#prompt-5-brainstorming-novel-research-ideas-deep-research)
    *   [Prompt 6: Summarizing and Structuring Research Ideas](#prompt-6-summarizing-and-structuring-research-ideas)
    *   [Prompt 7: Analyzing and Comparing Two Solutions (For Recombination)](#prompt-7-analyzing-and-comparing-two-solutions-for-recombination)
    *   [Prompt 8: Generating a Hybrid Solution (Recombination)](#prompt-8-generating-a-hybrid-solution-recombination)
4.  [Model Replication Prompts](#4-model-replication-prompts)
    *   [Prompt 9: Replicating an Existing Model from its Description](#prompt-9-replicating-an-existing-model-from-its-description)
5.  [Example Generated Content](#5-example-generated-content)
    *   [Content Example 1: Generated Summary of BBKNN Algorithm](#content-example-1-generated-summary-of-bbknn-algorithm)

---

## 1. Core Tree Search Prompts

These are the fundamental prompts used to start and run the main code generation loop.

### Prompt 1: Kick-starting a Task (Root Node Generation)
-   **Purpose:** To generate the very first piece of code (the "root node") for a given task.
-   **When to Use:** Once, at the very beginning of a new tree search.
-   **Source:** Supplementary Table 1.

```markdown
Please write the python code to work on a Kaggle competition. Use any model you like.
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

```

### Prompt 2: Iterative Code Mutation (Main Loop)
-   **Purpose:** The workhorse prompt. Asks the LLM to take existing code, analyze its performance, and rewrite it for a better score.
-   **When to Use:** In the "Expansion" step of every iteration of the tree search.
-   **Source:** Implied by the core logic of the paper. This is a practical template for implementation.

```markdown
You are an expert-level AI programmer. Your task is to improve a piece of Python code for a machine learning competition.

**Task Description:**
[Insert the full context from Prompt 1 here, e.g., competition name, metric, etc.]

**Previous Code:**
```python
[Insert code from the selected parent node here]
```

**Performance of Previous Code:**
The code above achieved a score of: [Insert score of the parent node here, e.g., 0.85 AUC]. A higher score is better.

**Your Goal:**
Rewrite the code to achieve a higher score. You can try a different model, add feature engineering, tune hyperparameters, or use any other strategy. The code MUST be a complete, runnable script.

Provide only the complete, raw Python code within a single code block. Do not add any explanation.
```

---

## 2. Guiding & Advisory Prompts

These prompts contain text that is **appended** to a core prompt (like Prompt 2) to provide strategic guidance.

### Prompt 3: Guiding with General Expert Advice
-   **Purpose:** To give the LLM high-level, strategic hints that a human expert might use.
-   **When to Use:** Inject this text into a core prompt to steer the LLM's creativity.
-   **Source:** Supplementary Table 2.

```markdown
Here is high level advice: Instead of putting all your effort into a single model, experiment with combining two or more models. Start with simple averaging of predictions and then explore more advanced techniques like stacking.
Try out several different types of models (e.g., gradient boosting machines, linear models, and even simpler models like logistic regression) to see how they perform.
Look for opportunities to go beyond standard preprocessing. Investigate the data for potential leaks, and consider using optimization libraries to find the best way to combine your models' predictions.
While feature engineering is a crucial skill, it's also important to recognize when it might not be the most important factor. Sometimes, the choice of model and ensembling strategy can have a bigger impact. Don't be afraid to try a more "brute-force" approach with powerful models that can handle raw data effectively.
```

### Prompt 4: Guiding with Advanced Algorithmic Advice
-   **Purpose:** To instruct the LLM to rewrite a library's internal algorithms from scratch.
-   **When to Use:** Inject this text for a very advanced tree search run, forcing first-principles reasoning.
-   **Source:** Supplementary Table 3.

```markdown
Given the code you are given please rewrite any library code (such as XGBoost, LightGBM, and CatBoost) by making internal algorithmic choices that produce performant training code and models that generalize well in many situations. Things you can try are alternative representations of data, using different step size algorithms, using the output of a strong learner as input to the next weak learner. If the code contains such libraries, please extract the raw code that is being used in the library and rewrite it to improve performance.
```

---

## 3. Research & Recombination Prompts

These are used for advanced "offline" tasks to prepare knowledge for the main search loop.

### Prompt 5: Brainstorming Novel Research Ideas ("Deep Research")
-   **Purpose:** To use an LLM for creative ideation, proposing new scientific methods.
-   **When to Use:** Before a tree search, to generate novel approaches for a complex scientific problem. The output is then processed by Prompt 6.
-   **Source:** Supplementary Table 12.

```markdown
I am developing new methods for winning single-cell batch integration competitions, as proposed by the Kaggle and extensively researched in the single-cell genomics community.

Briefly: Modelers are asked to develop a function, `eliminate_batch_effect_fn`, that transforms raw gene expression count data from multiple batches into a low-dimensional embedding or feature matrix. This transformed output should effectively remove technical variation (batch effects) while rigorously preserving biological information (e.g., cell type identity). The performance of these methods is evaluated against a suite of metrics that quantify both batch mixing and biological conservation.

[... The rest of the detailed problem description as seen in Supplementary Table 12 ...]

This task aims to develop a SUPERHUMAN METHOD for solving this problem.

Please give me 10 highly novel and creative ideas with detailed implementation notes for the set of methods I should explore for solving this task. I aim to create the best method for solving this problem, preferably creating the best ever method.
```

### Prompt 6: Summarizing and Structuring Research Ideas
-   **Purpose:** To process unstructured text (from a paper or another LLM) into a standardized format.
-   **When to Use:** As a processing step to convert human or AI-generated ideas into machine-readable instructions.
-   **Source:** Supplementary Tables 13 & 15.

```markdown
# Version for formatting ideas
Structure the given idea into the following format:
<description>
Your description about the method goes here.
</description>
<steps>
Your list of steps to implement the method goes here.
</steps>
<notes>
Strengths and weaknesses of the idea goes here.
</notes>

---
# Version for summarizing a paper
Given the following paper, please identify the main method being proposed. Then write a very short method description. This method description will be used to reproduce the method. DO NOT mention the algorithm by name.

Your output must follow this format:
<description>
Your very short description goes here.
</description>
<steps>
Your short list of steps goes here.
</steps>
```

### Prompt 7: Analyzing and Comparing Two Solutions (For Recombination)
-   **Purpose:** To have the LLM analyze two different, successful code solutions and articulate their core differences.
-   **When to Use:** The first step in the recombination workflow.
-   **Source:** Supplementary Table 6.

```markdown
Compare these two code solutions to the same problem of integrating single-cell batch effects. Explain the main principles that differ between the codes:

CODE 1: [CODE FROM BASELINE 1]
CODE 2: [CODE FROM BASELINE 2]
```

### Prompt 8: Generating a Hybrid Solution (Recombination)
-   **Purpose:** Takes the analysis from Prompt 7 and instructs the LLM to create a new, superior hybrid algorithm.
-   **When to Use:** The second step in recombination. The output of this prompt is then used to kick off a new tree search.
-   **Source:** Supplementary Table 14.

```markdown
We have up until now done experiments with two major types of codes, that are described in detail below. PLEASE CREATE AN ALGORITHM THAT USES THE BEST PARTS OF BOTH STRATEGIES TO CREATE A HYBRID STRATEGY THAT IS TRULY WONDERFUL AND SCORES HIGHER THAN EITHER OF THE INDIVIDUAL STRATEGIES.

[Insert the full analysis text generated by Prompt 7 here]
```

---

## 4. Model Replication Prompts

Used to test the system's ability to reproduce existing human-expert solutions from short descriptions.

### Prompt 9: Replicating an Existing Model from its Description
-   **Purpose:** To generate a working implementation of a specific method using only its brief public description.
-   **When to Use:** To kick-start a tree search focused on replicating and optimizing a known model. The `{method}` placeholder is filled with the target model's description.
-   **Source:** Supplementary Table 8.

```markdown
Please write the python code to work on a competition.
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
    """Make predictions for test_x by modeling train_x to train_y.
    Do not do any cross-validation in here.
    """
    mean_y = np.mean(train_y)
    return pd.Series([mean_y] * len(test_x), index=test_x.index)

# These will get scored by code that I supply. You'll get back a summary
# of the performance of each of them.

config_list = [{}]

And format it like this:

# YOUR CODE
# YOUR config_list
```

---

## 5. Example Generated Content

This is not a prompt, but an example of the *output* from Prompt 6, which then becomes *input* for another part of the system.

### Content Example 1: Generated Summary of BBKNN Algorithm
-   **Purpose:** To provide a structured summary of the BBKNN algorithm, ready for the AI coder to implement.
-   **Source:** Supplementary Table 16.

```markdown
<description>
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
</steps>
```