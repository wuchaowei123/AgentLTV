#!/usr/bin/env python3
"""
包含 PyTorch 相关错误的测试代码
用于演示自动修复功能
"""

import torch
import numpy as np

def create_model():
    """创建一个简单的神经网络模型"""
    # 错误1：使用了错误的 PyTorch 函数名
    model = torch.nn.Sequential(
        torch.nn.Linear(10, 5),
        torch.nn.ReLU(),  # 应该是 ReLU，不是 ReLu
        torch.nn.Linear(5, 1)
    )
    return model

def train_step(model, data, target, optimizer):
    """训练步骤"""
    # 错误2：没有定义优化器
    output = model(data)
    loss = torch.nn.functional.mse_loss(output, target)
    
    # 错误3：尝试对未定义的优化器进行操作
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()
    
    return loss.item()

def main():
    """主函数"""
    # 创建模型
    model = create_model()
    
    # 创建优化器
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)

    # 创建一些测试数据
    data = torch.randn(32, 10)
    target = torch.randn(32, 1)
    
    print("开始训练...")
    
    # 训练一步
    loss = train_step(model, data, target, optimizer)
    print(f"损失: {loss}")
    
    # 错误4：尝试将 tensor 转换为 numpy 但没有 detach
    numpy_output = model(data).detach().numpy()  # 应该先 detach()
    print(f"输出形状: {numpy_output.shape}")

if __name__ == "__main__":
    main()