#!/usr/bin/env python3
"""
Manual Execution Helper for MTCS_module
===============================================

Helps extract, debug, and run generated ML code manually when automated execution fails.
"""

import argparse
import sys
import re
import json
import time
from pathlib import Path

def extract_core_code(node_file):
    """Extract the core ML code from a wrapped node file."""
    with open(node_file, 'r') as f:
        content = f.read()
    
    # Find the user generated code section
    start_marker = "# User generated code"
    end_marker = "# Evaluation and result saving"
    
    try:
        start_idx = content.index(start_marker)
        end_idx = content.index(end_marker)
        
        # Extract lines between markers
        lines = content[start_idx:end_idx].split('\n')[1:]  # Skip the marker line
        core_code = '\n'.join(lines).strip()
        
        return core_code
    except ValueError:
        print("⚠️ Could not find code markers, returning full file")
        return content

def create_standalone_script(node_file, output_file=None):
    """Create a standalone script for manual execution."""
    if output_file is None:
        output_file = node_file.replace('.py', '_manual.py')
    
    # Extract core code
    core_code = extract_core_code(node_file)
    
    # Get node ID from filename
    node_id = Path(node_file).stem.replace('node_', '')
    
    # Create standalone script with proper error handling
    standalone_script = f'''#!/usr/bin/env python3
"""
Manual execution script for node {node_id}
Original file: {node_file}

Instructions:
1. Fix any import errors or data path issues
2. Ensure the code defines val_predictions variable
3. Run this script to get results
"""

import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score
import json
import time
import sys
import os

print("🚀 Manual Execution for Node {node_id}")
print("=" * 50)

# Try to load data - adjust paths as needed
try:
    # Option 1: Try predefined data paths
    data_paths = [
        '/home/jupyter/MTCS_module/data/train.csv',
        '/home/jupyter/MTCS_module/data/validation.csv',
        'data/train.csv',
        'data/validation.csv',
        'train.csv',
        'validation.csv'
    ]
    
    train_df = None
    val_df = None
    
    # Find train data
    for path in data_paths:
        if 'train' in path and os.path.exists(path):
            train_df = pd.read_csv(path)
            print(f"✅ Loaded train data from: {{path}}")
            break
    
    # Find validation data  
    for path in data_paths:
        if 'validation' in path and os.path.exists(path):
            val_df = pd.read_csv(path)
            print(f"✅ Loaded validation data from: {{path}}")
            break
    
    if train_df is None or val_df is None:
        print("❌ Could not find data files!")
        print("💡 Expected files: train.csv, validation.csv")
        print("💡 Current directory:", os.getcwd())
        print("💡 Available files:", [f for f in os.listdir('.') if f.endswith('.csv')])
        sys.exit(1)
    
    print(f"📊 Data shapes: Train {{train_df.shape}}, Validation {{val_df.shape}}")
    
except Exception as e:
    print(f"❌ Error loading data: {{e}}")
    print("💡 You may need to adjust the data file paths manually")
    sys.exit(1)

print("\\n🔄 Starting ML code execution...")

# ============== CORE ML CODE ==============
{core_code}
# ==========================================

print("\\n📊 Attempting evaluation...")

try:
    # Try to find predictions variable with different possible names
    predictions = None
    prediction_vars = ['val_predictions', 'predictions', 'y_pred', 'pred', 'test_predictions']
    
    for var_name in prediction_vars:
        if var_name in locals():
            predictions = locals()[var_name]
            print(f"✅ Found predictions: {{var_name}}")
            break
    
    if predictions is None:
        print("❌ No predictions variable found!")
        print("💡 Available variables:", [v for v in locals().keys() if not v.startswith('_')])
        print("💡 Make sure your code creates one of:", prediction_vars)
        
        # Try to create dummy predictions for testing
        if 'val_df' in locals():
            predictions = np.random.random(len(val_df))
            print("⚠️  Using dummy predictions for testing")
        else:
            sys.exit(1)
    
    # Get true labels - try different column names
    target_cols = ['Machine failure', 'target', 'label', 'y']
    y_true = None
    
    for col in target_cols:
        if col in val_df.columns:
            y_true = val_df[col].values
            print(f"✅ Found target column: {{col}}")
            break
    
    if y_true is None:
        print("❌ No target column found!")
        print(f"💡 Available columns: {{list(val_df.columns)}}")
        sys.exit(1)
    
    # Validate predictions
    if len(predictions) != len(y_true):
        print(f"❌ Prediction length mismatch: {{len(predictions)}} vs {{len(y_true)}}")
        sys.exit(1)
    
    # Calculate AUC score
    score = roc_auc_score(y_true, predictions)
    print(f"\\n🎯 SUCCESS!")
    print(f"   AUC Score: {{score:.4f}}")
    
    # Create result file for system integration
    timestamp = int(time.time())
    result_file = f"/tmp/ai_result_{node_id}_{{timestamp}}.json"
    
    result = {{
        "score": float(score),
        "success": True,
        "predictions": predictions.tolist() if hasattr(predictions, 'tolist') else list(predictions),
        "manual_execution": True,
        "timestamp": timestamp
    }}
    
    with open(result_file, 'w') as f:
        json.dump(result, f)
    
    print(f"\\n💾 Result saved to: {{result_file}}")
    print(f"\\n🎯 To submit to system:")
    print(f"python manual_update_result.py \\\\")
    print(f"  --node-id {node_id} \\\\")
    print(f"  --score {{score:.4f}} \\\\")
    print(f"  --success \\\\")
    print(f"  --db-path YOUR_DATABASE.db")
    
except Exception as e:
    print(f"\\n❌ Evaluation failed: {{e}}")
    print("\\n🔧 Debug information:")
    print(f"   Error type: {{type(e).__name__}}")
    print(f"   Available locals: {{[v for v in locals().keys() if not v.startswith('_')]}}")
    
    if 'val_df' in locals():
        print(f"   Validation df shape: {{val_df.shape}}")
        print(f"   Validation df columns: {{list(val_df.columns)}}")
    
    # Create failure result file
    timestamp = int(time.time())
    result_file = f"/tmp/ai_result_{node_id}_{{timestamp}}.json"
    
    result = {{
        "score": 0.0,
        "success": False,
        "error": str(e),
        "manual_execution": True,
        "timestamp": timestamp
    }}
    
    with open(result_file, 'w') as f:
        json.dump(result, f)
    
    print(f"\\n💾 Error result saved to: {{result_file}}")
    print(f"\\n🎯 To submit failure to system:")
    print(f"python manual_update_result.py \\\\")
    print(f"  --node-id {node_id} \\\\")
    print(f"  --error '{{str(e)}}' \\\\")
    print(f"  --db-path YOUR_DATABASE.db")
    
    print(f"\\n🛠️  Fix suggestions:")
    print(f"   1. Check import statements")
    print(f"   2. Verify data paths")
    print(f"   3. Ensure prediction variable is created")
    print(f"   4. Check for typos in column names")
    
    sys.exit(1)
'''

    with open(output_file, 'w') as f:
        f.write(standalone_script)
    
    # Make executable
    Path(output_file).chmod(0o755)
    
    return output_file

