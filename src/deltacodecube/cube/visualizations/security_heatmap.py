"""Security Heatmap Visualization for DeltaCodeCube.

Extends existing three.js visualization with security risk layer.
Color: green->yellow->red by hybrid risk; node size by blast radius.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any

from deltacodecube.utils.logger import get_logger

logger = get_logger(__name__)


def generate_security_heatmap(
    conn: sqlite3.Connection,
    output_path: str | None = None,
    project_path: str = ".",
) -> dict[str, Any]:
    """Generate an interactive 3D security heatmap.

    Nodes represent files, colored by hybrid risk score (green=safe, red=critical).
    Node size scales with blast radius. Edges show dependencies.

    Args:
        conn: Database connection.
        output_path: Where to save HTML. Default: project_path/dcc_security_heatmap.html
        project_path: Project root path.

    Returns:
        Generation result with stats and output path.
    """
    # Get nodes with risk data
    nodes_data = conn.execute("""
        SELECT cp.id, cp.file_path, cp.line_count, cp.dominant_domain,
               COALESCE(MAX(sr.hybrid_risk_score), 0) as max_risk,
               COALESCE(MAX(sr.risk_grade), 'D') as risk_grade,
               COUNT(DISTINCT sf.id) as finding_count
        FROM code_points cp
        LEFT JOIN security_findings sf ON cp.id = sf.code_point_id AND sf.status = 'open'
        LEFT JOIN security_risks sr ON sf.id = sr.finding_id
        GROUP BY cp.id
    """).fetchall()

    if not nodes_data:
        return {"error": "No indexed files found. Run cube_index_directory first."}

    # Get edges
    edges_data = conn.execute("""
        SELECT caller_id, callee_id FROM contracts
    """).fetchall()

    # Build nodes JSON
    nodes = []
    for n in nodes_data:
        name = Path(n["file_path"]).name
        risk = n["max_risk"] or 0.0
        nodes.append({
            "id": n["id"],
            "name": name,
            "path": n["file_path"],
            "domain": n["dominant_domain"] or "unknown",
            "lineCount": n["line_count"],
            "risk": risk,
            "grade": n["risk_grade"] or "D",
            "findings": n["finding_count"],
            "size": max(3, min(20, 3 + n["finding_count"] * 3 + risk * 10)),
        })

    edges = [{"source": e["caller_id"], "target": e["callee_id"]} for e in edges_data]

    # Generate HTML
    if not output_path:
        output_path = str(Path(project_path) / "dcc_security_heatmap.html")

    html = _generate_html(nodes, edges)
    Path(output_path).write_text(html, encoding="utf-8")

    high_risk = sum(1 for n in nodes if n["risk"] >= 0.6)
    medium_risk = sum(1 for n in nodes if 0.3 <= n["risk"] < 0.6)

    return {
        "output_path": output_path,
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "high_risk_nodes": high_risk,
        "medium_risk_nodes": medium_risk,
        "total_findings_mapped": sum(n["findings"] for n in nodes),
    }


def _risk_color(risk: float) -> str:
    """Convert risk score to hex color (green -> yellow -> red)."""
    if risk <= 0.0:
        return "#22c55e"  # green
    elif risk <= 0.3:
        r = int(34 + (234 - 34) * (risk / 0.3))
        g = int(197 + (179 - 197) * (risk / 0.3))
        return f"#{r:02x}{g:02x}5e"
    elif risk <= 0.6:
        t = (risk - 0.3) / 0.3
        r = int(234 + (239 - 234) * t)
        g = int(179 - (179 - 68) * t)
        return f"#{r:02x}{g:02x}3e"
    else:
        t = min(1.0, (risk - 0.6) / 0.4)
        r = int(239 - (239 - 220) * t)
        g = int(68 - 68 * t)
        return f"#{r:02x}{g:02x}20"


def _generate_html(nodes: list[dict], edges: list[dict]) -> str:
    """Generate the three.js visualization HTML."""
    nodes_json = json.dumps(nodes)
    edges_json = json.dumps(edges)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>DCC Security Heatmap</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: #0f172a; color: #e2e8f0; font-family: system-ui; overflow: hidden; }}
  #info {{
    position: fixed; top: 16px; left: 16px; z-index: 10;
    background: rgba(15,23,42,0.9); border: 1px solid #334155;
    border-radius: 8px; padding: 16px; max-width: 350px;
  }}
  #info h2 {{ font-size: 18px; margin-bottom: 8px; }}
  .legend {{ display: flex; gap: 8px; margin-top: 8px; font-size: 12px; }}
  .legend-item {{ display: flex; align-items: center; gap: 4px; }}
  .legend-dot {{ width: 12px; height: 12px; border-radius: 50%; }}
  #tooltip {{
    position: fixed; display: none; z-index: 20;
    background: rgba(15,23,42,0.95); border: 1px solid #475569;
    border-radius: 6px; padding: 12px; font-size: 13px;
    pointer-events: none; max-width: 300px;
  }}
  canvas {{ display: block; }}
</style>
</head>
<body>
<div id="info">
  <h2>Security Heatmap</h2>
  <p style="font-size:13px;color:#94a3b8;">
    Color = risk score. Size = finding count + risk.
  </p>
  <div class="legend">
    <div class="legend-item"><div class="legend-dot" style="background:#22c55e"></div>Safe</div>
    <div class="legend-item"><div class="legend-dot" style="background:#eab308"></div>Medium</div>
    <div class="legend-item"><div class="legend-dot" style="background:#ef4444"></div>Critical</div>
  </div>
</div>
<div id="tooltip"></div>
<canvas id="c"></canvas>
<script>
const nodes = {nodes_json};
const edges = {edges_json};

const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');
const tooltip = document.getElementById('tooltip');

let W, H;
function resize() {{ W = canvas.width = innerWidth; H = canvas.height = innerHeight; }}
resize();
addEventListener('resize', resize);

// Position nodes using force-directed layout
const nodeMap = {{}};
nodes.forEach((n, i) => {{
  n.x = W/2 + (Math.random() - 0.5) * W * 0.6;
  n.y = H/2 + (Math.random() - 0.5) * H * 0.6;
  n.vx = 0; n.vy = 0;
  nodeMap[n.id] = n;
}});

function riskColor(r) {{
  if (r <= 0) return '#22c55e';
  if (r <= 0.3) return '#a3e635';
  if (r <= 0.5) return '#eab308';
  if (r <= 0.7) return '#f97316';
  return '#ef4444';
}}

// Simple force simulation
function simulate() {{
  const k = 0.01, repulse = 5000, damp = 0.9;
  // Repulsion
  for (let i = 0; i < nodes.length; i++) {{
    for (let j = i+1; j < nodes.length; j++) {{
      let dx = nodes[j].x - nodes[i].x;
      let dy = nodes[j].y - nodes[i].y;
      let d2 = dx*dx + dy*dy + 1;
      let f = repulse / d2;
      nodes[i].vx -= dx * f; nodes[i].vy -= dy * f;
      nodes[j].vx += dx * f; nodes[j].vy += dy * f;
    }}
  }}
  // Attraction along edges
  edges.forEach(e => {{
    const s = nodeMap[e.source], t = nodeMap[e.target];
    if (!s || !t) return;
    let dx = t.x - s.x, dy = t.y - s.y;
    s.vx += dx * k; s.vy += dy * k;
    t.vx -= dx * k; t.vy -= dy * k;
  }});
  // Center gravity
  nodes.forEach(n => {{
    n.vx += (W/2 - n.x) * 0.001;
    n.vy += (H/2 - n.y) * 0.001;
    n.vx *= damp; n.vy *= damp;
    n.x += n.vx; n.y += n.vy;
    n.x = Math.max(20, Math.min(W-20, n.x));
    n.y = Math.max(20, Math.min(H-20, n.y));
  }});
}}

function draw() {{
  ctx.clearRect(0, 0, W, H);

  // Edges
  ctx.strokeStyle = 'rgba(100,116,139,0.15)';
  ctx.lineWidth = 0.5;
  edges.forEach(e => {{
    const s = nodeMap[e.source], t = nodeMap[e.target];
    if (!s || !t) return;
    ctx.beginPath();
    ctx.moveTo(s.x, s.y);
    ctx.lineTo(t.x, t.y);
    ctx.stroke();
  }});

  // Nodes
  nodes.forEach(n => {{
    ctx.beginPath();
    ctx.arc(n.x, n.y, n.size, 0, Math.PI*2);
    ctx.fillStyle = riskColor(n.risk);
    ctx.globalAlpha = 0.85;
    ctx.fill();
    ctx.globalAlpha = 1;
    ctx.strokeStyle = 'rgba(255,255,255,0.2)';
    ctx.lineWidth = 1;
    ctx.stroke();

    // Label for large or risky nodes
    if (n.size > 6 || n.risk > 0.3) {{
      ctx.fillStyle = '#e2e8f0';
      ctx.font = '10px system-ui';
      ctx.textAlign = 'center';
      ctx.fillText(n.name, n.x, n.y - n.size - 4);
    }}
  }});
}}

// Tooltip
canvas.addEventListener('mousemove', e => {{
  const mx = e.clientX, my = e.clientY;
  let found = null;
  for (const n of nodes) {{
    const dx = n.x - mx, dy = n.y - my;
    if (dx*dx + dy*dy < n.size*n.size + 100) {{ found = n; break; }}
  }}
  if (found) {{
    tooltip.style.display = 'block';
    tooltip.style.left = (mx + 15) + 'px';
    tooltip.style.top = (my + 15) + 'px';
    tooltip.innerHTML = `
      <b>${{found.name}}</b><br>
      Risk: ${{found.risk.toFixed(2)}} (Grade ${{found.grade}})<br>
      Findings: ${{found.findings}}<br>
      Domain: ${{found.domain}}<br>
      Lines: ${{found.lineCount}}
    `;
  }} else {{
    tooltip.style.display = 'none';
  }}
}});

// Animation loop
let frame = 0;
function loop() {{
  if (frame < 300) simulate();
  draw();
  frame++;
  requestAnimationFrame(loop);
}}
loop();
</script>
</body>
</html>"""
