# ToGMAL MCP Server - Hosting & Demo Guide

## ❓ Can You Host MCP Servers on Render (Like Aqumen)?

### Short Answer: **Not Directly** (But There Are Alternatives)

### Why MCP Servers Are Different from FastAPI

#### **FastAPI (Your Aqumen Project)**
```python
# Traditional web server
app = FastAPI()

@app.get("/api/endpoint")
async def endpoint():
    return {"data": "response"}

# Runs continuously, listens on HTTP port
# Accessible via: https://aqumen.onrender.com/api/endpoint
```

#### **FastMCP (ToGMAL)**
```python
# MCP server
mcp = FastMCP("togmal")

@mcp.tool()
async def tool_name(params):
    return "result"

# Runs on-demand, uses stdio (not HTTP)
# Spawned by client, communicates via stdin/stdout
# NOT accessible via URL
```

### Key Differences

| Feature | FastAPI | FastMCP (MCP) |
|---------|---------|---------------|
| **Protocol** | HTTP/HTTPS | JSON-RPC over stdio |
| **Communication** | Request/Response | Standard input/output |
| **Hosting** | Web server (Render, Vercel) | Local subprocess |
| **Access** | URL endpoints | Client spawns process |
| **Deployment** | Cloud hosting | Client-side execution |
| **Use Case** | Web APIs, REST services | LLM tool integration |

### Why MCP Uses stdio Instead of HTTP

1. **Tight Integration:** LLM clients (Claude Desktop) spawn tools as subprocesses
2. **Security:** No network exposure, all communication is process-local
3. **Performance:** No network latency, instant local communication
4. **Privacy:** Data never leaves the user's machine
5. **Simplicity:** No authentication, CORS, or network configuration needed

---

## 🌐 How to Create a Web-Based Demo for VCs

Since MCP servers can't be hosted directly, here are your options:

### **Option 1: MCP Inspector (Easiest)**

Already running at: `http://localhost:6274`

**To make it accessible:**
```bash
# Use ngrok or similar tunneling service
brew install ngrok
ngrok http 6274
```

**Result:** Get a public URL like `https://abc123.ngrok.io`

**Demo Flow:**
1. Show the ngrok URL to VCs
2. They can test the MCP tools in real-time
3. Fully interactive web UI

**Limitations:**
- Requires your laptop to be running
- Session expires when you close terminal

---

### **Option 2: Build a FastAPI Wrapper (Best for Demos)**

Create an HTTP API that wraps the MCP server:

```python
# api_wrapper.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

app = FastAPI(title="ToGMAL API Demo")

# Enable CORS for web demos
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/analyze/prompt")
async def analyze_prompt(prompt: str, response_format: str = "markdown"):
    """Analyze a prompt using ToGMAL MCP server."""
    server_params = StdioServerParameters(
        command="/Users/hetalksinmaths/togmal/.venv/bin/python",
        args=["/Users/hetalksinmaths/togmal/togmal_mcp.py"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "togmal_analyze_prompt",
                arguments={"prompt": prompt, "response_format": response_format}
            )
            return {"result": result.content[0].text}

@app.get("/")
async def root():
    return {"message": "ToGMAL API Demo - Use /docs for Swagger UI"}
```

**Deploy to Render:**
```yaml
# render.yaml
services:
  - type: web
    name: togmal-api
    env: python
    buildCommand: pip install -r requirements-api.txt
    startCommand: uvicorn api_wrapper:app --host 0.0.0.0 --port $PORT
```

**Access:** `https://togmal-api.onrender.com/docs`

---

### **Option 3: Static Demo Website with Frontend**

Build a simple React/HTML frontend that demonstrates the concepts:

```javascript
// Demo frontend (no real MCP server)
const demoExamples = [
  {
    prompt: "Build me a quantum gravity theory",
    risk: "HIGH",
    detections: ["math_physics_speculation"],
    interventions: ["step_breakdown", "web_search"]
  },
  // ... more examples
];

// Show pre-computed results from test_examples.py
```

**Deploy to:** Vercel, Netlify, GitHub Pages (free)

---

### **Option 4: Video Demo**

Record a screencast showing:
1. MCP Inspector UI
2. Running test examples
3. Claude Desktop integration
4. Real-time detection

**Tools:** Loom, QuickTime, OBS

---

## 🔑 Do You Need API Keys?

### **For ToGMAL MCP Server: NO**

- ✅ No API keys needed
- ✅ No external services
- ✅ Completely local and deterministic
- ✅ No authentication required (for local use)

### **For MCP Inspector: NO**

- ✅ Generates session token automatically
- ✅ Token is for browser security only
- ✅ No account or API key setup needed

### **When You WOULD Need API Keys:**

Only if you add features that call external services:
- Web search (need Google/Bing API key)
- LLM-based classification (need OpenAI/Anthropic API key)
- Database storage (need DB credentials)

**Current ToGMAL:** Zero API keys required! ✅

