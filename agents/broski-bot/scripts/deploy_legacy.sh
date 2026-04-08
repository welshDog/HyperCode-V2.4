#!/bin/bash
# ============================================================================
# BROski Bot v4.0 - Community Management System
# Automated Deployment & Setup Scripts
# ============================================================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# Makefile for Quick Commands
# ============================================================================
cat > Makefile << 'EOF'
.PHONY: help setup install test run deploy clean

help:
	@echo "BROski Bot v4.0 - Community Management System"
	@echo "=============================================="
	@echo ""
	@echo "Quick Start:"
	@echo "  make setup              - Complete setup (recommended)"
	@echo "  make install            - Install dependencies only"
	@echo "  make test               - Run all tests"
	@echo "  make run                - Start bot locally"
	@echo "  make dashboard          - Start web dashboard"
	@echo ""
	@echo "Development:"
	@echo "  make lint               - Run code quality checks"
	@echo "  make format             - Format code"
	@echo "  make migrate            - Run database migrations"
	@echo "  make analyze-code       - Run AI code analysis"
	@echo ""
	@echo "Deployment:"
	@echo "  make docker-build       - Build Docker images"
	@echo "  make docker-up          - Start full Docker stack"
	@echo "  make deploy-prod        - Deploy to production"
	@echo ""
	@echo "Community Features:"
	@echo "  make test-community     - Test community features"
	@echo "  make test-tokens        - Test token distribution"
	@echo "  make test-ai            - Test AI classifier"
	@echo "  make generate-report    - Generate analytics report"
	@echo ""
	@echo "Maintenance:"
	@echo "  make backup             - Backup database"
	@echo "  make clean              - Clean build artifacts"
	@echo "  make logs               - View application logs"

setup:
	@echo "🚀 Setting up BROski Bot Community System..."
	@./scripts/setup_community_system.sh

install:
	@echo "📦 Installing dependencies..."
	poetry install
	poetry run pre-commit install
	@echo "✅ Dependencies installed"

test:
	@echo "🧪 Running tests..."
	poetry run pytest tests/ -v --cov=src --cov-report=html
	@echo "📊 Coverage report: htmlcov/index.html"

run:
	@echo "🤖 Starting BROski Bot..."
	poetry run python -m src.main

dashboard:
	@echo "📊 Starting web dashboard..."
	cd src/dashboard && poetry run python app.py

lint:
	@echo "🔍 Running linters..."
	poetry run black --check src/ tests/
	poetry run isort --check-only src/ tests/
	poetry run flake8 src/ tests/
	poetry run mypy src/
	poetry run bandit -r src/

format:
	@echo "✨ Formatting code..."
	poetry run black src/ tests/
	poetry run isort src/ tests/

migrate:
	@echo "🗄️ Running database migrations..."
	poetry run alembic upgrade head

analyze-code:
	@echo "🤖 Running AI code analysis..."
	poetry run python scripts/analyze_codebase.py

docker-build:
	@echo "🐳 Building Docker images..."
	docker-compose build

docker-up:
	@echo "🐳 Starting Docker stack..."
	docker-compose up -d
	@echo "✅ Services started:"
	@echo "  - Bot: Running"
	@echo "  - Dashboard: http://localhost:5000"
	@echo "  - Prometheus: http://localhost:9090"
	@echo "  - Grafana: http://localhost:3000"
	docker-compose logs -f broski-bot

deploy-prod:
	@echo "🚀 Deploying to production..."
	@./scripts/deploy_production.sh

test-community:
	@echo "🧪 Testing community features..."
	poetry run pytest tests/unit/test_community_service.py -v
	poetry run pytest tests/integration/test_contribution_flow.py -v

test-tokens:
	@echo "🪙 Testing token distribution..."
	poetry run pytest tests/unit/test_token_distribution.py -v

test-ai:
	@echo "🤖 Testing AI classifier..."
	poetry run pytest tests/unit/test_ai_classifier.py -v

generate-report:
	@echo "📊 Generating analytics report..."
	poetry run python scripts/generate_reports.py

backup:
	@echo "💾 Creating database backup..."
	poetry run python scripts/backup.sh

clean:
	@echo "🧹 Cleaning build artifacts..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov/ dist/ build/
	@echo "✅ Cleaned"

logs:
	@echo "📄 Viewing logs..."
	docker-compose logs -f broski-bot
EOF

# ============================================================================
# Setup Script
# ============================================================================
cat > scripts/setup_community_system.sh << 'EOF'
#!/bin/bash
set -e

echo "╔════════════════════════════════════════════════════════╗"
echo "║  BROski Bot v4.0 - Community System Setup             ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Check prerequisites
echo "🔍 Checking prerequisites..."

