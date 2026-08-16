#!/usr/bin/env python3
"""
Tree Search Explorer - Flask Backend
===================================

Web application for visualizing and exploring the AI system's tree search process.
Provides interactive visualization of search nodes, breakthrough detection, and code comparisons.
"""

import sys
import os
import json
from flask import Flask, render_template, jsonify, request, send_from_directory
from pathlib import Path
import sqlite3
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import numpy as np

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from core.database.db_manager import DatabaseManager
from core.database.models import ExecutionNode

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tree-search-explorer-2024'

class TreeSearchDataProcessor:
    """Processes database data for tree search visualization."""
    
    def __init__(self, db_path: str):
        """Initialize with database path."""
        self.db_path = db_path
        self.db_manager = DatabaseManager(db_path)
        self._llm_worker = None
    
    def _get_llm_worker(self):
        """Lazy initialization of LLM worker for summaries."""
        if self._llm_worker is None:
            from core.llm_worker import UniversalLLMWorker
            self._llm_worker = UniversalLLMWorker()
        return self._llm_worker
    
    def get_search_run_info(self) -> Dict[str, Any]:
        """Get basic information about the search run."""
        stats = self.db_manager.get_stats()
        
        # Generate a search run ID based on timestamp and best score
        nodes = self.db_manager.get_all_nodes()
        if nodes:
            first_node = min(nodes, key=lambda n: n.created_at)
            timestamp = int(first_node.created_at.timestamp()) if first_node.created_at else 123456789
            best_score = stats.get('best_score', 0.0)
            search_run_id = f"{timestamp}-AI-Search-{best_score:.4f}"
        else:
            search_run_id = "No-Data-Available"
        
        return {
            'search_run_id': search_run_id,
            'total_nodes': stats.get('total_nodes', 0),
            'best_score': stats.get('best_score', 0.0),
            'success_rate': stats.get('success_rate', 0.0),
            'db_path': self.db_path
        }
    
    def get_all_nodes_data(self) -> List[Dict[str, Any]]:
        """Get all nodes with enhanced data for visualization."""
        print(f"📊 [get_all_nodes_data] DB path: {self.db_path}")
        nodes = self.db_manager.get_all_nodes()
        print(f"📊 [get_all_nodes_data] Retrieved {len(nodes)} nodes from database")
        
        # Convert to dict format and add enhancements
        nodes_data = []
        for i, node in enumerate(nodes):
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
                'llm_summary': self._generate_llm_summary(node),
                'code_diff_summary': self._generate_code_diff_summary(node, nodes)
            }
            nodes_data.append(node_dict)
        
        return nodes_data
    
    def _generate_llm_summary(self, node: ExecutionNode) -> str:
        """Generate LLM summary of the node's solution."""
        if not node.code:
            return "• No code available for this node"
        
        try:
            # Create a simplified summary based on code analysis
            code_lines = node.code.split('\n')
            imports = [line for line in code_lines if line.strip().startswith('import') or line.strip().startswith('from')]
            
            summary_parts = []
            
            # Analyze imports to understand approach
            if any('sklearn' in imp for imp in imports):
                summary_parts.append("• Uses scikit-learn for machine learning")
            if any('xgboost' in imp or 'XGB' in node.code for imp in imports):
                summary_parts.append("• Implements XGBoost gradient boosting")
            if any('RandomForest' in node.code):
                summary_parts.append("• Uses Random Forest ensemble method")
            if any('LogisticRegression' in node.code):
                summary_parts.append("• Applies Logistic Regression")
            if any('SMOTE' in node.code):
                summary_parts.append("• Handles class imbalance with SMOTE")
            if any('StandardScaler' in node.code):
                summary_parts.append("• Includes feature scaling/normalization")
            if any('cross_val' in node.code):
                summary_parts.append("• Uses cross-validation for model evaluation")
            if any('GridSearch' in node.code or 'RandomizedSearch' in node.code):
                summary_parts.append("• Performs hyperparameter optimization")
            
            # Add performance info
            if node.score:
                summary_parts.append(f"• Achieved AUC score of {node.score:.4f}")
            
            # Add mutation info
            if node.mutation_type and node.mutation_type != 'unknown':
                summary_parts.append(f"• Generated using {node.mutation_type} strategy")
            
            if not summary_parts:
                summary_parts.append("• Custom machine learning solution")
                summary_parts.append("• Code analysis shows data processing and model training")
            
            return '\n'.join(summary_parts)
            
        except Exception as e:
            return f"• Error generating summary: {str(e)}"
    
    def _generate_code_diff_summary(self, node: ExecutionNode, all_nodes: List[ExecutionNode]) -> str:
        """Generate summary of differences from parent node."""
        if not node.parent_id:
            return ""  # Root node has no parent
        
        # Find parent node
        parent_node = None
        for n in all_nodes:
            if n.node_id == node.parent_id:
                parent_node = n
                break
        
        if not parent_node or not parent_node.code or not node.code:
            return "• Unable to compare with parent (missing code)"
        
        try:
            # Simple diff analysis
            parent_lines = set(parent_node.code.split('\n'))
            child_lines = set(node.code.split('\n'))
            
            added_lines = child_lines - parent_lines
            removed_lines = parent_lines - child_lines
            
            diff_summary = []
            
            if added_lines:
                # Analyze what was added
                added_text = '\n'.join(added_lines)
                if 'import' in added_text.lower():
                    diff_summary.append("• Added new library imports")
                if any(term in added_text.lower() for term in ['xgboost', 'randomforest', 'svm', 'neuralnetwork']):
                    diff_summary.append("• Introduced different ML algorithm")
                if 'smote' in added_text.lower():
                    diff_summary.append("• Added SMOTE for handling class imbalance")
                if any(term in added_text.lower() for term in ['gridsearch', 'randomizedsearch', 'hyperopt']):
                    diff_summary.append("• Added hyperparameter optimization")
                if 'cross_val' in added_text.lower():
                    diff_summary.append("• Added cross-validation")
                if any(term in added_text.lower() for term in ['scaler', 'normalize', 'standard']):
                    diff_summary.append("• Added feature scaling/preprocessing")
            
            if removed_lines:
                diff_summary.append(f"• Removed {len(removed_lines)} lines from parent solution")
            
            if len(added_lines) > len(removed_lines):
                diff_summary.append("• Expanded the solution with additional functionality")
            elif len(removed_lines) > len(added_lines):
                diff_summary.append("• Simplified the solution by removing code")
            
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
            
        except Exception as e:
            return f"• Error comparing with parent: {str(e)}"
    
    def calculate_breakthrough_points(self, nodes_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
                breakthrough_points.append({
                    'node_id': node['node_id'],
                    'score': current_score,
                    'node_index': i + 1,
                    'improvement': current_score - (breakthrough_points[-1]['score'] if breakthrough_points else 0),
                    'is_first': len(breakthrough_points) == 0
                })
        
        return breakthrough_points
    
    def build_tree_structure(self, nodes_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build hierarchical tree structure for visualization."""
        # Create lookup for quick access
        nodes_by_id = {node['node_id']: node for node in nodes_data}
        
        # Find root node(s)
        root_nodes = [node for node in nodes_data if not node['parent_id']]
        
        print(f"🌳 [app.py] Building tree structure:")
        print(f"   Total nodes: {len(nodes_data)}")
        print(f"   Root nodes: {len(root_nodes)}")
        
        # Build tree recursively
        def build_subtree(node_id: str) -> Dict[str, Any]:
            node = nodes_by_id[node_id]
            children = [nodes_by_id[child_id] for child_id in nodes_by_id.keys() 
                       if nodes_by_id[child_id]['parent_id'] == node_id]
            
            return {
                **node,
                'children': [build_subtree(child['node_id']) for child in children]
            }
        
        # Handle multiple roots or single root
        if len(root_nodes) == 1:
            print(f"   Single root - building from {root_nodes[0]['node_id'][:8]}")
            result = build_subtree(root_nodes[0]['node_id'])
            print(f"   Result has {len(result.get('children', []))} children")
            return result
        else:
            # Multiple roots - create a virtual root
            print(f"   Multiple roots ({len(root_nodes)}) - creating virtual root")
            children_trees = [build_subtree(root['node_id']) for root in root_nodes]
            print(f"   Built {len(children_trees)} subtrees")
            result = {
                'node_id': 'virtual_root',
                'score': 0.0,
                'status': 'Virtual',
                'children': children_trees
            }
            print(f"   Virtual root has {len(result['children'])} children")
            print(f"   Returning tree structure...")
            return result


# Initialize global data processor
data_processor = None

def get_data_processor(db_path: str = None) -> TreeSearchDataProcessor:
    """Get or create data processor instance."""
    global data_processor
    
    if db_path:
        data_processor = TreeSearchDataProcessor(db_path)
    elif data_processor is None:
        # Default to most recent database
        db_files = list(Path('.').glob('*.db'))
        if db_files:
            latest_db = max(db_files, key=lambda p: p.stat().st_mtime)
            data_processor = TreeSearchDataProcessor(str(latest_db))
        else:
            raise ValueError("No database file found. Please specify db_path.")
    
    return data_processor

@app.route('/')
def index():
    """Main tree explorer page."""
    response = render_template('tree_explorer.html')
    # Disable caching for HTML page
    from flask import make_response
    resp = make_response(response)
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '-1'
    return resp

@app.route('/api/search_runs')
def get_search_runs():
    """Get available search runs."""
    # Look for database files in current directory and parent directory
    current_dir = Path('.')
    parent_dir = Path('..')
    
    db_files = []
    # Add files from current directory
    db_files.extend(current_dir.glob('*.db'))
    # Add files from parent directory 
    db_files.extend(parent_dir.glob('*.db'))
    
    runs = []
    
    for db_file in db_files:
        try:
            processor = TreeSearchDataProcessor(str(db_file))
            run_info = processor.get_search_run_info()
            run_info['db_file'] = str(db_file)
            runs.append(run_info)
            print(f"✅ Added search run: {run_info['search_run_id']} from {db_file}")
        except Exception as e:
            print(f"❌ Error processing {db_file}: {e}")
    
    print(f"📊 Found {len(runs)} search runs total")
    return jsonify(runs)

@app.route('/api/load_run/<path:db_file>')
def load_search_run(db_file: str):
    """Load a specific search run."""
    try:
        # Decode the URL-encoded path
        import urllib.parse
        db_file = urllib.parse.unquote(db_file)
        print(f"🔍 Loading search run from: {db_file}")
        
        processor = get_data_processor(db_file)
        
        # Get all data needed for visualization
        run_info = processor.get_search_run_info()
        nodes_data = processor.get_all_nodes_data()
        breakthrough_points = processor.calculate_breakthrough_points(nodes_data)
        tree_structure = processor.build_tree_structure(nodes_data)
        
        # Find best node
        best_node = max(nodes_data, key=lambda x: x['score']) if nodes_data else None
        
        return jsonify({
            'success': True,
            'run_info': run_info,
            'nodes': nodes_data,
            'breakthrough_points': breakthrough_points,
            'tree_structure': tree_structure,
            'best_node': best_node
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/node/<node_id>')
def get_node_details(node_id: str):
    """Get detailed information for a specific node."""
    try:
        processor = get_data_processor()
        nodes_data = processor.get_all_nodes_data()
        
        # Handle virtual_root special case
        if node_id == 'virtual_root':
            # Find all root nodes
            root_nodes = [n for n in nodes_data if not n['parent_id']]
            best_score = max((n['score'] for n in root_nodes if n['score']), default=0.0)
            
            virtual_root_node = {
                'node_id': 'virtual_root',
                'parent_id': None,
                'score': best_score,
                'execution_status': 'Virtual',
                'code': f'# Virtual Root Node\n# This node links {len(root_nodes)} separate search trees\n\n' +
                        '\n'.join([f'# Tree {i+1}: Node {n["node_id"][:8]} (score: {n["score"]:.4f})' 
                                   for i, n in enumerate(root_nodes)]),
                'llm_summary': f'• This is a virtual root node linking {len(root_nodes)} separate search trees\n' +
                              f'• Best score among roots: {best_score:.4f}\n' +
                              f'• Total nodes in search: {len(nodes_data)}',
                'code_diff_summary': '',
                'mutation_type': 'virtual',
                'generation': 0,
                'auto_fixes': 0,
                'execution_duration': 0,
                'created_at': '',
                'updated_at': ''
            }
            
            return jsonify({
                'success': True,
                'node': virtual_root_node,
                'parent_node': None
            })
        
        # Find the requested node
        node = next((n for n in nodes_data if n['node_id'] == node_id), None)
        if not node:
            return jsonify({'success': False, 'error': 'Node not found'}), 404
        
        # Find parent node if exists
        parent_node = None
        if node['parent_id']:
            parent_node = next((n for n in nodes_data if n['node_id'] == node['parent_id']), None)
        
        return jsonify({
            'success': True,
            'node': node,
            'parent_node': parent_node
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files with no-cache headers."""
    response = send_from_directory('static', filename)
    # Disable caching for all static files
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Tree Search Explorer')
    parser.add_argument('--db', type=str, help='Database file to load initially')
    parser.add_argument('--port', type=int, default=5000, help='Port to run on')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    if args.db:
        get_data_processor(args.db)
        print(f"✅ Loaded database: {args.db}")
    
    print(f"🌐 Starting Tree Search Explorer on http://{args.host}:{args.port}")
    print(f"📊 Available databases: {list(Path('.').glob('*.db'))}")
    
    app.run(host=args.host, port=args.port, debug=args.debug)