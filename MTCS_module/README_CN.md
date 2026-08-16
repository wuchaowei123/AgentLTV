# 🧬 科学AI系统

**使用树搜索和LLM驱动的代码生成，自动发现、生成和优化科学软件解决方案。**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Powered by Gemini](https://img.shields.io/badge/Powered%20by-Gemini-blue)](https://ai.google.dev/)

---

## 🎯 这是什么？

本系统能够**自动生成、测试和改进科学代码**，适用于任何可度量的研究问题。它使用**带自适应探索的树搜索**来导航解决方案空间，并使用**大语言模型**（Gemini、Claude、GPT）来生成高质量代码。

### 🏆 核心能力

- **🌳 PUCT树搜索**，带自适应C-PUCT，智能平衡探索与利用
- **🤖 多模型代码生成**，使用Gemini、Claude或GPT-4
- **🗄️ 数据库增强执行**，完整历史记录和恢复能力
- **🔧 自动修复与重试逻辑**，实现自主错误恢复
- **📊 实时监控与分析**，追踪进度
- **🧠 用户反馈集成**，用领域知识指导LLM
- **🔄 代码变更检测**，追踪手动编辑并重新执行
- **🎯 自适应探索**，在搜索过程中持续演进
- **⚡ 新功能：即时继续**，手动执行批准后 < 0.1秒

### 🏆 近期成果

| 领域 | 任务 | 最佳F1分数 | 迭代次数 | 备注 |
|--------|------|---------------|------------|-------|
| **NLP** | 多标签文本分类 | **0.9258** | 11 | 达到0.93目标的99.5% |
| **NLP** | 多标签（v5运行） | **0.9045** | 3 | 3次迭代达到97.3%（XGBoost） |
| **机器学习** | 二分类 | **1.0000 AUC** | 5 | 完美分数 |

**最新（v5）**：系统在手动模式下以即时继续工作流处理了3个节点（LogReg: 0.8666 → LightGBM: 0.8926 → XGBoost: 0.9045）。

---

## ⚡ 快速开始

### 前置要求

- **Python**: 3.10+（必需）
- **Conda**: 推荐用于环境管理
- **GPU**: 可选但推荐用于深度学习任务
- **LLM API访问**: Gemini、Claude或GPT-4（必需）
- **内存**: 至少8GB，推荐16GB+
- **存储**: 至少5GB，推荐50GB+

**📋 完整要求**: 查看[`REQUIREMENTS.md`](REQUIREMENTS.md)了解详细系统要求、依赖关系和安装故障排除。

### 安装

#### 步骤1：克隆仓库
```bash
git clone https://github.com/<your-username>/scientific-ai-system.git
cd scientific-ai-system
```

#### 步骤2：创建Python环境

**选项A：使用Conda（推荐）**
```bash
# 创建Python 3.10环境
conda create -n pytorch python=3.10 -y
conda activate pytorch

# 安装PyTorch与CUDA支持（如果有NVIDIA GPU）
conda install pytorch torchvision torchaudio pytorch-cuda=11.8 -c pytorch -c nvidia

# 或CPU版本（无GPU）
conda install pytorch torchvision torchaudio cpuonly -c pytorch
```

**选项B：使用venv（Python内置）**
```bash
python3.10 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装PyTorch（可选，用于深度学习任务）
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

#### 步骤3：安装依赖

```bash
# 安装核心依赖（必需）
pip install -r requirements.txt

# 安装可选依赖（如果任务需要）
pip install lightgbm xgboost catboost  # 梯度提升
pip install sentence-transformers      # 文本嵌入
```

**安装的核心包**:
- `pandas`, `numpy`, `scikit-learn` - 数据处理和机器学习
- `google-genai` - Gemini API客户端
- `flask` - 树搜索浏览器Web界面
- `pyyaml`, `pydantic` - 配置管理

#### 步骤4：配置LLM API访问

**对于Gemini（推荐）**:
```bash
# 添加到 ~/.bashrc 或 ~/.zshrc 以持久化
export GOOGLE_API_KEY="your-gemini-api-key-here"

# 或仅为当前会话设置
export GOOGLE_API_KEY="your-gemini-api-key-here"
```

**对于Claude**:
```bash
export ANTHROPIC_API_KEY="sk-ant-your-api-key-here"
```

**对于OpenAI GPT-4**:
```bash
export OPENAI_API_KEY="sk-your-openai-key"
```

**获取API密钥**:
- Gemini: https://ai.google.dev/
- Claude: https://console.anthropic.com/
- OpenAI: https://platform.openai.com/api-keys

#### 步骤5：验证安装

```bash
# 测试核心包
python -c "import pandas, numpy, sklearn; print('✅ 核心包正常')"

# 测试LLM API
python -c "from google import genai; print('✅ LLM客户端正常')"

# 测试PyTorch + GPU（如果已安装）
python -c "import torch; print(f'✅ PyTorch正常, CUDA: {torch.cuda.is_available()}')"

# 测试系统
python universal_main_database.py --help
```

**预期输出**：应该看到帮助消息，显示所有可用选项。

---

## 🚀 运行你的第一个实验

### 🤖 **模式1：全自动**（推荐用于大多数任务）

```bash
python universal_main_database.py \
  --task tasks/text_classification_for_custom_service/task_config.yaml \
  --iterations 100 \
  --db-path my_experiment.db \
  --execution-timeout 900
```

**工作原理：**
- ✅ 系统尝试自动运行代码（直接执行）
- ✅ 如果成功 → 继续到下一个节点
- ❌ 如果失败 → 尝试自动修复并重试
- ❌ 如果自动修复失败 → 触发手动执行模式
- **适用于：** 生产运行、代码生成可靠的任务

### 👤 **模式2：手动控制（立即）**（完全监督，无自动执行）

```bash
python universal_main_database.py \
  --task tasks/text_classification_for_custom_service/task_config.yaml \
  --iterations 100 \
  --db-path my_experiment.db \
  --skip-auto-fixer \
  --wait-for-manual \
  --execution-timeout 900
```

**工作原理：**
- 📝 系统生成代码
- 🚨 **立即进入手动模式**（跳过自动执行和自动修复）
- 💾 立即保存代码文件
- ⏸️ 等待你审查、修复和运行
- ✅ 你输入'yes' → 立即继续（< 0.1秒）
- **适用于：** 研究、调试、学习、避免在自动执行上浪费GPU时间

**⚡ 新行为：** 使用 `--skip-auto-fixer`，系统跳过所有自动尝试，直接进入手动模式，节省你的时间！

---

## 📚 文档

全面指南位于[`gen_doc/`](gen_doc/)：

### 核心系统

| 文档 | 说明 |
|----------|-------------|
| **[系统架构](gen_doc/SYSTEM_ARCHITECTURE_GUIDE.md)** | 端到端工作原理及Mermaid图 |
| **[系统通用性](gen_doc/SYSTEM_UNIVERSALITY_ANALYSIS.md)** | ⭐ 能处理你的任务吗？兼容性分析 |
| **[配置到提示流程](gen_doc/CONFIG_TO_PROMPT_FLOW.md)** | 任务配置如何变成LLM提示 |
| **[提示系统指南](gen_doc/PROMPT_SYSTEM_GUIDE.md)** | 所有可用提示及使用时机 |
| **[错误学习](gen_doc/ERROR_LEARNING_GUIDE.md)** | 系统如何捕获和学习失败 |

### 高级功能

| 文档 | 说明 |
|----------|-------------|
| **[PUCT算法](gen_doc/PUCT_ALGORITHM_GUIDE.md)** | 树搜索算法深入解析 |
| **[自适应C-PUCT](gen_doc/ADAPTIVE_C_PUCT_IMPLEMENTATION.md)** | 动态探索/利用平衡 |
| **[用户反馈系统](gen_doc/USER_FEEDBACK_SYSTEM.md)** | 用手动反馈指导LLM |
| **[系统改进](gen_doc/SYSTEM_IMPROVEMENT_PROPOSALS.md)** | 提议的增强功能 |

---

## 📖 创建自定义任务

### 1. 创建任务配置

创建 `tasks/your_task/task_config.yaml`:

```yaml
domain: "natural_language_processing"  # 或 machine_learning、bioinformatics 等
task_name: "你的任务名称"

description: |
  你想要实现什么的详细描述。
  包括关键特征、挑战和目标。

evaluation_metric: "f1_score"  # 或 auc、accuracy、rmse 等
higher_is_better: true

data_files:
  train: "/absolute/path/to/train.csv"  # 必须是绝对路径
  test: "/absolute/path/to/test.csv"

code_requirements:
  text_column: "text"
  labels_column: "labels"
  output_variable: "test_predictions"
  
  # 关键：指定要使用的确切模型
  embedding_model: "sentence-transformers/all-MiniLM-L6-v2"
  
  # 硬件约束
  hardware_constraints: "单个GPU，16GB显存"
  batch_size: 32
  
  # 必需的库
  required_libraries:
    - pandas
    - numpy
    - scikit-learn
    - torch

# 重要：引导LLM朝好的方向
research_ideas:
  - "使用基于transformer的嵌入以获得更好的文本表示"
  - "尝试集成方法（XGBoost + LightGBM + LogisticRegression）"
  - "为多标签任务实现每标签阈值优化"
  - "使用混合精度训练减少内存使用"

baseline_performance:
  description: "要超越的目标性能"
  target_improvement: 0.85
```

---

## 🤖 命令行选项

### 基本选项

```bash
python universal_main_database.py \
  --task <path_to_config.yaml>   # 必需：任务配置
  --iterations 100                # 搜索迭代次数
  --db-path experiment.db         # 数据库文件路径
```

### 树搜索选项

```bash
  --c-puct 1.5                    # 固定C-PUCT值（如果禁用自适应）
  --disable-adaptive-c-puct       # 使用固定C-PUCT而非自适应
  --c-puct-early 2.5              # 早期阶段的C（0-20%）
  --c-puct-mid 1.5                # 中期阶段的C（20-70%）
  --c-puct-late 0.8               # 后期阶段的C（70-100%）
```

### 功能标志

```bash
  --enable-all-phases             # 启用准备+分析阶段
  --multi-strategy-init           # 使用多种初始化策略
  --enable-user-feedback          # 执行后收集用户反馈
  --feedback-timeout 30           # 反馈输入超时（秒）
  --enable-code-reload            # 检测并重新运行手动代码编辑
  --reload-wait-time 60           # 等待手动编辑的时间（秒）
```

### 执行选项

```bash
  --skip-auto-fixer               # 跳过自动修复，直接进入手动执行
  --wait-for-manual               # 等待手动步骤的'yes'确认
  --manual-timeout 300            # 手动执行超时（秒）
  --disable-monitoring            # 禁用实时监控
```

---

## 📁 项目结构

```
scientific-ai-system/
├── universal_main_database.py       # 🚀 主入口点
├── core/                            # 核心系统组件
│   ├── controller/
│   │   ├── search.py                # PUCT树搜索 + 自适应C-PUCT
│   │   └── db_enhanced_search.py    # 数据库增强的树搜索
│   ├── sandbox/
│   │   ├── db_code_executor.py      # 代码执行 + 自动修复
│   │   └── db_universal_evaluator.py # 通用任务评估
│   ├── database/db_manager.py       # SQLite追踪
│   ├── prompts/                     # LLM提示系统
│   │   ├── prompt_library.py        # 多领域提示模板
│   │   ├── prompt_formatter.py      # 动态提示生成
│   │   └── prompt_strategies.py     # 变异策略
│   ├── llm_worker_enhanced.py       # LLM代码生成
│   └── utils/                       # 反馈 + 代码变更检测
├── tasks/<your_task>/               # 任务配置 + 数据
│   └── task_config.yaml             # 任务规范
├── tree_search_explorer/            # 🌳 基于Web的可视化工具
│   ├── app.py                       # Flask后端
│   ├── data_bridge.py               # 数据库 → JSON提取
│   ├── templates/                   # HTML模板
│   └── static/                      # CSS、JS（D3.js、Monaco Editor）
├── gen_doc/                         # 📚 9个全面指南
├── auto_code_fixer/                 # 自主错误修复系统
├── requirements.txt                 # Python依赖
├── .gitignore                       # Git忽略规则
└── official_run_v5_test.db          # 示例搜索数据库
```

---

## 🐛 常见问题与解决方案

| 问题 | 解决方案 |
|---------|----------|
| **LLM API无响应** | 检查 `$GOOGLE_API_KEY` 环境变量 |
| **数据库锁定** | `fuser -k your_run.db` 杀死陈旧的SQLite连接 |
| **CUDA内存不足** | 在任务的 `code_requirements` 中减小 `batch_size` 或使用纯CPU模型 |
| **搜索未恢复** | 检查 `execution_status='running'` 的节点并手动更新为 `'failed'` |
| **树浏览器仅显示1个节点** | 硬刷新浏览器（`Ctrl+Shift+R`）清除JavaScript缓存 |
| **端口已被占用** | `lsof -ti:8005 \| xargs kill -9` 杀死端口8005上的进程 |

---

## 💡 性能提示

| 提示 | 影响 |
|-----|--------|
| **在配置中精心编写 `research_ideas`** | +15-25%分数提升 |
| **使用自适应C-PUCT**（默认） | +15-25%最终分数提升 |
| **启用用户反馈**（`--enable-user-feedback`） | 系统从你的专业知识中学习 |
| **早期监控**（前20-30次迭代） | 好的解决方案会早期发现 |
| **使用GPU**进行嵌入模型 | 5-10倍更快的执行 |
| **从小开始**（先10-20次迭代） | 在完整运行前测试配置 |

---

## 📄 许可证

MIT许可证 - 详见LICENSE文件

---

## 🙏 致谢

- **Google Gemini** 用于代码生成和自主错误修复
- **OpenAI GPT-4** 和 **Anthropic Claude** 用于代码生成
- **SQLite** 用于稳健的数据持久化

---

## 📞 支持

- **文档**: 查看 [`gen_doc/`](gen_doc/) 获取全面指南
- **问题**: 检查上方故障排除部分
- **自定义任务**: 查看[创建自定义任务](#-创建自定义任务)

---

**准备好自主发现科学解决方案了吗？**

```bash
python universal_main_database.py \
  --task tasks/your_task/task_config.yaml \
  --iterations 100 \
  --db-path experiment.db
```

**让AI为你探索解决方案空间！🚀**

