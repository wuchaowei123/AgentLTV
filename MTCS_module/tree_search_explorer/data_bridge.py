#!/usr/bin/env python3
"""
Data Bridge for Tree Search Explorer
====================================

Utility to extract and prepare data from the AI system's database
for visualization in the Tree Search Explorer.
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from core.database.db_manager import DatabaseManager
from core.database.models import ExecutionNode

def extract_search_data(db_path: str, output_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract all search data from database and format for visualization.
    
    Args:
        db_path: Path to SQLite database file
        output_file: Optional path to save JSON output
        
    Returns:
        Formatted data dictionary ready for Tree Explorer
    """
    print(f"📊 Extracting data from: {db_path}")
    
    try:
        # Initialize database manager
        db_manager = DatabaseManager(db_path)
        
        # Get all nodes
        all_nodes = db_manager.get_all_nodes()
        print(f"✅ Found {len(all_nodes)} execution nodes")
        
        if not all_nodes:
            print("⚠️ No nodes found in database")
            return {"error": "No nodes found"}
        
        # Get statistics
        stats = db_manager.get_stats()
        
        # Convert nodes to visualization format
        nodes_data = []
        # Sort nodes by creation time for proper ordering
        try:
            sorted_nodes = sorted(all_nodes, key=lambda n: n.created_at or datetime.min)
        except Exception as e:
            print(f"Warning: Could not sort nodes by created_at: {e}")
            sorted_nodes = all_nodes
        
        for i, node in enumerate(sorted_nodes):
            try:
                node_dict = {
                    'node_id': node.node_id,
                    'parent_id': node.parent_id,
                    'score': node.score or 0.0,
                    'status': 'Success' if node.execution_status == 'completed' else 'Error',
                    'code': node.code or '',
                    'mutation_type': node.mutation_type or 'unknown',
                    'generation': node.generation or 0,
                    'execution_duration': node.execution_duration or 0.0,
                    'auto_fixes': node.auto_fixes or 0,
                    'error_message': node.error_message or '',
                    'created_at': node.created_at.isoformat() if node.created_at else '',
                    'order': i,  # Order in which nodes were created
                    'llm_summary': generate_simple_summary(node),
                    'code_diff_summary': generate_diff_summary(node, sorted_nodes)  # Use sorted_nodes
                }
                nodes_data.append(node_dict)
            except Exception as e:
                print(f"Error processing node {i} ({node.node_id}): {e}")
                import traceback
                traceback.print_exc()
                raise
        
        # Calculate breakthrough points
        breakthrough_points = calculate_breakthroughs(nodes_data)
        print(f"🚀 Found {len(breakthrough_points)} breakthrough points")
        
        # Build tree structure
        tree_structure = build_tree_structure(nodes_data)
        
        # Find best node
        best_node = max(nodes_data, key=lambda x: x['score']) if nodes_data else None
        
        # Generate search run info
        first_node = min(all_nodes, key=lambda n: n.created_at or n.node_id)
        timestamp = int(first_node.created_at.timestamp()) if first_node.created_at else 123456789
        search_run_id = f"{timestamp}-TreeSearch-{stats.get('best_score', 0.0):.4f}"
        
        run_info = {
            'search_run_id': search_run_id,
            'total_nodes': stats.get('total_nodes', 0),
            'best_score': stats.get('best_score', 0.0),
            'success_rate': stats.get('success_rate', 0.0),
            'db_path': db_path
        }
        
        # Compile final data
        extracted_data = {
            'success': True,
            'run_info': run_info,
            'nodes': nodes_data,
            'breakthrough_points': breakthrough_points,
            'tree_structure': tree_structure,
            'best_node': best_node,
            'extraction_timestamp': timestamp,
            'total_nodes': len(nodes_data)
        }
        
        # Save to file if requested
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(extracted_data, f, indent=2, default=str)
            print(f"💾 Saved extracted data to: {output_file}")
        
        print("✅ Data extraction completed successfully")
        return extracted_data
        
    except Exception as e:
        error_msg = f"❌ Error extracting data: {str(e)}"
        print(error_msg)
        return {
            'success': False,
            'error': str(e),
            'db_path': db_path
        }

def generate_simple_summary(node: ExecutionNode) -> str:
    """Generate a simple summary of the node's solution."""
    if not node.code:
        return "• No code available for this node"
    
    code_lines = node.code.split('\n')
    summary_parts = []
    
    # Analyze imports and key components
    if any('sklearn' in line for line in code_lines):
        summary_parts.append("• Uses scikit-learn for machine learning")
    if 'RandomForest' in node.code:
        summary_parts.append("• Implements Random Forest classifier")
    if 'LogisticRegression' in node.code:
        summary_parts.append("• Uses Logistic Regression")
    if 'XGB' in node.code or 'xgboost' in node.code:
        summary_parts.append("• Applies XGBoost gradient boosting")
    if 'SMOTE' in node.code:
        summary_parts.append("• Handles class imbalance with SMOTE")
    if 'StandardScaler' in node.code:
        summary_parts.append("• Includes feature scaling/normalization")
    if 'cross_val' in node.code:
        summary_parts.append("• Uses cross-validation for evaluation")
    if 'GridSearch' in node.code:
        summary_parts.append("• Performs hyperparameter optimization")
    
    # Add performance info
    if node.score:
        summary_parts.append(f"• Achieved AUC score of {node.score:.4f}")
    
    # Add mutation info
    if node.mutation_type and node.mutation_type != 'unknown':
        summary_parts.append(f"• Generated using {node.mutation_type} strategy")
    
    if not summary_parts:
        summary_parts.append("• Custom machine learning solution")
    
    return '\n'.join(summary_parts)

