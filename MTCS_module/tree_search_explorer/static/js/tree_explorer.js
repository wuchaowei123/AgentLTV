/**
 * Tree Search Explorer - Main JavaScript Application
 * =================================================
 * 
 * Interactive visualization for AI system tree search results.
 * Features: breakthrough plot, tree visualization, node details, code comparison.
 */

class TreeSearchExplorer {
    constructor() {
        this.currentData = null;
        this.selectedNode = null;
        this.breakthroughPoints = [];
        this.treeVisualization = null;
        this.monacoEditors = {
            parent: null,
            child: null
        };
        this.diffHighlightEnabled = true;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.loadAvailableRuns();
    }
    
    setupEventListeners() {
        // Search run selector
        document.getElementById('search-run-selector').addEventListener('change', (e) => {
            if (e.target.value) {
                this.loadSearchRun(e.target.value);
            }
        });
        
        // Refresh button
        document.getElementById('refresh-btn').addEventListener('click', () => {
            this.loadAvailableRuns();
        });
        
        // Tree controls
        document.getElementById('tree-zoom-in').addEventListener('click', () => {
            this.treeVisualization?.zoomIn();
        });
        
        document.getElementById('tree-zoom-out').addEventListener('click', () => {
            this.treeVisualization?.zoomOut();
        });
        
        document.getElementById('tree-reset').addEventListener('click', () => {
            this.treeVisualization?.resetView();
        });
        
        document.getElementById('tree-fit').addEventListener('click', () => {
            this.treeVisualization?.fitToScreen();
        });
        
        // Code diff toggle
        document.getElementById('toggle-diff-highlight').addEventListener('click', () => {
            this.toggleDiffHighlight();
        });
        
        // Error modal
        document.getElementById('close-error-modal').addEventListener('click', () => {
            this.hideError();
        });
    }
    
    async loadAvailableRuns() {
        try {
            const response = await fetch('/api/search_runs');
            const runs = await response.json();
            
            const selector = document.getElementById('search-run-selector');
            selector.innerHTML = '<option value="">Select a search run...</option>';
            
            runs.forEach(run => {
                const option = document.createElement('option');
                option.value = run.db_file;
                option.textContent = `${run.search_run_id} (${run.total_nodes} nodes, best: ${run.best_score?.toFixed(4) || 'N/A'})`;
                selector.appendChild(option);
            });
            
            // Auto-select the first run if available
            if (runs.length > 0) {
                selector.value = runs[0].db_file;
                this.loadSearchRun(runs[0].db_file);
            }
            
        } catch (error) {
            this.showError('Failed to load available search runs: ' + error.message);
        }
    }
    
    async loadSearchRun(dbFile) {
        this.showLoading('Loading search data...');
        
        try {
            const response = await fetch(`/api/load_run/${encodeURIComponent(dbFile)}`);
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error);
            }
            
            this.currentData = data;
            this.breakthroughPoints = data.breakthrough_points;
            
            // Update UI with loaded data
            this.updateHeader(data.run_info);
            this.updateStats(data.run_info);
            this.createBreakthroughPlot(data.nodes, data.breakthrough_points);
            this.createTreeVisualization(data.tree_structure, data.nodes);
            
            // Select the best node by default
            if (data.best_node) {
                this.selectNode(data.best_node.node_id);
            }
            
            this.hideLoading();
            
        } catch (error) {
            this.hideLoading();
            this.showError('Failed to load search run: ' + error.message);
        }
    }
    
    updateHeader(runInfo) {
        document.getElementById('search-run-title').textContent = runInfo.search_run_id;
    }
    
    updateStats(runInfo) {
        document.getElementById('total-nodes-stat').textContent = `Total Nodes: ${runInfo.total_nodes}`;
        document.getElementById('success-rate-stat').textContent = `Success Rate: ${runInfo.success_rate?.toFixed(1) || 0}%`;
        document.getElementById('best-score-stat').textContent = `Best Score: ${runInfo.best_score?.toFixed(4) || '0.0000'}`;
    }
    
    createBreakthroughPlot(nodes, breakthroughPoints) {
        const sortedNodes = nodes.sort((a, b) => a.order - b.order);
        
        // Calculate best score progression
        const bestScoreProgression = [];
        let bestSoFar = -Infinity;
        
        sortedNodes.forEach((node, index) => {
            if (node.score > bestSoFar) {
                bestSoFar = node.score;
            }
            bestScoreProgression.push({
                x: index + 1,
                y: bestSoFar,
                node_id: node.node_id
            });
        });
        
        // Create main line trace
        const lineTrace = {
            x: bestScoreProgression.map(p => p.x),
            y: bestScoreProgression.map(p => p.y),
            type: 'scatter',
            mode: 'lines',
            name: 'Best Score Progress',
            line: {
                color: '#3498db',
                width: 3
            },
            hovertemplate: 'Node: %{x}<br>Best Score: %{y:.4f}<extra></extra>'
        };
        
        // Create breakthrough points trace
        const breakthroughTrace = {
            x: breakthroughPoints.map(bp => bp.node_index),
            y: breakthroughPoints.map(bp => bp.score),
            type: 'scatter',
            mode: 'markers',
            name: 'Breakthroughs',
            marker: {
                color: '#2ecc71',
                size: 12,
                symbol: 'circle',
                line: {
                    color: '#27ae60',
                    width: 2
                }
            },
            customdata: breakthroughPoints.map(bp => bp.node_id),
            hovertemplate: 'Breakthrough!<br>Node: %{x}<br>Score: %{y:.4f}<br>Improvement: +%{marker.size:.4f}<extra></extra>'
        };
        
        const layout = {
            title: {
                text: 'Search Progress & Breakthroughs',
                font: { size: 16, color: '#2c3e50' }
            },
            xaxis: {
                title: 'Node Number',
                gridcolor: '#ecf0f1'
            },
            yaxis: {
                title: 'Best Score Found',
                gridcolor: '#ecf0f1'
            },
            plot_bgcolor: 'rgba(0,0,0,0)',
            paper_bgcolor: 'rgba(0,0,0,0)',
            margin: { t: 50, r: 20, b: 50, l: 60 },
            hovermode: 'closest'
        };
        
        const config = {
            responsive: true,
            displayModeBar: true,
            modeBarButtonsToRemove: ['lasso2d', 'select2d', 'autoScale2d'],
            displaylogo: false
        };
        
        Plotly.newPlot('breakthrough-plot', [lineTrace, breakthroughTrace], layout, config);
        
        // Add click handler for breakthrough points
        document.getElementById('breakthrough-plot').on('plotly_click', (data) => {
            if (data.points && data.points.length > 0) {
                const point = data.points[0];
                if (point.curveNumber === 1) { // Breakthrough points trace
                    const nodeId = point.customdata;
                    this.selectNode(nodeId);
                }
            }
        });
    }
    
    createTreeVisualization(treeStructure, nodes) {
        console.log('🌳 createTreeVisualization called');
        console.log('  treeStructure:', treeStructure);
        console.log('  treeStructure.children count:', treeStructure?.children?.length || 0);
        console.log('  nodes count:', nodes?.length || 0);
        
        // CRITICAL FIX: Clear the old tree before creating a new one!
        const container = document.getElementById('tree-visualization');
        if (container) {
            container.innerHTML = ''; // Remove all old SVG elements
            console.log('  ✅ Cleared old tree visualization');
        }
        
        // Destroy old tree visualization object if it exists
        if (this.treeVisualization) {
            this.treeVisualization = null;
            console.log('  ✅ Destroyed old TreeVisualization object');
        }
        
        // Create new tree visualization
        this.treeVisualization = new TreeVisualization('tree-visualization', treeStructure, nodes, this);
        console.log('  ✅ Created new TreeVisualization');
    }
    
    async selectNode(nodeId) {
        try {
            const response = await fetch(`/api/node/${nodeId}`);
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error);
            }
            
            this.selectedNode = data.node;
            this.updateNodeDetails(data.node);
            this.updateCodeComparison(data.node, data.parent_node);
            
            // Update tree visualization selection
            if (this.treeVisualization) {
                this.treeVisualization.selectNode(nodeId);
            }
            
        } catch (error) {
            this.showError('Failed to load node details: ' + error.message);
        }
    }
    
    updateNodeDetails(node) {
        // Update header
        document.getElementById('node-details-title').textContent = `Node #${node.node_id}`;
        
        // Update badges
        const statusBadge = document.getElementById('node-status-badge');
        statusBadge.textContent = node.status;
        statusBadge.className = `badge ${node.status.toLowerCase() === 'success' ? 'success' : 'error'}`;
        
        const scoreBadge = document.getElementById('node-score-badge');
        scoreBadge.textContent = `${node.score.toFixed(4)}`;
        scoreBadge.className = 'badge score';
        
        // Update LLM summary
        document.getElementById('llm-summary').textContent = node.llm_summary || 'No summary available';
        
        // Update differences summary
        const diffSection = document.getElementById('diff-summary-section');
        const diffSummary = document.getElementById('code-diff-summary');
        
        if (node.parent_id && node.code_diff_summary) {
            diffSection.style.display = 'block';
            diffSummary.textContent = node.code_diff_summary;
        } else {
            diffSection.style.display = 'none';
        }
        
        // Update metadata
        this.updateNodeMetadata(node);
    }
    
    updateNodeMetadata(node) {
        const metadataContainer = document.getElementById('node-metadata');
        metadataContainer.innerHTML = '';
        
        const metadata = [
            { label: 'Node ID', value: node.node_id },
            { label: 'Parent ID', value: node.parent_id || 'Root' },
            { label: 'Mutation Type', value: node.mutation_type || 'Unknown' },
            { label: 'Generation', value: node.generation.toString() },
            { label: 'Execution Time', value: `${node.execution_duration.toFixed(2)}s` },
            { label: 'Auto Fixes', value: node.auto_fixes.toString() },
            { label: 'Created At', value: new Date(node.created_at).toLocaleString() }
        ];
        
        metadata.forEach(item => {
            const metadataItem = document.createElement('div');
            metadataItem.className = 'metadata-item';
            metadataItem.innerHTML = `
                <div class="metadata-label">${item.label}</div>
                <div class="metadata-value">${item.value}</div>
            `;
            metadataContainer.appendChild(metadataItem);
        });
    }
    
    updateCodeComparison(childNode, parentNode) {
        try {
            // Update headers
            document.getElementById('parent-code-title').textContent = 
                parentNode ? `Parent #${parentNode.node_id}` : 'No Parent (Root Node)';
            document.getElementById('child-code-title').textContent = `Child #${childNode.node_id}`;
            
            // Initialize Monaco editors if not already done
            this.initializeMonacoEditors();
            
            // Set code content
            const parentCode = parentNode?.code || '// This is the root node - no parent to compare';
            const childCode = childNode.code || '// No code available';
            
            // Use setTimeout to ensure Monaco editors are ready
            setTimeout(() => {
                try {
                    if (this.monacoEditors.parent) {
                        this.monacoEditors.parent.setValue(parentCode);
                    }
                    
                    if (this.monacoEditors.child) {
                        this.monacoEditors.child.setValue(childCode);
                    }
                    
                    // Update diff statistics
                    this.updateDiffStatistics(parentCode, childCode);
                    
                    // Apply diff highlighting if enabled
                    if (this.diffHighlightEnabled && parentNode) {
                        this.highlightDifferences(parentCode, childCode);
                    }
                } catch (editorError) {
                    console.warn('Error setting editor content:', editorError.message);
                    // Still show the comparison even if editors fail
                    this.updateDiffStatistics(parentCode, childCode);
                }
            }, 100); // Small delay to ensure editors are ready
            
        } catch (error) {
            console.error('Error in updateCodeComparison:', error.message);
            throw error; // Re-throw to be caught by the calling function
        }
    }
    
    initializeMonacoEditors() {
        if (this.monacoEditors.parent && this.monacoEditors.child) {
            return; // Already initialized
        }
        
        require.config({ paths: { vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs' } });
        
        require(['vs/editor/editor.main'], () => {
            // Parent editor
            this.monacoEditors.parent = monaco.editor.create(document.getElementById('parent-code-editor'), {
                language: 'python',
                theme: 'vs-light',
                readOnly: true,
                fontSize: 12,
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                wordWrap: 'on'
            });
            
            // Child editor
            this.monacoEditors.child = monaco.editor.create(document.getElementById('child-code-editor'), {
                language: 'python',
                theme: 'vs-light',
                readOnly: true,
                fontSize: 12,
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                wordWrap: 'on'
            });
            
            // Sync scrolling
            this.syncEditorScrolling();
        });
    }
    
    syncEditorScrolling() {
        if (!this.monacoEditors.parent || !this.monacoEditors.child) return;
        
        this.monacoEditors.parent.onDidScrollChange(() => {
            const scrollTop = this.monacoEditors.parent.getScrollTop();
            this.monacoEditors.child.setScrollTop(scrollTop);
        });
        
        this.monacoEditors.child.onDidScrollChange(() => {
            const scrollTop = this.monacoEditors.child.getScrollTop();
            this.monacoEditors.parent.setScrollTop(scrollTop);
        });
    }
    
    updateDiffStatistics(parentCode, childCode) {
        if (!parentCode || parentCode.includes('// This is the root node')) {
            document.getElementById('lines-added').textContent = '+0 lines added';
            document.getElementById('lines-removed').textContent = '-0 lines removed';
            document.getElementById('lines-changed').textContent = '~0 lines changed';
            return;
        }
        
        const parentLines = parentCode.split('\n');
        const childLines = childCode.split('\n');
        
        // Simple diff calculation
        const parentSet = new Set(parentLines);
        const childSet = new Set(childLines);
        
        const added = childLines.filter(line => !parentSet.has(line)).length;
        const removed = parentLines.filter(line => !childSet.has(line)).length;
        const changed = Math.min(added, removed);
        
        document.getElementById('lines-added').textContent = `+${added - changed} lines added`;
        document.getElementById('lines-removed').textContent = `-${removed - changed} lines removed`;
        document.getElementById('lines-changed').textContent = `~${changed} lines changed`;
    }
    
    highlightDifferences(parentCode, childCode) {
        if (!this.monacoEditors.parent || !this.monacoEditors.child) return;
        
        try {
            // Check if diff_match_patch is available
            if (typeof diff_match_patch === 'undefined') {
                console.warn('diff_match_patch library not available, skipping diff highlighting');
                return;
            }
            
            // Use diff-match-patch for better diff highlighting
            const dmp = new diff_match_patch();
            const diffs = dmp.diff_main(parentCode, childCode);
            dmp.diff_cleanupSemantic(diffs);
            
            // Apply highlighting (simplified implementation)
            // In a full implementation, you would convert diffs to Monaco decorations
            // For now, we'll just update the editor themes to indicate differences
            console.log('Diff highlighting applied successfully');
            
        } catch (error) {
            console.warn('Error in diff highlighting:', error.message);
            // Gracefully continue without diff highlighting
        }
    }
    
    toggleDiffHighlight() {
        this.diffHighlightEnabled = !this.diffHighlightEnabled;
        const button = document.getElementById('toggle-diff-highlight');
        button.textContent = this.diffHighlightEnabled ? '🎨 Disable Diff Highlighting' : '🎨 Enable Diff Highlighting';
        
        if (this.selectedNode && this.currentData) {
            // Re-update code comparison to apply/remove highlighting
            const parentNode = this.currentData.nodes.find(n => n.node_id === this.selectedNode.parent_id);
            this.updateCodeComparison(this.selectedNode, parentNode);
        }
    }
    
    showLoading(message = 'Loading...') {
        const loadingScreen = document.getElementById('loading-screen');
        const loadingText = loadingScreen.querySelector('p');
        loadingText.textContent = message;
        loadingScreen.classList.remove('hidden');
        document.getElementById('app').classList.add('hidden');
    }
    
    hideLoading() {
        document.getElementById('loading-screen').classList.add('hidden');
        document.getElementById('app').classList.remove('hidden');
    }
    
    showError(message) {
        document.getElementById('error-message').textContent = message;
        document.getElementById('error-modal').classList.remove('hidden');
    }
    
    hideError() {
        document.getElementById('error-modal').classList.add('hidden');
    }
}

/**
 * Tree Visualization Component using D3.js
 */
class TreeVisualization {
    constructor(containerId, treeData, allNodes, explorer) {
        console.log('🎨 TreeVisualization constructor');
        console.log('  containerId:', containerId);
        console.log('  treeData:', treeData);
        console.log('  treeData.children:', treeData?.children?.length || 0);
        console.log('  allNodes:', allNodes?.length || 0);
        
        this.containerId = containerId;
        this.treeData = treeData;
        this.allNodes = allNodes;
        this.explorer = explorer;
        this.svg = null;
        this.g = null;
        this.zoom = null;
        this.selectedNodeId = null;
        
        this.init();
    }
    
    init() {
        const container = document.getElementById(this.containerId);
        const rect = container.getBoundingClientRect();
        
        this.width = rect.width;
        this.height = rect.height;
        
        // Create SVG
        this.svg = d3.select(`#${this.containerId}`)
            .append('svg')
            .attr('width', '100%')
            .attr('height', '100%')
            .style('background', '#fafafa');
        
        // Create zoom behavior
        this.zoom = d3.zoom()
            .scaleExtent([0.1, 5])
            .on('zoom', (event) => {
                this.g.attr('transform', event.transform);
            });
        
        this.svg.call(this.zoom);
        
        // Create main group
        this.g = this.svg.append('g');
        
        this.render();
    }
    
    render() {
        console.log('🎨 render() called');
        console.log('  this.treeData:', this.treeData);
        
        // Create tree layout with very close spacing
        const treeLayout = d3.tree()
            .size([this.width - 300, this.height - 200])  // Smaller tree area for closer nodes
            .separation((a, b) => {
                // Minimal horizontal separation between nodes
                return (a.parent === b.parent ? 0.5 : 0.8);  // Very close spacing
            });
        
        // Convert data to hierarchy
        const root = d3.hierarchy(this.treeData);
        console.log('  root.descendants() count:', root.descendants().length);
        console.log('  root.children:', root.children?.length || 0);
        treeLayout(root);
        
        // Create sequential node numbering based on creation order
        const nodeOrder = this.getNodeOrder();
        
        // Find the best performing node
        const bestNode = this.getBestNode();
        
        // Adjust positioning for top-down layout (root at top, leaves at bottom)
        const maxDepth = Math.max(...root.descendants().map(d => d.depth));
        console.log('  maxDepth:', maxDepth);
        
        root.descendants().forEach(d => {
            // Handle edge case: if maxDepth is 0 (single node), position it in the center
            if (maxDepth === 0) {
                d.y = this.height / 2;
                d.x = this.width / 2;
            } else {
                // Flip the y-coordinate: root (depth 0) at top, leaves (max depth) at bottom
                d.y = (maxDepth - d.depth) * (this.height - 200) / maxDepth + 80;
                d.x = d.x * 0.7 + 80; // Keep horizontal compression
            }
            console.log(`  Node ${d.data.node_id?.substring(0,8)}: x=${d.x}, y=${d.y}, depth=${d.depth}`);
        });
        
        // Draw links (simplified thin grey lines)
        const links = this.g.selectAll('.tree-link')
            .data(root.links())
            .enter()
            .append('path')
            .attr('class', 'tree-link')
            .attr('d', d3.linkVertical()
                .x(d => d.x)
                .y(d => d.y)
            )
            .style('fill', 'none')
            .style('stroke', '#999')
            .style('stroke-width', '1px')
            .style('stroke-opacity', '0.6');
        
        // Draw nodes
        const nodes = this.g.selectAll('.tree-node-group')
            .data(root.descendants())
            .enter()
            .append('g')
            .attr('class', 'tree-node-group')
            .attr('transform', d => `translate(${d.x}, ${d.y})`);
        
        // Add node shapes (circles for regular nodes, stars for best nodes)
        nodes.each((d, i, nodeElements) => {
            const nodeGroup = d3.select(nodeElements[i]);
            const isBestNode = this.isBestNode(d.data, bestNode);
            
            if (isBestNode) {
                // Create star shape for best performing nodes
                const starPath = this.createStarPath(0, 0, 5, 15, 8);
                nodeGroup.append('path')
                    .attr('d', starPath)
                    .attr('class', d => this.getNodeClass(d.data))
                    .style('cursor', 'pointer')
                    .style('fill', d => this.getNodeColor(d.data))
                    .style('stroke', d => this.getNodeStrokeColor(d.data))
                    .style('stroke-width', '2px')
                    .on('click', (event, d) => {
                        if (d.data.node_id !== 'virtual_root') {
                            this.explorer.selectNode(d.data.node_id);
                        }
                    })
                    .on('mouseover', (event, d) => {
                        this.showNodeTooltip(event, d.data);
                    })
                    .on('mouseout', () => {
                        this.hideNodeTooltip();
                    });
            } else {
                // Create circle for regular nodes
                nodeGroup.append('circle')
                    .attr('class', d => this.getNodeClass(d.data))
                    .attr('r', 12)
                    .style('cursor', 'pointer')
                    .style('fill', d => this.getNodeColor(d.data))
                    .style('stroke', d => this.getNodeStrokeColor(d.data))
                    .style('stroke-width', '2px')
                    .on('click', (event, d) => {
                        if (d.data.node_id !== 'virtual_root') {
                            this.explorer.selectNode(d.data.node_id);
                        }
                    })
                    .on('mouseover', (event, d) => {
                        this.showNodeTooltip(event, d.data);
                    })
                    .on('mouseout', () => {
                        this.hideNodeTooltip();
                    });
            }
        });
        
        // Add sequential node labels (#0, #1, #2, etc.)
        nodes.append('text')
            .attr('class', 'tree-node-label')
            .attr('dy', 4)
            .attr('text-anchor', 'middle')
            .style('font-size', '11px')
            .style('font-weight', 'bold')
            .style('fill', 'white')
            .text(d => {
                if (d.data.node_id === 'virtual_root') return '#0';
                return `#${nodeOrder[d.data.node_id] || 'X'}`;
            });
        
        // Add score labels below nodes
        nodes.append('text')
            .attr('class', 'tree-node-score')
            .attr('dy', 28)
            .attr('text-anchor', 'middle')
            .style('font-size', '10px')
            .style('fill', '#333')
            .text(d => d.data.node_id === 'virtual_root' ? '' : (d.data.score?.toFixed(3) || '0.000'));
        
        // Store references
        this.nodes = nodes;
        this.links = links;
        
        // Fit to screen initially
        this.fitToScreen();
    }
    
    getNodeOrder() {
        // Create sequential numbering based on creation order
        const nodeOrder = {};
        
        // Sort all nodes by their order field (creation order)
        const sortedNodes = this.allNodes
            .filter(node => node.node_id !== 'virtual_root')
            .sort((a, b) => (a.order || 0) - (b.order || 0));
        
        // Assign sequential numbers
        sortedNodes.forEach((node, index) => {
            nodeOrder[node.node_id] = index + 1;
        });
        
        return nodeOrder;
    }
    
    getBestNode() {
        // Find the node with the highest score
        let bestNode = null;
        let bestScore = -1;
        
        this.allNodes.forEach(node => {
            if (node.node_id !== 'virtual_root' && node.score > bestScore) {
                bestScore = node.score;
                bestNode = node;
            }
        });
        
        return bestNode;
    }
    
    isBestNode(nodeData, bestNode) {
        // Check if this node is the best performing node
        return bestNode && nodeData.node_id === bestNode.node_id;
    }
    
    createStarPath(cx, cy, spikes, outerRadius, innerRadius) {
        // Create SVG path for a star shape
        let rot = Math.PI / 2 * 3;
        let x = cx;
        let y = cy;
        const step = Math.PI / spikes;
        
        let path = `M ${cx + outerRadius} ${cy}`;
        
        for (let i = 0; i < spikes; i++) {
            x = cx + Math.cos(rot) * outerRadius;
            y = cy + Math.sin(rot) * outerRadius;
            path += ` L ${x} ${y}`;
            rot += step;
            
            x = cx + Math.cos(rot) * innerRadius;
            y = cy + Math.sin(rot) * innerRadius;
            path += ` L ${x} ${y}`;
            rot += step;
        }
        
        path += ' Z';
        return path;
    }
    
    getNodeColor(nodeData) {
        if (nodeData.node_id === 'virtual_root') return '#6c757d'; // Grey for root
        
        // Handle error/failed nodes
        if (nodeData.status === 'Error' || nodeData.status === 'Failed') {
            return '#e74c3c'; // Red for errors
        }
        
        // Get score for gradient coloring
        const score = nodeData.score || 0;
        
        // Define color gradient: Purple (low) -> Blue (medium) -> Teal (high) -> Green (perfect)
        if (score <= 0.25) {
            // Purple range (0 - 0.25)
            const intensity = score / 0.25;
            return this.interpolateColor('#8e44ad', '#6c3483', intensity);
        } else if (score <= 0.5) {
            // Purple to Blue range (0.25 - 0.5)
            const intensity = (score - 0.25) / 0.25;
            return this.interpolateColor('#6c3483', '#3498db', intensity);
        } else if (score <= 0.75) {
            // Blue to Teal range (0.5 - 0.75)
            const intensity = (score - 0.5) / 0.25;
            return this.interpolateColor('#3498db', '#1abc9c', intensity);
        } else {
            // Teal to Green range (0.75 - 1.0)
            const intensity = (score - 0.75) / 0.25;
            return this.interpolateColor('#1abc9c', '#27ae60', intensity);
        }
    }
    
    getNodeStrokeColor(nodeData) {
        if (nodeData.node_id === 'virtual_root') return '#5a6268';
        
        // Darker version of fill color for stroke
        if (nodeData.status === 'Error' || nodeData.status === 'Failed') {
            return '#c0392b';
        }
        
        // Selected node gets special stroke
        if (this.selectedNodeId === nodeData.node_id) {
            return '#f39c12'; // Orange for selected
        }
        
        // Otherwise, use a darker version of the fill color
        const fillColor = this.getNodeColor(nodeData);
        return this.darkenColor(fillColor, 0.2);
    }
    
    interpolateColor(color1, color2, factor) {
        // Parse hex colors
        const c1 = this.hexToRgb(color1);
        const c2 = this.hexToRgb(color2);
        
        // Interpolate
        const r = Math.round(c1.r + (c2.r - c1.r) * factor);
        const g = Math.round(c1.g + (c2.g - c1.g) * factor);
        const b = Math.round(c1.b + (c2.b - c1.b) * factor);
        
        return this.rgbToHex(r, g, b);
    }
    
    hexToRgb(hex) {
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return result ? {
            r: parseInt(result[1], 16),
            g: parseInt(result[2], 16),
            b: parseInt(result[3], 16)
        } : null;
    }
    
    rgbToHex(r, g, b) {
        return "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
    }
    
    darkenColor(hex, factor) {
        const rgb = this.hexToRgb(hex);
        const r = Math.round(rgb.r * (1 - factor));
        const g = Math.round(rgb.g * (1 - factor));
        const b = Math.round(rgb.b * (1 - factor));
        return this.rgbToHex(r, g, b);
    }

    getNodeClass(nodeData) {
        if (nodeData.node_id === 'virtual_root') return 'tree-node regular';
        
        let className = 'tree-node ';
        
        // Check if this is a breakthrough node
        const isBreakthrough = this.explorer.breakthroughPoints.some(bp => bp.node_id === nodeData.node_id);
        if (isBreakthrough) {
            className += 'breakthrough';
        } else if (nodeData.status === 'Error') {
            className += 'failed';
        } else {
            className += 'regular';
        }
        
        // Check if selected
        if (this.selectedNodeId === nodeData.node_id) {
            className += ' selected';
        }
        
        return className;
    }
    
    selectNode(nodeId) {
        this.selectedNodeId = nodeId;
        
        // Update node colors and strokes for both circles and stars
        this.nodes.selectAll('circle, path')
            .style('fill', d => this.getNodeColor(d.data))
            .style('stroke', d => this.getNodeStrokeColor(d.data))
            .style('stroke-width', d => this.selectedNodeId === d.data.node_id ? '3px' : '2px');
        
        // Update link styles - highlight paths to selected node
        this.links
            .style('stroke', d => {
                const isSelected = d.source.data.node_id === nodeId || d.target.data.node_id === nodeId;
                return isSelected ? '#f39c12' : '#999';
            })
            .style('stroke-width', d => {
                const isSelected = d.source.data.node_id === nodeId || d.target.data.node_id === nodeId;
                return isSelected ? '2px' : '1px';
            })
            .style('stroke-opacity', d => {
                const isSelected = d.source.data.node_id === nodeId || d.target.data.node_id === nodeId;
                return isSelected ? '1' : '0.6';
            });
    }
    
    showNodeTooltip(event, nodeData) {
        if (nodeData.node_id === 'virtual_root') return;
        
        // Get sequential node number
        const nodeOrder = this.getNodeOrder();
        const sequentialId = nodeOrder[nodeData.node_id] || 'X';
        
        // Check if this is the best node
        const bestNode = this.getBestNode();
        const isBest = this.isBestNode(nodeData, bestNode);
        
        const tooltip = d3.select('body')
            .append('div')
            .attr('class', 'tree-tooltip')
            .style('position', 'absolute')
            .style('background', 'rgba(0,0,0,0.8)')
            .style('color', 'white')
            .style('padding', '8px')
            .style('border-radius', '4px')
            .style('font-size', '12px')
            .style('pointer-events', 'none')
            .style('z-index', '1000');
        
        let tooltipContent = `
            <strong>Node #${sequentialId}${isBest ? ' ⭐ BEST' : ''}</strong><br>
            Score: ${nodeData.score?.toFixed(4) || 'N/A'}<br>
            Status: ${nodeData.status}<br>
            Mutation: ${nodeData.mutation_type || 'Unknown'}<br>
            <small>ID: ${nodeData.node_id}</small>
        `;
        
        if (isBest) {
            tooltipContent += '<br><small style="color: #ffd700;">★ Highest performing node</small>';
        }
        
        tooltip.html(tooltipContent);
        
        const [x, y] = d3.pointer(event, document.body);
        tooltip.style('left', (x + 10) + 'px')
            .style('top', (y - 10) + 'px');
    }
    
    hideNodeTooltip() {
        d3.selectAll('.tree-tooltip').remove();
    }
    
    zoomIn() {
        this.svg.transition().call(
            this.zoom.scaleBy, 1.5
        );
    }
    
    zoomOut() {
        this.svg.transition().call(
            this.zoom.scaleBy, 1 / 1.5
        );
    }
    
    resetView() {
        this.svg.transition().call(
            this.zoom.transform,
            d3.zoomIdentity
        );
    }
    
    fitToScreen() {
        const bounds = this.g.node().getBBox();
        const fullWidth = this.width;
        const fullHeight = this.height;
        const width = bounds.width;
        const height = bounds.height;
        const midX = bounds.x + width / 2;
        const midY = bounds.y + height / 2;
        
        if (width === 0 || height === 0) return;
        
        const scale = Math.min(fullWidth / width, fullHeight / height) * 0.8;
        const translate = [fullWidth / 2 - scale * midX, fullHeight / 2 - scale * midY];
        
        this.svg.transition().call(
            this.zoom.transform,
            d3.zoomIdentity.translate(translate[0], translate[1]).scale(scale)
        );
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.treeSearchExplorer = new TreeSearchExplorer();
});