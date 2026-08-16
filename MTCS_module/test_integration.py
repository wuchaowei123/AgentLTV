#!/usr/bin/env python3
"""
Integration test for Claude Code CLI Auto-Fixer with Database System
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.task_manager import TaskConfiguration
from core.sandbox.db_code_executor import DatabaseCodeExecutor

def test_integration():
    print("=" * 70)
    print("🧪 TESTING CLAUDE CODE CLI AUTO-FIXER INTEGRATION")
    print("=" * 70)
    
    # Load task config
    print("\n📋 Loading task configuration...")
    task_config = TaskConfiguration(
        "tasks/text_classification_for_custom_service/task_config.yaml"
    )
    print(f"✅ Task loaded: {task_config.task_name}")
    
    # Create executor with database
    print("\n🔧 Initializing Database Code Executor...")
    executor = DatabaseCodeExecutor(
        task_config=task_config,
        db_path="test_integration.db",
        skip_auto_fixer=False  # Enable auto-fixer
    )
    print("✅ Executor initialized")
    
    # Create a simple broken code to test
    print("\n📝 Creating test code with intentional bugs...")
    broken_code = """
import pandas as pd
import numpy as np
from sklearn.metrics import f1_score

# Load data
train_df = pd.read_csv('/home/jupyter/scientific-ai-system/tasks/text_classification_for_custom_service/train.csv')
test_df = pd.read_csv('/home/jupyter/scientific-ai-system/tasks/text_classification_for_custom_service/test.csv')

print(f"Data loaded: {len(train_df)} train, {len(test_df)} test")

# BUG: Wrong column name
labels = train_df['label'].unique()  # Should be 'labels' not 'label'

print(f"Found {len(labels)} unique labels")

# Dummy predictions for testing
test_predictions = ['Withdrawal category-Withdrawal process提现流程-(Sent) Withdrawal status issues咨询提现进度（已打款）'] * len(test_df)

# Calculate score
true_labels = test_df['labels'].tolist()
score = 0.85  # Dummy score for testing

print(f"Score: {score:.4f}")
"""
    
    print("✅ Test code created (contains bug: 'label' should be 'labels')")
    
    # Execute with auto-fixer
    print("\n🚀 Executing code with Claude Code CLI auto-fixer...")
    print("   This will:")
    print("   1. Create execution node and save code")
    print("   2. Run the code and detect the error")
    print("   3. Ask Claude CLI for fix suggestion")
    print("   4. Automatically apply the fix")
    print("   5. Re-run the code")
    print("\n" + "-" * 70)
    
    # Create execution node
    node_id = executor.create_execution_node(
        code=broken_code,
        parent_id=None,
        mutation_type="test_integration"
    )
    print(f"✅ Execution node created: {node_id}")
    
    # Execute the node with auto-fixer
    result = executor.execute_node(node_id, timeout=300)
    
    print("\n" + "=" * 70)
    print("📊 INTEGRATION TEST RESULTS")
    print("=" * 70)
    print(f"✅ Success: {result['success']}")
    print(f"📈 Score: {result.get('score', 0.0):.4f}")
    print(f"🔧 Auto-fixes applied: {result.get('auto_fixes', 0)}")
    print(f"🆔 Node ID: {result.get('node_id', 'N/A')}")
    
    if result['success']:
        print("\n🎉 INTEGRATION TEST PASSED!")
        print("   Claude Code CLI auto-fixer successfully:")
        print("   ✓ Detected the error")
        print("   ✓ Applied the fix automatically")
        print("   ✓ Code executed successfully")
    else:
        print("\n⚠️  INTEGRATION TEST FAILED")
        print(f"   Error: {result.get('error', 'Unknown error')}")
    
    print("\n" + "=" * 70)
    
    return result['success']

if __name__ == "__main__":
    try:
        success = test_integration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

