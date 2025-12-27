# BOI Agentic GraphRAG System

A local, no-Docker Agentic GraphRAG system for HSBC BOI knowledge transfer. Ingests technical design documents into Neo4j (Graph) + Chroma (Vector), and uses a LangGraph agent to answer complex architectural questions with traceability.

## Quick Start

### Prerequisites
- Python 3.11+
- Neo4j Desktop or Neo4j Aura
- Node.js 18+ (for frontend)

### Backend Setup

```bash
# Install dependencies with uv
uv sync

# Copy environment template
cp .env.example .env
# Edit .env with your credentials

# Start the backend server
uv run python -m backend.server
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

## Architecture

- **Backend**: FastAPI + LangGraph + Neo4j GraphRAG
- **Frontend**: Next.js (App Router) + Vercel AI SDK
- **LLM**: Qwen-Plus (DashScope)
- **Embeddings**: text-embedding-v1 (DashScope)
- **Storage**: Neo4j (Graph) + ChromaDB (Vector)

## Project Structure

```
gts_graph_rag/
├── backend/
│   ├── models/        # LLM & embedding wrappers
│   ├── schema/        # BOI knowledge graph schema
│   ├── ingestion/     # Document ingestion pipeline
│   ├── agent/         # LangGraph workflow
│   └── server.py      # FastAPI application
├── frontend/          # Next.js App Router
├── data/chroma/       # ChromaDB persistent storage
└── pyproject.toml
```
