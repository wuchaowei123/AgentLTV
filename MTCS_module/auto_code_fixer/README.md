# 🤖 自动代码执行和修复模块

这是 Scientific AI System 的自动代码执行和修复模块，使用 Google Gemini CLI 实现智能代码错误检测和自动修复功能。

## 📋 模块概述

本模块提供了一套完整的自动化解决方案，能够：
- 🔍 自动检测 Python 代码执行错误
- 🧠 使用 Gemini AI 智能分析错误原因
- 🔧 自动生成并应用修复方案
- 🔄 支持迭代修复直到代码成功运行
- 📁 自动备份原始文件确保安全

## 🗂️ 文件结构

```
auto_code_fixer/
├── README.md                         # 本文档
├── enhanced_gemini_auto_fixer.py     # 🆕 增强版自动修复脚本（推荐）
├── gemini_auto_fixer.py             # 标准版自动修复脚本
├── auto_code_executor.py            # 完整版执行器（带详细日志）
├── run_with_auto_fix.sh             # 便捷启动脚本
├── test_enhanced_fixer.py           # 🆕 增强版测试脚本
├── integration_example.py           # 集成示例代码
├── IMPROVEMENTS.md                  # 🆕 改进报告和问题解决方案
├── README_auto_fixer.md             # 详细使用文档
└── examples/                        # 测试示例
    ├── test_pytorch_buggy.py        # PyTorch 相关错误示例
    ├── complex_buggy_code.py        # 复杂错误代码示例
    └── test_buggy_code.py           # 基础错误代码示例
```

## 🚀 快速开始

### 1. 前置要求

确保已安装 Gemini CLI：
```bash
npm install -g @google/gemini-cli
```

### 2. 使用方法

#### 方法一：使用增强版（推荐）
```bash
cd /home/jupyter/MTCS_module/auto_code_fixer
python enhanced_gemini_auto_fixer.py your_script.py
```

#### 方法二：使用标准版
```bash
cd /home/jupyter/MTCS_module/auto_code_fixer
python gemini_auto_fixer.py your_script.py
```

#### 方法三：使用便捷脚本
```bash
cd /home/jupyter/MTCS_module/auto_code_fixer
./run_with_auto_fix.sh your_script.py
```

#### 方法三：从任何位置调用
```bash
# 设置别名（可添加到 ~/.bashrc）
alias autofix="python /home/jupyter/MTCS_module/auto_code_fixer/gemini_auto_fixer.py"

# 使用
autofix your_script.py
```

### 3. 测试示例

```bash
cd /home/jupyter/MTCS_module/auto_code_fixer

# 测试增强版修复器（推荐）
python test_enhanced_fixer.py

# 测试 PyTorch 错误修复
python enhanced_gemini_auto_fixer.py examples/test_pytorch_buggy.py

# 测试复杂错误修复
python enhanced_gemini_auto_fixer.py examples/complex_buggy_code.py

# 测试基础错误修复
python enhanced_gemini_auto_fixer.py examples/test_buggy_code.py
```

## 🔧 核心功能

### 🆕 增强版功能 (Enhanced)

- 🚀 **超时处理**: 120秒超时 + 3次重试机制
- 🧠 **本地智能修复**: Gemini失败时的备用修复方案
- 📊 **自动评分提取**: 从输出中智能识别AUC、Accuracy等评分
- 🔄 **递增重试**: 智能等待时间，提高成功率
- 🛡️ **容错增强**: 多层错误处理和恢复机制

### 支持的错误类型

- ✅ **语法错误** (SyntaxError)
- ✅ **名称错误** (NameError) - 未定义变量，如 `pi` → `math.pi`
- ✅ **类型错误** (TypeError) - 数据类型不匹配
- ✅ **值错误** (ValueError) - 值超出范围
- ✅ **导入错误** (ImportError/ModuleNotFoundError)
- ✅ **属性错误** (AttributeError) - 对象属性不存在
- ✅ **索引错误** (IndexError) - 列表索引越界
- ✅ **键错误** (KeyError) - 字典键不存在
- ✅ **零除错误** (ZeroDivisionError)
- ✅ **PyTorch 相关错误** - 模型定义、训练等
- 🆕 **sklearn 实验性功能** - 自动添加 `enable_iterative_imputer` 等

### 工作流程

1. **执行代码** → 尝试运行指定的 Python 文件
2. **错误捕获** → 如果执行失败，捕获详细错误信息
3. **AI 分析** → 将代码和错误发送给 Gemini AI 分析
4. **生成修复** → AI 提供完整的修复后代码
5. **应用修复** → 自动备份原文件并应用修复
6. **重新执行** → 执行修复后的代码
7. **迭代优化** → 如需要，重复步骤 2-6（最多3次）

## 📊 使用示例

### 示例 1: PyTorch 错误修复

**原始代码（有错误）：**
```python
import torch

def create_model():
    model = torch.nn.Sequential(
        torch.nn.Linear(10, 5),
        torch.nn.ReLu(),  # 错误：应该是 ReLU
        torch.nn.Linear(5, 1)
    )
    return model

def main():
    model = create_model()
    data = torch.randn(32, 10)
    output = model(data).numpy()  # 错误：需要 detach()
    print(f"输出形状: {output.shape}")
```

**执行自动修复：**
```bash
python gemini_auto_fixer.py examples/test_pytorch_buggy.py
```

