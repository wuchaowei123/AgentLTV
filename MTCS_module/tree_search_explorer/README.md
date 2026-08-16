# Tree Search Explorer

A powerful web-based visualization tool for exploring AI system tree search results, designed specifically for the Universal MTCS_module.

## 🌟 Features

- **🚀 Breakthrough Progress Visualization**: Interactive line chart showing score improvements over time
- **🌳 Interactive Tree Visualization**: D3.js-powered tree showing the complete search space
- **📊 Node Details Panel**: LLM-generated summaries and metadata for each solution
- **💻 Code Comparison**: Side-by-side diff view with syntax highlighting
- **🔍 Real-time Search**: Load and explore multiple search runs
- **📈 Comprehensive Analytics**: Success rates, execution statistics, and performance metrics

## 🎯 Key Components

### 1. Breakthrough Plot (Top Left)
- Line chart showing best score progression
- Green breakthrough points mark significant improvements
- **Click breakthrough points** to jump to specific solutions
- Hover for detailed information

### 2. Node Details Panel (Top Right)
- **LLM Summary**: Automatically generated description of the solution approach
- **Differences Summary**: What changed from the parent solution
- **Metadata**: Execution time, auto-fixes, generation info, mutation strategy

### 3. Tree Visualization (Bottom Left)
- **Interactive tree** showing parent-child relationships
- **Color coding**:
  - 🟢 Green: Breakthrough nodes (new best scores)
  - 🟣 Purple: Regular nodes
  - 🟠 Orange: Selected node
  - 🔴 Red: Failed executions
- **Click any node** to view its details
- **Zoom controls**: +/- zoom, reset view, fit to screen

### 4. Code Comparison (Bottom Right)
- **Side-by-side view**: Parent code vs. Child code
- **Monaco Editor**: Full syntax highlighting for Python
- **Diff statistics**: Lines added, removed, changed
- **Synchronized scrolling**: Navigate both panels together

## 🚀 Quick Start

### Method 1: Using the Web Interface

1. **Activate the PyTorch Environment** (Required):
   ```bash
   source ~/.bashrc
   conda activate pytorch
   ```

2. **Start the Tree Explorer**:
   ```bash
   cd /home/jupyter/MTCS_module/tree_search_explorer
   python app.py --db ../official_run_v5_test.db --port 8005 --host 0.0.0.0
   ```
   
   **Default Configuration**:
   - Port: 8005 (use `--port` to change)
   - Host: 0.0.0.0 (accessible from any IP)
   - Displays all available databases from parent directory

3. **Open your browser**: Navigate to one of:
   - `http://localhost:8005` (local access)
   - `http://<your-server-ip>:8005` (remote access)

4. **Select a search run** from the dropdown menu at the top

5. **Explore**:
   - Click breakthrough points on the plot to jump to specific nodes
   - Navigate the tree visualization by clicking nodes
   - Compare code between parent and child nodes in the diff viewer
   - Switch between different search runs using the dropdown

### Quick Restart (If Port is Busy)
```bash
# Kill existing processes and restart
pkill -9 -f "tree_search_explorer/app.py"
cd /home/jupyter/MTCS_module/tree_search_explorer
source ~/.bashrc && conda activate pytorch
python app.py --db ../official_run_v5_test.db --port 8005 --host 0.0.0.0
```

### Method 2: Data Extraction Only

Extract search data to JSON for analysis:

```bash
cd tree_search_explorer
python data_bridge.py ../test_fixed.db --output extracted_data.json --pretty
```

## 📊 Understanding the Data

### Search Run Format
Each search run includes:
- **Run ID**: Timestamp-based identifier
- **Total Nodes**: Number of solutions explored
- **Best Score**: Highest metric achieved
- **Success Rate**: Percentage of successful executions

### Node Information
Each node contains:
- **Code**: The complete Python solution
- **Score**: Performance metric (e.g., AUC, RMSE)
- **Status**: Success/Error execution result
- **Mutation Type**: Strategy used to generate this solution
- **Genealogy**: Parent relationships and generation depth
- **Execution Metadata**: Runtime, auto-fixes, error messages

### Breakthrough Detection
Breakthrough points are automatically identified where:
- A new best score is achieved
- Significant improvement over previous best
- Marked prominently in visualizations

## 🔧 Technical Architecture

### Backend (Flask)
- **`app.py`**: Main Flask application
- **`data_bridge.py`**: Database extraction and processing
- **REST API endpoints**:
  - `/api/search_runs`: List available search runs
  - `/api/load_run/<db_file>`: Load specific search data
  - `/api/node/<node_id>`: Get detailed node information

