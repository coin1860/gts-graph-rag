#!/bin/bash

# GTS Graph RAG Cleanup Script

echo "WARNING: This script will delete ALL data, including:"
echo " - Uploaded documents (data/uploads)"
echo " - ChromaDB vector store (data/chroma)"
echo " - SQLite database (data/app.db)"
echo " - Neo4j database content"
echo ""
echo "Press Ctrl+C to cancel or wait 5 seconds to proceed..."
sleep 5

echo "Stopping any potential background processes..."
# Optional: find and kill server if needed, but best left to user control usually.

echo "🗑️  Cleaning up file storage..."
rm -rf data/uploads/*
echo "✅ Uploads cleared."

echo "🗑️  Cleaning up ChromaDB..."
rm -rf data/chroma
mkdir -p data/chroma
echo "✅ ChromaDB cleared."

echo "🗑️  Cleaning up SQLite Database..."
rm -f data/app.db
echo "✅ Database deleted (will be recreated on restart)."

echo "🗑️  Cleaning up Neo4j..."
# Use uv run to ensure dependencies are available
uv run python wipe_neo4j.py

echo "👤 Re-creating Admin User..."
uv run python reset_admin_password.py

echo ""
echo "✨ Cleanup complete!"
echo "   Run: uv run python -m backend.server"
