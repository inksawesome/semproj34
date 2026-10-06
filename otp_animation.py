import json
import streamlit.components.v1 as components

def render_otp_animation(graph_adj, path, otp, counter, time_remaining, time_step):
    graph_json = json.dumps(graph_adj)
    path_json = json.dumps(path)
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@600;700&family=Inter:wght@400;600;700&family=Geist+Mono:wght@500;700&display=swap');
            
            :root {{
                --neon-pink: #FF2E97;
                --neon-cyan: #00E5FF;
                --neon-lime: #B6FF00;
                --neon-violet: #7A5CFF;
                --rainbow: linear-gradient(90deg, #FF2E97, #FF6B00, #FFE600, #B6FF00, #00E5FF, #7A5CFF);
                
                --glass-bg: rgba(255, 255, 255, 0.45);
                --glass-blur: blur(20px) saturate(180%);
                --glass-border: 1px solid rgba(255, 255, 255, 0.7);
                --glass-shadow: 0 8px 24px -4px rgba(10,10,10,0.08);
            }}

            body {{
                margin: 0; padding: 0; 
                background-color: #FFFFFF;
                background-image: radial-gradient(circle, rgba(10,10,10,0.14) 1px, transparent 1.2px);
                background-size: 24px 24px;
                color: #0A0A0A;
                font-family: 'Inter', sans-serif; 
                display: flex; height: 100vh; overflow: hidden;
            }}
            
            /* Gradient Blobs */
            .blob-1 {{
                position: absolute; width: 400px; height: 400px; background: rgba(255,46,151,0.2); 
                top: -100px; left: -100px; filter: blur(80px); border-radius: 50%; z-index: -1;
            }}
            .blob-2 {{
                position: absolute; width: 500px; height: 500px; background: rgba(0,229,255,0.2); 
                bottom: -150px; right: -150px; filter: blur(80px); border-radius: 50%; z-index: -1;
            }}

            .sidebar {{
                width: 350px; 
                background: var(--glass-bg);
                backdrop-filter: var(--glass-blur);
                border-right: var(--glass-border);
                box-shadow: var(--glass-shadow);
                padding: 2rem; display: flex; flex-direction: column; justify-content: space-between; z-index: 10;
            }}
            
            .main-content {{
                flex-grow: 1; position: relative; display: flex; align-items: center; justify-content: center;
            }}
            
            canvas {{ display: block; width: 100%; height: 100%; }}
            
            .title {{ 
                font-family: 'Space Grotesk', sans-serif;
                font-size: 1.8rem; font-weight: 700; 
                background: var(--rainbow);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin-bottom: 0.25rem; 
            }}
            
            .subtitle {{ font-size: 0.95rem; color: #52525B; margin-bottom: 2rem; font-weight: 500; }}
            
            .otp-display {{
                font-family: 'Space Grotesk', sans-serif; font-size: 4rem; color: #0A0A0A;
                font-weight: 700; letter-spacing: 0.15rem; text-align: center; margin: 2rem 0;
                text-shadow: 0 4px 12px rgba(10,10,10,0.1);
            }}
            
            .status-bar {{ 
                background: rgba(10,10,10,0.05); border-radius: 8px; overflow: hidden; height: 12px; margin-top: 1rem; 
            }}
            
            .status-fill {{ 
                height: 100%; background: var(--rainbow); width: 100%; transition: width 1s linear; 
            }}
            
            .info-card {{ 
                background: rgba(255, 255, 255, 0.6); 
                border: var(--glass-border); 
                padding: 1.2rem; border-radius: 16px; margin-bottom: 1rem; font-size: 0.85rem; 
                box-shadow: inset 0 1px 0 rgba(255,255,255,0.9);
            }}
            
            .stat-row {{ display: flex; justify-content: space-between; margin-bottom: 0.6rem; }}
            .stat-row:last-child {{ margin-bottom: 0; }}
            .stat-val {{ font-family: 'Geist Mono', monospace; font-weight: 700; color: var(--neon-violet); }}
            
            .node-info {{ 
                position: absolute; top: 2rem; right: 2rem; 
                background: var(--glass-bg); backdrop-filter: var(--glass-blur);
                padding: 1rem 1.5rem; border-radius: 16px; border: var(--glass-border); 
                font-family: 'Geist Mono', monospace; font-weight: 600; color: #0A0A0A;
                box-shadow: var(--glass-shadow);
            }}
        </style>
    </head>
    <body>
        <div class="blob-1"></div>
        <div class="blob-2"></div>
        <div class="sidebar">
            <div>
                <div class="title">Server Visualizer</div>
                <div class="subtitle">Random-Walk OTP Generation</div>
                <div class="info-card">
                    <div class="stat-row"><span style="color:#52525B">Algorithm</span><span class="stat-val">Graph Walk</span></div>
                    <div class="stat-row"><span style="color:#52525B">Nodes</span><span class="stat-val">{len(graph_adj)}</span></div>
                    <div class="stat-row"><span style="color:#52525B">Walk Steps</span><span class="stat-val">{len(path)-1}</span></div>
                    <div class="stat-row"><span style="color:#52525B">Time Window</span><span class="stat-val">T = {counter}</span></div>
                </div>
                <div class="otp-display">{otp}</div>
                <div style="display:flex; justify-content:space-between; font-size:0.85rem; color:#52525B; font-weight: 600;">
                    <span>Valid for: <span id="time-rem" style="color:#0A0A0A">{time_remaining}s</span></span>
                </div>
                <div class="status-bar"><div class="status-fill" id="status-fill"></div></div>
            </div>
            <div style="font-size:0.8rem; color:#52525B; line-height: 1.4;">The server generates the OTP based on the deterministic graph walk shown on the right.</div>
        </div>
        <div class="main-content">
            <div class="node-info" id="node-info">Current Path Length: 0/{len(path)-1}</div>
            <canvas id="graphCanvas"></canvas>
        </div>
        <script>
            const graph = {graph_json};
            const currentPath = {path_json};
            let timeRemaining = {time_remaining};
            const timeStep = {time_step};
            
            const canvas = document.getElementById('graphCanvas');
            const ctx = canvas.getContext('2d');
            let nodes = [];
            let animatedPathIndex = 0;

            function resize() {{
                canvas.width = canvas.clientWidth;
                canvas.height = canvas.clientHeight;
                calculateNodePositions();
                drawGraph();
            }}
            window.addEventListener('resize', resize);

            function calculateNodePositions() {{
                nodes = [];
                const radius = Math.min(canvas.width, canvas.height) * 0.4;
                const centerX = canvas.width / 2;
                const centerY = canvas.height / 2;
                for (let i = 0; i < graph.length; i++) {{
                    const angle = (i / graph.length) * Math.PI * 2 - Math.PI / 2;
                    nodes.push({{ x: centerX + Math.cos(angle) * radius, y: centerY + Math.sin(angle) * radius }});
                }}
            }}

            function drawGraph() {{
                if (nodes.length === 0) return;
                ctx.clearRect(0, 0, canvas.width, canvas.height);

                ctx.strokeStyle = 'rgba(10, 10, 10, 0.1)';
                ctx.lineWidth = 1;
                for (let i = 0; i < graph.length; i++) {{
                    for (let j of graph[i]) {{
                        if (i < j) {{
                            ctx.beginPath(); ctx.moveTo(nodes[i].x, nodes[i].y); ctx.lineTo(nodes[j].x, nodes[j].y); ctx.stroke();
                        }}
                    }}
                }}

                if (currentPath.length > 0) {{
                    ctx.strokeStyle = 'rgba(255, 46, 151, 0.8)'; // neon pink
                    ctx.lineWidth = 3;
                    ctx.beginPath();
                    ctx.moveTo(nodes[currentPath[0]].x, nodes[currentPath[0]].y);
                    for (let i = 1; i <= animatedPathIndex; i++) {{
                        ctx.lineTo(nodes[currentPath[i]].x, nodes[currentPath[i]].y);
                    }}
                    ctx.stroke();
                }}

                for (let i = 0; i < nodes.length; i++) {{
                    const isActive = currentPath.slice(0, animatedPathIndex + 1).includes(i);
                    const isCurrent = currentPath[animatedPathIndex] === i;
                    ctx.beginPath();
                    ctx.arc(nodes[i].x, nodes[i].y, isActive ? 8 : 5, 0, Math.PI * 2);
                    if (isCurrent) {{
                        ctx.fillStyle = '#FF2E97'; ctx.shadowColor = '#FF2E97'; ctx.shadowBlur = 15;
                    }} else if (isActive) {{
                        ctx.fillStyle = '#00E5FF'; ctx.shadowBlur = 0;
                    }} else {{
                        ctx.fillStyle = '#E4E4E7'; ctx.shadowBlur = 0;
                    }}
                    ctx.fill();
                }}
                ctx.shadowBlur = 0;
            }}

            function animateWalk() {{
                if (animatedPathIndex < currentPath.length - 1) {{
                    animatedPathIndex++;
                    document.getElementById('node-info').innerText = `Path Length: ${{animatedPathIndex}}/{len(path)-1} (Node ${{currentPath[animatedPathIndex]}})`;
                    drawGraph();
                    setTimeout(animateWalk, 100);
                }}
            }}

            function updateCountdown() {{
                const percent = (timeRemaining / timeStep) * 100;
                document.getElementById('status-fill').style.width = `${{percent}}%`;
                document.getElementById('time-rem').innerText = `${{timeRemaining}}s`;
                
                if (timeRemaining > 0) {{
                    timeRemaining--;
                    setTimeout(updateCountdown, 1000);
                }} else {{
                    // When it hits 0, wait a brief moment then reload the iframe parent to get new OTP
                    setTimeout(() => {{
                        window.parent.postMessage({{type: 'streamlit:setComponentValue', value: true}}, '*');
                    }}, 1000);
                }}
            }}

            // Start everything
            resize();
            animateWalk();
            updateCountdown();
        </script>
    </body>
    </html>
    """
    
    # Render component
    components.html(html, height=700)
