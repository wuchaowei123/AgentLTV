# Contributing to MTCS_module

Thank you for your interest in contributing to the MTCS_module! This document provides guidelines for contributing to the project.

## 🎯 Ways to Contribute

### 1. 🐛 Bug Reports

If you find a bug, please open an issue with:
- **Clear title** describing the problem
- **Steps to reproduce** the issue
- **Expected behavior** vs. **actual behavior**
- **Environment details**: OS, Python version, GPU info (if applicable)
- **Relevant logs** or error messages
- **Database state** (if relevant): Node counts, execution status

**Example Bug Report**:
```
Title: Tree Explorer shows only one node despite 20 in database

Environment:
- OS: Ubuntu 20.04
- Python: 3.10.16
- Browser: Chrome 120

Steps to Reproduce:
1. Run tree_search_explorer/app.py with --db official_run_v5_test.db
2. Open http://localhost:8005
3. Select database with 20 nodes
4. Tree visualization shows only 1 node

Expected: Should show all 20 nodes in tree
Actual: Only shows 1 node
```

### 2. ✨ Feature Requests

We welcome feature suggestions! Please open an issue with:
- **Problem statement**: What problem does this solve?
- **Proposed solution**: How would it work?
- **Use case**: When would this be useful?
- **Alternatives considered**: Other approaches you've thought about

### 3. 📝 Documentation Improvements

Documentation is critical! You can help by:
- Fixing typos or unclear sections
- Adding examples for common use cases
- Creating tutorials for specific domains
- Translating documentation to other languages

### 4. 🚀 Code Contributions

We accept pull requests for:
- Bug fixes
- New features (please discuss in an issue first)
- Performance improvements
- Test coverage
- Code quality improvements

## 💻 Development Setup

### Prerequisites

- Python 3.10+
- Conda (recommended)
- Git
- GPU (optional but recommended for testing)

### Setup Steps

```bash
# 1. Fork the repository on GitHub

# 2. Clone your fork
git clone https://github.com/<your-username>/MTCS_module.git
cd MTCS_module

# 3. Add upstream remote
git remote add upstream https://github.com/<original-repo>/MTCS_module.git

# 4. Create development environment
conda create -n scientific-ai-dev python=3.10 -y
conda activate scientific-ai-dev

# 5. Install dependencies
pip install -r requirements.txt

# 6. Install development dependencies (if any)
pip install pytest pytest-cov black flake8 mypy

# 7. Create a feature branch
git checkout -b feature/your-feature-name
```

## 🔄 Development Workflow

### 1. Before You Start

- **Check existing issues** to avoid duplicate work
- **Discuss major changes** in an issue before implementing
- **Keep changes focused**: One feature/fix per PR

### 2. Making Changes

```bash
# 1. Ensure you're on your feature branch
git checkout feature/your-feature-name

# 2. Pull latest changes from upstream
git fetch upstream
git rebase upstream/main

# 3. Make your changes
# Edit files...

# 4. Test your changes
python -m pytest tests/  # If tests exist
python universal_main_database.py --task tasks/custom_task/task_config.yaml --iterations 5

# 5. Format code (if using formatters)
black .
flake8 .

# 6. Commit changes
git add .
git commit -m "feat: Add feature description"
```

### 3. Commit Message Guidelines

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style (formatting, etc.)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples**:
```
feat(tree-search): Add adaptive C-PUCT scheduling

Implement dynamic C-PUCT adjustment based on search progress.
Early phase uses high exploration (C=2.5), late phase exploits (C=0.8).

Closes #42
```

```
fix(executor): Correct JSON result file naming

Changed from timestamped filenames to `_manual.json` suffix
to enable auto-detection of manual execution results.

Fixes #123
```

### 4. Submitting a Pull Request

```bash
# 1. Push your branch to your fork
git push origin feature/your-feature-name

# 2. Open a pull request on GitHub
# - Use a descriptive title
# - Reference any related issues
# - Provide context and testing details

# 3. Respond to review comments
# 4. Make requested changes
# 5. Push updates (will automatically update PR)
```

## 🧪 Testing Guidelines

### Running Tests