**输出：**
```
🚀 开始自动修复和执行: examples/test_pytorch_buggy.py
📍 第 1 次尝试执行...
❌ 执行失败: AttributeError: module 'torch.nn' has no attribute 'ReLu'
🔧 尝试修复代码...
🤖 正在使用 Gemini 分析和修复代码...
📁 原文件已备份
✏️ 修复后的代码已保存
📍 第 2 次尝试执行...
✅ 代码执行成功！
📤 输出结果:
输出形状: (32, 1)
🎉 任务完成！
```

### 示例 2: 数据处理错误修复

**原始代码（有错误）：**
```python
import pandas as pd

def analyze_data():
    data = {'name': ['Alice', 'Bob'], 'age': [25, 30]}
    df = pd.DataFrame(data)
    
    # 错误：列名拼写错误
    avg_age = df['aeg'].mean()
    
    # 错误：除零
    result = 10 / 0
    
    return avg_age, result
```

**自动修复后：**
```python
import pandas as pd

def analyze_data():
    data = {'name': ['Alice', 'Bob'], 'age': [25, 30]}
    df = pd.DataFrame(data)
    
    # 修复：正确的列名
    avg_age = df['age'].mean()
    
    # 修复：异常处理
    try:
        result = 10 / 0
    except ZeroDivisionError:
        result = "错误：不能除以零"
    
    return avg_age, result
```

## ⚙️ 配置选项

### 修改最大尝试次数
在 `gemini_auto_fixer.py` 中：
```python
class GeminiAutoFixer:
    def __init__(self):
        self.max_attempts = 3  # 修改为你需要的次数
```

### 修改超时设置
```python
result = subprocess.run(
    [sys.executable, file_path],
    capture_output=True,
    text=True,
    timeout=30  # 修改超时时间（秒）
)
```

## 🔗 与 Scientific AI System 集成

### 在主系统中使用

```python
# 在主系统代码中集成自动修复功能
import sys
sys.path.append('/home/jupyter/MTCS_module/auto_code_fixer')
from gemini_auto_fixer import GeminiAutoFixer

def run_with_auto_fix(script_path):
    fixer = GeminiAutoFixer()
    return fixer.auto_fix_and_run(script_path)

# 使用示例
success = run_with_auto_fix('my_analysis_script.py')
if success:
    print("分析脚本执行成功")
else:
    print("分析脚本修复失败")
```

### 批量处理

```python
import os
from gemini_auto_fixer import GeminiAutoFixer

def batch_fix_scripts(directory):
    """批量修复目录中的所有 Python 脚本"""
    fixer = GeminiAutoFixer()
    results = {}
    
    for file in os.listdir(directory):
        if file.endswith('.py'):
            file_path = os.path.join(directory, file)
            success = fixer.auto_fix_and_run(file_path)
            results[file] = success
    
    return results

# 使用示例
results = batch_fix_scripts('/path/to/scripts')
print(f"成功修复: {sum(results.values())}/{len(results)} 个脚本")
```

## 📝 注意事项

### API 使用限制
- **免费版限制**: 60次/分钟，1000次/天
- **网络要求**: 需要稳定的网络连接访问 Gemini API
- **认证**: 首次使用需要运行 `gemini auth` 进行身份验证

### 安全考虑
- ✅ 自动备份原文件（`.backup_timestamp` 格式）
- ✅ 不会修改系统文件或敏感配置
- ⚠️ 重要代码建议额外备份
- ⚠️ 生产环境使用前请充分测试

### 限制说明
- 🔸 主要支持 Python 代码（可扩展到其他语言）
- 🔸 复杂的业务逻辑错误可能需要人工干预
- 🔸 依赖外部 API，离线环境无法使用

## 🛠️ 故障排除

### 常见问题

**1. Gemini CLI 未找到**
```bash
npm uninstall -g @google/gemini-cli
npm install -g @google/gemini-cli
```

**2. 身份验证失败**
```bash
gemini auth
```

**3. 权限问题**
```bash
chmod +x /home/jupyter/MTCS_module/auto_code_fixer/run_with_auto_fix.sh
```

**4. Python 路径问题**
确保使用正确的 Python 环境：
```bash
which python
python --version
```

### 调试模式

启用详细日志：
```python
# 在 gemini_auto_fixer.py 中添加
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🚀 扩展功能

### 支持其他编程语言

修改执行命令来支持其他语言：
```python
# 支持 JavaScript
if file_path.endswith('.js'):
    result = subprocess.run(['node', file_path], ...)

# 支持 R
if file_path.endswith('.R'):
    result = subprocess.run(['Rscript', file_path], ...)
```

### 自定义修复提示

```python
def get_custom_prompt(code, error, language='python'):
    prompts = {
        'python': f"修复这个Python代码错误：\n代码：{code}\n错误：{error}",
        'javascript': f"Fix this JavaScript error:\nCode: {code}\nError: {error}",
    }
    return prompts.get(language, prompts['python'])
```

## 📚 相关文档

- [详细使用文档](README_auto_fixer.md)
- [Scientific AI System 主文档](../README.MD)
- [Gemini CLI 官方文档](https://github.com/google-gemini/gemini-cli)

## 🤝 贡献

欢迎提交问题报告和功能请求！如需扩展功能，请：

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 发起 Pull Request

---

*本模块是 Scientific AI System 的组成部分，专注于提供智能化的代码执行和错误修复能力。*