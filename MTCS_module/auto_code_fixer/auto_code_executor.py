#!/usr/bin/env python3
"""
自动代码执行和修复系统
使用 Gemini CLI 自动执行代码并在出现错误时进行修复
"""

import subprocess
import json
import os
import sys
import time
import logging
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('auto_executor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AutoCodeExecutor:
    def __init__(self, max_iterations: int = 5):
        """
        初始化自动代码执行器
        
        Args:
            max_iterations: 最大修复尝试次数
        """
        self.max_iterations = max_iterations
        self.execution_log = []
        
    def execute_script(self, script_path: str) -> Tuple[bool, str, Optional[str]]:
        """
        执行Python脚本并捕获输出和错误
        
        Args:
            script_path: 脚本文件路径
            
        Returns:
            (成功标志, 输出内容, 错误信息)
        """
        try:
            logger.info(f"执行脚本: {script_path}")
            process = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=30  # 30秒超时
            )
            
            if process.returncode == 0:
                logger.info("脚本执行成功")
                return True, process.stdout, None
            else:
                logger.warning(f"脚本执行失败，返回码: {process.returncode}")
                return False, process.stderr, process.stderr
                
        except subprocess.TimeoutExpired:
            logger.error("脚本执行超时")
            return False, "", "脚本执行超时"
        except Exception as e:
            logger.error(f"执行脚本时发生异常: {e}")
            return False, "", str(e)
    
    def get_gemini_fix(self, script_path: str, error_message: str) -> Optional[str]:
        """
        使用 Gemini CLI 获取代码修复建议
        
        Args:
            script_path: 脚本文件路径
            error_message: 错误信息
            
        Returns:
            修复后的代码内容
        """
        try:
            # 读取原始代码
            with open(script_path, 'r', encoding='utf-8') as f:
                original_code = f.read()
            
            # 构建 Gemini 提示
            prompt = f"""请分析以下Python代码中的错误并提供修复方案：

原始代码：
```python
{original_code}
```

错误信息：
```
{error_message}
```

请提供完整的修复后的代码，只返回Python代码，不要包含任何解释或markdown格式。确保代码可以直接运行。"""

            # 创建临时提示文件
            prompt_file = "/tmp/gemini_prompt.txt"
            with open(prompt_file, 'w', encoding='utf-8') as f:
                f.write(prompt)
            
            logger.info("正在使用 Gemini CLI 分析错误...")
            
            # 调用 Gemini CLI
            process = subprocess.run(
                ['gemini', 'chat', '--input', prompt_file],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if process.returncode == 0:
                fixed_code = process.stdout.strip()
                # 清理可能的markdown格式
                if fixed_code.startswith('```python'):
                    fixed_code = fixed_code.split('```python')[1]
                if fixed_code.endswith('```'):
                    fixed_code = fixed_code.rsplit('```', 1)[0]
                
                logger.info("Gemini CLI 成功提供了修复建议")
                return fixed_code.strip()
            else:
                logger.error(f"Gemini CLI 调用失败: {process.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"获取 Gemini 修复建议时发生异常: {e}")
            return None
        finally:
            # 清理临时文件
            if os.path.exists(prompt_file):
                os.remove(prompt_file)
    
    def apply_fix(self, script_path: str, fixed_code: str) -> bool:
        """
        应用修复后的代码
        
        Args:
            script_path: 脚本文件路径
            fixed_code: 修复后的代码
            
        Returns:
            是否成功应用修复
        """
        try:
            # 备份原始文件
            backup_path = f"{script_path}.backup.{int(time.time())}"
            with open(script_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(original_content)
            
            # 写入修复后的代码
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(fixed_code)
            
            logger.info(f"已应用修复，原始文件备份为: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"应用修复时发生异常: {e}")
            return False
    
    def auto_execute_and_fix(self, script_path: str) -> Dict[str, Any]:
        """
        自动执行代码并在出现错误时进行修复
        
        Args:
            script_path: 脚本文件路径
            
        Returns:
            执行结果摘要
        """
        if not os.path.exists(script_path):
            logger.error(f"脚本文件不存在: {script_path}")
            return {"success": False, "error": "文件不存在", "iterations": 0}
        
        result = {
            "script_path": script_path,
            "success": False,
            "iterations": 0,
            "execution_log": [],
            "final_output": "",
            "error": None
        }
        
        for iteration in range(1, self.max_iterations + 1):
            logger.info(f"=== 第 {iteration} 次尝试 ===")
            result["iterations"] = iteration
            
            # 执行脚本
            success, output, error = self.execute_script(script_path)
            
            iteration_log = {
                "iteration": iteration,
                "success": success,
                "output": output,
                "error": error,
                "timestamp": time.time()
            }
            
            result["execution_log"].append(iteration_log)
            
            if success:
                logger.info(f"脚本在第 {iteration} 次尝试中成功执行！")
                result["success"] = True
                result["final_output"] = output
                break
            else:
                logger.warning(f"第 {iteration} 次执行失败: {error}")
                
                if iteration < self.max_iterations:
                    # 尝试使用 Gemini 修复
                    logger.info("正在尝试自动修复...")
                    fixed_code = self.get_gemini_fix(script_path, error)
                    
                    if fixed_code:
                        if self.apply_fix(script_path, fixed_code):
                            logger.info("修复已应用，准备重新执行...")
                            time.sleep(1)  # 短暂等待
                        else:
                            logger.error("应用修复失败")
                            result["error"] = "应用修复失败"
                            break
                    else:
                        logger.error("无法获取修复建议")
                        result["error"] = "无法获取修复建议"
                        break
                else:
                    logger.error(f"达到最大尝试次数 ({self.max_iterations})，放弃修复")
                    result["error"] = f"达到最大尝试次数，最后错误: {error}"
        
        return result

def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("用法: python auto_code_executor.py <script_path>")
        print("示例: python auto_code_executor.py test_script.py")
        sys.exit(1)
    
    script_path = sys.argv[1]
    
    print("🚀 自动代码执行和修复系统启动")
    print(f"目标脚本: {script_path}")
    print("=" * 50)
    
    executor = AutoCodeExecutor(max_iterations=5)
    result = executor.auto_execute_and_fix(script_path)
    
    print("\n" + "=" * 50)
    print("📊 执行结果摘要:")
    print(f"✅ 成功: {'是' if result['success'] else '否'}")
    print(f"🔄 尝试次数: {result['iterations']}")
    
    if result['success']:
        print("🎉 脚本执行成功！")
        if result['final_output']:
            print("\n📤 最终输出:")
            print(result['final_output'])
    else:
        print(f"❌ 执行失败: {result.get('error', '未知错误')}")
    
    # 保存详细日志
    log_file = f"execution_log_{int(time.time())}.json"
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n📝 详细日志已保存到: {log_file}")

if __name__ == "__main__":
    main()