```bash
# Run all tests (when test suite exists)
pytest

# Run specific test file
pytest tests/test_tree_search.py

# Run with coverage
pytest --cov=core --cov-report=html
```

### Writing Tests

- Place tests in `tests/` directory
- Name test files `test_<module>.py`
- Use descriptive test names: `test_adaptive_cpuct_adjusts_correctly`
- Include both positive and negative test cases
- Mock external dependencies (LLM APIs, file I/O)

**Example Test**:
```python
def test_tree_search_selects_best_node():
    """Test that PUCT search selects the highest UCB node."""
    tree = TreeSearch(c_puct=1.5)
    node1 = Node(score=0.8, visits=10)
    node2 = Node(score=0.9, visits=5)
    
    selected = tree.select_node([node1, node2])
    
    assert selected == node2, "Should select node with higher UCB"
```

## 📋 Code Style Guidelines

### Python Style

- Follow **PEP 8** for general Python style
- Use **type hints** where possible
- Write **docstrings** for public functions/classes
- Keep functions **focused** and **small** (<50 lines ideally)
- Use **descriptive variable names**

**Example**:
```python
def calculate_ucb(node: Node, parent_visits: int, c_puct: float) -> float:
    """
    Calculate Upper Confidence Bound for a tree search node.
    
    Args:
        node: The node to calculate UCB for
        parent_visits: Number of times parent node was visited
        c_puct: Exploration constant (higher = more exploration)
    
    Returns:
        UCB score as a float
    
    Formula:
        UCB = Q(node) + c_puct * sqrt(log(N_parent) / N(node))
    """
    if node.visits == 0:
        return float('inf')
    
    exploitation = node.score / node.visits
    exploration = c_puct * math.sqrt(math.log(parent_visits) / node.visits)
    
    return exploitation + exploration
```

### File Organization

- **One class per file** (unless tightly coupled)
- **Group related functions** together
- **Order**: Imports → Constants → Classes → Functions → Main
- **Use meaningful file names**: `db_enhanced_search.py` not `search2.py`

## 🎯 Areas Needing Contributions

### High Priority

- [ ] **Test Coverage**: Write unit tests for core components
- [ ] **Docker Support**: Create Dockerfile for easy deployment
- [ ] **CI/CD Pipeline**: Set up GitHub Actions for testing
- [ ] **Example Tasks**: Add more task configuration examples
- [ ] **Error Handling**: Improve error messages and recovery

### Medium Priority

- [ ] **Performance Optimization**: Profile and optimize hot paths
- [ ] **Multi-GPU Support**: Parallel node execution
- [ ] **Cloud Integration**: AWS/GCP deployment guides
- [ ] **Alternative LLM Support**: Add more LLM providers
- [ ] **Visualization Enhancements**: More charts in Tree Explorer

### Documentation

- [ ] **Video Tutorials**: Screen recordings of common workflows
- [ ] **Domain-Specific Guides**: NLP, Computer Vision, Time Series
- [ ] **API Documentation**: Auto-generate from docstrings
- [ ] **FAQ**: Common questions and answers
- [ ] **Troubleshooting Database**: Searchable issue resolutions

## 🤝 Community Guidelines

### Be Respectful

- **Assume good intentions**
- **Be patient** with new contributors
- **Provide constructive feedback**
- **Celebrate contributions** of all sizes

### Communication

- **Use clear, concise language**
- **Ask questions** if anything is unclear
- **Provide context** when reporting issues
- **Update issues** if you find a solution

### Getting Help

- **Check documentation** first: [`gen_doc/`](gen_doc/)
- **Search existing issues** before opening new ones
- **Ask in discussions** for general questions
- **Tag issues** with `help-wanted` if you need assistance

## 📜 Legal

By contributing, you agree that your contributions will be licensed under the MIT License.

You confirm that:
- You have the right to submit the contribution
- Your contribution is your original work
- You understand the contribution is public and may be redistributed

## 🎉 Recognition

Contributors will be recognized in:
- **README.md** Contributors section
- **CHANGELOG.md** for significant contributions
- **Release notes** for feature contributions

Thank you for helping make the MTCS_module better! 🚀

---

**Questions?** Open a discussion or reach out to the maintainers.

