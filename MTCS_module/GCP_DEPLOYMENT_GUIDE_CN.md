# 🚀 GCP云端部署指南

本指南将帮助您在Google Cloud Platform (GCP)上部署和运行科学AI系统。

---

## 📋 前提条件

- GCP账号（需要启用计费）
- 安装了 [Google Cloud SDK (gcloud CLI)](https://cloud.google.com/sdk/docs/install)
- Gemini API密钥（从 https://ai.google.dev/ 获取）

---

## 🌩️ 第一步：创建GCP虚拟机实例

### 1.1 使用gcloud命令创建实例（推荐）

```bash
# 登录GCP
gcloud auth login

# 设置项目ID（替换为您的项目ID）
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID

# 创建具有GPU的虚拟机（用于深度学习任务）
gcloud compute instances create scientific-ai-vm \
  --zone=us-central1-a \
  --machine-type=n1-standard-8 \
  --accelerator=type=nvidia-tesla-t4,count=1 \
  --image-family=pytorch-latest-gpu \
  --image-project=deeplearning-platform-release \
  --boot-disk-size=100GB \
  --boot-disk-type=pd-ssd \
  --maintenance-policy=TERMINATE \
  --metadata="install-nvidia-driver=True"

# 或创建纯CPU实例（成本更低）
gcloud compute instances create scientific-ai-vm-cpu \
  --zone=us-central1-a \
  --machine-type=n1-standard-4 \
  --image-family=ubuntu-2004-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=50GB \
  --boot-disk-type=pd-standard
```

### 1.2 通过GCP Console创建（图形界面）

1. 访问 [GCP Console](https://console.cloud.google.com/)
2. 导航到 **Compute Engine** → **VM实例**
3. 点击 **创建实例**
4. 配置如下：
   - **名称**：`scientific-ai-vm`
   - **区域**：`us-central1` 或其他靠近您的区域
   - **机器类型**：
     - CPU任务：`n1-standard-4`（4 vCPU，15 GB内存）
     - GPU任务：`n1-standard-8` + `1x NVIDIA Tesla T4`
   - **启动磁盘**：
     - **操作系统**：Deep Learning on Linux（含GPU驱动）
     - **大小**：100 GB SSD
   - **防火墙**：允许HTTP和HTTPS流量
5. 点击 **创建**

**成本估算**：
- CPU实例（n1-standard-4）：~$0.19/小时 (~$140/月)
- GPU实例（n1-standard-8 + T4）：~$0.65/小时 (~$470/月)
- **提示**：使用可抢占实例节省60-90%成本

---

## 🔐 第二步：连接到虚拟机

```bash
# SSH连接
gcloud compute ssh scientific-ai-vm --zone=us-central1-a

# 或使用浏览器SSH（从GCP Console）
# 点击实例旁边的"SSH"按钮
```

---

## 📦 第三步：安装依赖

### 3.1 更新系统

```bash
sudo apt-get update
sudo apt-get upgrade -y
```

### 3.2 安装Conda（如果未预装）

```bash
# 下载Miniconda
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh

# 安装
bash miniconda.sh -b -p $HOME/miniconda
echo 'export PATH="$HOME/miniconda/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# 验证安装
conda --version
```

### 3.3 创建Python环境

```bash
# 创建环境
conda create -n scientific-ai python=3.10 -y
conda activate scientific-ai

# 如果有GPU，安装PyTorch（CUDA版本）
conda install pytorch torchvision torchaudio pytorch-cuda=11.8 -c pytorch -c nvidia

# 如果仅CPU
conda install pytorch torchvision torchaudio cpuonly -c pytorch
```

---

## 📂 第四步：上传项目文件

### 方法1：使用gcloud scp

```bash
# 在本地机器上执行
gcloud compute scp 中文版LLM+决策树.zip scientific-ai-vm:~ --zone=us-central1-a

# 在VM上解压
ssh scientific-ai-vm
unzip 中文版LLM+决策树.zip
cd scientific-ai-system
```

### 方法2：使用Git（推荐）

```bash
# 在VM上执行
git clone https://github.com/your-username/scientific-ai-system.git
cd scientific-ai-system
```

### 方法3：使用Google Cloud Storage

```bash
# 在本地上传到GCS
gsutil cp 中文版LLM+决策树.zip gs://your-bucket-name/

# 在VM上下载
gsutil cp gs://your-bucket-name/中文版LLM+决策树.zip .
unzip 中文版LLM+决策树.zip
cd scientific-ai-system
```

---

## 🔧 第五步：配置环境

### 5.1 安装Python依赖

```bash
conda activate scientific-ai
cd scientific-ai-system

# 安装核心依赖
pip install -r requirements.txt

# 安装可选依赖（根据需要）
pip install lightgbm xgboost catboost
pip install sentence-transformers
```

### 5.2 配置Gemini API密钥

```bash
# 设置环境变量（临时）
export GOOGLE_API_KEY="your-gemini-api-key-here"

# 或永久设置
echo 'export GOOGLE_API_KEY="your-gemini-api-key-here"' >> ~/.bashrc
source ~/.bashrc

# 验证
echo $GOOGLE_API_KEY
```

### 5.3 验证GPU（如果有）

```bash
# 检查NVIDIA驱动
nvidia-smi

# 检查PyTorch GPU支持
python -c "import torch; print(f'CUDA可用: {torch.cuda.is_available()}')"
python -c "import torch; print(f'GPU设备: {torch.cuda.get_device_name(0)}')"
```

---

## 🚀 第六步：运行系统

### 6.1 快速测试运行

```bash
conda activate scientific-ai

# 运行帮助命令
python universal_main_database.py --help

# 运行快速测试（3次迭代）
python universal_main_database.py \
  --task tasks/kaggle_machine_failures/task_config.yaml \
  --iterations 3 \
  --db-path test_run.db
```

### 6.2 生产运行（后台运行）

```bash
# 使用nohup后台运行
nohup python universal_main_database.py \
  --task tasks/text_classification_for_custom_service/task_config.yaml \
  --iterations 100 \
  --db-path experiment.db \
  --execution-timeout 900 \
  > experiment.log 2>&1 &

# 查看进程
ps aux | grep python

# 查看日志
tail -f experiment.log

# 如果需要停止
pkill -f universal_main_database.py
```

### 6.3 使用screen会话（推荐）

```bash
# 安装screen
sudo apt-get install screen -y

# 创建screen会话
screen -S ai-experiment

# 在screen会话中运行
conda activate scientific-ai
python universal_main_database.py \
  --task tasks/your_task/task_config.yaml \
  --iterations 100 \
  --db-path experiment.db

# 分离会话：按 Ctrl+A，然后按 D

# 重新连接会话
screen -r ai-experiment

# 列出所有会话
screen -ls

# 终止会话
screen -S ai-experiment -X quit
```

---

## 📊 第七步：监控和可视化

### 7.1 启动树搜索浏览器

```bash
cd tree_search_explorer

# 启动Web服务器
python app.py --db ../experiment.db --port 8005 --host 0.0.0.0 &

# 查看日志
tail -f nohup.out
```

### 7.2 配置防火墙规则

```bash
# 允许端口8005
gcloud compute firewall-rules create allow-tree-explorer \
  --allow tcp:8005 \
  --source-ranges 0.0.0.0/0 \
  --description "允许树搜索浏览器访问"

# 获取VM的外部IP
gcloud compute instances describe scientific-ai-vm \
  --zone=us-central1-a \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
```

### 7.3 访问Web界面

在浏览器中打开：`http://[VM-EXTERNAL-IP]:8005`

---

## 💾 第八步：数据管理

### 8.1 下载结果到本地

```bash
# 从VM下载数据库
gcloud compute scp scientific-ai-vm:~/scientific-ai-system/experiment.db . --zone=us-central1-a

# 下载整个结果目录
gcloud compute scp --recurse scientific-ai-vm:~/scientific-ai-system/results . --zone=us-central1-a
```

### 8.2 备份到Google Cloud Storage

```bash
# 在VM上执行
gsutil cp experiment.db gs://your-bucket-name/backups/experiment_$(date +%Y%m%d_%H%M%S).db

# 自动化每日备份
crontab -e
# 添加：0 2 * * * gsutil cp ~/scientific-ai-system/*.db gs://your-bucket-name/backups/
```

---

## 🛑 第九步：停止和清理

### 9.1 停止实例（保留数据）

```bash
gcloud compute instances stop scientific-ai-vm --zone=us-central1-a
```

### 9.2 重新启动实例

```bash
gcloud compute instances start scientific-ai-vm --zone=us-central1-a
```

### 9.3 删除实例

```bash
# 删除实例（保留磁盘）
gcloud compute instances delete scientific-ai-vm --zone=us-central1-a --keep-disks=boot

# 完全删除（包括磁盘）
gcloud compute instances delete scientific-ai-vm --zone=us-central1-a
```

---

## 💰 成本优化技巧

### 1. 使用可抢占实例

```bash
gcloud compute instances create scientific-ai-vm-preemptible \
  --zone=us-central1-a \
  --machine-type=n1-standard-8 \
  --accelerator=type=nvidia-tesla-t4,count=1 \
  --preemptible \
  --image-family=pytorch-latest-gpu \
  --image-project=deeplearning-platform-release
```

**节省**：60-90%成本  
**缺点**：可能在24小时内被终止

### 2. 使用Spot VM

```bash
gcloud compute instances create scientific-ai-vm-spot \
  --zone=us-central1-a \
  --machine-type=n1-standard-8 \
  --provisioning-model=SPOT \
  --instance-termination-action=STOP
```

### 3. 自动停机

```bash
# 在VM上创建自动停机脚本
cat > ~/auto_shutdown.sh << 'EOF'
#!/bin/bash
# 检查是否有活动的Python进程
if ! pgrep -f "universal_main_database.py" > /dev/null; then
    echo "无活动进程，关闭实例..."
    sudo shutdown -h now
fi
EOF

chmod +x ~/auto_shutdown.sh

# 添加到crontab（每小时检查）
crontab -e
# 添加：0 * * * * ~/auto_shutdown.sh
```

### 4. 使用持久化磁盘

- 删除实例时保留磁盘
- 需要时重新附加磁盘到新实例

---

## 🔍 故障排除

### 问题1：GPU不可用

```bash
# 检查驱动
nvidia-smi

# 重新安装CUDA驱动
sudo apt-get install -y cuda-drivers

# 重启
sudo reboot
```

### 问题2：内存不足

```bash
# 增加swap空间
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 问题3：连接超时

```bash
# 检查防火墙规则
gcloud compute firewall-rules list

# 检查实例状态
gcloud compute instances list
```

### 问题4：磁盘空间不足

```bash
# 检查磁盘使用
df -h

# 清理conda缓存
conda clean --all -y

# 清理pip缓存
pip cache purge

# 调整磁盘大小（需要停止实例）
gcloud compute disks resize DISK_NAME --size 200GB --zone=us-central1-a
```

---

## 📚 有用的命令

```bash
# 查看实例列表
gcloud compute instances list

# 查看实例详情
gcloud compute instances describe scientific-ai-vm --zone=us-central1-a

# 实时查看成本
gcloud billing accounts list
gcloud billing projects list

# SSH端口转发（访问Jupyter Notebook）
gcloud compute ssh scientific-ai-vm --zone=us-central1-a -- -L 8888:localhost:8888

# 检查实例日志
gcloud compute instances get-serial-port-output scientific-ai-vm --zone=us-central1-a
```

---

## 🎯 完整部署脚本

将以下内容保存为 `deploy.sh`：

```bash
#!/bin/bash

# 配置
PROJECT_ID="your-project-id"
ZONE="us-central1-a"
INSTANCE_NAME="scientific-ai-vm"
GEMINI_API_KEY="your-api-key"

# 设置项目
gcloud config set project $PROJECT_ID

# 创建实例
gcloud compute instances create $INSTANCE_NAME \
  --zone=$ZONE \
  --machine-type=n1-standard-8 \
  --accelerator=type=nvidia-tesla-t4,count=1 \
  --image-family=pytorch-latest-gpu \
  --image-project=deeplearning-platform-release \
  --boot-disk-size=100GB \
  --metadata="install-nvidia-driver=True"

# 等待实例启动
sleep 60

# 安装和配置
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE --command="
  # 更新系统
  sudo apt-get update -y
  
  # 克隆项目
  git clone https://github.com/your-repo/scientific-ai-system.git
  cd scientific-ai-system
  
  # 创建conda环境
  conda create -n scientific-ai python=3.10 -y
  source activate scientific-ai
  
  # 安装依赖
  pip install -r requirements.txt
  
  # 配置API密钥
  echo 'export GOOGLE_API_KEY=\"$GEMINI_API_KEY\"' >> ~/.bashrc
  
  echo '部署完成！'
"
```

运行：
```bash
chmod +x deploy.sh
./deploy.sh
```

---

## ✅ 检查清单

部署前确认：

- [ ] 已创建GCP项目并启用计费
- [ ] 已获取Gemini API密钥
- [ ] 已选择合适的机器类型（CPU vs GPU）
- [ ] 已配置防火墙规则（如需Web访问）
- [ ] 已准备任务配置文件（task_config.yaml）
- [ ] 已上传数据文件到VM或GCS

部署后确认：

- [ ] GPU可用（nvidia-smi）
- [ ] Python环境正常（conda activate scientific-ai）
- [ ] API密钥已配置（echo $GOOGLE_API_KEY）
- [ ] 依赖已安装（pip list）
- [ ] 可以运行测试（python universal_main_database.py --help）

---

## 📞 获取帮助

- **GCP文档**：https://cloud.google.com/compute/docs
- **项目文档**：查看 `gen_doc/` 目录
- **问题排查**：README_CN.md 中的故障排除部分

---

**准备好在云端运行了吗？祝实验成功！🚀**

