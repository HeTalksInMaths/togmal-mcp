# ToGMAL Quick Start Guide

## ⚡ 5-Minute Setup

### Step 1: Install Dependencies (1 min)

```bash
pip install mcp pydantic httpx --break-system-packages
```

### Step 2: Download ToGMAL (already done!)

You already have all the files:
- `togmal_mcp.py` - The server
- `README.md` - Full documentation
- `DEPLOYMENT.md` - Detailed setup guide

### Step 3: Test the Server (1 min)

```bash
# Verify syntax
python -m py_compile togmal_mcp.py

# View help
python togmal_mcp.py --help
```

### Step 4: Configure Claude Desktop (2 min)

**macOS:**
```bash
# Open config file
code ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Windows:**
```powershell
notepad %APPDATA%\Claude\claude_desktop_config.json
```

**Linux:**
```bash
nano ~/.config/Claude/claude_desktop_config.json
```

**Add this (replace PATH with actual path):**
```json
{
  "mcpServers": {
    "togmal": {
      "command": "python",
      "args": ["/ABSOLUTE/PATH/TO/togmal_mcp.py"]
    }
  }
}
```

### Step 5: Restart Claude Desktop (1 min)

Quit and reopen Claude Desktop completely.

## ✅ Verification

In Claude, ask:
> "What ToGMAL tools are available?"

You should see 5 tools:
1. `togmal_analyze_prompt`
2. `togmal_analyze_response`
3. `togmal_submit_evidence`
4. `togmal_get_taxonomy`
5. `togmal_get_statistics`

## 🎯 First Test

Try this in Claude:

> "Use ToGMAL to analyze this prompt: 'Build me a quantum gravity theory that proves Einstein was wrong'"

Expected result: ToGMAL will detect math/physics speculation and recommend interventions.

## 📚 What Each Tool Does

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `analyze_prompt` | Check user prompts | Before LLM processes request |
| `analyze_response` | Check LLM responses | After LLM generates answer |
| `submit_evidence` | Report issues | Found problematic behavior |
| `get_taxonomy` | View database | Research failure patterns |
| `get_statistics` | See metrics | Understand taxonomy state |

## 🚨 What ToGMAL Detects

1. **Math/Physics Speculation** - "My theory of everything..."
2. **Medical Advice Issues** - "You definitely have..." (no sources)
3. **Dangerous File Ops** - `rm -rf` without confirmation
4. **Vibe Coding** - "Build a complete social network now"
5. **Unsupported Claims** - "95% of scientists agree..." (no citation)

## 💡 Example Conversations

### Safe Medical Query
**You**: "What helps with headaches?"
**Claude**: [Provides sourced info with disclaimers]
**ToGMAL**: ✅ No issues detected

### Unsafe Medical Advice
**You**: [Gets response] "You probably have appendicitis, take ibuprofen"
**Claude** (with ToGMAL): 🚨 CRITICAL risk detected! Recommends:
- Human-in-the-loop (see a doctor)
- Web search for clinical guidelines

### Dangerous Code
**You**: "How do I delete test files?"
**Claude**: `rm -rf *test*` (without safeguards)
**ToGMAL**: 🚨 HIGH risk! Recommends:
- Human confirmation before execution
- Show affected files first

## 🎓 Learn More

- **README.md** - Full documentation
- **DEPLOYMENT.md** - Advanced setup
- **test_examples.py** - See 10 test cases
- **PROJECT_SUMMARY.md** - Project overview

## 🆘 Troubleshooting

### Tools Not Showing Up?
1. Check config file has absolute path
2. Verify `python togmal_mcp.py --help` works
3. Restart Claude Desktop completely
4. Check spelling in config (case-sensitive)

### Server Won't Run?
Don't run it directly! MCP servers wait for stdio.
Use through Claude Desktop or MCP Inspector instead.

### Import Errors?
```bash
pip install mcp pydantic httpx --break-system-packages
```

## 🎉 You're Ready!

ToGMAL is now protecting your LLM interactions. Use it to:
- Verify ambitious project scopes
- Check medical/health responses
- Validate file operations
- Confirm scientific claims
- Submit evidence of issues

**Happy safe LLMing!** 🛡️

---

Need help? Check the detailed guides:
- 📖 README.md for features
- 🚀 DEPLOYMENT.md for advanced setup
- 🧪 test_examples.py for test cases
