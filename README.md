# AgentLTV

**An Automated Multi-Agent Search-then-Evolution Framework for Lifetime Value Prediction**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Paper](https://img.shields.io/badge/paper-CIKM%20'26-B31B1B.svg)](https://doi.org/10.1145/3799682.3841119)

---

## Overview

AgentLTV is an automated multi-agent framework for Lifetime Value (LTV) prediction. It treats each candidate solution as an **executable pipeline program** and uses LLM-driven agents to generate, execute, and refine code. Two decision agents coordinate a **two-stage search**:

1. **MCTS Module** (`MTCS_module/`): Explores a broad space of modeling choices using Monte Carlo Tree Search with the PUCT criterion and a Pareto-aware multi-metric value function.
2. **EA Module** (`EA_module/`): Refines the best MCTS program via island-based evolution with crossover, mutation, and migration.

The framework is designed to handle **negative LTV values**, **scenario-dependent data distributions**, and **complex feature interactions** without manual feature engineering or hyperparameter tuning.

---

## Key Features

- **Two-Stage Search**: MCTS for broad exploration, EA for stable refinement
- **Multi-Agent Architecture**: Code Generator, Code Fixer, Adviser Agent, Expert Optimizer, MCTS Agent, and EA Agent
- **Execution-Grounded**: All generated code is executed and evaluated with real metrics
- **Negative LTV Support**: Explicitly handles negative LTV values common in advertising and short-video platforms
- **Multi-Objective Optimization**: Pareto-aware reward with ranking and error metrics
- **Island-Based Evolution**: Multi-island diversity preservation with inter-island migration
- **LLM-Driven Code Generation**: Supports Claude, GPT-4, Gemini, and other LLMs
- **Auto-Fixing**: Automatic error detection and code repair with retry logic
- **WebUI**: Real-time visualization of search progress and results
- **Database-Enhanced**: Full execution history with resume capability

---

## Framework Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AgentLTV Framework                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Configuration Module                              │    │
│  │  Instantiates agents, LLM APIs, and execution interfaces             │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                        │
│                    ┌───────────────┴───────────────┐                        │
│                    ▼                               ▼                        │
│  ┌─────────────────────────────┐  ┌─────────────────────────────────────┐  │
│  │      MCTS Module            │  │           EA Module                  │  │
│  │      (MTCS_module/)          │  │           (EA_module/)               │  │
│  │                             │  │                                      │  │
│  │  • PUCT-guided tree search  │  │  • Island-based evolution            │  │
│  │  • Pareto-aware reward      │  │  • Crossover & mutation              │  │
│  │  • Multi-root initialization│  │  • Inter-island migration            │  │
│  │  • Adaptive exploration     │  │  • Archive-based inspiration         │  │
│  │                             │  │                                      │  │
│  │  Output: Best program       │  │  Output: Refined program            │  │
│  │          c_MCTS             │  │          c*                         │  │
│  └──────────────┬──────────────┘  └──────────────┬──────────────────────┘  │
│                 │                                 │                         │
│                 └───────────────┬─────────────────┘                         │
│                                 ▼                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Auxiliary Agents                                  │    │
│  │  • Code Generator    • Code Fixer    • Adviser Agent                 │    │
│  │  • Expert Optimizer  • Execution & Evaluation                        │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Installation

### Prerequisites

- Python 3.10+
- LLM API access (Claude, GPT-4, or Gemini)
- 8 GB+ RAM (16 GB+ recommended)

### Setup

```bash
# Clone the repository
git clone https://github.com/wuchaowei123/AgentLTV.git
cd AgentLTV

# Create environment
conda create -n agentltv python=3.10 -y
conda activate agentltv

# Install MCTS module dependencies
cd MTCS_module
pip install -r requirements.txt
cd ..

# Install EA module
cd EA_module
pip install -e ..
cd ..
```

### Configure LLM API

```bash
# For Claude
export ANTHROPIC_AUTH_TOKEN="sk-ant-your-api-key"

# For OpenAI
export OPENAI_API_KEY="sk-your-openai-key"

# For Gemini
export GOOGLE_API_KEY="your-gemini-api-key"
```

---

## Quick Start

### Stage 1: MCTS Exploration

```bash
cd MTCS_module
python universal_main_database.py \
  --task tasks/your_task/task_config.yaml \
  --iterations 133 \
  --db-path mcts_results.db
```

### Stage 2: EA Refinement

```bash
cd EA_module
python -c "
from ea.core import EvolutionRunner, EvolutionConfig
from ea.database import DatabaseConfig
from ea.launch import LocalJobConfig

job_config = LocalJobConfig(eval_program_path='evaluate.py')
db_config = DatabaseConfig()
evo_config = EvolutionConfig(
    init_program_path='best_mcts_program.py',
    num_generations=10,
    max_parallel_jobs=2,
)

runner = EvolutionRunner(
    evo_config=evo_config,
    job_config=job_config,
    db_config=db_config,
)
runner.run()
"
```

---

## Project Structure

```
AgentLTV/
├── MTCS_module/              # MCTS Module
│   ├── core/                 # Tree search, prompts, LLM worker
│   ├── tasks/                # Task configurations
│   ├── tree_search_explorer/ # Web visualization
│   ├── universal_main.py     # Main entry point
│   └── requirements.txt
│
├── EA_module/                # EA Module
│   ├── ea/                   # Core package
│   │   ├── core/             # Evolution runner, sampler, evaluator
│   │   ├── database/         # Program database, islands, parents
│   │   ├── launch/           # Job scheduling (local/Slurm)
│   │   ├── llm/              # LLM client
│   │   ├── edit/             # Code patching
│   │   ├── prompts/          # Prompt templates
│   │   ├── utils/            # Utilities
│   │   ├── webui/            # Web interface
│   │   └── ...
│   ├── configs/              # Hydra configurations
│   ├── examples/             # Example tasks
│   ├── tests/                # Test suite
│   └── README.md
│
├── README.md                 # This file
└── requirements.txt
```

---

## Modules

### MCTS Module (`MTCS_module/`)

The MCTS module performs broad exploration over LTV pipeline programs:

- **Multi-Root Initialization**: Generates K diverse root programs using Code Generator
- **PUCT Selection**: Balances exploration and exploitation with adaptive C-PUCT
- **Pareto-Aware Reward**: Combines multiple metrics with Pareto frontier and diversity
- **LLM-Driven Expansion**: Uses Adviser Agent and Expert Optimizer to guide code generation
- **Backpropagation**: Updates node values along the search path

### EA Module (`EA_module/`)

The EA module refines the best MCTS program through evolutionary search:

- **Multi-Island Initialization**: Creates K mutated variants of the best MCTS program
- **Code Evolution**: Evaluates, selects elites, and generates offspring via crossover/mutation
- **Inter-Island Migration**: Periodically transfers high-fitness programs between islands
- **Archive-Based Inspiration**: Uses successful programs as inspiration for new generations
- **Novelty Assessment**: Rejects similar programs to maintain diversity

---

## Agents

| Agent | Role |
|-------|------|
| **Code Generator** | Generates or modifies executable pipeline code |
| **Code Fixer** | Executes and repairs programs, ensures executability |
| **Adviser Agent** | Analyzes code and metrics, proposes optimization suggestions |
| **Expert Optimizer** | Injects LTV domain knowledge, converts suggestions to prompts |
| **MCTS Agent** | Implements MCTS loop, selects nodes using PUCT |
| **EA Agent** | Implements island-based evolutionary search |

---

## Evaluation Metrics

AgentLTV optimizes multiple metrics simultaneously:

| Metric | Description |
|--------|-------------|
| **ER** | Error Rate: sum of absolute errors / sum of absolute labels |
| **Norm Gini** | Normalized Gini coefficient for ranking quality |
| **Spearman** | Spearman rank-order correlation |
| **RMSE** | Root Mean Squared Error |

---

## Experiments

### Datasets

- **Industrial Dataset**: Large-scale proprietary dataset from a mobile game (~800K users, 132 features)
- **Public Benchmark**: Publicly available LTV prediction dataset

### Baselines

- Wide&Deep, DeepFM, ZILN, DCN, GateNet
- Kuaishou, TSUR, OptDist, USE-LTV, HiLTV

### Results

AgentLTV consistently discovers strong LTV models across ranking and error metrics, with improved online bucket-level ranking consistency and calibration.

---

## Citation

If you use AgentLTV in your research, please cite:

```bibtex
@inproceedings{wu2026agentltv,
  title={An Automated Multi-Agent Search-then-Evolution Framework for Lifetime Value Prediction},
  author={Wu, Chaowei and Chen, Huazhu and Yang, Qirui and Li, Jiahui and Luo, Li and Guo, Mengzhuo},
  booktitle={Proceedings of the 35th ACM International Conference on Information and Knowledge Management (CIKM '26)},
  year={2026},
  month={November},
  location={Rome, Italy},
  doi={10.1145/3799682.3841119},
  isbn={979-8-4007-2539-5/2026/11}
}
```

---

## License

MIT License - See [LICENSE](LICENSE) for details.

---

## Acknowledgments

- Claude, GPT-4, and Gemini for LLM-powered code generation
- SQLite for robust data persistence
- The evolutionary computation and LLM-based code generation communities

---

## Contact

- Chaowei Wu (wuchaowei@stu.scu.edu.cn)
- Mengzhuo Guo (mengzhguo@scu.edu.cn) - Corresponding author
