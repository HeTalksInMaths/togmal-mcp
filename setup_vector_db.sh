#!/bin/bash
# Setup script for Benchmark Vector Database
# Run this to install dependencies and build the database

set -e

echo "=================================================="
echo "ToGMAL Vector Database Setup"
echo "=================================================="

# Navigate to project directory
cd /Users/hetalksinmaths/togmal

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
uv pip install sentence-transformers chromadb datasets

# Build the vector database
echo "Building vector database (this may take 5-10 minutes)..."
python benchmark_vector_db.py

echo ""
echo "=================================================="
echo "Setup complete!"
echo "=================================================="
echo ""
echo "Test the vector DB with:"
echo "  python -c \"from benchmark_vector_db import BenchmarkVectorDB; db = BenchmarkVectorDB(); print(db.get_statistics())\""
echo ""
echo "The MCP tool 'togmal_check_prompt_difficulty' is now available!"
