#!/bin/bash

# HyperCode Agent Crew - Quick Start Script
# This script helps you set up and run the agent crew

set -e

echo "🤖 HyperCode Agent Crew - Setup Script"
echo "======================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"

# Check if .env.agents exists
if [ ! -f .env.agents ]; then
    echo ""
    echo "📝 Creating .env.agents file..."
    cp .env.agents.example .env.agents
    
    echo ""
    echo "⚠️  Please edit .env.agents and add your PERPLEXITY_API_KEY"
    echo "Then run this script again."
    exit 0
fi

# Check if API key is set
if grep -q "your_PERPLEXITY_API_KEY_here" .env.agents; then
    echo ""
    echo "⚠️  Please edit .env.agents and add your PERPLEXITY_API_KEY"
    echo "The file is located at: .env.agents"
    exit 1
fi

echo "✅ Environment configuration found"

# Prompt for action
echo ""
echo "What would you like to do?"
echo "1) Build and start all agents"
echo "2) Start agents (without rebuild)"
echo "3) Stop all agents"
echo "4) View logs"
echo "5) Check agent status"
echo "6) Clean up (remove containers and volumes)"
read -p "Enter choice [1-6]: " choice

case $choice in
    1)
        echo ""
        echo "🔨 Building and starting all agents..."
        docker-compose -f docker-compose.agents.yml --env-file .env.agents build
        docker-compose -f docker-compose.agents.yml --env-file .env.agents up -d
        echo ""
        echo "✅ All agents are starting up!"
        echo "🌐 Orchestrator API: http://localhost:8080"
        echo "📊 Dashboard: http://localhost:8090"
        echo ""
        echo "Run 'docker-compose -f docker-compose.agents.yml logs -f' to view logs"
        ;;
    2)
        echo ""
        echo "▶️  Starting agents..."
        docker-compose -f docker-compose.agents.yml --env-file .env.agents up -d
        echo "✅ Agents started"
        ;;
    3)
        echo ""
        echo "⏸️  Stopping agents..."
        docker-compose -f docker-compose.agents.yml down
        echo "✅ Agents stopped"
        ;;
    4)
        echo ""
        echo "📜 Viewing logs (Ctrl+C to exit)..."
        docker-compose -f docker-compose.agents.yml logs -f
        ;;
    5)
        echo ""
        echo "🔍 Checking agent status..."
        docker-compose -f docker-compose.agents.yml ps
        echo ""
        echo "Querying orchestrator..."
        curl -s http://localhost:8080/agents/status | python3 -m json.tool
        ;;
    6)
        echo ""
        read -p "⚠️  This will remove all containers and volumes. Continue? [y/N]: " confirm
        if [[ $confirm == [yY] ]]; then
            docker-compose -f docker-compose.agents.yml down -v
            echo "✅ Cleanup complete"
        else
            echo "Cancelled"
        fi
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac
