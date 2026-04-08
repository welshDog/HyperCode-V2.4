"""
MintMe blockchain integration and web dashboard for community management.
"""
from typing import Dict, Optional

import aiohttp
from flask import Flask, jsonify, render_template, request
from prometheus_client import Counter, Gauge

from src.config.logging import get_logger
from src.config.settings import settings

logger = get_logger(__name__)

# Prometheus metrics
MINTME_API_CALLS = Counter(
    "mintme_api_calls_total",
    "Total MintMe API calls",
    ["endpoint", "status"],
)
TOKEN_CONVERSIONS = Counter(
    "token_conversions_total",
    "Total token conversions",
    ["direction"],
)
ACTIVE_USERS = Gauge("active_community_users", "Currently active community users")


# ============================================================================
# MintMe API Client
# ============================================================================

class MintMeAPIClient:
    """
    Client for interacting with MintMe.com blockchain API.
    
    Handles wallet operations, token transfers, and blockchain verification.
    """
    
    BASE_URL = "https://www.mintme.com/api"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        wallet_address: Optional[str] = None,
    ) -> None:
        """
        Initialize MintMe API client.
        
        Args:
            api_key: MintMe API key (if available)
            wallet_address: Bot's wallet address
        """
        self.api_key = api_key
        self.wallet_address = wallet_address
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Create aiohttp session."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close aiohttp session."""
        if self.session:
            await self.session.close()
    
    async def get_token_balance(self, wallet_address: str, token_symbol: str = "BROski") -> float:
        """
        Get token balance for a wallet.
        
        Args:
            wallet_address: Wallet address to check
            token_symbol: Token symbol
            
        Returns:
            Token balance
        """
        try:
            # Placeholder - actual MintMe API endpoint would be used
            endpoint = f"/wallet/{wallet_address}/balance/{token_symbol}"
            
            async with self.session.get(f"{self.BASE_URL}{endpoint}") as response:
                MINTME_API_CALLS.labels(endpoint=endpoint, status=response.status).inc()
                
                if response.status == 200:
                    data = await response.json()
                    return float(data.get("balance", 0))
                else:
                    logger.error(
                        "Failed to get token balance",
                        status=response.status,
                        wallet=wallet_address,
                    )
                    return 0.0
        
        except Exception as e:
            logger.error("Token balance request failed", error=str(e), exc_info=True)
            return 0.0
    
    async def transfer_tokens(
        self,
        to_address: str,
        amount: float,
        token_symbol: str = "BROski",
    ) -> Optional[str]:
        """
        Transfer tokens to another wallet.
        
        Args:
            to_address: Recipient wallet address
            amount: Amount to transfer
            token_symbol: Token symbol
            
        Returns:
            Transaction hash or None if failed
        """
        try:
            endpoint = "/transfer"
            payload = {
                "from": self.wallet_address,
                "to": to_address,
                "amount": amount,
                "token": token_symbol,
                "api_key": self.api_key,
            }
            
            async with self.session.post(
                f"{self.BASE_URL}{endpoint}",
                json=payload,
            ) as response:
                MINTME_API_CALLS.labels(endpoint=endpoint, status=response.status).inc()
                
                if response.status == 200:
                    data = await response.json()
                    tx_hash = data.get("transaction_hash")
                    
                    TOKEN_CONVERSIONS.labels(direction="to_blockchain").inc()
                    
                    logger.info(
                        "Token transfer successful",
                        to_address=to_address,
                        amount=amount,
                        tx_hash=tx_hash,
                    )
                    
                    return tx_hash
                else:
                    logger.error(
                        "Token transfer failed",
                        status=response.status,
                        to_address=to_address,
                    )
                    return None
        
        except Exception as e:
            logger.error("Token transfer request failed", error=str(e), exc_info=True)
            return None
    
    async def verify_transaction(self, tx_hash: str) -> bool:
        """
        Verify a blockchain transaction.
        
        Args:
            tx_hash: Transaction hash
            
        Returns:
            True if transaction is confirmed
        """
        try:
            endpoint = f"/transaction/{tx_hash}"
            
            async with self.session.get(f"{self.BASE_URL}{endpoint}") as response:
                MINTME_API_CALLS.labels(endpoint=endpoint, status=response.status).inc()
                
                if response.status == 200:
                    data = await response.json()
                    return data.get("confirmed", False)
                else:
                    return False
        
        except Exception as e:
            logger.error("Transaction verification failed", error=str(e))
            return False
    
    async def get_token_info(self, token_symbol: str = "BROski") -> Dict[str, any]:
        """
        Get information about a token.
        
        Args:
            token_symbol: Token symbol
            
        Returns:
            Token information dictionary
        """
        try:
            endpoint = f"/token/{token_symbol}"
            
            async with self.session.get(f"{self.BASE_URL}{endpoint}") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {}
        
        except Exception as e:
            logger.error("Token info request failed", error=str(e))
            return {}


