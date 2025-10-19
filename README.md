# ToGMAL MCP Server

**Taxonomy of Generative Model Apparent Limitations**

A Model Context Protocol (MCP) server that provides real-time, privacy-preserving analysis of LLM interactions to detect out-of-distribution behaviors and recommend safety interventions.

## Overview

ToGMAL helps prevent common LLM pitfalls by detecting:

- 🔬 **Math/Physics Speculation**: Ungrounded "theories of everything" and invented physics
- 🏥 **Medical Advice Issues**: Health recommendations without proper sources or disclaimers
- 💾 **Dangerous File Operations**: Mass deletions, recursive operations without safeguards
- 💻 **Vibe Coding Overreach**: Overly ambitious projects without proper scoping
- 📊 **Unsupported Claims**: Strong assertions without evidence or hedging

## Key Features

- **Privacy-Preserving**: All analysis is deterministic and local (no external API calls)
- **Low Latency**: Heuristic-based detection for real-time analysis
- **Intervention Recommendations**: Suggests step breakdown, human-in-the-loop, or web search
- **Taxonomy Building**: Crowdsourced evidence collection for improving detection
- **Extensible**: Easy to add new detection patterns and categories

## Installation

### Prerequisites

- Python 3.10 or higher
- pip package manager

### Install Dependencies

```bash
pip install mcp pydantic httpx --break-system-packages
```

### Install the Server

```bash
# Clone or download the server
# Then run it directly
python togmal_mcp.py
```

## Usage

### Available Tools

#### 1. `togmal_analyze_prompt`

Analyze a user prompt before the LLM processes it.

**Parameters:**
- `prompt` (str): The user prompt to analyze
- `response_format` (str): Output format - `"markdown"` or `"json"`

**Example:**
```python
{
  "prompt": "Build me a complete theory of quantum gravity that unifies all forces",
  "response_format": "json"
}
```

**Use Cases:**
- Detect speculative physics theories before generating responses
- Flag overly ambitious coding requests
- Identify requests for medical advice that need disclaimers

#### 2. `togmal_analyze_response`

Analyze an LLM response for potential issues.

**Parameters:**
- `response` (str): The LLM response to analyze
- `context` (str, optional): Original prompt for better analysis
- `response_format` (str): Output format - `"json"` or `"json"`

**Example:**
```python
{
  "response": "You should definitely take 500mg of ibuprofen every 4 hours...",
  "context": "I have a headache",
  "response_format": "json"
}
```

**Use Cases:**
- Check for ungrounded medical advice
- Detect dangerous file operation instructions
- Flag unsupported statistical claims

#### 3. `togmal_submit_evidence`

Submit evidence of LLM limitations to improve the taxonomy.

**Parameters:**
- `category` (str): Type of limitation - `"math_physics_speculation"`, `"ungrounded_medical_advice"`, etc.
- `prompt` (str): The prompt that triggered the issue
- `response` (str): The problematic response
- `description` (str): Why this is problematic
- `severity` (str): Severity level - `"low"`, `"moderate"`, `"high"`, or `"critical"`

**Example:**
```python
{
  "category": "ungrounded_medical_advice",
  "prompt": "What should I do about chest pain?",
  "response": "It's probably nothing serious, just indigestion...",
  "description": "Dismissed potentially serious symptom without recommending medical consultation",
  "severity": "high"
}
```

**Features:**
- Human-in-the-loop confirmation before submission
- Generates unique entry ID for tracking
- Contributes to improving detection heuristics

#### 4. `togmal_get_taxonomy`

Retrieve entries from the taxonomy database.

**Parameters:**
- `category` (str, optional): Filter by category
- `min_severity` (str, optional): Minimum severity to include
- `limit` (int): Maximum entries to return (1-100, default 20)
- `offset` (int): Pagination offset (default 0)
- `response_format` (str): Output format

**Example:**
```python
{
  "category": "dangerous_file_operations",
  "min_severity": "high",
  "limit": 10,
  "offset": 0,
  "response_format": "json"
}
```

**Use Cases:**
- Research common LLM failure patterns
- Train improved detection models
- Generate safety guidelines

#### 5. `togmal_get_statistics`

Get statistical overview of the taxonomy database.

**Parameters:**
- `response_format` (str): Output format

**Returns:**
- Total entries by category
- Severity distribution
- Database capacity status

## Detection Heuristics

