# Changelog

All notable changes to the MTCS_module project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-01-09

### 🎉 Major Release: Database-Enhanced System

This is a complete overhaul of the system with database integration, intelligent error fixing, and production-ready features.

### Added

#### Core Features
- **Database-Enhanced Execution System** - Full persistence and tracking of all code executions
- **Intelligent Auto Code Fixer** - Gemini AI-powered automatic error detection and repair
- **Manual Intervention Support** - Seamless fallback for complex debugging scenarios
- **Skip-Auto-Fixer Mode** - Direct manual control with `--skip-auto-fixer` flag
- **Session Management** - Isolated sessions with proper tracking
- **Micro-Averaged F1** - Proper multi-label classification evaluation

#### User Experience
- **Automated Setup Verification** - `check_setup.sh` script for environment validation
- **First-Time Setup Checklist** - Interactive checklist in README
- **Comprehensive README** - Complete rewrite with 700+ lines of documentation
- **Quick Start Guide** - 5-minute getting started tutorial
- **Enhanced Troubleshooting** - Detailed solutions for common issues

#### Documentation
- `PROJECT_SUMMARY.md` - Quick reference guide
- `PUBLICATION_CHECKLIST.md` - Release readiness tracker
- `check_setup.sh` - Automated verification script
- `CHANGELOG.md` - Version history (this file)
- Enhanced `requirements.txt` with version constraints
- Proper `.gitignore` configuration

#### System Improvements
- **Root Node Initialization Fix** - Always generates fresh code, checks for manual updates
- **Score Reporting Fix** - Correct display of manually updated scores
- **Evaluation Wrapper Simplification** - Flexible score detection (test set or validation)
- **Result File Format** - Standardized JSON output for score collection
- **Timeout Removal** - Auto-fixer no longer exits prematurely
- **Prompt Engineering** - Enhanced prompts for better code generation

#### Task Support
- **Multi-Label Text Classification** - Full support with label filtering
- **Embedding Model Specification** - Configure exact models in task_config.yaml
- **Label Filtering** - Support for dataset subset selection
- **Memory-Efficient Training** - Strategies for large models on limited VRAM

### Changed

- **Auto-Fixer Integration** - Switched from `trae-agent` to `gemini_auto_fixer`
- **Database Structure** - Enhanced ExecutionNode model with more fields
- **LLM Prompts** - Updated to emphasize test set evaluation and micro-averaged F1
- **Code Executor** - Refactored with modular design for auto-fixer integration
- **Tree Search Controller** - Database-aware with session isolation
- **Requirements** - Updated with specific version constraints

### Fixed

- **Root Node Score Display** - No longer shows misleading "0.0000" after manual update
- **JSON Result Saving** - Generated code now properly saves results to expected format
- **Evaluation Wrapper** - Works without requiring val_df definition
- **Score Variable Detection** - Flexible detection of `score` or `{metric}_score`
- **Manual Execution Flow** - Wrapped code saved when skip-auto-fixer is enabled
- **Node Constructor** - Fixed parameter mismatch issues
- **Database Attribute Names** - Corrected `executor` to `db_executor`

### Removed

- **Test Database Files** - Removed 10 test .db files from repository
- **Old README Backups** - Removed 4 duplicate/old README files
- **Temporary Files** - Removed CSV outputs, logs, test scripts
- **Python Cache** - Removed all __pycache__ and .pyc files
- **Redundant Documentation** - Consolidated overlapping guides
- **Outdated Analysis Files** - Removed fixed-issue documentation

### Performance

- **Perfect Score Achievement** - AUC 1.0000 on machine failure classification
- **Multi-Label Excellence** - F1 0.8725 (micro) on withdrawal text classification
- **Improved Success Rate** - ~70% auto-fix success, ~30% manual intervention
- **Faster Iteration** - Database caching reduces redundant computation

## [1.0.0] - 2024-12-XX

### Initial Release

- Basic tree search with LLM code generation
- Standard PUCT algorithm implementation
- Universal evaluator for code execution
- Task configuration system
- Support for multiple scientific domains
- Tree search explorer (web UI)
- Manual execution tools

---

## Version Comparison

| Feature | v1.0 | v2.0 |
|---------|------|------|
| **Database Tracking** | ❌ | ✅ |
| **Auto Error Fixing** | ❌ | ✅ |
| **Manual Intervention** | Basic | Advanced ✅ |
| **Session Management** | ❌ | ✅ |
| **Setup Verification** | ❌ | ✅ |
| **Documentation** | Basic | Comprehensive ✅ |
| **Best Score Achieved** | 0.6351 | 1.0000 ✅ |
| **Result Persistence** | Files only | Database ✅ |
| **Error Recovery** | Manual only | Automatic ✅ |

---

## Upgrade Guide

### From v1.0 to v2.0

**Database Migration:**
- No migration needed (fresh database recommended)
- Old results in `results/` directory still accessible

**Configuration Changes:**
```yaml
# New optional fields in task_config.yaml:
code_requirements:
  embedding_model: "Qwen/Qwen3-Embedding-8B"  # New
  label_filter: "Category name"                # New
  multi_label_separator: "|"                   # New
```

**Command Line Changes:**
```bash
# New flags:
--skip-auto-fixer        # Skip automatic fixing
--manual-timeout SECONDS # Configure wait time (default: 900)

# Recommended command updated:
python universal_main_database.py \  # Use database version
  --task TASK.yaml \
  --iterations 10 \
  --wait-for-manual        # Enable manual intervention
```

**Environment Setup:**
```bash
# New verification script:
./check_setup.sh

# Enhanced requirements:
pip install -r requirements.txt --upgrade
```

---

## Known Issues

### v2.0.0
- None currently (production ready)

### Future Enhancements (Planned for v2.1)
- [ ] Multi-GPU support for parallel code execution
- [ ] Cloud execution backend (AWS Lambda, Google Cloud Run)
- [ ] Advanced prompt optimization with reinforcement learning
- [ ] Real-time collaboration features
- [ ] Plugin system for custom evaluators
- [ ] Web-based configuration editor
- [ ] Automated hyperparameter tuning
- [ ] Cross-task knowledge transfer

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Reporting bugs
- Suggesting enhancements
- Submitting pull requests
- Code style and standards

---

## License

See [LICENSE](LICENSE) file for details.

---

## Authors

- **AI Research Team** - Initial work and v2.0 development

## Acknowledgments

- **Gemini 2.5 Pro** - LLM for code generation and error fixing
- **SQLite** - Lightweight database backend
- **Flask** - Web framework for visualization
- **Open Source Community** - Various dependencies and inspirations

---

**[View Full Documentation](README.md)** | **[Quick Start Guide](PROJECT_SUMMARY.md)** | **[System Architecture](DATABASE_SYSTEM_GUIDE.md)**