# ============================================================================
# Community Dashboard (Flask)
# ============================================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = settings.secret_key


@app.route('/')
def dashboard():
    """Main dashboard view."""
    return render_template('dashboard.html')


@app.route('/api/stats/overview')
async def api_stats_overview():
    """Get overview statistics."""
    # This would query the database for actual stats
    # Placeholder data for demonstration
    return jsonify({
        "active_users_24h": 142,
        "total_contributions_24h": 387,
        "tokens_distributed_24h": 12450,
        "tokens_converted_24h": 3000,
        "avg_contribution_quality": 1.85,
        "community_sentiment": "positive",
        "top_contributors": [
            {"user_id": 123, "username": "TopBROski", "tokens": 1250},
            {"user_id": 456, "username": "HelpfulBRO", "tokens": 980},
            {"user_id": 789, "username": "CodeMaster", "tokens": 875},
        ],
    })


@app.route('/api/stats/contributions')
async def api_stats_contributions():
    """Get contribution statistics."""
    return jsonify({
        "by_type": {
            "answering_question": 125,
            "creating_content": 45,
            "helping_newcomer": 89,
            "code_contribution": 12,
            "moderating": 34,
            "other": 82,
        },
        "by_hour": [
            {"hour": "00:00", "count": 12},
            {"hour": "01:00", "count": 8},
            {"hour": "02:00", "count": 5},
            # ... 24 hours
        ],
        "quality_distribution": {
            "1.0-1.5": 120,
            "1.5-2.0": 180,
            "2.0-2.5": 65,
            "2.5-3.0": 22,
        },
    })


@app.route('/api/stats/tokens')
async def api_stats_tokens():
    """Get token flow statistics."""
    return jsonify({
        "total_supply_internal": 1245000,
        "total_distributed": 987500,
        "total_converted": 125000,
        "conversion_rate": 12.7,  # percentage
        "distribution_by_source": {
            "contributions": 750000,
            "daily_rewards": 150000,
            "focus_sessions": 87500,
        },
        "top_earners": [
            {"user_id": 123, "earned": 15000},
            {"user_id": 456, "earned": 12500},
            {"user_id": 789, "earned": 11200},
        ],
    })


@app.route('/api/user/<int:user_id>/profile')
async def api_user_profile(user_id: int):
    """Get user profile with contribution history."""
    # Placeholder data
    return jsonify({
        "user_id": user_id,
        "username": "ExampleUser",
        "reputation_score": 78,
        "reputation_tier": "⭐ Gold BROski",
        "total_contributions": 145,
        "total_earned": 8750,
        "total_converted": 2000,
        "average_quality": 1.92,
        "streak_days": 14,
        "achievements": [
            "Helpful Helper",
            "Code Contributor",
            "Content Creator",
        ],
        "recent_contributions": [
            {
                "type": "answering_question",
                "reward": 45,
                "timestamp": "2025-03-03T10:30:00Z",
            },
            {
                "type": "helping_newcomer",
                "reward": 60,
                "timestamp": "2025-03-03T08:15:00Z",
            },
        ],
    })


@app.route('/api/leaderboard/<string:metric>')
async def api_leaderboard(metric: str):
    """Get leaderboard by metric."""
    # Placeholder data
    leaderboard = [
        {"rank": 1, "user_id": 123, "username": "TopBROski", "value": 15000},
        {"rank": 2, "user_id": 456, "username": "HelpfulBRO", "value": 12500},
        {"rank": 3, "user_id": 789, "username": "CodeMaster", "value": 11200},
        {"rank": 4, "user_id": 101, "username": "ContentKing", "value": 9800},
        {"rank": 5, "user_id": 112, "username": "ModSquad", "value": 8500},
    ]
    
    return jsonify({
        "metric": metric,
        "leaderboard": leaderboard,
    })


@app.route('/api/conversion/estimate', methods=['POST'])
async def api_conversion_estimate():
    """Estimate token conversion."""
    data = request.json
    internal_amount = data.get('amount', 0)
    
    mintme_tokens = internal_amount / 1000  # Conversion rate
    
    return jsonify({
        "internal_amount": internal_amount,
        "mintme_tokens": mintme_tokens,
        "conversion_rate": 1000,
        "estimated_gas_fee": 0.001,  # Placeholder
        "estimated_time": "5-10 minutes",
    })


