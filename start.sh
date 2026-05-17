#!/bin/bash
set -e

echo "================================"
echo "  ProTrade Stock Analysis"
echo "================================"
echo ""

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "Docker is not running. Please start Docker first."
    exit 1
fi

echo "Building and starting services..."
docker-compose up --build -d

echo ""
echo "Services started!"
echo ""
echo "Frontend: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo "Health:   http://localhost:8000/health"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop:      docker-compose down"