command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3.11+ required"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "⚠️  Docker recommended but not required"; }
command -v psql >/dev/null 2>&1 || { echo "⚠️  PostgreSQL recommended but not required"; }

echo "✅ Prerequisites check complete"
echo ""

# Install Poetry
echo "📦 Installing Poetry..."
if ! command -v poetry &> /dev/null; then
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
fi
echo "✅ Poetry installed"
echo ""

# Install dependencies
echo "📦 Installing Python dependencies..."
poetry install
echo "✅ Dependencies installed"
echo ""

# Create directories
echo "📁 Creating directory structure..."
mkdir -p src/{ai,integrations/mintme,dashboard,services/community}
mkdir -p tests/{unit,integration,e2e}
mkdir -p scripts docs monitoring
echo "✅ Directories created"
echo ""

# Copy environment template
echo "⚙️  Setting up environment configuration..."
if [ ! -f .env ]; then
    cat > .env << 'ENVFILE'
# Application
APP_NAME=BROski-Bot
ENVIRONMENT=development
DEBUG=true

# Discord
DISCORD_TOKEN=paste_your_token_here
DISCORD_OWNER_IDS=

# Database
DATABASE_URL=postgresql+asyncpg://broski:broski@localhost:5432/broski_community

# Redis
REDIS_URL=redis://localhost:6379

# AI Features
AI_CLASSIFIER_ENABLED=true
AI_CLASSIFIER_CONFIDENCE=0.75

# Token System
TOKEN_CONVERSION_ENABLED=true
MINTME_CONVERSION_RATE=1000

# Dashboard
DASHBOARD_ENABLED=true
DASHBOARD_PORT=5000

# Monitoring
PROMETHEUS_ENABLED=true
SENTRY_DSN=
ENVFILE
    echo "✅ Environment file created: .env"
    echo "⚠️  IMPORTANT: Edit .env and add your Discord bot token!"
else
    echo "✅ Environment file already exists"
fi
echo ""

# Setup database
echo "🗄️  Setting up database..."
if command -v docker-compose &> /dev/null; then
    echo "Starting PostgreSQL with Docker..."
    docker-compose up -d postgres redis
    sleep 5
    echo "✅ Database containers started"
else
    echo "⚠️  Docker not available. Please set up PostgreSQL manually."
    echo "   Database name: broski_community"
    echo "   User: broski"
    echo "   Password: broski"
fi
echo ""

# Run migrations
echo "🗄️  Running database migrations..."
if [ -f alembic.ini ]; then
    poetry run alembic upgrade head
    echo "✅ Migrations complete"
else
    echo "⚠️  Alembic not configured yet. Run 'alembic init migrations' first."
fi
echo ""

# Install pre-commit hooks
echo "🔧 Installing pre-commit hooks..."
poetry run pre-commit install
echo "✅ Git hooks installed"
echo ""

# Run initial code analysis
echo "🤖 Running AI code analysis..."
poetry run python scripts/analyze_codebase.py . || true
echo ""

# Final instructions
echo "╔════════════════════════════════════════════════════════╗"
echo "║  Setup Complete! 🎉                                    ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo ""
echo "1. Edit .env file:"
echo "   nano .env"
echo "   (Add your Discord bot token)"
echo ""
echo "2. Start the bot:"
echo "   make run"
echo ""
echo "3. Start the dashboard:"
echo "   make dashboard"
echo "   (Access at http://localhost:5000)"
echo ""
echo "4. Run tests:"
echo "   make test"
echo ""
echo "5. View full documentation:"
echo "   cat README.md"
echo ""
echo "For help:"
echo "   make help"
echo ""
EOF

chmod +x scripts/setup_community_system.sh

# ============================================================================
# Production Deployment Script
# ============================================================================
cat > scripts/deploy_production.sh << 'EOF'
#!/bin/bash
set -e

echo "🚀 BROski Bot - Production Deployment"
echo "======================================"
echo ""

# Safety check
read -p "Deploy to PRODUCTION? This will affect live users. (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "❌ Deployment cancelled"
    exit 1
fi

# Pre-deployment checks
echo "🔍 Running pre-deployment checks..."

# 1. Tests must pass
echo "  → Running tests..."
poetry run pytest tests/ -v --cov-fail-under=80 || {
    echo "❌ Tests failed! Fix tests before deploying."
    exit 1
}
echo "  ✅ All tests passed"

# 2. Linting must pass
echo "  → Running linters..."
poetry run black --check src/ || {
    echo "❌ Code formatting issues! Run 'make format' first."
    exit 1
}
echo "  ✅ Code quality checks passed"

# 3. Security scan
echo "  → Running security scan..."
poetry run bandit -r src/ || {
    echo "⚠️  Security issues found! Review and fix."
}

