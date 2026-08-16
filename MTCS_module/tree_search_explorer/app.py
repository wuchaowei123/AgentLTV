from flask import Flask, jsonify, render_template_string
import random
import argparse

app = Flask(__name__)

# ==========================================================
# 🌟 前端 HTML 模板
# ==========================================================
HTML_PAGE = """
<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="UTF-8" />
  <title>🌲 Tree Search Explorer Pro</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
  <link rel="stylesheet"
        href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">
  <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
  <style>
    html, body { scroll-behavior: smooth; }
    .fade-in { animation: fadeIn 0.6s ease-out; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(10px);} to {opacity: 1; transform: translateY(0);} }
    .node circle { transition: all 0.25s ease; cursor: pointer; }
    .node:hover circle { stroke-width: 3; stroke: #3b82f6; r: 8; }
    #loader {
      display: none;
      position: fixed; inset: 0;
      background: rgba(0,0,0,0.6);
      z-index: 100; justify-content: center; align-items: center;
    }
  </style>
</head>
<body class="bg-gray-950 text-gray-100 min-h-screen">

  <!-- Header -->
  <header class="bg-gray-900/80 backdrop-blur p-4 flex justify-between items-center shadow-md border-b border-gray-800">
    <h1 class="text-2xl font-bold text-blue-400 tracking-wide">🌲 Tree Search Explorer Pro</h1>
    <div>
      <select id="dbSelector" class="bg-gray-800 border border-gray-700 text-gray-200 px-3 py-1.5 rounded-lg focus:ring-2 focus:ring-blue-500">
        <option value="mock_run_1">mock_run_1</option>
        <option value="mock_run_2">mock_run_2</option>
      </select>
      <button id="loadBtn" class="ml-3 px-4 py-1.5 bg-blue-600 hover:bg-blue-700 rounded-lg shadow transition">加载</button>
    </div>
  </header>

  <!-- Loading overlay -->
  <div id="loader" class="fixed flex">
    <div class="text-center">
      <div class="w-12 h-12 border-4 border-blue-400 border-t-transparent rounded-full animate-spin mx-auto"></div>
      <p class="mt-3 text-gray-300">正在加载数据，请稍候...</p>
    </div>
  </div>

  <!-- Layout -->
  <main class="grid grid-cols-3 gap-6 p-6">

    <!-- Left: Info panel -->
    <aside class="col-span-1 space-y-6 fade-in">

      <section id="runInfo" class="bg-gray-900 rounded-2xl p-5 hidden shadow-md">
        <h2 class="text-lg font-semibold mb-3 text-blue-400">📊 搜索运行信息</h2>
        <div id="runInfoContent" class="text-sm text-gray-300 leading-relaxed"></div>
      </section>

      <section id="chartSection" class="bg-gray-900 rounded-2xl p-5 hidden shadow-md">
        <h2 class="text-lg font-semibold mb-3 text-blue-400">📈 性能趋势</h2>
        <canvas id="scoreChart" height="180"></canvas>
      </section>

      <section id="bestNode" class="bg-gray-900 rounded-2xl p-5 hidden shadow-md">
        <h2 class="text-lg font-semibold mb-3 text-blue-400">🏆 最优节点</h2>
        <div id="bestNodeSummary" class="text-sm text-gray-300 leading-relaxed"></div>
      </section>
    </aside>

    <!-- Middle: Graph -->
    <section id="graphArea" class="col-span-2 bg-gray-900 rounded-2xl p-5 relative fade-in shadow-md">
      <h2 class="text-lg font-semibold mb-3 text-blue-400">🧭 搜索树可视化</h2>
      <svg id="treeGraph" width="100%" height="720"></svg>
    </section>
  </main>

  <!-- Modal -->
  <div id="nodeModal" class="fixed inset-0 bg-black bg-opacity-70 hidden items-center justify-center z-50">
    <div class="bg-gray-900 p-6 rounded-2xl shadow-2xl max-w-3xl w-[90%] max-h-[80vh] overflow-y-auto fade-in border border-gray-800">
      <button id="closeModal" class="float-right text-gray-400 hover:text-gray-200">✖</button>
      <h3 class="text-xl font-semibold text-blue-400 mb-3">🧩 节点详情</h3>
      <div id="modalContent" class="text-gray-300 text-sm space-y-2"></div>
      <pre class="mt-4 rounded-lg bg-gray-800 p-3 overflow-x-auto"><code id="modalCode" class="language-python"></code></pre>
    </div>
  </div>

  <footer class="text-center text-gray-500 text-sm py-6 border-t border-gray-800">
    © 2025 Tree Explorer Pro — Built with Flask + Tailwind + D3.js
  </footer>

  <script>
    const dbSelector = document.getElementById('dbSelector');
    const loadBtn = document.getElementById('loadBtn');
    const loader = document.getElementById('loader');
    const modal = document.getElementById('nodeModal');
    const closeModal = document.getElementById('closeModal');

    closeModal.onclick = () => modal.classList.add('hidden');

    // 加载数据
    loadBtn.addEventListener('click', async () => {
      const dbFile = dbSelector.value;
      loader.style.display = 'flex';
      try {
        const res = await fetch(`/api/load_run/${encodeURIComponent(dbFile)}`);
        const data = await res.json();
        if (!data.success) throw new Error(data.error || '加载失败');

        renderRunInfo(data.run_info);
        renderChart(data.nodes);
        renderBestNode(data.best_node);
        drawTree(data.nodes);
      } catch (err) {
        alert("❌ 加载失败：" + err.message);
      } finally {
        loader.style.display = 'none';
      }
    });

    function renderRunInfo(info) {
      const el = document.getElementById('runInfo');
      el.classList.remove('hidden');
      document.getElementById('runInfoContent').innerHTML = `
        <p>运行ID：<span class="text-blue-300">${info.search_run_id}</span></p>
        <p>节点数：${info.total_nodes}</p>
        <p>最佳分数：<span class="text-green-400 font-semibold">${info.best_score.toFixed(4)}</span></p>
        <p>成功率：${(info.success_rate * 100).toFixed(1)}%</p>
      `;
    }

    function renderChart(nodes) {
      const ctx = document.getElementById('scoreChart');
      document.getElementById('chartSection').classList.remove('hidden');
      new Chart(ctx, {
        type: 'line',
        data: {
          labels: nodes.map((_, i) => i + 1),
          datasets: [{
            label: 'Score',
            data: nodes.map(n => n.score),
            borderColor: '#60a5fa',
            backgroundColor: 'rgba(96,165,250,0.2)',
            borderWidth: 2,
            tension: 0.3,
            pointRadius: 0
          }]
        },
        options: {
          plugins: { legend: { labels: { color: '#e5e7eb' } } },
          scales: {
            x: { ticks: { color: '#9ca3af' }, grid: { color: '#1f2937' } },
            y: { ticks: { color: '#9ca3af' }, grid: { color: '#1f2937' } }
          }
        }
      });
    }

    function renderBestNode(best) {
      const el = document.getElementById('bestNode');
      el.classList.remove('hidden');
      document.getElementById('bestNodeSummary').innerHTML = `
        <p>ID: ${best.node_id}</p>
        <p>Score: <span class="text-green-400 font-semibold">${best.score.toFixed(4)}</span></p>
        <p>Status: <span class="text-yellow-400">${best.status}</span></p>
        <p>摘要:<br>${best.llm_summary.replace(/\\n/g, '<br>')}</p>
      `;
    }

    function drawTree(nodes) {
      d3.select("#treeGraph").selectAll("*").remove();
      const svg = d3.select("#treeGraph");
      const width = svg.node().getBoundingClientRect().width;
      const height = +svg.attr("height");

      const links = nodes.filter(n => n.parent_id != null).map(n => ({
        source: n.parent_id,
        target: n.node_id
      }));

      const simulation = d3.forceSimulation(nodes)
        .force("link", d3.forceLink(links).id(d => d.node_id).distance(70))
        .force("charge", d3.forceManyBody().strength(-200))
        .force("center", d3.forceCenter(width/2, height/2));

      const link = svg.append("g")
        .attr("stroke", "#4b5563").attr("stroke-opacity", 0.5)
        .selectAll("line")
        .data(links)
        .join("line")
        .attr("stroke-width", 1.5);

      const node = svg.append("g")
        .attr("stroke", "#fff").attr("stroke-width", 1)
        .selectAll("circle")
        .data(nodes)
        .join("circle")
        .attr("r", 6)
        .attr("fill", d => ({
          completed: "#3b82f6",
          running: "#facc15",
          failed: "#ef4444"
        }[d.status] || "#9ca3af"))
        .on("click", showNodeDetail)
        .call(drag(simulation));

      const label = svg.append("g")
        .selectAll("text")
        .data(nodes)
        .join("text")
        .attr("font-size", "10px")
        .attr("fill", "#d1d5db")
        .text(d => d.node_id);

      simulation.on("tick", () => {
        link.attr("x1", d => d.source.x)
            .attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x)
            .attr("y2", d => d.target.y);
        node.attr("cx", d => d.x)
            .attr("cy", d => d.y);
        label.attr("x", d => d.x + 8)
             .attr("y", d => d.y + 3);
      });

      function drag(simulation) {
        return d3.drag()
          .on("start", event => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            event.subject.fx = event.subject.x;
            event.subject.fy = event.subject.y;
          })
          .on("drag", event => {
            event.subject.fx = event.x;
            event.subject.fy = event.y;
          })
          .on("end", event => {
            if (!event.active) simulation.alphaTarget(0);
            event.subject.fx = null;
            event.subject.fy = null;
          });
      }
    }

    function showNodeDetail(event, node) {
      document.getElementById('modalContent').innerHTML = `
        <p><strong>ID:</strong> ${node.node_id}</p>
        <p><strong>Score:</strong> ${node.score?.toFixed(4)}</p>
        <p><strong>Status:</strong> ${node.status}</p>
        <p><strong>摘要:</strong><br>${node.llm_summary?.replace(/\\n/g, "<br>") || '无'}</p>
      `;
      document.getElementById('modalCode').textContent = node.code || "# 无代码";
      hljs.highlightAll();
      modal.classList.remove('hidden');
    }
  </script>

</body>
</html>
"""

