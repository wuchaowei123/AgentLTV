#!/usr/bin/env python3
"""
测试增强版自动代码修复器
"""

import os
import sys
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from enhanced_gemini_auto_fixer import EnhancedGeminiAutoFixer

def create_test_files():
    """创建测试用的错误代码文件"""
    
    # 测试1: IterativeImputer 错误
    test1_code = '''
import pandas as pd
import numpy as np
from sklearn.impute import IterativeImputer
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score

# 创建测试数据
np.random.seed(42)
data = pd.DataFrame({
    'feature1': np.random.randn(100),
    'feature2': np.random.randn(100),
    'target': np.random.randint(0, 2, 100)
})

# 添加一些缺失值
data.loc[10:15, 'feature1'] = np.nan

# 使用 IterativeImputer
imputer = IterativeImputer(random_state=42)
data_imputed = imputer.fit_transform(data[['feature1', 'feature2']])

# 训练模型
X = data_imputed
y = data['target']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

model = RandomForestClassifier(random_state=42)
model.fit(X_train, y_train)

# 预测和评分
y_pred = model.predict_proba(X_test)[:, 1]
auc_score = roc_auc_score(y_test, y_pred)

print(f"AUC Score: {auc_score:.4f}")
'''

    # 测试2: 导入错误
    test2_code = '''
import pandas as pd
import numpy as np
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

# 创建测试数据
np.random.seed(42)
X = np.random.randn(100, 4)
y = np.random.randint(0, 2, 100)

# 训练模型
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

model = RandomForestClassifier(random_state=42)
model.fit(X_train, y_train)

# 预测和评分
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
f1 = f1_score(y_test, y_pred)

print(f"Accuracy: {accuracy:.4f}")
print(f"F1 Score: {f1:.4f}")
'''

    # 测试3: 数学错误
    test3_code = '''
import math

def calculate_area(radius):
    return pi * radius ** 2  # 错误：pi 未定义

def main():
    radius = 5
    area = calculate_area(radius)
    print(f"圆的面积: {area:.4f}")
    
    # 除零错误
    result = 10 / 0
    print(f"结果: {result}")

if __name__ == "__main__":
    main()
'''

    test_files = [
        ("test_iterative_imputer.py", test1_code),
        ("test_import_errors.py", test2_code),
        ("test_math_errors.py", test3_code)
    ]
    
    for filename, code in test_files:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(code)
        print(f"✅ 创建测试文件: {filename}")
    
    return [filename for filename, _ in test_files]

def test_enhanced_fixer():
    """测试增强版修复器"""
    print("🧪 测试增强版 Gemini 自动代码修复器")
    print("=" * 60)
    
    # 创建测试文件
    test_files = create_test_files()
    
    # 初始化修复器
    fixer = EnhancedGeminiAutoFixer()
    
    results = {}
    
    for test_file in test_files:
        print(f"\n🔧 测试文件: {test_file}")
        print("-" * 40)
        
        try:
            success = fixer.auto_fix_and_run(test_file)
            results[test_file] = success
            
            if success:
                print(f"✅ {test_file} 修复成功")
                
                # 获取详细结果
                result = fixer.get_execution_result(test_file)
                if result['score'] > 0:
                    print(f"📊 检测到评分: {result['score']:.4f}")
            else:
                print(f"❌ {test_file} 修复失败")
                
        except Exception as e:
            print(f"❌ {test_file} 测试异常: {e}")
            results[test_file] = False
    
    # 输出总结
    print("\n" + "=" * 60)
    print("📊 测试结果总结:")
    
    successful = sum(results.values())
    total = len(results)
    
    print(f"✅ 成功: {successful}/{total} 个测试")
    print(f"❌ 失败: {total - successful}/{total} 个测试")
    
    for test_file, success in results.items():
        status = "✅" if success else "❌"
        print(f"  {status} {test_file}")
    
    # 清理测试文件
    print(f"\n🧹 清理测试文件...")
    for test_file in test_files:
        try:
            os.remove(test_file)
            # 也删除可能的备份文件
            backup_files = [f for f in os.listdir('.') if f.startswith(f"{test_file}.backup_")]
            for backup_file in backup_files:
                os.remove(backup_file)
        except:
            pass
    
    return results

def test_score_extraction():
    """测试评分提取功能"""
    print("\n🎯 测试评分提取功能")
    print("-" * 30)
    
    fixer = EnhancedGeminiAutoFixer()
    
    # 测试不同的输出格式
    test_outputs = [
        "AUC Score: 0.8542",
        "Final AUC: 0.9123",
        "Accuracy: 0.7654",
        "F1 Score: 0.6789",
        "ROC AUC: 0.8888",
        "Model achieved 0.9234 AUC",
        "No score information",
    ]
    
    for output in test_outputs:
        score = fixer._extract_score_from_output(output)
        print(f"输出: '{output}' → 评分: {score}")

if __name__ == "__main__":
    # 测试增强版修复器
    results = test_enhanced_fixer()
    
    # 测试评分提取
    test_score_extraction()
    
    print(f"\n🎉 测试完成！")
    
    # 返回测试是否全部成功
    all_success = all(results.values())
    sys.exit(0 if all_success else 1)