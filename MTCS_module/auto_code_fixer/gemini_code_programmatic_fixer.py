"""
Gemini 编程式自动修复器
====================================

使用 Google Gemini API 自动修复和运行 Python 代码。

这个模块模拟交互式代码会话工作流：
1. 运行代码 → 获取错误
2. 询问 Gemini 修复 → 应用修复  
3. 再次运行代码 → 重复直到成功
"""

import subprocess
import json
import os
import time
import re
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
from google import genai
from google.genai import types

class GeminiCodeProgrammaticFixer:
    """使用 Gemini API 的自动修复器"""
    
    # def __init__(self, max_attempts: int = 5):
        # """
        # 初始化编程式自动修复器。
        
        # Args:
        #     max_attempts: 最大修复尝试次数
        # """
        # self.max_attempts = max_attempts
        # self.api_key = os.getenv("GOOGLE_API_KEY", "AIzaSyCPWw2gwyEuaj0DMFxTig3iEZcwGBh8F5A")
        # self.model = "gemini-2.0-flash-exp"
        
        # print("✅ Gemini 编程式自动修复器已初始化")
        # print(f"   模型: {self.model}")
        # print(f"   最大尝试次数: {max_attempts}")
        # print(f"   超时设置: 240 秒（4 分钟）")
        # print(f"   超时重试次数: 2")
    def __init__(self, max_attempts: int = 5):
        self.max_attempts = max_attempts
        self.model = 'gemini-2.5-pro'  # 你在GCP上使用的模型
        self.project = "prefab-root-439302-c5"
        self.location = "us-central1"
        
        print(f"✅ Gemini 自动修复器已初始化")
        print(f"   模型: {self.model} (Vertex AI 模式)")
    
    def run_code(self, file_path: str, run_timeout: int = 600, conda_env: str = "pytorch") -> Tuple[bool, str, str]:
        """
        运行 Python 代码并捕获输出/错误。
        
        Args:
            file_path: Python 文件路径
            run_timeout: 超时时间（秒）
            conda_env: Conda 环境名称
            
        Returns:
            元组 (是否成功, 标准输出, 标准错误)
        """
        # 获取绝对路径和工作目录
        abs_path = Path(file_path).resolve()
        work_dir = abs_path.parent
        file_name = abs_path.name
        
        '''cmd = f"""
        source ~/.bashrc && \
        conda activate {conda_env} && \
        cd {work_dir} && \
        timeout {run_timeout} python {file_name} 2>&1
        """
        '''
        cmd = f"""
        source ~/.bashrc && \
        cd {work_dir} && \
        timeout {run_timeout} python {file_name} 2>&1
        """
        
        try:
            result = subprocess.run(
                ["bash", "-c", cmd],
                capture_output=True,
                text=True,
                timeout=run_timeout + 5  # 额外缓冲
            )
            
            output = result.stdout + result.stderr
            success = result.returncode == 0
            
            return success, output, ""
            
        except subprocess.TimeoutExpired:
            return False, "", f"超时 {run_timeout} 秒"
        except Exception as e:
            return False, "", f"执行错误: {e}"
    
    def ask_gemini(self, prompt: str, timeout: int = 240, max_retries: int = 2) -> Optional[str]:
        """
        使用 Gemini API 获取代码修复建议。
        
        Args:
            prompt: 给 Gemini 的问题/指令
            timeout: Gemini 请求超时时间（默认: 240 秒）
            max_retries: 超时重试次数（默认: 2）
            
        Returns:
            Gemini 的响应文本，出错时返回 None
        """
        # 超时重试逻辑
        for retry_attempt in range(max_retries + 1):
            if retry_attempt > 0:
                print(f"   🔄 重试 {retry_attempt}/{max_retries}...")
                time.sleep(2)  # 重试前短暂延迟
            
            try:
                from google import genai
                
                start_time = time.time()
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
                
                duration = time.time() - start_time
                
                if response and response.text:
                    print(f"   ✓ Gemini 响应已收到，耗时 {duration:.1f} 秒")
                    if retry_attempt > 0:
                        print(f"   ✅ 在 {retry_attempt} 次重试后成功")
                    return response.text
                else:
                    print(f"   ❌ Gemini 返回空响应")
                    return None
                    
            except Exception as e:
                print(f"   ❌ 调用 Gemini API 时出错: {e}")
                if retry_attempt < max_retries:
                    continue  # 重试
                else:
                    return None  # 所有重试都用完了
        
        return None  # 不应该到达这里
    
    def extract_error_info(self, output: str) -> str:
        """从输出中提取简洁的错误信息"""
        lines = output.split('\n')
        
        # 查找回溯信息
        error_lines = []
        in_traceback = False
        
        for line in lines:
            if 'Traceback (most recent call last):' in line:
                in_traceback = True
            if in_traceback:
                error_lines.append(line)
        
        if error_lines:
            # 返回回溯信息的最后 20 行
            return '\n'.join(error_lines[-20:])
        else:
            # 如果没有回溯信息，返回最后 10 行
            return '\n'.join(lines[-10:])
    
    def try_auto_install_package(self, error_output: str) -> bool:
        """
        检测 ModuleNotFoundError 并自动安装缺失的包。
        
        Args:
            error_output: 代码执行的错误信息
            
        Returns:
            如果安装了包返回 True，否则返回 False
        """
        # 检查是否是 ModuleNotFoundError
        if 'ModuleNotFoundError' not in error_output and 'No module named' not in error_output:
            return False
        
        # 提取模块名称
        import re
        match = re.search(r"No module named ['\"]([^'\"]+)['\"]", error_output)
        if not match:
            return False
        
        module_name = match.group(1)
        print(f"   📦 检测到缺失的模块: {module_name}")
        
        # 常见模块名到 pip 包名的映射
        module_to_package = {
            'iterstrat': 'iterative-stratification',
            'skmultilearn': 'scikit-multilearn',
            'cv2': 'opencv-python',
            'sklearn': 'scikit-learn',
            'PIL': 'Pillow',
        }
        
        # 获取基础模块名（例如从 'iterstrat.ml_stratifiers' 中获取 'iterstrat'）
        base_module = module_name.split('.')[0]
        package_name = module_to_package.get(base_module, base_module)
        
        print(f"   🔧 尝试安装: {package_name}")
        
        try:
            import subprocess
            result = subprocess.run(
                ['pip', 'install', package_name],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                print(f"   ✅ 成功安装 {package_name}")
                return True
            else:
                print(f"   ❌ 安装 {package_name} 失败: {result.stderr[:200]}")
                return False
                
        except Exception as e:
            print(f"   ❌ 安装过程中出错: {e}")
            return False
    
    def apply_fix_to_file(self, file_path: str, fixed_code: str) -> bool:
        """
        将修复后的代码应用到文件。
        
        Args:
            file_path: 文件路径
            fixed_code: 修复后的代码
            
        Returns:
            成功返回 True，失败返回 False
        """
        try:
            # 从响应中提取代码块
            code_to_write = fixed_code
            
            # 如果包含 markdown 代码块，提取它
            if '```python' in fixed_code:
                start = fixed_code.find('```python') + 9
                end = fixed_code.find('```', start)
                if end != -1:
                    code_to_write = fixed_code[start:end].strip()
            elif '```' in fixed_code:
                start = fixed_code.find('```') + 3
                end = fixed_code.find('```', start)
                if end != -1:
                    code_to_write = fixed_code[start:end].strip()
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(code_to_write)
            
            print(f"   ✅ 代码已更新到文件")
            return True
            
        except Exception as e:
            print(f"   ❌ 应用修复时出错: {e}")
            return False
    
    def auto_fix_and_run(self, file_path: str, run_timeout: int = 600) -> Tuple[bool, str]:
        """
        使用 Gemini 自动修复并运行代码。
        
        这模拟了交互式代码会话工作流：
        1. 运行代码
        2. 如果出错 → 询问 Gemini 修复
        3. 再次运行 → 重复直到成功或达到最大尝试次数
        
        Args:
            file_path: Python 文件路径
            run_timeout: 每次代码运行的超时时间
            
        Returns:
            元组 (是否成功, 最终输出)
        """
        abs_path = Path(file_path).resolve()
        
        print("=" * 70)
        print("🚀 开始编程式自动修复和运行工作流")
        print("=" * 70)
        print(f"📁 文件: {abs_path}")
        print(f"🔢 最大尝试次数: {self.max_attempts}")
        print(f"⏱️  运行超时: {run_timeout} 秒")
        print(f"🤖 模型: {self.model}")
        print("=" * 70)
        print()
        
        all_output = []
        
        for attempt in range(1, self.max_attempts + 1):
            print("─" * 70)
            print(f"📍 尝试 {attempt}/{self.max_attempts}")
            print("─" * 70)
            print()
            
            # 运行代码
            print(f"🔄 运行 {abs_path.name}...")
            success, output, error = self.run_code(str(abs_path), run_timeout=run_timeout)
            all_output.append(output)
            
            if success:
                print()
                print("=" * 70)
                print("✅ 成功！代码执行无错误！")
                print("=" * 70)
                print()
                print("📊 最终输出（最后 50 行）:")
                print('\n'.join(output.split('\n')[-50:]))
                print()
                return True, '\n\n'.join(all_output)
            
            print(f"❌ 执行失败")
            error_info = self.extract_error_info(output)
            print(f"   错误:\n{error_info[:500]}")
            print()
            
            # 首先尝试自动安装缺失的包
            if self.try_auto_install_package(output):
                print(f"   🔄 包已安装，重新运行代码...")
                print()
                # 安装包后立即重新运行
                success, output, error = self.run_code(str(abs_path), run_timeout=run_timeout)
                all_output.append(output)
                
                if success:
                    print()
                    print("=" * 70)
                    print("✅ 自动安装后成功！")
                    print("=" * 70)
                    print()
                    print("📊 最终输出（最后 50 行）:")
                    print('\n'.join(output.split('\n')[-50:]))
                    print()
                    return True, '\n\n'.join(all_output)
                else:
                    print(f"   ⚠️  安装包后仍然失败，将请求 Gemini 修复")
                    error_info = self.extract_error_info(output)
            
            # 如果不是最后一次尝试，请求 Gemini 修复
            if attempt < self.max_attempts:
                print(f"🤖 询问 Gemini 修复错误...")
                
                # 读取当前代码
                with open(abs_path, 'r', encoding='utf-8') as f:
                    current_code = f.read()
                
                # 为 Gemini 构建提示词
                prompt = f"""请修复这个 Python 代码。代码执行时出现了以下错误:

错误信息:
{error_info}

当前代码:
```python
{current_code}
```

请提供完整的修复后的代码。只返回修复后的 Python 代码，不要添加任何解释。"""
                
                print(f"   📝 提示词长度: {len(prompt)} 字符")
                
                response = self.ask_gemini(prompt, timeout=120)
                
                if not response:
                    print(f"   ❌ 未能获取 Gemini 响应，跳到下一次尝试...")
                    continue
                
                print(f"   💡 Gemini 的响应（前 300 字符）:")
                print(f"      {response[:300]}...")
                print()
                
                # 应用修复
                if self.apply_fix_to_file(str(abs_path), response):
                    print("   ✅ 修复已应用到文件")
                else:
                    print("   ❌ 应用修复失败")
                    continue
                
                print()
                
                # 下次尝试前短暂延迟
                time.sleep(1)
            else:
                print()
                print("😞 达到最大尝试次数但未成功")
        
        print()
        print("=" * 70)
        print("❌ 经过所有尝试后仍未能修复代码")
        print("=" * 70)
        return False, '\n\n'.join(all_output)


def test_programmatic_fixer():
    """在测试代码上测试编程式修复器"""
    fixer = GeminiCodeProgrammaticFixer(max_attempts=5)
    
    test_file = Path.cwd() / "test_broken_code.py"
    if not test_file.exists():
        print(f"❌ 测试文件未找到: {test_file}")
        return
    
    success, output = fixer.auto_fix_and_run(str(test_file), run_timeout=60)
    
    if success:
        print("🎉 测试通过！")
    else:
        print("❌ 测试失败")
    
    return success


if __name__ == "__main__":
    test_programmatic_fixer()