# ==========================================================
# 🧠 后端 Flask 接口
# ==========================================================
@app.route("/")
def index():
    return render_template_string(HTML_PAGE)


@app.route("/api/load_run/<db>")
def load_run(db):
    random.seed(42)
    total_nodes = 30
    nodes = []
    for i in range(total_nodes):
        parent_id = random.randint(0, i - 1) if i > 0 and random.random() > 0.3 else None
        nodes.append({
            "node_id": i,
            "parent_id": parent_id,
            "score": round(random.uniform(0.3, 1.0), 4),
            "status": random.choice(["completed", "running", "failed"]),
            "llm_summary": f"节点 {i} 的摘要说明，这里展示 LLM 输出的内容。",
            "code": f"def node_{i}():\\n    return 'Result_{i}'"
        })

    best_node = max(nodes, key=lambda n: n["score"])
    run_info = {
        "search_run_id": db,
        "total_nodes": total_nodes,
        "best_score": best_node["score"],
        "success_rate": sum(1 for n in nodes if n["status"] == "completed") / total_nodes,
    }

    return jsonify({
        "success": True,
        "run_info": run_info,
        "nodes": nodes,
        "best_node": best_node
    })


# ==========================================================
# 🚀 启动入口（支持命令行参数）
# ==========================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run Tree Search Explorer Pro")
    parser.add_argument("--db", type=str, default="mock_run_1", help="数据库文件路径（目前未使用）")
    parser.add_argument("--port", type=int, default=8080, help="Flask 运行端口")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="监听地址")

    args = parser.parse_args()

    print(f"🚀 Tree Search Explorer Pro 启动中：http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=True)

# 💡 启动命令：
# python app.py --port 8080 --host 0.0.0.0
# ==========================================================