### Math/Physics Speculation

**Detects:**
- "Theory of everything" claims
- Unified field theory proposals
- Invented equations or particles
- Modifications to fundamental constants

**Patterns:**
```
- "new equation for quantum gravity"
- "my unified theory"
- "discovered particle"
- "redefine the speed of light"
```

### Ungrounded Medical Advice

**Detects:**
- Diagnoses without qualifications
- Treatment recommendations without sources
- Specific drug dosages
- Dismissive responses to symptoms

**Patterns:**
```
- "you probably have..."
- "take 500mg of..."
- "don't worry about it"
- Missing citations or disclaimers
```

### Dangerous File Operations

**Detects:**
- Mass deletion commands
- Recursive operations without safeguards
- Operations on test files without confirmation
- No human-in-the-loop for destructive actions

**Patterns:**
```
- "rm -rf" without confirmation
- "delete all test files"
- "recursively remove"
- Missing safety checks
```

### Vibe Coding Overreach

**Detects:**
- Requests for complete applications
- Massive line count targets (1000+ lines)
- Unrealistic timeframes
- Scope without proper planning

**Patterns:**
```
- "build a complete social network"
- "5000 lines of code"
- "everything in one shot"
- Missing architectural planning
```

### Unsupported Claims

**Detects:**
- Absolute statements without hedging
- Statistical claims without sources
- Over-confident predictions
- Missing citations

**Patterns:**
```
- "always/never/definitely"
- "95% of doctors agree" (no source)
- "guaranteed to work"
- Missing uncertainty language
```

## Risk Levels

Calculated based on weighted confidence scores:

- **LOW**: Minor issues, no immediate intervention needed
- **MODERATE**: Worth noting, consider additional verification
- **HIGH**: Significant concern, interventions recommended
- **CRITICAL**: Serious risk, multiple interventions strongly advised

## Intervention Types

### Step Breakdown
Complex tasks should be broken into verifiable components.

**Recommended for:**
- Math/physics speculation
- Large coding projects
- Dangerous file operations

### Human-in-the-Loop
Critical decisions require human oversight.

**Recommended for:**
- Medical advice
- Destructive file operations
- High-severity issues

### Web Search
Claims should be verified against authoritative sources.

**Recommended for:**
- Medical recommendations
- Physics/math theories
- Unsupported factual claims

### Simplified Scope
Overly ambitious projects need realistic scoping.

**Recommended for:**
- Vibe coding requests
- Complex system designs
- Feature-heavy applications

## Configuration

### Character Limit
Default: 25,000 characters per response
```python
CHARACTER_LIMIT = 25000
```

### Taxonomy Capacity
Default: 1,000 evidence entries
```python
MAX_EVIDENCE_ENTRIES = 1000
```

### Detection Sensitivity
Adjust pattern matching and confidence thresholds in detection functions:
```python
def detect_math_physics_speculation(text: str) -> Dict[str, Any]:
    # Modify patterns or confidence calculations
    ...
```

## Integration Examples

### Claude Desktop App

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "togmal": {
      "command": "python",
      "args": ["/path/to/togmal_mcp.py"]
    }
  }
}
```

### CLI Testing

```bash
# Run the server
python togmal_mcp.py

# In another terminal, test with MCP inspector
npx @modelcontextprotocol/inspector python togmal_mcp.py
```

### Programmatic Usage

```python
from mcp.client import Client

async def analyze_prompt(prompt: str):
    async with Client("togmal") as client:
        result = await client.call_tool(
            "togmal_analyze_prompt",
            {"prompt": prompt, "response_format": "json"}
        )
        return result
```

## Architecture

### Design Principles

1. **Privacy First**: No external API calls, all processing local
2. **Deterministic**: Heuristic-based detection for reproducibility
3. **Low Latency**: Fast pattern matching for real-time use
4. **Extensible**: Easy to add new patterns and categories
5. **Human-Centered**: Always allows human override and judgment

### Future Enhancements

The system is designed for progressive enhancement:

1. **Phase 1 (Current)**: Heuristic pattern matching
2. **Phase 2 (Planned)**: Traditional ML models (clustering, anomaly detection)
3. **Phase 3 (Future)**: Federated learning from submitted evidence
4. **Phase 4 (Advanced)**: Custom fine-tuned models for specific domains

### Data Flow

```
User Prompt
    ↓
togmal_analyze_prompt
    ↓