---

## 📖 How to Use MCP Inspector

### **Already Running:**
```
http://localhost:6274/?MCP_PROXY_AUTH_TOKEN=b9c04f13d4a272be1e9d368aaa82d23d54f59910fe36c873edb29fee800c30b4
```

### **Step-by-Step Guide:**

1. **Open the URL** in your browser

2. **Select a Tool** from the left sidebar:
   - `togmal_analyze_prompt`
   - `togmal_analyze_response`
   - `togmal_submit_evidence`
   - `togmal_get_taxonomy`
   - `togmal_get_statistics`

3. **View Tool Schema:**
   - See parameters, types, descriptions
   - Understand what each tool expects

4. **Enter Parameters:**
   - Fill in the form fields
   - Example for `togmal_analyze_prompt`:
     ```json
     {
       "prompt": "Build me a complete social network in 5000 lines",
       "response_format": "markdown"
     }
     ```

5. **Execute Tool:**
   - Click "Call Tool" button
   - See the request being sent
   - View the response

6. **Inspect Results:**
   - See risk level, detections, interventions
   - Copy results for documentation
   - Test different scenarios

### **Demo Scenarios to Test:**

```json
// Math/Physics Speculation
{
  "prompt": "I've discovered a new theory of quantum gravity",
  "response_format": "markdown"
}

// Medical Advice
{
  "response": "You definitely have the flu. Take 1000mg vitamin C.",
  "context": "I have a fever",
  "response_format": "markdown"
}

// Dangerous File Operations
{
  "response": "Run: rm -rf node_modules && delete all test files",
  "response_format": "markdown"
}

// Vibe Coding
{
  "prompt": "Build a complete social network with 10,000 lines of code",
  "response_format": "markdown"
}

// Statistics
{
  "response_format": "markdown"
}
```

---

## 🎯 Recommended Demo Strategy for VCs

### **1. Preparation**
- Run MCP Inspector
- Use ngrok for public URL
- Prepare test cases
- Have slides ready

### **2. Demo Flow**

**Act 1: The Problem (2 min)**
- Show `test_examples.py` output
- Demonstrate 5 failure categories
- Emphasize privacy concerns with external LLM judges

**Act 2: The Solution (3 min)**
- Open MCP Inspector
- Live demo: Test math/physics speculation
- Live demo: Test medical advice
- Show risk levels and interventions

**Act 3: The Architecture (2 min)**
- Explain local-first approach
- No API keys, no cloud dependencies
- Privacy-preserving by design
- Perfect for regulated industries

**Act 4: The Business (3 min)**
- Enterprise licensing model
- On-premise deployment
- Integration with existing LLM workflows
- Roadmap: heuristics → ML → federated learning

### **3. Collateral**
- Live MCP Inspector URL
- GitHub repo with docs
- Video walkthrough
- Technical whitepaper

---

## 💡 Alternative: Build a Streamlit Demo

Quick interactive demo without complex hosting:

```python
# streamlit_demo.py
import streamlit as st
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

st.title("ToGMAL: LLM Safety Analysis")

prompt = st.text_area("Enter a prompt to analyze:")

if st.button("Analyze"):
    # Call MCP server
    result = asyncio.run(analyze_with_togmal(prompt))
    st.markdown(result)
```

**Deploy to:** Streamlit Cloud (free hosting)

---

## 📊 Comparison: Hosting Options

| Option | Complexity | Cost | VC Demo Quality | Best For |
|--------|-----------|------|-----------------|----------|
| MCP Inspector + ngrok | Low | Free | Medium | Quick demos |
| FastAPI Wrapper + Render | Medium | Free | High | Professional demos |
| Streamlit Cloud | Low | Free | Medium | Interactive showcases |
| Static Frontend | Medium | Free | Medium | Concept demos |
| Video Recording | Low | Free | Medium | Async presentations |

---

## 🚀 Next Steps for Demo

1. **Short Term (This Week):**
   - Use MCP Inspector + ngrok for live demos
   - Record a video walkthrough
   - Prepare test cases with compelling examples

2. **Medium Term (Next Month):**
   - Build FastAPI wrapper for stable demo URL
   - Deploy to Render (free tier)
   - Create simple frontend UI

3. **Long Term (Before Launch):**
   - Professional demo website
   - Integration examples with popular LLMs
   - Video testimonials from beta users

---

## 🔐 Security Note for Public Demos

If you expose MCP Inspector publicly:

```bash
# Add authentication
export MCP_PROXY_AUTH=your_secret_token

# Or use SSH tunnel instead of ngrok
ssh -R 80:localhost:6274 serveo.net
```

For production demos, always use the FastAPI wrapper with proper authentication.

---

**Summary:** MCP servers are fundamentally different from FastAPI - they're designed for local subprocess execution, not HTTP hosting. For VC demos, wrap the MCP server in a FastAPI application or use ngrok with MCP Inspector for quick public access.
