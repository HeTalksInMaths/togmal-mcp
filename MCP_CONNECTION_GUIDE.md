# MCP Server Connection Guide

This guide explains how to connect to the ToGMAL MCP server from different platforms.

## 1. Claude Desktop (Already Configured) ✅

**Config file updated at:** `claude_desktop_config.json`

**Location on macOS:**
```bash
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Copy this configuration:**
```json
{
  "mcpServers": {
    "togmal": {
      "command": "/Users/hetalksinmaths/togmal/.venv/bin/python",
      "args": ["/Users/hetalksinmaths/togmal/togmal_mcp.py"],
      "description": "Taxonomy of Generative Model Apparent Limitations - Safety analysis for LLM interactions",
      "env": {
        "TOGMAL_DEBUG": "false",
        "TOGMAL_MAX_ENTRIES": "1000"
      }
    }
  }
}
```

**Steps:**
1. Copy the config to the Claude Desktop location
2. Restart Claude Desktop completely (Quit → Reopen)
3. Verify by asking: "What ToGMAL tools are available?"

---

## 2. Qoder Platform (This IDE) 🤖

Qoder doesn't natively support MCP servers yet, but you can:

### Option A: Test with MCP Inspector
```bash
# In terminal
source .venv/bin/activate
npx @modelcontextprotocol/inspector python togmal_mcp.py
```
This opens a web UI where you can test the MCP tools.

### Option B: Direct Python Testing
Use the test examples script:
```bash
source .venv/bin/activate
python test_examples.py
```

### Option C: Programmatic Usage
Create a client script to interact with the server:

```python
# test_client.py
import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_togmal():
    server_params = StdioServerParameters(
        command="/Users/hetalksinmaths/togmal/.venv/bin/python",
        args=["/Users/hetalksinmaths/togmal/togmal_mcp.py"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # List available tools
            tools = await session.list_tools()
            print("Available tools:", [tool.name for tool in tools.tools])
            
            # Test analyze_prompt
            result = await session.call_tool(
                "togmal_analyze_prompt",
                {
                    "prompt": "Build me a quantum gravity theory",
                    "response_format": "markdown"
                }
            )
            print("\nAnalysis result:")
            print(result.content[0].text)

if __name__ == "__main__":
    asyncio.run(test_togmal())
```

Run with:
```bash
source .venv/bin/activate
python test_client.py
```

---

## 3. Claude Code (VS Code Extension)

### Configuration

**Config location:**
- **macOS:** `~/Library/Application Support/Code/User/globalStorage/anthropic.claude-code/settings.json`
- **Linux:** `~/.config/Code/User/globalStorage/anthropic.claude-code/settings.json`
- **Windows:** `%APPDATA%\Code\User\globalStorage\anthropic.claude-code\settings.json`

**Add to settings:**
```json
{
  "mcpServers": {
    "togmal": {
      "command": "/Users/hetalksinmaths/togmal/.venv/bin/python",
      "args": ["/Users/hetalksinmaths/togmal/togmal_mcp.py"],
      "env": {
        "TOGMAL_DEBUG": "false"
      }
    }
  }
}
```

**Steps:**
1. Install Claude Code extension in VS Code
2. Add the configuration above
3. Reload VS Code
4. The tools should appear in Claude Code's tool palette

---

## 4. Cline (formerly Claude-Dev) in VS Code

### Configuration

**Config location:**
Open VS Code settings (⌘+,) and search for "Cline MCP Servers"

Or edit `.vscode/settings.json` in your workspace:

```json
{
  "cline.mcpServers": {
    "togmal": {
      "command": "/Users/hetalksinmaths/togmal/.venv/bin/python",
      "args": ["/Users/hetalksinmaths/togmal/togmal_mcp.py"]
    }
  }
}
```

**Steps:**
1. Install Cline extension
2. Add configuration to settings
3. Reload window
4. Cline will detect the MCP server

---

## 5. MCP Inspector (Testing Tool)

### Installation & Usage

```bash
# Navigate to project
cd /Users/hetalksinmaths/togmal

# Activate venv
source .venv/bin/activate

# Run inspector
npx @modelcontextprotocol/inspector python togmal_mcp.py
```

**Features:**
- Web-based UI for testing MCP tools
- Manual tool invocation with parameter input
- Response inspection
- Perfect for development and debugging

**Access:** Opens automatically in browser (usually `http://localhost:5173`)

---

## 6. Custom MCP Client

For programmatic access or custom integrations:

```python
# custom_client.py
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def analyze_with_togmal(prompt: str):
    """Analyze a prompt using ToGMAL."""
    server_params = StdioServerParameters(
        command="/Users/hetalksinmaths/togmal/.venv/bin/python",
        args=["/Users/hetalksinmaths/togmal/togmal_mcp.py"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            result = await session.call_tool(
                "togmal_analyze_prompt",
                {"prompt": prompt, "response_format": "json"}
            )
            
            return result.content[0].text

# Usage
result = asyncio.run(analyze_with_togmal(
    "Build me a complete social network in 5000 lines"
))
print(result)
```

---

## 7. API Server Wrapper (For HTTP Access)

If you need HTTP/REST access, create a wrapper:

```python
# api_server.py
from fastapi import FastAPI
from pydantic import BaseModel
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

app = FastAPI()

class AnalyzeRequest(BaseModel):
    prompt: str
    response_format: str = "markdown"

@app.post("/analyze")
async def analyze_prompt(request: AnalyzeRequest):
    server_params = StdioServerParameters(
        command="/Users/hetalksinmaths/togmal/.venv/bin/python",
        args=["/Users/hetalksinmaths/togmal/togmal_mcp.py"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "togmal_analyze_prompt",
                {
                    "prompt": request.prompt,
                    "response_format": request.response_format
                }
            )
            return {"result": result.content[0].text}

# Run with: uvicorn api_server:app --reload
```

Then access via HTTP:
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Build quantum computer", "response_format": "json"}'
```

---

## Quick Reference: Connection Methods

| Platform | Connection Method | Difficulty | Best For |
|----------|------------------|------------|----------|
| Claude Desktop | Config file | Easy | Daily use |
| MCP Inspector | Command line | Easy | Testing/debugging |
| Qoder IDE | Not supported | N/A | Use inspector instead |
| Claude Code | VS Code settings | Medium | Development |
| Cline | VS Code settings | Medium | Development |
| Custom Client | Python script | Medium | Automation |
| API Wrapper | FastAPI server | Hard | HTTP/REST access |

---

## Troubleshooting

### Server Won't Start
- Verify Python path: `/Users/hetalksinmaths/togmal/.venv/bin/python`
- Check syntax: `python -m py_compile togmal_mcp.py`
- Test directly: `python togmal_mcp.py` (will hang - this is OK!)

### Tools Not Appearing
- Ensure absolute paths in config
- Restart the client application completely
- Check client logs for error messages
- Verify venv is activated with dependencies installed

### Permission Issues
```bash
chmod +x /Users/hetalksinmaths/togmal/togmal_mcp.py
```

---

## For VC Pitch Demo

**Recommended setup:**
1. **Claude Desktop** - For live demonstration
2. **MCP Inspector** - For showing technical architecture
3. **Test examples** - For showing detection capabilities

**Demo flow:**
1. Show test_examples.py output (various detection scenarios)
2. Open MCP Inspector to show tool architecture
3. Use Claude Desktop for interactive demo
4. Show taxonomy database capabilities

This demonstrates both technical sophistication and practical safety applications!
