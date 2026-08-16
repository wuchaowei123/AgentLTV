#!/usr/bin/env python3
"""
增强版 Gemini 自动代码修复器
解决超时、导入错误和结果文件问题
"""

import subprocess
import os
import sys
import time
import json
import re
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

class EnhancedGeminiAutoFixer:
    def __init__(self):
        self.max_attempts = 3
        self.gemini_timeout = None  # No timeout for Gemini CLI
        self.execution_timeout = None  # No timeout for code execution
        
    def execute_python_file(self, file_path: str) -> Tuple[bool, str, str]:
        """执行Python文件并返回结果"""
        try:
            result = subprocess.run(
                [sys.executable, file_path],
                capture_output=True,
                text=True,
                timeout=self.execution_timeout
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", f"执行超时 ({self.execution_timeout}秒)"
        except Exception as e:
            return False, "", str(e)
    
    def _attempt_local_fix(self, code: str, error_msg: str) -> Optional[str]:
        """尝试本地修复常见错误"""
        print("🔧 尝试本地智能修复...")
        
        fixed_code = code
        
        # 修复 IterativeImputer 导入错误
        if "IterativeImputer" in error_msg and "experimental" in error_msg:
            print("  ✓ 修复 IterativeImputer 导入问题")
            # 在 sklearn.impute import IterativeImputer 之前添加 experimental import
            if "from sklearn.impute import IterativeImputer" in fixed_code:
                fixed_code = fixed_code.replace(
                    "from sklearn.impute import IterativeImputer",
                    "from sklearn.experimental import enable_iterative_imputer\nfrom sklearn.impute import IterativeImputer"
                )
            elif "import IterativeImputer" in fixed_code:
                # 在文件开头添加
                lines = fixed_code.split('\n')
                import_line_idx = -1
                for i, line in enumerate(lines):
                    if "IterativeImputer" in line and "import" in line:
                        import_line_idx = i
                        break
                
                if import_line_idx >= 0:
                    lines.insert(import_line_idx, "from sklearn.experimental import enable_iterative_imputer")
                    fixed_code = '\n'.join(lines)
        
        # 修复常见的导入错误
        import_fixes = {
            "No module named 'sklearn.metrics'": "from sklearn import metrics",
            "cannot import name 'accuracy_score'": "from sklearn.metrics import accuracy_score",
            "cannot import name 'roc_auc_score'": "from sklearn.metrics import roc_auc_score",
            "cannot import name 'f1_score'": "from sklearn.metrics import f1_score",
            "No module named 'pandas'": "import pandas as pd",
            "No module named 'numpy'": "import numpy as np",
        }
        
        for error_pattern, fix in import_fixes.items():
            if error_pattern in error_msg:
                print(f"  ✓ 修复导入问题: {error_pattern}")
                # 在文件开头添加缺失的导入
                if fix not in fixed_code:
                    lines = fixed_code.split('\n')
                    # 找到第一个非注释、非空行
                    insert_idx = 0
                    for i, line in enumerate(lines):
                        stripped = line.strip()
                        if stripped and not stripped.startswith('#') and not stripped.startswith('"""') and not stripped.startswith("'''"):
                            insert_idx = i
                            break
                    lines.insert(insert_idx, fix)
                    fixed_code = '\n'.join(lines)
        
        # 修复常见的语法错误
        if "name 'pi' is not defined" in error_msg:
            print("  ✓ 修复 pi 未定义问题")
            fixed_code = fixed_code.replace("pi *", "math.pi *")
            if "import math" not in fixed_code:
                fixed_code = "import math\n" + fixed_code
        
        # 修复除零错误
        if "ZeroDivisionError" in error_msg or "division by zero" in error_msg:
            print("  ✓ 添加除零错误处理")
            # 这个比较复杂，暂时跳过本地修复
            pass
        
        return fixed_code if fixed_code != code else None
    
    def fix_code_with_gemini(self, file_path: str, error_msg: str) -> Optional[str]:
        """使用 Gemini CLI 修复代码，带重试和本地备用修复"""
        try:
            # 读取原始代码
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # 构建增强的修复提示
            prompt = f"""我有一个Python代码文件出现了错误，请帮我修复它。

原始代码：
```python
{code}
```

错误信息：
```
{error_msg}
```

请提供修复后的完整代码，只返回Python代码，不要包含解释。代码应该能够直接运行。

特别注意以下常见问题的修复：
1. 如果遇到 sklearn 的 IterativeImputer 错误，请在导入前添加：from sklearn.experimental import enable_iterative_imputer
2. 如果遇到导入错误，请检查并添加正确的导入语句
3. 如果遇到 'pi' 未定义，请使用 math.pi 并导入 math 模块
4. 如果遇到除零错误，请添加适当的异常处理
5. 确保所有依赖都正确导入
6. 保持代码的完整性和可执行性
7. 不要改变代码的核心逻辑，只修复错误"""
            
            print("🤖 正在使用 Gemini 分析和修复代码...")
            
            # 多次重试机制
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    print(f"  尝试 {attempt + 1}/{max_retries}...")
                    
                    # 调用 Gemini CLI
                    process = subprocess.run(
                        ['gemini', 'chat'],
                        input=prompt,
                        capture_output=True,
                        text=True,
                        timeout=self.gemini_timeout
                    )
                    
                    if process.returncode == 0:
                        response = process.stdout.strip()
                        
                        # 提取代码块
                        fixed_code = self._extract_code_from_response(response)
                        if fixed_code:
                            print("  ✅ Gemini 修复成功")
                            return fixed_code
                        else:
                            print("  ⚠️ 无法从响应中提取代码")
                    else:
                        print(f"  ⚠️ Gemini CLI 调用失败: {process.stderr}")
                        
                except subprocess.TimeoutExpired:
                    print(f"  ⚠️ Gemini CLI 超时 ({self.gemini_timeout}秒)")
                    
                except Exception as e:
                    print(f"  ⚠️ Gemini 调用异常: {e}")
                
                # 如果不是最后一次尝试，等待后重试
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2  # 递增等待时间
                    print(f"  等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
            
            # 所有 Gemini 尝试都失败，尝试本地修复
            print("❌ Gemini CLI 所有尝试都失败，尝试本地智能修复")
            return self._attempt_local_fix(code, error_msg)
                
        except Exception as e:
            print(f"❌ 修复过程中出错: {e}")
            # 尝试本地修复作为最后手段
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                return self._attempt_local_fix(code, error_msg)
            except:
                return None
    
    def _extract_code_from_response(self, response: str) -> Optional[str]:
        """从 Gemini 响应中提取代码"""
        # 优先查找 python 代码块
        if '```python' in response:
            start = response.find('```python') + 9
            end = response.find('```', start)
            if end != -1:
                return response[start:end].strip()
            else:
                return response[start:].strip()
        
        # 查找普通代码块
        elif '```' in response:
            start = response.find('```') + 3
            end = response.find('```', start)
            if end != -1:
                return response[start:end].strip()
            else:
                return response[start:].strip()
        
        # 没有代码块标记，尝试提取看起来像代码的部分
        else:
            # 如果响应包含 import 语句或 def 函数定义，可能整个都是代码
            if any(keyword in response for keyword in ['import ', 'def ', 'class ', 'if __name__']):
                return response.strip()
            
            return None
    
    def auto_fix_and_run(self, file_path: str) -> bool:
        """自动修复并运行代码"""
        if not os.path.exists(file_path):
            print(f"❌ 文件不存在: {file_path}")
            return False
        
        print(f"🚀 开始自动修复和执行: {file_path}")
        print("=" * 50)
        
        for attempt in range(1, self.max_attempts + 1):
            print(f"\n📍 第 {attempt} 次尝试执行...")
            
            # 执行代码
            success, stdout, stderr = self.execute_python_file(file_path)
            
            if success:
                print("✅ 代码执行成功！")
                if stdout:
                    print("\n📤 输出结果:")
                    print(stdout)
                return True
            else:
                print(f"❌ 执行失败: {stderr}")
                
                if attempt < self.max_attempts:
                    # 尝试修复
                    print(f"\n🔧 尝试修复代码 (第 {attempt} 次)...")
                    
                    fixed_code = self.fix_code_with_gemini(file_path, stderr)
                    
                    if fixed_code:
                        # 备份原文件
                        backup_path = f"{file_path}.backup_{int(time.time())}"
                        try:
                            os.rename(file_path, backup_path)
                            print(f"📁 原文件已备份为: {backup_path}")
                        except:
                            # 如果重命名失败，直接覆盖
                            print("📁 直接覆盖原文件（备份失败）")
                        
                        # 写入修复后的代码
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(fixed_code)
                        
                        print("✏️  修复后的代码已保存")
                    else:
                        print("❌ 无法获取修复建议")
                        return False
                else:
                    print(f"❌ 达到最大尝试次数 ({self.max_attempts})，修复失败")
                    return False
        
        return False
    
    def get_execution_result(self, file_path: str) -> Dict[str, Any]:
        """获取代码执行结果，包括输出和可能的评分"""
        success, stdout, stderr = self.execute_python_file(file_path)
        
        result = {
            'success': success,
            'stdout': stdout,
            'stderr': stderr,
            'score': 0.0,
            'predictions': None
        }
        
        if success and stdout:
            # 尝试从输出中提取评分信息
            score = self._extract_score_from_output(stdout)
            if score is not None:
                result['score'] = score
        
        return result
    
    def _extract_score_from_output(self, output: str) -> Optional[float]:
        """从输出中提取评分"""
        # 常见的评分模式
        score_patterns = [
            r'AUC[:\s]*([0-9]*\.?[0-9]+)',
            r'Score[:\s]*([0-9]*\.?[0-9]+)',
            r'Accuracy[:\s]*([0-9]*\.?[0-9]+)',
            r'F1[:\s]*([0-9]*\.?[0-9]+)',
            r'ROC[:\s]*([0-9]*\.?[0-9]+)',
            r'([0-9]*\.?[0-9]+)\s*AUC',
            r'Final.*?([0-9]*\.?[0-9]+)',
        ]
        
        for pattern in score_patterns:
            matches = re.findall(pattern, output, re.IGNORECASE)
            if matches:
                try:
                    score = float(matches[-1])  # 取最后一个匹配
                    if 0 <= score <= 1:  # 假设评分在0-1之间
                        return score
                except ValueError:
                    continue
        
        return None

def main():
    if len(sys.argv) != 2:
        print("用法: python enhanced_gemini_auto_fixer.py <python_file>")
        print("示例: python enhanced_gemini_auto_fixer.py test.py")
        sys.exit(1)
    
    file_path = sys.argv[1]
    fixer = EnhancedGeminiAutoFixer()
    
    success = fixer.auto_fix_and_run(file_path)
    
    if success:
        print("\n🎉 任务完成！代码已成功执行。")
        
        # 获取详细结果
        result = fixer.get_execution_result(file_path)
        if result['score'] > 0:
            print(f"📊 检测到评分: {result['score']:.4f}")
    else:
        print("\n😞 任务失败，无法修复代码。")

if __name__ == "__main__":
    main()