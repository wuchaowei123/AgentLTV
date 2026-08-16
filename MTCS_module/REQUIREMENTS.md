# Requirements for MTCS_module

## 📋 System Requirements

### Minimum Requirements

| Component | Requirement | Notes |
|-----------|-------------|-------|
| **OS** | Linux (Ubuntu 20.04+) / macOS / Windows with WSL2 | Linux recommended for best performance |
| **Python** | 3.10+ | Python 3.9 may work but 3.10+ recommended |
| **RAM** | 8 GB | 16 GB+ recommended for large tasks |
| **Storage** | 5 GB free | More needed for task-specific data |
| **Internet** | Required | For LLM API access |

### Recommended Requirements

| Component | Requirement | Why |
|-----------|-------------|-----|
| **RAM** | 16-32 GB | Better for embedding models and large datasets |
| **GPU** | NVIDIA GPU with 8GB+ VRAM | 10-50x faster for deep learning tasks |
| **CUDA** | 11.8+ | Required for GPU acceleration |
| **Storage** | 50 GB+ SSD | Fast I/O for databases and models |

---

## 🐍 Python Dependencies

### Core Dependencies (Required)

Install with: `pip install -r requirements.txt`

```
# Core Scientific Computing
pandas>=2.0.0              # Data manipulation
numpy>=1.24.0              # Numerical computing
scikit-learn>=1.3.0        # Machine learning algorithms

# LLM and API Integration
anthropic>=0.18.0          # Claude API client
requests>=2.31.0           # HTTP requests

# Configuration and Data
pyyaml>=6.0                # YAML config parsing
pydantic>=2.0.0            # Data validation

# Web UI (Tree Search Explorer)
flask>=2.3.0               # Web framework
jinja2>=3.1.0              # Templating engine

# Utilities
tqdm>=4.65.0               # Progress bars
colorama>=0.4.6            # Colored terminal output
```

**Total Size**: ~100 MB

---

## 🚀 Optional Dependencies

### For Deep Learning Tasks (NLP, Computer Vision)

```bash
pip install torch>=2.0.0 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install transformers>=4.30.0
pip install sentence-transformers>=2.2.0
```

**When needed**:
- Text classification / NLP tasks
- Image classification
- Using embedding models (BERT, Sentence Transformers, etc.)

**Size**: ~5-10 GB (includes PyTorch + models)

### For Gradient Boosting Tasks

```bash
pip install lightgbm>=4.0.0
pip install xgboost>=2.0.0
pip install catboost>=1.2.0
```

**When needed**:
- Tabular data classification/regression
- Ensemble methods
- Kaggle-style competitions

**Size**: ~500 MB

### For Additional LLM Providers

```bash
pip install openai>=1.0.0          # For GPT-4
pip install google-generativeai    # For Gemini
pip install litellm>=1.0.0         # Unified LLM API
```

**When needed**:
- Using OpenAI GPT-4 instead of Claude
- Using Google Gemini
- Managing multiple LLM providers

---

## 🔑 API Access Requirements

### LLM API (Required)

You need access to **at least one** LLM provider:

#### Option 1: Claude (Recommended)
```bash
export ANTHROPIC_BASE_URL="https://api.anthropic.com"  # Or your custom endpoint
export ANTHROPIC_AUTH_TOKEN="sk-ant-your-token-here"
```

**Cost**: Pay-per-use (~$15-50 per 100 iterations for typical tasks)

#### Option 2: OpenAI GPT-4
```bash
export OPENAI_API_KEY="sk-your-openai-key"
```

**Cost**: Pay-per-use (~$20-60 per 100 iterations)

#### Option 3: Google Gemini
```bash
export GOOGLE_API_KEY="your-gemini-key"
```

**Cost**: Free tier available, then pay-per-use

### Custom LLM Endpoint (Enterprise)

If you have a self-hosted or enterprise LLM:
```bash
export ANTHROPIC_BASE_URL="http://your-llm-server.com"
export ANTHROPIC_AUTH_TOKEN="your-custom-token"
```

---

## 🖥️ GPU Requirements (Optional but Recommended)

