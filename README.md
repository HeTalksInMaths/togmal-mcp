---
title: Togmal Demo
emoji: 🧠
colorFrom: yellow
colorTo: purple
sdk: gradio
sdk_version: 5.42.0
app_file: app.py
pinned: false
license: apache-2.0
short_description: Prompt difficulty predictor using vector similarity
---

# 🧠 ToGMAL Prompt Difficulty Analyzer

**Taxonomy of Generative Model Apparent Limitations** - Real-time difficulty assessment for LLM prompts.

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

## Technology

- **Vector Database**: ChromaDB with persistent storage
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **Frontend**: Gradio
- **Data**: Real benchmark questions with ground-truth success rates

## Repository

Full source code: [github.com/HeTalksInMaths/togmal-mcp](https://github.com/HeTalksInMaths/togmal-mcp)