Detection Heuristics (parallel)
    ├── Math/Physics
    ├── Medical Advice
    ├── File Operations
    ├── Vibe Coding
    └── Unsupported Claims
    ↓
Risk Calculation
    ↓
Intervention Recommendations
    ↓
Response to Client
```

## Contributing

### Adding New Detection Patterns

1. Create a new detection function:
```python
def detect_new_category(text: str) -> Dict[str, Any]:
    patterns = {
        'subcategory1': [r'pattern1', r'pattern2'],
        'subcategory2': [r'pattern3']
    }
    # Implement detection logic
    return {
        'detected': bool,
        'categories': list,
        'confidence': float
    }
```

2. Add to CategoryType enum
3. Update analysis functions to include new detector
4. Add intervention recommendations if needed

### Submitting Evidence

Use the `togmal_submit_evidence` tool to contribute examples of problematic LLM behavior. This helps improve detection for everyone.

## Limitations

### Current Constraints

- **Heuristic-Based**: May have false positives/negatives
- **English-Only**: Patterns optimized for English text
- **Context-Free**: Doesn't understand full conversation history
- **No Learning**: Detection rules are static until updated

### Not a Replacement For

- Professional judgment in critical domains (medicine, law, etc.)
- Comprehensive code review
- Security auditing
- Safety testing in production systems

## License

MIT License - See LICENSE file for details

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Submit evidence through the MCP tool
- Contact: [Your contact information]

## Citation

If you use ToGMAL in your research or product, please cite:

```bibtex
@software{togmal_mcp,
  title={ToGMAL: Taxonomy of Generative Model Apparent Limitations},
  author={[Your Name]},
  year={2025},
  url={https://github.com/[your-repo]/togmal-mcp}
}
```

## Acknowledgments

Built using:
- [Model Context Protocol](https://modelcontextprotocol.io)
- [FastMCP](https://github.com/modelcontextprotocol/python-sdk)
- [Pydantic](https://docs.pydantic.dev)

Inspired by the need for safer, more grounded AI interactions.

# 🧠 ToGMAL Prompt Difficulty Analyzer

Real-time LLM capability boundary detection using vector similarity search.

## 🎯 What This Does

This system analyzes any prompt and tells you:
1. **How difficult it is** for current LLMs (based on real benchmark data)
2. **Why it's difficult** (shows similar benchmark questions)
3. **What to do about it** (actionable recommendations)

## 🔥 Key Innovation

Instead of clustering by domain (all math together), we cluster by **difficulty** - what's actually hard for LLMs regardless of domain.

## 📊 Real Data

- **14,042 MMLU questions** with real success rates from top models
- **<50ms query time** for real-time analysis
- **Production ready** vector database

## 🚀 Demo

- **Local**: http://127.0.0.1:7861
- **Public**: https://db11ee71660c8a3319.gradio.live

## 🧪 Example Results

### Hard Questions (Low Success Rates)
```
Prompt: "Statement 1 | Every field is also a ring..."
Risk: HIGH (23.9% success)
Recommendation: Multi-step reasoning with verification

Prompt: "Find all zeros of polynomial x³ + 2x + 2 in Z₇"
Risk: MODERATE (43.8% success)
Recommendation: Use chain-of-thought prompting
```

### Easy Questions (High Success Rates)
```
Prompt: "What is 2 + 2?"
Risk: MINIMAL (100% success)
Recommendation: Standard LLM response adequate

Prompt: "What is the capital of France?"
Risk: MINIMAL (100% success)
Recommendation: Standard LLM response adequate
```

## 🛠️ Technical Details

### Architecture
```
User Prompt → Embedding Model → Vector DB → K Nearest Questions → Weighted Score
```

### Components
1. **Sentence Transformers** (all-MiniLM-L6-v2) for embeddings
2. **ChromaDB** for vector storage
3. **Real MMLU data** with success rates from top models
4. **Gradio** for web interface

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt
pip install gradio

# Run the demo
python demo_app.py
```

Visit http://127.0.0.1:7861 to use the web interface.

## 📈 Next Steps

1. Add more benchmark datasets (GPQA, MATH)
2. Fetch real per-question results from multiple top models
3. Integrate with ToGMAL MCP server for Claude Desktop
4. Deploy to HuggingFace Spaces for permanent hosting

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a pull request

## 📧 Contact

For questions or support, please open an issue on GitHub.