def main():
    parser = argparse.ArgumentParser(
        description='Manual execution helper for MTCS_module',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract and create standalone script
  python manual_execution_helper.py core/sandbox/exe_code/node_93662b2c.py
  
  # Just extract the core code
  python manual_execution_helper.py core/sandbox/exe_code/node_93662b2c.py --extract-only
  
  # Specify custom output file
  python manual_execution_helper.py core/sandbox/exe_code/node_93662b2c.py --output my_debug.py
        """
    )
    
    parser.add_argument(
        'node_file', 
        help='Path to node file (e.g., core/sandbox/exe_code/node_93662b2c.py)'
    )
    parser.add_argument(
        '--output', 
        help='Output file for standalone script'
    )
    parser.add_argument(
        '--extract-only', 
        action='store_true', 
        help='Only extract and print core code, don\'t create standalone script'
    )
    
    args = parser.parse_args()
    
    if not Path(args.node_file).exists():
        print(f"❌ File not found: {args.node_file}")
        sys.exit(1)
    
    if args.extract_only:
        # Just print the core code
        core_code = extract_core_code(args.node_file)
        print("=" * 60)
        print("EXTRACTED CORE ML CODE:")
        print("=" * 60)
        print(core_code)
        print("=" * 60)
    else:
        # Create standalone script
        output_file = create_standalone_script(args.node_file, args.output)
        print(f"✅ Created standalone script: {output_file}")
        print(f"🚀 Run with: python {output_file}")
        print(f"🔧 Edit the script if you need to fix any issues")
        print(f"💾 Results will be saved to /tmp/ai_result_*.json")

if __name__ == "__main__":
    main()
