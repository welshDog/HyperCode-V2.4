"""
HyperFocus Flow Dashboard - Real-time monitoring for neurodivergent builders
FastAPI + WebSocket for live updates
"""

from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import asyncio
import json
import docker
import psutil
from datetime import datetime
import sys

app = FastAPI(title="HyperFocus Flow")
client = docker.from_env()

# Store connected clients for broadcasting
connected_clients = []

async def get_system_stats():
    """Get real-time system metrics"""
    try:
        containers = client.containers.list()
        running = len([c for c in containers if c.status == "running"])
        total = len(containers)
        
        stats = {
            "timestamp": datetime.now().isoformat(),
            "containers_running": running,
            "containers_total": total,
            "health": int((running / max(total, 1)) * 100),
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
        }
        
        # Get container statuses
        container_statuses = []
        for c in containers[:10]:  # Top 10
            status_text = c.status
            is_healthy = "healthy" in str(c.attrs.get("State", {}).get("Health", {}))
            container_statuses.append({
                "name": c.name,
                "status": status_text,
                "is_healthy": is_healthy,
                "image": c.image.short_id[:12]
            })
        
        stats["containers"] = container_statuses
        return stats
    except Exception as e:
        return {"error": str(e)}

@app.get("/")
async def dashboard():
    """Serve dashboard HTML"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>HyperFocus Flow</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                background: #0a0e27;
                color: #e0e6ff;
                font-family: 'Courier New', monospace;
                line-height: 1.6;
                overflow: hidden;
            }
            
            .container {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                padding: 20px;
                height: 100vh;
                overflow: auto;
            }
            
            .panel {
                background: #1a1f3a;
                border: 2px solid #00d9ff;
                border-radius: 8px;
                padding: 20px;
                box-shadow: 0 0 20px rgba(0, 217, 255, 0.3);
            }
            
            .panel-title {
                color: #00d9ff;
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 15px;
                border-bottom: 2px solid #00d9ff;
                padding-bottom: 10px;
            }
            
            .metric {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin: 12px 0;
                padding: 10px;
                background: rgba(0, 217, 255, 0.05);
                border-left: 3px solid #00d9ff;
            }
            
            .metric-label { color: #00d9ff; font-weight: bold; }
            .metric-value { color: #00ff88; font-size: 20px; font-weight: bold; }
            
            .status-indicator {
                width: 12px;
                height: 12px;
                border-radius: 50%;
                display: inline-block;
                margin-right: 8px;
            }
            .status-healthy { background: #00ff88; box-shadow: 0 0 10px #00ff88; }
            .status-warning { background: #ffaa00; box-shadow: 0 0 10px #ffaa00; }
            .status-error { background: #ff3333; box-shadow: 0 0 10px #ff3333; }
            
            .container-list {
                display: grid;
                gap: 8px;
                max-height: 300px;
                overflow-y: auto;
            }
            
            .container-item {
                background: rgba(0, 217, 255, 0.05);
                padding: 10px;
                border-left: 3px solid #00ff88;
                border-radius: 4px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                font-size: 13px;
            }
            
            .container-name { color: #00d9ff; font-weight: bold; }
            .container-status { color: #00ff88; }
            
            .chart {
                margin-top: 15px;
                padding: 15px;
                background: rgba(0, 217, 255, 0.05);
                border-radius: 4px;
            }
            
            .progress-bar {
                width: 100%;
                height: 20px;
                background: rgba(0, 0, 0, 0.3);
                border-radius: 10px;
                overflow: hidden;
                margin-top: 5px;
            }
            
            .progress-fill {
                height: 100%;
                background: linear-gradient(90deg, #00d9ff, #00ff88);
                width: 0%;
                transition: width 0.3s ease;
                box-shadow: 0 0 10px rgba(0, 217, 255, 0.8);
            }
            
            .header {
                grid-column: 1 / -1;
                text-align: center;
                padding-bottom: 20px;
                border-bottom: 2px solid #00d9ff;
            }
            
            .header h1 {
                color: #00ff88;
                font-size: 28px;
                text-shadow: 0 0 20px rgba(0, 255, 136, 0.5);
            }
            
            .health-score {
                color: #00ff88;
                font-size: 48px;
                font-weight: bold;
                text-align: center;
                margin: 20px 0;
                text-shadow: 0 0 20px rgba(0, 255, 136, 0.8);
            }
            
            .pulse { animation: pulse 2s infinite; }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🧠 HyperFocus Flow Dashboard</h1>
                <p id="timestamp">Loading...</p>
            </div>
            
            <div class="panel">
                <div class="panel-title">System Health</div>
                <div class="health-score" id="health-score">--</div>
                <div class="metric">
                    <span class="metric-label">Containers Running</span>
                    <span class="metric-value" id="containers-running">-/-</span>
                </div>
                <div class="metric">
                    <span class="metric-label">CPU Usage</span>
                    <span class="metric-value" id="cpu-value">--%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="cpu-bar" style="width: 0%"></div>
                </div>
                <div class="metric" style="margin-top: 15px;">
                    <span class="metric-label">Memory Usage</span>
                    <span class="metric-value" id="memory-value">--%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="memory-bar" style="width: 0%"></div>
                </div>
                <div class="metric" style="margin-top: 15px;">
                    <span class="metric-label">Disk Usage</span>
                    <span class="metric-value" id="disk-value">--%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="disk-bar" style="width: 0%"></div>
                </div>
            </div>
            
            <div class="panel">
                <div class="panel-title">Container Status (Top 10)</div>
                <div class="container-list" id="container-list">
                    <div class="container-item">
                        <span>Loading containers...</span>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            const ws = new WebSocket("ws://localhost:8000/ws");
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                updateDashboard(data);
            };
            
            ws.onerror = (error) => {
                console.error("WebSocket error:", error);
            };
            
            function updateDashboard(stats) {
                // Update timestamp
                document.getElementById("timestamp").textContent = 
                    new Date(stats.timestamp).toLocaleTimeString();
                
                // Update health score
                const healthScore = stats.health || 0;
                const healthEl = document.getElementById("health-score");
                healthEl.textContent = healthScore + "%";
                
                // Update containers
                document.getElementById("containers-running").textContent = 
                    `${stats.containers_running}/${stats.containers_total}`;
                
                // Update resources
                const cpuVal = (stats.cpu_percent || 0).toFixed(1);
                document.getElementById("cpu-value").textContent = cpuVal + "%";
                document.getElementById("cpu-bar").style.width = cpuVal + "%";
                
                const memVal = (stats.memory_percent || 0).toFixed(1);
                document.getElementById("memory-value").textContent = memVal + "%";
                document.getElementById("memory-bar").style.width = memVal + "%";
                
                const diskVal = (stats.disk_percent || 0).toFixed(1);
                document.getElementById("disk-value").textContent = diskVal + "%";
                document.getElementById("disk-bar").style.width = diskVal + "%";
                
                // Update containers list
                if (stats.containers && stats.containers.length > 0) {
                    const containerList = document.getElementById("container-list");
                    containerList.innerHTML = stats.containers.map(c => {
                        const statusClass = c.is_healthy ? "status-healthy" : "status-warning";
                        return `
                            <div class="container-item">
                                <span>
                                    <span class="status-indicator ${statusClass}"></span>
                                    <span class="container-name">${c.name}</span>
                                </span>
                                <span class="container-status">${c.status}</span>
                            </div>
                        `;
                    }).join("");
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for live updates"""
    await websocket.accept()
    connected_clients.append(websocket)
    
    try:
        while True:
            # Get stats every 2 seconds
            stats = await get_system_stats()
            await websocket.send_json(stats)
            await asyncio.sleep(2)
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        connected_clients.remove(websocket)

@app.get("/api/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "HyperFocus Flow Dashboard"}

if __name__ == "__main__":
    import uvicorn
    print("Starting HyperFocus Flow Dashboard on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
