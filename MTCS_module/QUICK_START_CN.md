# ⚡ 快速开始指南

本指南帮助您在5分钟内开始使用科学AI系统。

---

## 📦 方式1：本地部署（推荐用于开发）

### 1. 安装依赖

```bash
# 克隆或解压项目
cd MTCS_module

# 创建Conda环境
conda create -n scientific-ai python=3.10 -y
conda activate scientific-ai

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置API密钥

```bash
# Gemini API密钥（推荐）
export GOOGLE_API_KEY="your-gemini-api-key"

# 或者使用Claude
export ANTHROPIC_API_KEY="your-claude-api-key"

# 或者使用OpenAI
export OPENAI_API_KEY="your-openai-api-key"
```

### 3. 运行第一个实验

```bash
# 快速测试（3次迭代）
python universal_main_database.py \
  --task tasks/kaggle_machine_failures/task_config.yaml \
  --iterations 3 \
  --db-path test.db

# 完整运行（手动模式）
python universal_main_database.py \
  --task tasks/text_classification_for_custom_service/task_config.yaml \
  --iterations 10 \
  --db-path experiment.db \
  --skip-auto-fixer \
  --wait-for-manual
```

---

## ☁️ 方式2：GCP云端部署（推荐用于生产）

### 1. 创建VM实例

```bash
# 登录GCP
gcloud auth login

# 创建GPU实例
gcloud compute instances create scientific-ai-vm \
  --zone=us-central1-a \
  --machine-type=n1-standard-8 \
  --accelerator=type=nvidia-tesla-t4,count=1 \
  --image-family=pytorch-latest-gpu \
  --image-project=deeplearning-platform-release \
  --boot-disk-size=100GB
```

### 2. 连接并配置

```bash
# SSH连接
gcloud compute ssh scientific-ai-vm --zone=us-central1-a

# 上传项目
gcloud compute scp 中文版LLM+决策树.zip scientific-ai-vm:~ --zone=us-central1-a
```

### 3. 在VM上运行

```bash
# 解压
unzip 中文版LLM+决策树.zip
cd MTCS_module

# 创建环境
conda create -n scientific-ai python=3.10 -y
conda activate scientific-ai
pip install -r requirements.txt

# 配置API密钥
export GOOGLE_API_KEY="your-api-key"

# 运行
python universal_main_database.py \
  --task tasks/your_task/task_config.yaml \
  --iterations 100 \
  --db-path experiment.db
```

**详细GCP部署指南**：查看 [`GCP_DEPLOYMENT_GUIDE_CN.md`](GCP_DEPLOYMENT_GUIDE_CN.md)

---

## 🎯 常用命令

### 运行模式

```bash
# 全自动模式
python universal_main_database.py --task TASK.yaml --iterations 100

# 手动模式（立即）
python universal_main_database.py \
  --task TASK.yaml \
  --iterations 10 \
  --skip-auto-fixer \
  --wait-for-manual

# 后台运行
nohup python universal_main_database.py \
  --task TASK.yaml --iterations 100 \
  > experiment.log 2>&1 &
```

### 监控和可视化

```bash
# 启动Web浏览器
cd tree_search_explorer
python app.py --db ../experiment.db --port 8005 --host 0.0.0.0

# 查看日志
tail -f experiment.log

# 检查进度
sqlite3 experiment.db "SELECT COUNT(*) FROM execution_nodes"
```

---

## 🔧 创建自定义任务

### 1. 准备数据

```
tasks/my_task/
├── task_config.yaml
├── train.csv
└── test.csv
```

### 2. 配置任务

创建 `task_config.yaml`：

```yaml
domain: "natural_language_processing"
task_name: "我的文本分类任务"

description: |
  任务描述...

evaluation_metric: "f1_score"
higher_is_better: true

data_files:
  train: "/absolute/path/to/train.csv"
  test: "/absolute/path/to/test.csv"

code_requirements:
  text_column: "text"
  labels_column: "labels"
  output_variable: "test_predictions"

research_ideas:
  - "使用sentence-transformers嵌入"
  - "尝试LightGBM分类器"
  - "优化每标签阈值"
```

### 3. 运行

```bash
python universal_main_database.py \
  --task tasks/my_task/task_config.yaml \
  --iterations 10
```

---

## 📊 查看结果

### 方法1：Web界面

```bash
cd tree_search_explorer
python app.py --db ../experiment.db --port 8005
# 访问 http://localhost:8005
```

### 方法2：命令行

```bash
# 查看最佳结果
sqlite3 experiment.db "
  SELECT node_id, score, execution_status 
  FROM execution_nodes 
  ORDER BY score DESC 
  LIMIT 10
"

# 导出最佳代码
cp core/sandbox/exe_code/node_<best_id>.py my_best_solution.py
```

---

## 🆘 常见问题

### Q1: API密钥错误

```bash
# 检查环境变量
echo $GOOGLE_API_KEY

# 重新设置
export GOOGLE_API_KEY="your-key"
```

### Q2: 内存不足

```yaml
# 在task_config.yaml中调整
code_requirements:
  batch_size: 16  # 减小批次大小
```

### Q3: GPU不可用

```bash
# 检查
python -c "import torch; print(torch.cuda.is_available())"

# 使用CPU模式
# 系统会自动降级到CPU
```

---

## 📚 更多文档

- **主文档**：[README_CN.md](README_CN.md)
- **GCP部署**：[GCP_DEPLOYMENT_GUIDE_CN.md](GCP_DEPLOYMENT_GUIDE_CN.md)
- **项目概要**：[PROJECT_SUMMARY_CN.md](PROJECT_SUMMARY_CN.md)
- **系统架构**：[gen_doc/SYSTEM_ARCHITECTURE_GUIDE.md](gen_doc/SYSTEM_ARCHITECTURE_GUIDE.md)

---

## 🎉 下一步

1. **运行示例任务**：使用提供的示例配置
2. **创建自定义任务**：根据您的数据调整配置
3. **优化性能**：查看性能提示和最佳实践
4. **部署到云端**：使用GCP获得更强大的计算能力

---

**准备好开始了吗？让AI为你探索解决方案空间！🚀**

