# EA Module - Evolutionary Algorithm Module for AgentLTV

## Overview

This is the **Evolutionary Algorithm (EA) Module** of the [AgentLTV](https://github.com/wuchaowei123/AgentLTV) framework. It refines the best program discovered by the MCTS module through island-based evolutionary search with crossover, mutation, and migration.

The EA module maintains a population of programs that evolve over generations, with LLMs acting as intelligent mutation operators that suggest code improvements. It features:

- **Multi-island evolution** for diversity preservation
- **Inter-island migration** for knowledge sharing
- **LLM-guided crossover and mutation** for intelligent code refinement
- **Archive-based inspiration** for cross-generational learning
- **Parallel evaluation** with local or Slurm cluster support

## AgentLTV Framework

AgentLTV is an automated multi-agent search-then-evolution framework for Lifetime Value (LTV) prediction. It consists of two decision agents:

1. **MCTS Agent** (`../MTCS_module/`): Explores a broad space of modeling choices using Monte Carlo Tree Search with PUCT criterion
2. **EA Agent** (`EA_module/`): Refines the best MCTS program via island-based evolution

The two stages form a **search-then-evolution** pipeline: MCTS performs broad exploration under a fixed budget, and EA refines the best solution for stable improvement.

## Installation

```bash
cd EA_module
pip install -e .
```

## Quick Start

### Python API

```python
from ea.core import EvolutionRunner, EvolutionConfig
from ea.database import DatabaseConfig
from ea.launch import LocalJobConfig

# Configure the evolution
job_config = LocalJobConfig(eval_program_path="evaluate.py")
db_config = DatabaseConfig()
evo_config = EvolutionConfig(
    init_program_path="initial.py",
    num_generations=10,
    max_parallel_jobs=2,
)

# Run evolution
runner = EvolutionRunner(
    evo_config=evo_config,
    job_config=job_config,
    db_config=db_config,
)
runner.run()
```

### Command Line

```bash
# Run with pre-configured variant
ea_launch variant=circle_packing_example

# Run with custom parameters
ea_launch \
    task=circle_packing \
    database=island_large \
    evolution=small_budget \
    cluster=local \
    evo_config.num_generations=20
```

## Configuration

The EA module uses [Hydra](https://hydra.cc/) for configuration. Key configuration options:

### EvolutionConfig

| Key | Default | Description |
|-----|---------|-------------|
| `num_generations` | 10 | Number of evolution generations |
| `max_parallel_jobs` | 2 | Maximum parallel evaluation jobs |
| `patch_types` | `["diff"]` | Types of patches: "diff", "full", "cross" |
| `llm_models` | `["azure-gpt-4.1-mini"]` | LLM models for code generation |
| `init_program_path` | `"initial.py"` | Path to initial program |

### DatabaseConfig

| Key | Default | Description |
|-----|---------|-------------|
| `num_islands` | 4 | Number of evolution islands |
| `archive_size` | 100 | Program archive size per island |
| `elite_selection_ratio` | 0.3 | Proportion of elite programs |
| `migration_interval` | 10 | Generations between migrations |

## Project Structure

```
EA_module/
├── ea/                          # Main package
│   ├── core/                    # Core evolution logic
│   │   ├── runner.py            # EvolutionRunner + EvolutionConfig
│   │   ├── sampler.py           # Prompt sampling
│   │   ├── wrap_eval.py         # Evaluation wrapper
│   │   ├── adaptive_patch.py    # Adaptive patch selection
│   │   ├── summarizer.py        # Meta-recommendations
│   │   └── novelty_judge.py     # Novelty assessment
│   ├── database/                # Program database
│   │   ├── dbase.py             # ProgramDatabase
│   │   ├── islands.py           # Island management
│   │   ├── parents.py           # Parent selection
│   │   └── inspirations.py      # Context selection
│   ├── launch/                  # Job scheduling
│   │   ├── local.py             # Local execution
│   │   ├── slurm.py             # Slurm cluster execution
│   │   └── scheduler.py         # Job scheduler
│   ├── llm/                     # LLM client
│   ├── edit/                    # Code patching
│   ├── prompts/                 # Prompt templates
│   ├── utils/                   # Utilities
│   ├── plots/                   # Visualization
│   ├── webui/                   # Web interface
│   ├── knowledge/               # Knowledge management
│   └── kosmos/                  # Analysis tools
├── configs/                     # Hydra configurations
├── examples/                    # Example tasks
├── tests/                       # Test suite
├── docs/                        # Documentation
├── pyproject.toml               # Package configuration
└── README.md                    # This file
```

## Citation

If you use AgentLTV in your research, please cite:

```bibtex
@inproceedings{wu2026agentltv,
  title={An Automated Multi-Agent Search-then-Evolution Framework for Lifetime Value Prediction},
  author={Wu, Chaowei and Chen, Huazhu and Yang, Qirui and Li, Jiahui and Luo, Li and Guo, Mengzhuo},
  booktitle={Proceedings of the 35th ACM International Conference on Information and Knowledge Management (CIKM '26)},
  year={2026}
}
```

## Acknowledgments

This module builds upon ideas from the evolutionary computation and LLM-based code generation communities. We thank the authors of [EAFramework](https://arxiv.org/abs/2509.19349) for their foundational work on LLM-guided evolutionary search.

## License

MIT License - See [LICENSE](LICENSE) for details.