### NVIDIA GPU Setup

#### 1. Check GPU Availability
```bash
nvidia-smi
```

Should show your GPU model and CUDA version.

#### 2. Install CUDA Toolkit (if not installed)
```bash
# Ubuntu
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/cuda-ubuntu2004.pin
sudo mv cuda-ubuntu2004.pin /etc/apt/preferences.d/cuda-repository-pin-600
wget https://developer.download.nvidia.com/compute/cuda/11.8.0/local_installers/cuda-repo-ubuntu2004-11-8-local_11.8.0-520.61.05-1_amd64.deb
sudo dpkg -i cuda-repo-ubuntu2004-11-8-local_11.8.0-520.61.05-1_amd64.deb
sudo apt-get update
sudo apt-get -y install cuda
```

#### 3. Verify PyTorch GPU Support
```python
import torch
print(torch.cuda.is_available())  # Should print: True
print(torch.cuda.get_device_name(0))  # Should print: Your GPU name
```

### Without GPU

The system works fine without GPU but:
- **Slower**: 5-10x slower for deep learning tasks
- **Limited**: Large embedding models may not fit in RAM
- **CPU-Only Models**: Use smaller models (e.g., `all-MiniLM-L6-v2` instead of `Qwen3-Embedding-8B`)

---

## 🐳 Environment Setup

### Option 1: Conda (Recommended)

```bash
# Create environment
conda create -n scientific-ai python=3.10 -y
conda activate scientific-ai

# Install PyTorch with CUDA (if you have GPU)
conda install pytorch torchvision torchaudio pytorch-cuda=11.8 -c pytorch -c nvidia

# Install other dependencies
pip install -r requirements.txt
```

### Option 2: venv (Python Built-in)

```bash
# Create environment
python3.10 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# If you need PyTorch with GPU
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Option 3: Docker (Coming Soon)

Docker support is planned. See [CONTRIBUTING.md](CONTRIBUTING.md) if you'd like to help!

---

## 🎯 Task-Specific Requirements

### Text Classification (NLP)

**Required**:
- `torch` (PyTorch)
- `transformers`
- `sentence-transformers`
- 8GB+ RAM (16GB+ recommended)

**Optional**:
- GPU with 8GB+ VRAM for large models

**Example Models**:
- `sentence-transformers/all-MiniLM-L6-v2` (CPU-friendly, 384 dim)
- `Qwen/Qwen3-Embedding-8B` (GPU recommended, 8192 dim)

### Tabular Data (Kaggle-style)

**Required**:
- `scikit-learn`
- `pandas`, `numpy`

**Optional**:
- `lightgbm`, `xgboost`, `catboost`
- 4-16GB RAM depending on dataset size

**Example Tasks**:
- Binary classification
- Multi-class classification
- Regression

### Time Series Forecasting

**Required**:
- `pandas`, `numpy`
- `scikit-learn`

**Optional**:
- `prophet` (for Facebook Prophet models)
- `statsmodels` (for ARIMA, SARIMA)

### Image Classification

**Required**:
- `torch`, `torchvision`
- GPU with 8GB+ VRAM
- 16GB+ RAM

**Optional**:
- `timm` (PyTorch Image Models)
- `albumentations` (data augmentation)

---

## ✅ Quick Verification

After installation, verify everything works:

```bash
# 1. Check Python version
python --version  # Should be 3.10+

# 2. Check core packages
python -c "import pandas, numpy, sklearn; print('✅ Core packages OK')"

# 3. Check LLM API (Claude example)
python -c "import anthropic; print('✅ Anthropic package OK')"

# 4. Check PyTorch + GPU (if installed)
python -c "import torch; print(f'✅ PyTorch OK, CUDA: {torch.cuda.is_available()}')"

# 5. Check Flask (for Tree Explorer)
python -c "import flask; print('✅ Flask OK')"