def generate_diff_summary(node: ExecutionNode, all_nodes: List[ExecutionNode]) -> str:
    """Generate summary of differences from parent node."""
    if not node.parent_id:
        return ""  # Root node has no parent
    
    # Find parent node
    parent_node = next((n for n in all_nodes if n.node_id == node.parent_id), None)
    
    if not parent_node or not parent_node.code or not node.code:
        return "• Unable to compare with parent (missing code)"
    
    # Simple diff analysis
    parent_lines = set(parent_node.code.split('\n'))
    child_lines = set(node.code.split('\n'))
    
    added_lines = child_lines - parent_lines
    removed_lines = parent_lines - child_lines
    
    diff_summary = []
    
    if added_lines:
        added_text = '\n'.join(added_lines)
        if 'import' in added_text.lower():
            diff_summary.append("• Added new library imports")
        if any(term in added_text.lower() for term in ['xgboost', 'randomforest', 'svm']):
            diff_summary.append("• Introduced different ML algorithm")
        if 'smote' in added_text.lower():
            diff_summary.append("• Added SMOTE for class imbalance handling")
        if any(term in added_text.lower() for term in ['gridsearch', 'randomizedsearch']):
            diff_summary.append("• Added hyperparameter optimization")
    
    if removed_lines:
        diff_summary.append(f"• Removed {len(removed_lines)} lines from parent")
    
    # Compare scores
    if node.score and parent_node.score:
        score_diff = node.score - parent_node.score
        if score_diff > 0.001:
            diff_summary.append(f"• Improved AUC by {score_diff:.4f}")
        elif score_diff < -0.001:
            diff_summary.append(f"• Decreased AUC by {abs(score_diff):.4f}")
        else:
            diff_summary.append("• Similar performance to parent")
    
    if not diff_summary:
        diff_summary.append("• Minor modifications to parent solution")
    
    return '\n'.join(diff_summary)

def calculate_breakthroughs(nodes_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Calculate breakthrough points where best score improved."""
    if not nodes_data:
        return []
    
    # Sort nodes by creation order
    sorted_nodes = sorted(nodes_data, key=lambda x: x['order'])
    
    breakthrough_points = []
    best_score_so_far = float('-inf')
    
    for i, node in enumerate(sorted_nodes):
        current_score = node['score']
        
        if current_score > best_score_so_far:
            best_score_so_far = current_score
            improvement = current_score - (breakthrough_points[-1]['score'] if breakthrough_points else 0)
            breakthrough_points.append({
                'node_id': node['node_id'],
                'score': current_score,
                'node_index': i + 1,
                'improvement': improvement,
                'is_first': len(breakthrough_points) == 0
            })
    
    return breakthrough_points

def build_tree_structure(nodes_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build hierarchical tree structure for visualization."""
    # Create lookup for quick access
    nodes_by_id = {node['node_id']: node for node in nodes_data}
    
    # Find root node(s)
    root_nodes = [node for node in nodes_data if not node['parent_id']]
    
    print(f"🌳 Building tree structure:")
    print(f"   Total nodes: {len(nodes_data)}")
    print(f"   Root nodes: {len(root_nodes)}")
    for root in root_nodes:
        print(f"     - {root['node_id'][:8]} (score: {root['score']:.4f})")
    
    # Build tree recursively
    def build_subtree(node_id: str) -> Dict[str, Any]:
        node = nodes_by_id[node_id]
        children = [nodes_by_id[child_id] for child_id in nodes_by_id.keys() 
                   if nodes_by_id[child_id]['parent_id'] == node_id]
        
        result = {
            **node,
            'children': [build_subtree(child['node_id']) for child in children]
        }
        print(f"   Built subtree for {node_id[:8]}: {len(result['children'])} children")
        return result
    
    # Handle multiple roots or single root
    if len(root_nodes) == 1:
        print(f"   Single root - building tree from {root_nodes[0]['node_id'][:8]}")
        return build_subtree(root_nodes[0]['node_id'])
    else:
        # Multiple roots - create a virtual root
        print(f"   Multiple roots - creating virtual root with {len(root_nodes)} children")
        children_trees = [build_subtree(root['node_id']) for root in root_nodes]
        virtual_root = {
            'node_id': 'virtual_root',
            'score': 0.0,
            'status': 'Virtual',
            'children': children_trees
        }
        print(f"   Virtual root created with {len(virtual_root['children'])} children")
        return virtual_root

def main():
    parser = argparse.ArgumentParser(description='Extract search data for Tree Explorer visualization')
    parser.add_argument('db_path', help='Path to SQLite database file')
    parser.add_argument('--output', '-o', help='Output JSON file path')
    parser.add_argument('--pretty', '-p', action='store_true', help='Pretty print JSON output')
    
    args = parser.parse_args()
    
    # Check if database exists
    if not Path(args.db_path).exists():
        print(f"❌ Database file not found: {args.db_path}")
        return 1
    
    # Extract data
    data = extract_search_data(args.db_path, args.output)
    
    # Print summary
    if data.get('success'):
        print(f"\n📊 Extraction Summary:")
        print(f"   • Total Nodes: {data['total_nodes']}")
        print(f"   • Best Score: {data['run_info']['best_score']:.4f}")
        print(f"   • Success Rate: {data['run_info']['success_rate']:.1f}%")
        print(f"   • Breakthrough Points: {len(data['breakthrough_points'])}")
        
        if args.pretty and not args.output:
            print(f"\n📄 JSON Data Preview:")
            print(json.dumps({k: v for k, v in data.items() if k != 'nodes'}, indent=2, default=str))
    else:
        print(f"❌ Extraction failed: {data.get('error', 'Unknown error')}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())