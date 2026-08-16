#!/usr/bin/env python3
"""
Gemini 自动代码修复器
使用 Google Gemini API 自动修复 Python 代码错误
"""

import subprocess
import os
import sys
import time
import json
from pathlib import Path
from google import genai
from google.genai import types

class GeminiAutoFixer:
    # def __init__(self):
    #     self.max_attempts = 3
    #     # 从环境变量获取API密钥
    #     self.api_key = os.getenv('GOOGLE_API_KEY', 'AIzaSyCPWw2gwyEuaj0DMFxTig3iEZcwGBh8F5A')
    #     self.model = 'gemini-2.0-flash-exp'
        
    #     if not self.api_key:
    #         raise ValueError("未设置 GOOGLE_API_KEY 环境变量")
        
    #     print(f"✅ Gemini 自动修复器已初始化")
    #     print(f"   模型: {self.model}")

    class GeminiAutoFixer:
    def __init__(self):
        self.max_attempts = 3
        self.model = 'gemini-2.5-pro'  # 你在GCP上使用的模型
        self.project = "prefab-root-439302-c5"
        self.location = "us-central1"
        
        print(f"✅ Gemini 自动修复器已初始化")
        print(f"   模型: {self.model} (Vertex AI 模式)")

    
    def execute_python_file(self, file_path):
        """执行 Python 文件并返回结果"""
        try:
            result = subprocess.run(
                [sys.executable, file_path],
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "执行超时（300秒）"
        except Exception as e:
            return False, "", str(e)
    
    def fix_code_with_gemini(self, file_path, error_msg):
        """使用 Gemini API 修复代码"""
        try:
            # 读取原始代码
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # 构建修复提示词
            prompt = f"""我有一个 Python 代码文件出现了错误。请帮我修复它。

原始代码:
```python
{code}
```

错误信息:
```
{error_msg}
```

请提供完整的修复后的代码。只返回 Python 代码，不要添加任何解释或 markdown 格式。代码应该可以直接执行。"""
            
            # 调用 Gemini API
            print("🤖 使用 Gemini 分析和修复代码...")
            
            try:
                # from google import genai
                
                # client = genai.Client(api_key=self.api_key)
                
                # response = client.models.generate_content(
                #     model=self.model,
                #     contents=prompt
                # )

                # 如果在GCP环境，直接使用Vertex AI方式，无需API Key
                client = genai.Client(vertexai=True, project="prefab-root-439302-c5", location="us-central1")
                response = client.models.generate_content(
                    model=self.model,
                    config=types.GenerateContentConfig(
                        temperature=0.4,  # 可选：生成稳定一点
                        system_instruction="你是一个帮助自动修复Python错误的专家。请只返回Python代码。"
                    ),
                    contents=prompt
                )
                
                fixed_code = response.text.strip()
                
                # 从 markdown 中提取代码（如果存在）
                if '```python' in fixed_code:
                    start = fixed_code.find('```python') + 9
                    end = fixed_code.find('```', start)
                    if end != -1:
                        fixed_code = fixed_code[start:end].strip()
                    else:
                        fixed_code = fixed_code[start:].strip()
                elif '```' in fixed_code:
                    start = fixed_code.find('```') + 3
                    end = fixed_code.find('```', start)
                    if end != -1:
                        fixed_code = fixed_code[start:end].strip()
                    else:
                        fixed_code = fixed_code[start:].strip()
                
                return fixed_code
                
            except Exception as e:
                print(f"❌ Gemini API 调用失败: {e}")
                return None
                
        except Exception as e:
            print(f"❌ 修复过程中出错: {e}")
            return None
    
    def extract_score_from_output(self, stdout):
        """从输出中提取分数"""
        import re
        
        # 尝试从输出中提取分数
        score_patterns = [
            r'📊\s+(?:f1_score|F1|accuracy|AUC|RMSE):\s+([0-9.]+)',
            r'分数:\s+([0-9.]+)',
            r'最终分数:\s+([0-9.]+)',
            r'结果:\s+([0-9.]+)',
            r'([0-9.]+)(?=\s*$)',  # 最后一行的数字
        ]
        
        for pattern in score_patterns:
            matches = re.findall(pattern, stdout, re.IGNORECASE)
            if matches:
                try:
                    return float(matches[-1])  # 取最后一个匹配的分数
                except ValueError:
                    continue
        
        return 0.0
    
    def save_result_file(self, file_path, success, score, stdout, stderr):
        """保存结果文件"""
        # 从文件路径提取 node_id
        node_id = None
        if 'node_' in file_path:
            node_id = file_path.split('node_')[1].split('.py')[0]
        
        if node_id:
            # 创建结果文件路径（AI系统期望的格式）
            result_file = f"/tmp/ai_result_{node_id}_{int(time.time())}.json"
            
            result_data = {
                'score': float(score),
                'success': success,
                'stdout': stdout,
                'stderr': stderr,
                'metric': 'f1_score',  # 默认指标
                'higher_is_better': True
            }
            
            try:
                with open(result_file, 'w', encoding='utf-8') as f:
                    json.dump(result_data, f, indent=2)
                print(f"💾 结果已保存到: {result_file}")
                return result_file
            except Exception as e:
                print(f"❌ 保存结果文件失败: {e}")
        
        return None

    def auto_fix_and_run(self, file_path):
        """自动修复并运行代码"""
        if not os.path.exists(file_path):
            print(f"❌ 文件未找到: {file_path}")
            return False
        
        print(f"🚀 开始自动修复和执行: {file_path}")
        print("=" * 50)
        
        final_stdout = ""
        final_stderr = ""
        final_success = False
        
        for attempt in range(1, self.max_attempts + 1):
            print(f"\n📍 第 {attempt} 次尝试执行...")
            
            # 执行代码
            success, stdout, stderr = self.execute_python_file(file_path)
            
            final_stdout = stdout
            final_stderr = stderr
            final_success = success
            
            if success:
                print("✅ 代码执行成功！")
                if stdout:
                    print("\n📤 输出:")
                    print(stdout)
                
                # 提取分数并保存结果文件
                score = self.extract_score_from_output(stdout)
                self.save_result_file(file_path, True, score, stdout, stderr)
                return True
            else:
                print(f"❌ 执行失败: {stderr}")
                
                if attempt < self.max_attempts:
                    # 尝试修复
                    print(f"\n🔧 尝试修复代码（第 {attempt} 次）...")
                    
                    fixed_code = self.fix_code_with_gemini(file_path, stderr)
                    
                    if fixed_code:
                        # 备份原文件
                        backup_path = f"{file_path}.backup_{int(time.time())}"
                        os.rename(file_path, backup_path)
                        print(f"📁 原文件已备份为: {backup_path}")
                        
                        # 写入修复后的代码
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(fixed_code)
                        
                        print("✏️  修复后的代码已保存")
                    else:
                        print("❌ 无法获取修复建议")
                        # 保存失败结果
                        self.save_result_file(file_path, False, 0.0, final_stdout, final_stderr)
                        return False
                else:
                    print(f"❌ 达到最大尝试次数（{self.max_attempts}），修复失败")
                    # 保存失败结果
                    self.save_result_file(file_path, False, 0.0, final_stdout, final_stderr)
                    return False
        
        return False

def main():
    if len(sys.argv) != 2:
        print("用法: python gemini_auto_fixer.py <python_file>")
        print("示例: python gemini_auto_fixer.py test.py")
        sys.exit(1)
    
    file_path = sys.argv[1]
    fixer = GeminiAutoFixer()
    
    success = fixer.auto_fix_and_run(file_path)
    
    if success:
        print("\n🎉 任务完成！代码执行成功。")
    else:
        print("\n😞 任务失败，无法修复代码。")

if __name__ == "__main__":
    main()

