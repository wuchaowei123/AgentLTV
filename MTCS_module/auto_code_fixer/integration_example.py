#!/usr/bin/env python3
"""
集成示例：展示如何在主系统中使用自动代码修复功能
"""

import sys
import os
from pathlib import Path

# 添加当前目录到 Python 路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from gemini_auto_fixer import GeminiAutoFixer

def integrate_auto_fixer_with_main_system():
    """演示如何将自动修复功能集成到主系统中"""
    
    print("🔗 MTCS_module - 自动代码修复集成示例")
    print("=" * 60)
    
    # 初始化自动修复器
    fixer = GeminiAutoFixer()
    
    # 示例：批量修复多个脚本
    test_scripts = [
        "examples/test_buggy_code.py",
        "examples/test_pytorch_buggy.py", 
        "examples/complex_buggy_code.py"
    ]
    
    results = {}
    
    for script in test_scripts:
        if os.path.exists(script):
            print(f"\n🔧 正在处理: {script}")
            print("-" * 40)
            
            success = fixer.auto_fix_and_run(script)
            results[script] = success
            
            if success:
                print(f"✅ {script} 修复并执行成功")
            else:
                print(f"❌ {script} 修复失败")
        else:
            print(f"⚠️  文件不存在: {script}")
            results[script] = False
    
    # 输出总结
    print("\n" + "=" * 60)
    print("📊 批量修复结果总结:")
    
    successful = sum(results.values())
    total = len(results)
    
    print(f"✅ 成功: {successful}/{total} 个脚本")
    print(f"❌ 失败: {total - successful}/{total} 个脚本")
    
    for script, success in results.items():
        status = "✅" if success else "❌"
        print(f"  {status} {script}")
    
    return results

def demonstrate_api_usage():
    """演示 API 使用方式"""
    
    print("\n🚀 API 使用示例")
    print("=" * 30)
    
    # 方式1：直接使用类
    fixer = GeminiAutoFixer()
    
    # 方式2：自定义配置
    fixer.max_attempts = 5  # 增加最大尝试次数
    
    # 方式3：检查文件是否需要修复（不执行）
    def check_script_syntax(file_path):
        """检查脚本语法是否正确"""
        try:
            with open(file_path, 'r') as f:
                code = f.read()
            compile(code, file_path, 'exec')
            return True, "语法正确"
        except SyntaxError as e:
            return False, f"语法错误: {e}"
        except Exception as e:
            return False, f"其他错误: {e}"
    
    # 示例使用
    test_file = "examples/test_buggy_code.py"
    if os.path.exists(test_file):
        is_valid, message = check_script_syntax(test_file)
        print(f"📝 {test_file}: {message}")
    
    print("\n💡 集成建议:")
    print("1. 在主系统的代码生成后调用自动修复")
    print("2. 可以作为代码评估的预处理步骤")
    print("3. 支持批量处理多个生成的解决方案")
    print("4. 可以与现有的错误处理流程集成")

if __name__ == "__main__":
    # 运行集成示例
    results = integrate_auto_fixer_with_main_system()
    
    # 演示 API 使用
    demonstrate_api_usage()
    
    print(f"\n🎉 集成示例完成！")
    print(f"📁 详细文档请查看: README.md")
    print(f"🔧 主要脚本: gemini_auto_fixer.py")
    print(f"🚀 便捷启动: ./run_with_auto_fix.sh <script.py>")