@app.route('/api/analytics/community-health')
async def api_community_health():
    """Get community health metrics."""
    return jsonify({
        "health_score": 85,
        "status": "Healthy",
        "metrics": {
            "engagement_rate": 78.5,
            "response_time_avg": "4.2 minutes",
            "question_answer_rate": 92.3,
            "sentiment_positive": 81.2,
            "sentiment_neutral": 15.3,
            "sentiment_negative": 3.5,
            "new_member_retention": 67.8,
        },
        "trends": {
            "engagement": "increasing",
            "contributions": "stable",
            "sentiment": "improving",
        },
    })


@app.route('/api/ai/insights')
async def api_ai_insights():
    """Get AI-generated insights about community."""
    return jsonify({
        "insights": [
            {
                "type": "trend",
                "title": "Increasing Code Contributions",
                "description": "Code contributions have increased 35% this week, primarily driven by 3 active developers.",
                "confidence": 0.92,
            },
            {
                "type": "opportunity",
                "title": "New Members Need Support",
                "description": "15 new members joined in the last 24h. Consider organizing a welcome event.",
                "confidence": 0.88,
            },
            {
                "type": "pattern",
                "title": "Peak Activity Hours",
                "description": "Most activity occurs between 14:00-18:00 UTC. Schedule important announcements accordingly.",
                "confidence": 0.95,
            },
        ],
        "recommendations": [
            "Consider increasing rewards for newcomer assistance",
            "Create a #code-contributions channel",
            "Host a weekly community event",
        ],
    })


# ============================================================================
# Dashboard HTML Template (Base Structure)
# ============================================================================

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BROski Community Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            min-height: 100vh;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        header {
            background: rgba(255,255,255,0.95);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        h1 { color: #667eea; margin-bottom: 10px; }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .stat-value {
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
        }
        .stat-label {
            color: #666;
            margin-top: 5px;
        }
        .chart-container {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .leaderboard {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .leaderboard-item {
            display: flex;
            justify-content: space-between;
            padding: 15px;
            border-bottom: 1px solid #eee;
        }
        .rank { font-weight: bold; color: #667eea; }
        .medal { font-size: 1.5em; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🐶 BROski Community Dashboard</h1>
            <p>Real-time community analytics and token distribution</p>
        </header>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value" id="active-users">-</div>
                <div class="stat-label">Active Users (24h)</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="contributions">-</div>
                <div class="stat-label">Contributions</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="tokens-distributed">-</div>
                <div class="stat-label">BROski$ Distributed</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="avg-quality">-</div>
                <div class="stat-label">Avg Quality</div>
            </div>
        </div>
        
        <div class="chart-container">
            <h2>Contribution Distribution</h2>
            <canvas id="contributionChart"></canvas>
        </div>
        
        <div class="leaderboard">
            <h2>🏆 Top Contributors</h2>
            <div id="leaderboard-list"></div>
        </div>
    </div>
    
    <script>
        // Fetch and display real-time stats
        async function updateStats() {
            const response = await fetch('/api/stats/overview');
            const data = await response.json();
            
            document.getElementById('active-users').textContent = data.active_users_24h;
            document.getElementById('contributions').textContent = data.total_contributions_24h;
            document.getElementById('tokens-distributed').textContent = data.tokens_distributed_24h.toLocaleString();
            document.getElementById('avg-quality').textContent = data.avg_contribution_quality.toFixed(2);
            
            // Update leaderboard
            const leaderboardHtml = data.top_contributors.map((user, idx) => `
                <div class="leaderboard-item">
                    <div>
                        <span class="rank">#${idx + 1}</span>
                        <span class="medal">${['🥇','🥈','🥉'][idx] || '▫️'}</span>
                        ${user.username}
                    </div>
                    <div><strong>${user.tokens.toLocaleString()}</strong> BROski$</div>
                </div>
            `).join('');
            
            document.getElementById('leaderboard-list').innerHTML = leaderboardHtml;
        }
        
        // Initialize chart
        async function initChart() {
            const response = await fetch('/api/stats/contributions');
            const data = await response.json();
            
            const ctx = document.getElementById('contributionChart').getContext('2d');
            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: Object.keys(data.by_type).map(k => k.replace('_', ' ')),
                    datasets: [{
                        label: 'Contributions',
                        data: Object.values(data.by_type),
                        backgroundColor: 'rgba(102, 126, 234, 0.6)',
                        borderColor: 'rgba(102, 126, 234, 1)',
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });
        }
        
        // Initialize
        updateStats();
        initChart();
        
        // Update every 30 seconds
        setInterval(updateStats, 30000);
    </script>
</body>
</html>
"""


def run_dashboard(host: str = '0.0.0.0', port: int = 5000):
    """Run the dashboard web server."""
    logger.info(f"Starting community dashboard on {host}:{port}")
    app.run(host=host, port=port, debug=settings.debug)


if __name__ == '__main__':
    run_dashboard()
