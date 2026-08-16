#!/usr/bin/env python3
"""
测试用的有错误的Python代码
用于演示自动修复功能
"""

import math

def calculate_area(radius):
    """计算圆的面积"""
    # 修复了未定义的变量错误
    return math.pi * radius ** 2

def main():
    radius = 5
    area = calculate_area(radius)
    print(f"半径为 {radius} 的圆的面积是: {area}")
    
    # 修复了除零错误
    try:
        result = 10 / 0
        print(f"结果: {result}")
    except ZeroDivisionError:
        print("错误：不能除以零")

if __name__ == "__main__":
    main()