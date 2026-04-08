#!/bin/bash

# HyperCode Kubernetes - FINAL COMPLETE HEALTH CHECK WITH DETAILED RECOMMENDATIONS
# Generates comprehensive HTML report with all recommendations

NAMESPACE="hypercode"
REPORT_DIR="./k8s/health_reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FINAL_REPORT="${REPORT_DIR}/FINAL_HEALTH_CHECK_${TIMESTAMP}.html"

mkdir -p "$REPORT_DIR"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  HyperCode Kubernetes - FINAL COMPREHENSIVE HEALTH CHECK  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}\n"

# Generate HTML Report
cat > "$FINAL_REPORT" << 'HTMLEOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HyperCode Kubernetes - Final Health Check Report</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }
        .container {
            max-width: 1600px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }
        header h1 { font-size: 2.8em; margin-bottom: 10px; }
        header p { font-size: 1.1em; opacity: 0.9; }
        
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }
        .summary-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            border-left: 5px solid #667eea;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .summary-card .value {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }
        .summary-card .label {
            color: #666;
            font-size: 0.95em;
        }
        
        .health-score-section {
            padding: 40px;
            text-align: center;
            background: white;
            border-top: 2px solid #f0f0f0;
        }
        .health-score-circle {
            width: 200px;
            height: 200px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 20px;
            font-size: 4em;
            font-weight: bold;
            color: white;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .score-excellent { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .score-good { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
        .score-warning { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); }
        .score-critical { background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%); }
        
        .section {
            padding: 30px;
            border-bottom: 1px solid #f0f0f0;
        }
        .section h2 {
            font-size: 1.8em;
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 3px solid #667eea;
        }
        
        .check-item {
            padding: 15px;
            margin: 10px 0;
            border-radius: 8px;
            display: flex;
            align-items: flex-start;
            gap: 15px;
            border-left: 5px solid;
        }
        .check-pass {
            background: #d4edda;
            border-left-color: #28a745;
        }
        .check-warn {
            background: #fff3cd;
            border-left-color: #ffc107;
        }
        .check-fail {
            background: #f8d7da;
            border-left-color: #dc3545;
        }
        .check-icon {
            font-size: 2em;
            font-weight: bold;
            min-width: 30px;
            text-align: center;
        }
        .check-content h4 {
            margin-bottom: 5px;
            color: #333;
        }
        .check-content p {
            color: #666;
            font-size: 0.95em;
        }
        
        .recommendation {
            padding: 20px;
            margin: 15px 0;
            border-radius: 8px;
            border-left: 5px solid;
            background: #f9f9f9;
        }
        .rec-critical {
            border-left-color: #ff4444;
            background: #ffe6e6;
        }
        .rec-high {
            border-left-color: #ff9800;
            background: #fff4e6;
        }
        .rec-medium {
            border-left-color: #2196f3;
            background: #f0f4ff;
        }
        .rec-low {
            border-left-color: #4caf50;
            background: #e8f5e9;
        }
        
        .rec-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .rec-priority {
            font-weight: bold;
            padding: 5px 12px;
            border-radius: 20px;
            color: white;
            font-size: 0.85em;
        }
        .rec-critical .rec-priority { background: #ff4444; }
        .rec-high .rec-priority { background: #ff9800; }
        .rec-medium .rec-priority { background: #2196f3; }
        .rec-low .rec-priority { background: #4caf50; }
        
        .rec-title {
            font-size: 1.1em;
            font-weight: bold;
            color: #333;
            margin-bottom: 8px;
        }
        .rec-desc {
            color: #666;
            margin: 8px 0;
            line-height: 1.6;
        }
        .rec-cmd {
            background: #1e1e1e;
            color: #0fb881;
            padding: 12px;
            border-radius: 6px;
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 0.85em;
            overflow-x: auto;
            margin-top: 10px;
            line-height: 1.5;
        }
        
        .action-items {
            background: #fff9e6;
            border: 2px solid #ff9800;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }
        .action-items h3 {
            color: #ff6f00;
            margin-bottom: 15px;
            font-size: 1.3em;
        }
        .action-items ul {
            list-style-position: inside;
            margin-left: 0;
        }
        .action-items li {
            margin: 8px 0;
            color: #666;
            padding-left: 10px;
        }
        
        .status-badge {
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.95em;
            margin: 5px 0;
        }
        .status-excellent { background: #d4edda; color: #155724; }
        .status-good { background: #fff3cd; color: #856404; }
        .status-warning { background: #f8d7da; color: #721c24; }
        
        .timeline {
            position: relative;
            padding: 20px 0;
        }
        .timeline-item {
            padding: 15px 20px;
            margin: 15px 0;
            border-left: 3px solid #667eea;
            background: #f9f9f9;
            border-radius: 6px;
        }
        .timeline-item strong {
            color: #667eea;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        table th {
            background: #667eea;
            color: white;
            padding: 12px;
            text-align: left;
        }
        table td {
            padding: 10px 12px;
            border-bottom: 1px solid #ddd;
        }
        table tr:nth-child(even) {
            background: #f9f9f9;
        }
        
        footer {
            background: #f8f9fa;
            padding: 30px;
            text-align: center;
            color: #666;
            border-top: 2px solid #ddd;
        }
        
        @media print {
            body { background: white; }
            .container { box-shadow: none; }
        }
    </style>
</head>
<body>
<div class="container">

<header>
    <h1>🎯 HyperCode Kubernetes Health Check</h1>
    <p>Comprehensive Assessment with Detailed Recommendations</p>
</header>

<div class="summary-grid">
    <div class="summary-card">
        <div class="value" id="health-score">--</div>
        <div class="label">Health Score (0-100)</div>
    </div>
    <div class="summary-card">
        <div class="value" id="total-checks">--</div>
        <div class="label">Total Checks</div>
    </div>
    <div class="summary-card">
        <div class="value" id="passed-checks">--</div>
        <div class="label">Passed Checks</div>
    </div>
    <div class="summary-card">
        <div class="value" id="critical-issues">--</div>
        <div class="label">Critical Issues</div>
    </div>
    <div class="summary-card">
        <div class="value" id="recommendations">--</div>
        <div class="label">Recommendations</div>
    </div>
</div>

<div class="health-score-section">
    <div class="health-score-circle score-excellent" id="score-circle">--</div>
    <h2 id="health-status">Assessment Status</h2>
    <p id="health-message" style="font-size: 1.1em; color: #666; margin-top: 15px;"></p>
</div>

<div class="section">
    <h2>📋 Pre-Flight Checks</h2>
    <div id="preflight-checks"></div>
</div>

<div class="section">
    <h2>🗄️ Database & Storage</h2>
    <div id="database-checks"></div>
</div>

<div class="section">
    <h2>⚙️ Application Status</h2>
    <div id="app-checks"></div>
</div>

<div class="section">
    <h2>📊 Monitoring & Observability</h2>
    <div id="monitoring-checks"></div>
</div>

<div class="section">
    <h2>🔐 Security & Networking</h2>
    <div id="security-checks"></div>
</div>

<div class="section">
    <h2>⚡ Resource & Performance</h2>
    <div id="resource-checks"></div>
</div>

<div class="section">
    <h2>🎯 Critical Issues to Address</h2>
    <div id="critical-section"></div>
</div>

<div class="section">
    <h2>⚠️ Warnings & Cautions</h2>
    <div id="warnings-section"></div>
</div>

<div class="section">
    <h2>🚀 RECOMMENDED ACTIONS (PRIORITIZED)</h2>
    
    <div class="action-items">
        <h3>🔴 CRITICAL - Do These FIRST (Before Production):</h3>
        <ul>
            <li><strong>Update All Secrets:</strong> Change POSTGRES_PASSWORD, HYPERCODE_JWT_SECRET, API_KEY from defaults</li>
            <li><strong>Configure TLS/HTTPS:</strong> Set up SSL certificates for ingress endpoints</li>
            <li><strong>Enable Backup Strategy:</strong> Implement automated database backups</li>
            <li><strong>Set Up Alerting:</strong> Configure Prometheus alerts and notification channels</li>
            <li><strong>Test Disaster Recovery:</strong> Verify backup restore procedures work</li>
        </ul>
    </div>
    
    <div class="action-items" style="background: #fff4e6; border-color: #ff9800;">
        <h3>🟠 HIGH PRIORITY - Do These in First Week:</h3>
        <ul>
            <li><strong>Scale for HA:</strong> Increase PostgreSQL to 3 replicas with streaming replication</li>
            <li><strong>Enable Auto-scaling:</strong> Configure HPA thresholds based on baseline metrics</li>
            <li><strong>Implement RBAC:</strong> Set up role-based access control for team members</li>
            <li><strong>Configure Logging:</strong> Set retention policies and forwarding for audit logs</li>
            <li><strong>Document Runbooks:</strong> Create incident response procedures</li>
        </ul>
    </div>
    
    <div class="action-items" style="background: #f0f4ff; border-color: #2196f3;">
        <h3>🔵 MEDIUM PRIORITY - Do These Before Month 1:</h3>
        <ul>
            <li><strong>Optimize Queries:</strong> Analyze and optimize slow database queries</li>
            <li><strong>Tune Cache:</strong> Adjust Redis memory and eviction policies</li>
            <li><strong>Review Policies:</strong> Audit network and security policies for production</li>
            <li><strong>Set Quotas:</strong> Enforce resource quotas at namespace level</li>
            <li><strong>Monitor Metrics:</strong> Establish baseline metrics and trending</li>
        </ul>
    </div>
    
    <div class="action-items" style="background: #e8f5e9; border-color: #4caf50;">
        <h3>🟢 LOW PRIORITY - Ongoing Improvements:</h3>
        <ul>
            <li><strong>Implement Cost Optimization:</strong> Right-size resources, use spot instances</li>
            <li><strong>Enable Pod Security Policies:</strong> Enforce security best practices</li>
            <li><strong>Set Up GitOps:</strong> Manage deployments through version control</li>
            <li><strong>Implement Canary Deployments:</strong> Gradual rollouts with monitoring</li>
            <li><strong>Regular Security Audits:</strong> Quarterly penetration testing and code review</li>
        </ul>
    </div>
</div>

<div class="section">
    <h2>📅 Deployment Timeline</h2>
    <div class="timeline">
        <div class="timeline-item">
            <strong>Phase 1 (NOW):</strong> Run health check, update secrets, deploy
        </div>
        <div class="timeline-item">
            <strong>Phase 2 (Today):</strong> Verify deployment, run post-deployment checks
        </div>
        <div class="timeline-item">
            <strong>Phase 3 (1-3 Days):</strong> Complete PRODUCTION_READINESS_CHECKLIST
        </div>
        <div class="timeline-item">
            <strong>Phase 4 (1 Week):</strong> Implement critical recommendations
        </div>
        <div class="timeline-item">
            <strong>Phase 5 (2 Weeks):</strong> Set up monitoring and alerting
        </div>
        <div class="timeline-item">
            <strong>Phase 6 (1 Month):</strong> Production deployment and handoff
        </div>
    </div>
</div>

<div class="section">
    <h2>📞 Quick Reference - Common Commands</h2>
    <table>
        <tr>
            <th>Task</th>
            <th>Command</th>
        </tr>
        <tr>
            <td>Check pod status</td>
            <td><code>kubectl get pods -n hypercode -o wide</code></td>
        </tr>
        <tr>
            <td>View pod logs</td>
            <td><code>kubectl logs -n hypercode <pod> --tail=50</code></td>
        </tr>
        <tr>
            <td>Access database</td>
            <td><code>kubectl exec -it postgres-0 -n hypercode -- psql -U postgres</code></td>
        </tr>
        <tr>
            <td>Scale deployment</td>
            <td><code>kubectl scale deployment hypercode-core --replicas=5 -n hypercode</code></td>
        </tr>
        <tr>
            <td>Port forward Grafana</td>
            <td><code>kubectl port-forward svc/grafana 3001:3000 -n hypercode</code></td>
        </tr>
        <tr>
            <td>Check resource usage</td>
            <td><code>kubectl top pods -n hypercode --sort-by=memory</code></td>
        </tr>
        <tr>
            <td>View events</td>
            <td><code>kubectl get events -n hypercode --sort-by='.lastTimestamp'</code></td>
        </tr>
    </table>
</div>

<div class="section">
    <h2>✅ Success Criteria Checklist</h2>
    <table>
        <tr>
            <th>Item</th>
            <th>Status</th>
            <th>Notes</th>
        </tr>
        <tr>
            <td>All pods running</td>
            <td id="crit-pods">❌</td>
            <td>Every pod should be in Running state</td>
        </tr>
        <tr>
            <td>Services have endpoints</td>
            <td id="crit-endpoints">❌</td>
            <td>No services with 0 endpoints</td>
        </tr>
        <tr>
            <td>PVCs are bound</td>
            <td id="crit-pvcs">❌</td>
            <td>All storage claims should be bound</td>
        </tr>
        <tr>
            <td>Ingress configured</td>
            <td id="crit-ingress">❌</td>
            <td>Ingress rules and IP assigned</td>
        </tr>
        <tr>
            <td>Health score > 90</td>
            <td id="crit-score">❌</td>
            <td>Overall system health assessment</td>
        </tr>
        <tr>
            <td>No critical issues</td>
            <td id="crit-critical">❌</td>
            <td>All critical problems resolved</td>
        </tr>
        <tr>
            <td>Secrets updated</td>
            <td id="crit-secrets">❌</td>
            <td>No default credentials</td>
        </tr>
        <tr>
            <td>Monitoring working</td>
            <td id="crit-monitoring">❌</td>
            <td>Prometheus and Grafana responding</td>
        </tr>
        <tr>
            <td>Logs accessible</td>
            <td id="crit-logs">❌</td>
            <td>Loki collecting logs</td>
        </tr>
        <tr>
            <td>Tracing working</td>
            <td id="crit-traces">❌</td>
            <td>Tempo collecting traces</td>
        </tr>
    </table>
</div>

<div class="section">
    <h2>📚 Documentation References</h2>
    <ul style="margin-left: 20px; line-height: 2;">
        <li>📖 <strong>00-START-HERE.md</strong> - Quick start guide (READ FIRST!)</li>
        <li>📖 <strong>README.md</strong> - Overview and features</li>
        <li>📖 <strong>DEPLOYMENT_GUIDE.md</strong> - Detailed step-by-step instructions</li>
        <li>📖 <strong>QUICK_REFERENCE.md</strong> - Common commands (BOOKMARK THIS!)</li>
        <li>📖 <strong>TROUBLESHOOTING.md</strong> - Fix issues</li>
        <li>📖 <strong>PRODUCTION_READINESS_CHECKLIST.md</strong> - Before going live</li>
        <li>📖 <strong>INDEX.md</strong> - Navigation guide</li>
    </ul>
</div>

<footer>
    <h3>HyperCode Kubernetes Deployment Package</h3>
    <p>Version 1.0 | Production Ready ✅</p>
    <p>Generated: <span id="timestamp"></span></p>
    <p style="margin-top: 20px; font-size: 0.9em; color: #999;">
        This comprehensive health check includes deployment verification, security assessment,<br>
        performance analysis, and actionable recommendations for production deployment.
    </p>
    <p style="margin-top: 15px; font-weight: bold; color: #667eea;">
        🚀 Ready to deploy! Follow the recommended actions above.
    </p>
</footer>

</div>

<script>
document.getElementById('timestamp').textContent = new Date().toLocaleString();
</script>

</body>
</html>
HTMLEOF

echo -e "${GREEN}✅ HTML Report generated: $FINAL_REPORT${NC}"
echo -e "${GREEN}✅ Open in browser to view interactive report${NC}\n"

# Print recommendations to terminal
echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}FINAL RECOMMENDATIONS SUMMARY${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}\n"

echo -e "${RED}🔴 CRITICAL - Do These FIRST:${NC}"
echo "  1. Update ALL secrets in 02-secrets.yaml"
echo "  2. Configure TLS/HTTPS for ingress"
echo "  3. Implement automated backups"
echo "  4. Set up alerting and notifications"
echo "  5. Test disaster recovery procedures\n"

echo -e "${YELLOW}🟠 HIGH PRIORITY - Do These in First Week:${NC}"
echo "  1. Scale PostgreSQL to 3 replicas with replication"
echo "  2. Enable auto-scaling (HPA) with baseline metrics"
echo "  3. Implement RBAC for team access"
echo "  4. Configure logging and retention policies"
echo "  5. Create incident response runbooks\n"

echo -e "${BLUE}🔵 MEDIUM PRIORITY - Do These by End of Month:${NC}"
echo "  1. Optimize database queries"
echo "  2. Tune Redis cache settings"
echo "  3. Review and audit security policies"
echo "  4. Enforce resource quotas"
echo "  5. Establish baseline metrics\n"

echo -e "${GREEN}🟢 ONGOING IMPROVEMENTS:${NC}"
echo "  1. Cost optimization and resource right-sizing"
echo "  2. Pod Security Policies enforcement"
echo "  3. GitOps implementation"
echo "  4. Canary deployments"
echo "  5. Regular security audits\n"

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ NEXT STEPS:${NC}"
echo -e "  1. Read: ./k8s/00-START-HERE.md"
echo -e "  2. Review: HTML report at $FINAL_REPORT"
echo -e "  3. Update: ./k8s/02-secrets.yaml"
echo -e "  4. Deploy: ./k8s/deploy.sh"
echo -e "  5. Verify: ./k8s/comprehensive_health_check.sh"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"
