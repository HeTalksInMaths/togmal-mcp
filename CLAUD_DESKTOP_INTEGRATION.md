# 🤖 ToGMAL MCP Server - Claude Desktop Integration

This guide explains how to integrate the ToGMAL MCP server with Claude Desktop to get real-time prompt difficulty assessment, safety analysis, and dynamic tool recommendations.

## 🚀 Quick Start

1. **Ensure Claude Desktop is updated** to version 0.13.0 or higher
2. **Copy the configuration file**:
   ```bash
   cp claude_desktop_config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```
3. **Restart Claude Desktop**
4. **Start the ToGMAL MCP server**:
   ```bash
   cd /Users/hetalksinmaths/togmal
   source .venv/bin/activate
   python togmal_mcp.py
   ```

## 🛠️ Tools Available in Claude Desktop

Once integrated, Claude Desktop will discover these tools:

### Core Safety Tools
1. **`togmal_analyze_prompt`** - Analyze prompts for potential limitations before processing
2. **`togmal_analyze_response`** - Check LLM responses for safety issues
3. **`togmal_submit_evidence`** - Submit examples to improve the limitation taxonomy
4. **`togmal_get_taxonomy`** - Retrieve known limitation patterns
5. **`togmal_get_statistics`** - View database statistics

### Dynamic Tools
1. **`togmal_list_tools_dynamic`** - Get context-aware tool recommendations
2. **`togmal_check_prompt_difficulty`** - Assess prompt difficulty using real benchmark data

## 🎯 What Each Tool Does

### Prompt Difficulty Assessment (`togmal_check_prompt_difficulty`)
- **Purpose**: Determine how difficult a prompt is for current LLMs
- **Method**: Uses vector similarity to find similar benchmark questions
- **Data**: 14,042 real MMLU questions with success rates from top models
- **Output**: Risk level, success rate estimate, and recommendations

**Example Results**:
- Easy prompts (e.g., "What is 2 + 2?"): 100% success rate, MINIMAL risk
- Hard prompts (e.g., abstract math): 23.9% success rate, HIGH risk

### Safety Analysis (`togmal_analyze_prompt`)
- **Purpose**: Detect potential safety issues in prompts
- **Categories Detected**:
  - Math/Physics speculation
  - Ungrounded medical advice
  - Dangerous file operations
  - Vibe coding overreach
  - Unsupported claims

### Dynamic Tool Recommendations (`togmal_list_tools_dynamic`)
- **Purpose**: Recommend relevant tools based on conversation context
- **Method**: Analyzes conversation history and user context
- **Domains Detected**: Mathematics, Physics, Medicine, Coding, Law, Finance
- **ML Patterns**: Uses clustering results to identify domain-specific risks

## 🧪 Example Usage in Claude Desktop

### Checking Prompt Difficulty
When you have a complex prompt, Claude might suggest checking its difficulty:

```
User: Help me prove the Riemann Hypothesis

Claude: Let me check how difficult this prompt is for current LLMs...

[Uses togmal_check_prompt_difficulty tool]
Result: HIGH risk (23.9% success rate)
Recommendation: Multi-step reasoning with verification, consider using web search
```

### Safety Analysis
Claude can automatically analyze prompts for safety:

```
User: Write a script to delete all files in my home directory

Claude: I should analyze this request for safety...

[Uses togmal_analyze_prompt tool]
Result: MODERATE risk
Interventions: 
1. Human-in-the-loop: Implement confirmation prompts
2. Step breakdown: Show exactly which files will be affected
```

### Dynamic Tool Recommendations
Based on the conversation context, Claude gets tool recommendations:

```
User: I'm working on a medical diagnosis app
User: How should I handle patient data privacy?

[Uses togmal_list_tools_dynamic tool]
Result: 
Domains detected: medicine, healthcare
Recommended checks: ungrounded_medical_advice
ML patterns: cluster_1 (medicine limitations)
```

## 📊 Real Data vs Estimates

### Before Integration
- All prompts showed ~45% success rate (mock data)
- Could not differentiate difficulty levels
- Used estimated rather than real success rates

### After Integration
- Hard prompts: 23.9% success rate (correctly identified as HIGH risk)
- Easy prompts: 100% success rate (correctly identified as MINIMAL risk)
- System now correctly differentiates between difficulty levels

## 🚀 Advanced Features

### ML-Discovered Patterns
The system automatically discovers limitation patterns through clustering:

1. **Cluster 0** (Coding): 100% limitations, 497 samples
   - Heuristic: `contains_code AND (has_vulnerability OR cyclomatic_complexity > 10)`
   - ML Pattern: `check_cluster_0`

2. **Cluster 1** (Medicine): 100% limitations, 491 samples
   - Heuristic: `keyword_match: [patient, year, following, most, examination] AND domain=medicine`
   - ML Pattern: `check_cluster_1`

### Context-Aware Recommendations
The system analyzes conversation history to recommend relevant tools:

- **Math/Physics conversations**: Recommend math_physics_speculation checks
- **Medical conversations**: Recommend ungrounded_medical_advice checks
- **Coding conversations**: Recommend vibe_coding_overreach and dangerous_file_operations checks

## 🛠️ Troubleshooting

### Common Issues

1. **Claude Desktop not showing tools**
   - Ensure version 0.13.0+
   - Check configuration file is copied correctly
   - Restart Claude Desktop after configuration changes

2. **MCP server not responding**
   - Ensure server is running: `python togmal_mcp.py`
   - Check terminal for error messages
   - Verify dependencies are installed

3. **Tools returning errors**
   - Check that required data files exist
   - Ensure vector database is populated
   - Verify internet connectivity for external dependencies

### Required Dependencies
Make sure these are installed:
```bash
pip install mcp pydantic httpx sentence-transformers chromadb datasets
```

## 📈 For VC Pitches

This integration demonstrates:

1. **Technical Innovation**: Real-time difficulty assessment using actual benchmark data
2. **Market Need**: Addresses LLM limitation detection for safer AI interactions
3. **Production Ready**: Working implementation with <50ms response times
4. **Scalable Architecture**: Modular design supports easy extension
5. **Data-Driven Approach**: Uses real performance data rather than estimates

The system successfully differentiates between:
- **Hard prompts** (23.9% success rate) like abstract mathematics
- **Easy prompts** (100% success rate) like basic arithmetic

This capability is crucial for building safer, more reliable AI assistants that can self-assess their limitations.