### Frontend (JavaScript)
- **D3.js**: Tree visualization and breakthrough plot
- **Plotly.js**: Interactive line charts
- **Monaco Editor**: Code comparison with syntax highlighting
- **Responsive design**: Works on desktop and mobile
- **Cache-busting**: Query parameters and no-cache headers prevent stale JavaScript
- **Proper cleanup**: Tree visualization is cleared before rendering new data to prevent overlapping

### Database Integration
- **Direct SQLite access**: Reads from AI system databases
- **Real-time data**: No caching, always fresh results
- **Multiple database support**: Switch between search runs

## 🎛️ Configuration Options

### Command Line Arguments

```bash
python app.py [OPTIONS]

Options:
  --db PATH          Database file to load initially
  --port PORT        Port to run on (default: 5000)
  --host HOST        Host to bind to (default: 127.0.0.1)
  --debug            Enable debug mode
```

### Data Bridge Options

```bash
python data_bridge.py DB_PATH [OPTIONS]

Options:
  --output, -o FILE  Output JSON file path
  --pretty, -p       Pretty print JSON output
```

## 🎨 User Interface Guide

### Navigation Flow
1. **Page Load**: Displays the best node from the search
2. **Breakthrough Interaction**: Click green circles to jump to breakthroughs
3. **Tree Exploration**: Click any node to view its details
4. **Code Analysis**: Compare solutions side-by-side

### Interactive Elements
- **Breakthrough Plot**: Click points for navigation
- **Tree Nodes**: Click to select, hover for tooltips
- **Zoom Controls**: Navigate large trees easily
- **Code Editors**: Full-featured with search and highlighting
- **Diff Toggle**: Enable/disable difference highlighting

## 📈 Analytics & Insights

### Performance Metrics
- **Success Rate**: Execution reliability
- **Score Progression**: Improvement over time
- **Generation Depth**: How deep the search went
- **Strategy Effectiveness**: Which mutations work best

### Pattern Recognition
- **Breakthrough Patterns**: What triggers major improvements
- **Failed Paths**: Understanding what doesn't work
- **Code Evolution**: How solutions evolve over generations
- **Strategy Distribution**: Which approaches are explored

## 🔍 Advanced Features

### Search Run Comparison
- Load multiple databases
- Compare different search strategies
- Analyze performance across runs

### Code Analysis
- Automatic LLM summaries
- Difference detection
- Syntax highlighting
- Error tracking

### Export Capabilities
- JSON data export
- CSV results export
- Tree structure export
- Performance analytics

## 🛠️ Development Setup

### Requirements
```bash
pip install -r requirements.txt
```

### Dependencies
- Flask 2.3.2
- pandas 2.0.3
- numpy 1.24.3
- Python 3.8+

### File Structure
```
tree_search_explorer/
├── app.py                 # Flask backend
├── data_bridge.py         # Data extraction
├── requirements.txt       # Dependencies
├── templates/
│   └── tree_explorer.html # Main UI template
├── static/
│   ├── css/
│   │   └── tree_explorer.css
│   └── js/
│       └── tree_explorer.js
└── data/                  # Extracted data storage
```

## 🎯 Use Cases

### 1. Research Analysis
- **Understanding Search Behavior**: How does the AI explore the solution space?
- **Strategy Evaluation**: Which mutation strategies are most effective?
- **Breakthrough Analysis**: What triggers major improvements?

### 2. Algorithm Development
- **Debug Search Issues**: Why did certain paths fail?
- **Optimize Parameters**: Which settings produce better results?
- **Compare Approaches**: Different algorithms side-by-side

### 3. Solution Discovery
- **Find Best Solutions**: Identify top-performing code
- **Understand Evolution**: How solutions improve over time
- **Extract Patterns**: Common elements in successful solutions

### 4. Educational Exploration
- **Learn ML Techniques**: See various approaches in action
- **Code Learning**: Study how solutions evolve
- **Scientific Method**: Observe hypothesis testing in practice

## 🚨 Troubleshooting

### Common Issues

