---
title: ToGMAL - AI Difficulty & Safety Analysis
emoji: 🧠
colorFrom: yellow
colorTo: purple
sdk: gradio
sdk_version: 5.42.0
app_file: app_combined.py
pinned: false
license: apache-2.0
short_description: LLM difficulty analyzer with chat assistant & MCP tools
---

# 🧠 ToGMAL - Intelligent LLM Difficulty & Safety Analysis

**Taxonomy of Generative Model Apparent Limitations** - Real-time difficulty assessment and chat interface with MCP tool integration.

## 🎯 Unified Tabbed Interface

Switch seamlessly between two powerful tools:

### 📊 **Tab 1: Difficulty Analyzer**
- Direct analysis using 32K+ benchmark questions
- Instant difficulty ratings and success rates
- Vector similarity search
- Perfect for quick assessments

### 🤖 **Tab 2: Chat Assistant** 🆕
**Interactive chat where a free LLM can call MCP tools!**

- 🤖 Chat with Mistral-7B (free via HuggingFace)
- 🛠️ LLM calls tools dynamically based on context
- 📊 Transparent tool execution (see what's happening)
- 💬 Natural language responses using tool data

## Features

- 📊 **Real Benchmark Data**: Analyzes prompts against 14,042 questions from MMLU, MMLU-Pro, GPQA, and MATH datasets
- 🎯 **Vector Similarity Search**: Uses semantic embeddings to find similar benchmark questions
- 📈 **Success Rate Prediction**: Shows weighted success rates from top LLMs (Claude, GPT-4, Gemini)
- 💡 **Smart Recommendations**: Provides actionable suggestions based on difficulty level

## How It Works

1. Enter any prompt or question
2. The system finds the 5 most similar benchmark questions using vector embeddings
3. Calculates a weighted difficulty score based on how well LLMs perform on similar questions
4. Provides risk assessment and recommendations

## Example Prompts

- "Calculate the quantum correction to the partition function for a 3D harmonic oscillator"
- "Prove that there are infinitely many prime numbers"
- "Diagnose a patient with acute chest pain and shortness of breath"
- "Implement a binary search tree with insert and search operations"

## 🎯 Quick Start

### Run Combined Demo (Recommended)
```bash
python app_combined.py
```

Or run individual demos:

### Run Difficulty Analyzer Only
```bash
python app.py
```

### Run Chat Demo Only
```bash
python chat_app.py
# Or use the launcher:
./launch_chat.sh
```

**Try in the Chat tab:**
- "How difficult is this: [your prompt]?"
- "Is this safe: [your prompt]?"
- "Analyze the difficulty of: Calculate quantum corrections..."

See [`CHAT_DEMO_README.md`](CHAT_DEMO_README.md) for full documentation.

## Technology

- **Vector Database**: ChromaDB with persistent storage
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **Frontend**: Gradio
- **Data**: Real benchmark questions with ground-truth success rates

## Repository

Full source code: [github.com/HeTalksInMaths/togmal-mcp](https://github.com/HeTalksInMaths/togmal-mcp)
