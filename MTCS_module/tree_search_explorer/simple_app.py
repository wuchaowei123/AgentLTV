#!/usr/bin/env python3
"""
Simplified Tree Search Explorer
===============================

A simplified version that directly loads the extracted JSON data.
"""

from flask import Flask, render_template, jsonify, send_from_directory
import json
from pathlib import Path

app = Flask(__name__)

# Load the pre-extracted data
DATA_FILE = "official_run_data.json"

@app.route('/')
def index():
    """Main tree explorer page."""
    return render_template('tree_explorer.html')

@app.route('/api/search_runs')
def get_search_runs():
    """Get available search runs."""
    try:
        # Return a simple list with our test data
        runs = [
            {
                'search_run_id': '1758505441-Official-Run-1.0000',
                'total_nodes': 13,
                'best_score': 1.0000,
                'success_rate': 69.2,
                'db_file': 'official_run_data.json'
            }
        ]
        print(f"✅ Returning {len(runs)} search runs")
        return jsonify(runs)
    except Exception as e:
        print(f"❌ Error in get_search_runs: {e}")
        return jsonify([])

@app.route('/api/load_run/<path:db_file>')
def load_search_run(db_file: str):
    """Load a specific search run."""
    try:
        print(f"🔍 Loading data from: {DATA_FILE}")
        
        # Load the extracted JSON data
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
        
        print(f"✅ Loaded {len(data.get('nodes', []))} nodes")
        return jsonify(data)
        
    except Exception as e:
        print(f"❌ Error loading search run: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/node/<node_id>')
def get_node_details(node_id: str):
    """Get detailed information for a specific node."""
    try:
        print(f"🔍 Getting details for node: {node_id}")
        
        # Load the extracted JSON data
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
        
        # Find the requested node
        nodes = data.get('nodes', [])
        node = next((n for n in nodes if n['node_id'] == node_id), None)
        
        if not node:
            return jsonify({'success': False, 'error': 'Node not found'}), 404
        
        # Find parent node if exists
        parent_node = None
        if node.get('parent_id'):
            parent_node = next((n for n in nodes if n['node_id'] == node['parent_id']), None)
        
        print(f"✅ Found node {node_id}")
        return jsonify({
            'success': True,
            'node': node,
            'parent_node': parent_node
        })
        
    except Exception as e:
        print(f"❌ Error getting node details: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files."""
    return send_from_directory('static', filename)

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Simple Tree Search Explorer')
    parser.add_argument('--port', type=int, default=5000, help='Port to run on')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    # Check if data file exists
    if not Path(DATA_FILE).exists():
        print(f"❌ Data file not found: {DATA_FILE}")
        print("Please run: python data_bridge.py ../test_fixed.db --output test_data.json")
        exit(1)
    
    print(f"✅ Using data file: {DATA_FILE}")
    print(f"🌐 Starting Simple Tree Search Explorer on http://{args.host}:{args.port}")
    
    app.run(host=args.host, port=args.port, debug=args.debug)