1. **Tree Shows Only One Node (Despite Multiple Nodes in Database)**
   
   **Symptom**: You see only a single node in the tree visualization, but the server logs show "Total nodes: 20" or similar.
   
   **Cause**: Browser is caching old JavaScript files that don't properly clear previous tree visualizations.
   
   **Solutions**:
   ```bash
   # Solution 1: Hard refresh browser (best option)
   # - Chrome/Firefox: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)
   # - Safari: Cmd+Option+R
   
   # Solution 2: Clear browser cache
   # - Chrome: Settings → Privacy → Clear browsing data → Cached images and files
   # - Firefox: Settings → Privacy & Security → Clear Data → Cached Web Content
   
   # Solution 3: Kill and restart server (forces cache-busting)
   pkill -9 -f "tree_search_explorer/app.py"
   cd /home/jupyter/MTCS_module/tree_search_explorer
   source ~/.bashrc && conda activate pytorch
   python app.py --db ../official_run_v5_test.db --port 8005 --host 0.0.0.0
   
   # Solution 4: Open in incognito/private browsing mode
   # This bypasses all caches completely
   ```
   
   **Prevention**: The app now includes cache-busting headers and query parameters to prevent this issue.

2. **Database Connection Error**
   ```bash
   # Check database file exists
   ls -la ../test_fixed.db
   
   # Verify database format
   python data_bridge.py ../test_fixed.db --pretty
   ```

3. **Port Already in Use**
   ```bash
   # Kill existing processes on port
   lsof -ti:8005 | xargs kill -9 2>/dev/null || fuser -k 8005/tcp 2>/dev/null
   
   # Or use a different port
   python app.py --port 5001
   ```

4. **"Node not found" Error When Clicking Virtual Root**
   
   **Symptom**: Clicking the star node (virtual_root) shows "Node not found" error.
   
   **Cause**: This was a bug in older versions where the virtual root (used to connect multiple search trees) wasn't properly handled.
   
   **Solution**: Update to the latest version - this is now fixed. The virtual root now shows a summary of all root nodes.

5. **Tree Visualization Not Updating When Switching Databases**
   
   **Symptom**: You select a different database from the dropdown, but the tree still shows the old data.
   
   **Cause**: Old tree visualization was not being cleared before rendering the new one.
   
   **Solution**: This is fixed in the latest version. The tree now properly clears old visualizations using `container.innerHTML = ''` before rendering new data.

6. **Memory Issues with Large Trees**
   - Use data export for analysis
   - Filter to specific node ranges
   - Increase system memory

7. **Browser Compatibility**
   - Use modern browsers (Chrome, Firefox, Safari)
   - Enable JavaScript
   - Clear browser cache if you see stale data

### Performance Tips
- **Large Datasets**: Use data export for initial analysis
- **Memory Usage**: Close unused browser tabs
- **Rendering Speed**: Use tree zoom controls for large graphs
- **Network Issues**: Run locally for best performance

## 🌟 Best Practices

### Effective Exploration
1. **Start with Overview**: Check breakthrough plot first
2. **Identify Patterns**: Look for clustering in the tree
3. **Compare Strategically**: Focus on breakthrough nodes
4. **Study Evolution**: Follow parent-child chains

### Analysis Workflow
1. **Load Data**: Select appropriate search run
2. **Overview Analysis**: Check statistics and breakthrough points
3. **Deep Dive**: Explore specific nodes of interest
4. **Code Review**: Compare solutions and understand differences
5. **Export Results**: Save insights for further analysis

## 🔄 Recent Fixes & Improvements

### Version 2025-10-15 (Latest)

**Fixed: Tree Visualization Issues**
- ✅ **Tree not clearing between database switches**: Added `container.innerHTML = ''` to properly clear old tree visualizations before rendering new ones
- ✅ **Browser caching stale JavaScript**: Implemented cache-busting query parameters (`?v=20251015_fix3_final`) and no-cache headers on static files
- ✅ **NaN positioning errors**: Added edge case handling for `maxDepth === 0` (single-node trees)
- ✅ **Virtual root "Node not found"**: Special handling for synthetic `virtual_root` node that connects multiple search trees
- ✅ **Database path confusion**: Resolved issue where Flask app was loading wrong database file from subdirectory

**Technical Details**:
```javascript
// Before (BUG - overlapping trees):
this.treeVisualization = new TreeVisualization('tree-visualization', treeStructure, nodes, this);

// After (FIXED - proper cleanup):
const container = document.getElementById('tree-visualization');
if (container) {
    container.innerHTML = ''; // Clear old tree
}
if (this.treeVisualization) {
    this.treeVisualization = null; // Destroy old object
}
this.treeVisualization = new TreeVisualization('tree-visualization', treeStructure, nodes, this);
```

## 🎉 Success! 

The Tree Search Explorer is now ready to help you visualize and understand your AI system's search process. Navigate through the solution space, discover breakthrough moments, and gain insights into how your Universal MTCS_module discovers and improves scientific software!

---

**Need Help?** Check the troubleshooting section or examine the sample data extraction to understand the expected format.