# 6. Test database
python -c "import sqlite3; print('✅ SQLite OK')"
```

**Expected output**:
```
✅ Core packages OK
✅ Anthropic package OK
✅ PyTorch OK, CUDA: True  (or False if no GPU)
✅ Flask OK
✅ SQLite OK
```

---

## 🐛 Common Installation Issues

### Issue 1: `pip install torch` fails

**Solution**: Use PyTorch's official index URL:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Issue 2: CUDA not found

**Solution**: Check CUDA installation:
```bash
nvcc --version  # Should show CUDA version
nvidia-smi      # Should show GPU info
```

If missing, install CUDA toolkit for your OS.

### Issue 3: `ModuleNotFoundError: No module named 'flask'`

**Solution**: Activate your conda/venv environment:
```bash
conda activate scientific-ai  # or: source venv/bin/activate
pip install -r requirements.txt
```

### Issue 4: `ImportError: cannot import name 'LLMWorker'`

**Solution**: You're in the wrong directory:
```bash
cd /path/to/MTCS_module  # Go to project root
python universal_main_database.py --help
```

### Issue 5: SQLite version too old

**Solution**: Python 3.10+ includes SQLite 3.35+, which is sufficient. If using older Python:
```bash
conda install sqlite>=3.35  # Or upgrade Python to 3.10+
```

---

## 📦 Minimal Installation (No Deep Learning)

If you **only** want to use the system with lightweight ML (no embeddings):

```bash
# Create environment
conda create -n scientific-ai-minimal python=3.10 -y
conda activate scientific-ai-minimal

# Install minimal dependencies
pip install pandas numpy scikit-learn anthropic requests pyyaml pydantic flask tqdm colorama

# Optional: Gradient boosting only
pip install lightgbm xgboost
```

**Total size**: ~500 MB

**Works for**:
- Tabular data tasks
- Scikit-learn algorithms only
- Tree Search Explorer

**Doesn't work for**:
- Text classification with embeddings
- Image classification
- Deep learning tasks

---

## 🌐 Network Requirements

### Required Endpoints

- **LLM API**: `https://api.anthropic.com` (or your custom endpoint)
- **PyPI**: `https://pypi.org` (for pip installs)
- **Conda**: `https://repo.anaconda.com` (for conda installs)

### Firewall Rules

If behind a corporate firewall, ensure these ports are open:
- **443 (HTTPS)**: For LLM API access
- **80 (HTTP)**: For some package downloads

### Proxy Configuration

If using a proxy:
```bash
export HTTP_PROXY="http://your-proxy:8080"
export HTTPS_PROXY="http://your-proxy:8080"
pip install --proxy http://your-proxy:8080 -r requirements.txt
```

---

## 💰 Cost Estimate

### LLM API Costs (Most Significant)

| Usage | Claude API Cost | GPT-4 API Cost |
|-------|----------------|----------------|
| 10 iterations | $1-5 | $2-6 |
| 100 iterations | $15-50 | $20-60 |
| 1000 iterations | $150-500 | $200-600 |

**Factors affecting cost**:
- Task complexity (code length)
- Number of auto-fix attempts
- LLM model used (Claude 3.5 Sonnet vs Opus)

### Compute Costs (If Using Cloud)

| Resource | Cost per Hour | When Needed |
|----------|---------------|-------------|
| CPU-only (8 vCPU, 32GB RAM) | $0.30-0.50 | Lightweight tasks |
| GPU (T4, 16GB VRAM) | $0.35-0.50 | NLP, small images |
| GPU (A100, 40GB VRAM) | $3-5 | Large models, big datasets |

**Self-hosted**: Free (electricity costs only)

---

## ✅ Installation Checklist

Before running the system, verify:

- [ ] Python 3.10+ installed
- [ ] Virtual environment created and activated
- [ ] All dependencies from `requirements.txt` installed
- [ ] Optional dependencies installed (if needed for your task)
- [ ] LLM API credentials configured
- [ ] GPU detected (if applicable)
- [ ] SQLite working
- [ ] Flask working (for Tree Explorer)
- [ ] Quick verification commands passed

---

**Ready to start?** See [README.md](README.md#-quick-start) for Quick Start guide!

**Having issues?** See [Common Installation Issues](#-common-installation-issues) above or open an issue on GitHub.