# 4. Database backup
echo "  → Creating database backup..."
BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"
pg_dump $DATABASE_URL > backups/$BACKUP_FILE || {
    echo "❌ Backup failed!"
    exit 1
}
echo "  ✅ Backup created: $BACKUP_FILE"

# Build Docker images
echo "🐳 Building Docker images..."
docker-compose build --no-cache

# Tag with version
VERSION=$(poetry version -s)
docker tag broski-bot:latest broski-bot:$VERSION

# Push to registry (if configured)
# docker push broski-bot:$VERSION

# Deploy
echo "🚀 Deploying..."
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Health check
docker-compose ps | grep "healthy" || {
    echo "⚠️  Some services may not be healthy. Check logs:"
    echo "    docker-compose logs"
}

# Verify deployment
echo "✅ Checking bot status..."
curl -f http://localhost:8000/health || {
    echo "❌ Health check failed!"
    echo "Rolling back..."
    docker-compose down
    docker-compose up -d --force-recreate
    exit 1
}

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║  Deployment Successful! 🎉                             ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo "Services:"
echo "  - Bot: Running"
echo "  - Dashboard: http://your-domain:5000"
echo "  - Metrics: http://your-domain:9090"
echo ""
echo "Monitor with:"
echo "  docker-compose logs -f"
echo ""
echo "Backup saved to: backups/$BACKUP_FILE"
echo ""
EOF

chmod +x scripts/deploy_production.sh

# ============================================================================
# Code Analysis Script
# ============================================================================
cat > scripts/analyze_codebase.py << 'PYTHON'
#!/usr/bin/env python3
"""
Automated codebase analysis script.
Runs AI-powered code analysis and generates report.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai.code_analyzer import AICodeAnalyzer

def main():
    project_root = sys.argv[1] if len(sys.argv) > 1 else "."
    
    print("🤖 BROski Bot - AI Code Analysis")
    print("=" * 50)
    print(f"Analyzing: {project_root}")
    print()
    
    analyzer = AICodeAnalyzer(project_root)
    
    # Run analysis
    report_md = analyzer.generate_report_markdown()
    
    # Save report
    output_path = Path(project_root) / "CODE_ANALYSIS_REPORT.md"
    with open(output_path, 'w') as f:
        f.write(report_md)
    
    print(f"✅ Analysis complete!")
    print(f"📄 Report saved to: {output_path}")
    print()
    
    # Print summary
    report = analyzer.scan_codebase()
    print("Summary:")
    print(f"  Files analyzed: {report['total_files']}")
    print(f"  Lines of code: {report['total_loc']:,}")
    print(f"  Features detected: {report['detected_features']}")
    print(f"  New features: {report['new_features']}")
    print()
    print("View full report for detailed recommendations.")

if __name__ == "__main__":
    main()
PYTHON

chmod +x scripts/analyze_codebase.py

# ============================================================================
# Quick Test Script
# ============================================================================
cat > scripts/test_community_features.sh << 'EOF'
#!/bin/bash
# Quick test of community features

echo "🧪 Testing BROski Bot Community Features"
echo "========================================="
echo ""

# Test 1: AI Classifier
echo "1️⃣  Testing AI Contribution Classifier..."
poetry run pytest tests/unit/test_ai_classifier.py::TestAIContributionClassifier::test_classify_message -v
echo ""

# Test 2: Token Distribution
echo "2️⃣  Testing Token Distribution..."
poetry run pytest tests/unit/test_token_distribution.py::TestTokenDistributionService::test_distribute_tokens -v
echo ""

# Test 3: Community Service
echo "3️⃣  Testing Community Service..."
poetry run pytest tests/unit/test_community_service.py::TestCommunityService::test_process_contribution -v
echo ""

# Test 4: Integration Flow
echo "4️⃣  Testing End-to-End Contribution Flow..."
poetry run pytest tests/integration/test_contribution_flow.py -v
echo ""

echo "✅ All community feature tests complete!"
EOF

chmod +x scripts/test_community_features.sh

# ============================================================================
# Print Success Message
# ============================================================================

echo -e "${GREEN}"
echo "╔════════════════════════════════════════════════════════╗"
echo "║  BROski Bot v4.0 Scripts Generated! 🎉                 ║"
echo "╚════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""
echo "Generated files:"
echo "  ✅ Makefile"
echo "  ✅ scripts/setup_community_system.sh"
echo "  ✅ scripts/deploy_production.sh"
echo "  ✅ scripts/analyze_codebase.py"
echo "  ✅ scripts/test_community_features.sh"
echo ""
echo "Quick Start:"
echo "  1. make setup          # Complete automated setup"
echo "  2. Edit .env file      # Add your Discord token"
echo "  3. make run            # Start the bot"
echo ""
echo "Full documentation:"
echo "  make help"
echo ""
