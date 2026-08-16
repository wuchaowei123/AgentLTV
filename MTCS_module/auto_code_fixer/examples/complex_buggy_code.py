#!/usr/bin/env python3
"""
复杂的错误代码，包含多种类型的错误
"""

import pandas as pd
import numpy as np

def analyze_data():
    """分析数据函数"""
    # 错误1：使用了不存在的列名
    data = {'name': ['Alice', 'Bob', 'Charlie'], 
            'age': [25, 30, 35],
            'salary': [50000, 60000, 70000]}
    
    df = pd.DataFrame(data)
    
    # 修正：列名拼写错误
    average_age = df['age'].mean()  # 应该是 'age'
    print(f"平均年龄: {average_age}")
    
    # 修正：除零错误
    try:
        result = 100 / 0
        print(f"结果: {result}")
    except ZeroDivisionError:
        print("错误：不能除以零")
    
    return df

def process_numbers():
    """处理数字"""
    numbers = [1, 2, 3, 4, 5]
    
    # 修正：索引超出范围
    try:
        print(f"第10个数字: {numbers[10]}")
    except IndexError:
        print("错误：索引超出范围")
    
    # 修正：类型错误
    total = sum(numbers)  # 不能将字符串和数字相加
    
    return total

def main():
    print("开始数据分析...")
    df = analyze_data()
    
    print("处理数字...")
    total = process_numbers()
    
    print(f"总计: {total}")

if __name__ == "__main__":
    main()