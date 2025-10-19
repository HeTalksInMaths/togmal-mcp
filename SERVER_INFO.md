# ToGMAL MCP Server - Running Information

## 🌐 MCP Inspector Web UI (Currently Running)

**Access URL:**
```
http://localhost:6274/?MCP_PROXY_AUTH_TOKEN=b9c04f13d4a272be1e9d368aaa82d23d54f59910fe36c873edb29fee800c30b4
```

**Details:**
- **Web UI Port:** `6274` (automatically assigned, avoids your 5173)
- **Proxy Port:** `6277`
- **Status:** ✅ Running in background (terminal_id: 1)
- **Session Token:** `b9c04f13d4a272be1e9d368aaa82d23d54f59910fe36c873edb29fee800c30b4`

**Features:**
- Test all 5 MCP tools interactively
- View tool schemas and parameters
- Execute tools and see responses
- Debug MCP communication

---

## 🖥️ Claude Desktop Configuration

**Status:** ✅ Config copied successfully

**Config Location:**
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Next Steps:**
1. **Quit Claude Desktop completely** (⌘+Q)
2. **Reopen Claude Desktop**
3. **Verify** by asking: "What ToGMAL tools are available?"

You should see 5 tools:
- `togmal_analyze_prompt`
- `togmal_analyze_response`
- `togmal_submit_evidence`
- `togmal_get_taxonomy`
- `togmal_get_statistics`

---

## 📍 Where is the Server Hosted?

### **The Server is LOCAL - Not Hosted Anywhere Remote**

**Important:** The ToGMAL MCP server is **not hosted on any cloud server or remote location**. Here's how it works:

### Architecture Explanation

```
┌─────────────────────────────────────────────────────────┐
│  YOUR LOCAL MACHINE (MacBook)                           │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │  Client (Claude Desktop or MCP Inspector)       │    │
│  │  Runs in: Your local environment                │    │
│  └──────────────────┬───────────────────────────────┘    │
│                     │                                     │
│                     │ stdio (standard input/output)       │
│                     │ JSON-RPC communication              │
│                     ▼                                     │
│  ┌────────────────────────────────────────────────┐    │
│  │  ToGMAL MCP Server (togmal_mcp.py)             │    │
│  │  Location: /Users/hetalksinmaths/togmal/       │    │
│  │  Python: .venv/bin/python                       │    │
│  │  Process: Spawned on-demand by client           │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### How It Works

1. **On-Demand Execution:**
   - When Claude Desktop starts, it reads the config file
   - It spawns the MCP server as a **subprocess** using:
     ```bash
     /Users/hetalksinmaths/togmal/.venv/bin/python /Users/hetalksinmaths/togmal/togmal_mcp.py
     ```
   - The server runs **only while Claude Desktop is open**

2. **Communication Method:**
   - **stdio (Standard Input/Output)** - Not HTTP, not network
   - The client sends JSON-RPC requests via stdin
   - The server responds via stdout
   - All communication is **process-to-process on your local machine**

3. **MCP Inspector:**
   - Runs a **local web server** at `http://localhost:6274`
   - Also spawns the MCP server as a subprocess
   - Provides a web UI to interact with the local server
   - **Still 100% local** - nothing leaves your machine

### Privacy & Security Benefits

✅ **No Network Traffic:** All analysis happens locally  
✅ **No External APIs:** No data sent to cloud services  
✅ **No Data Storage:** Everything in memory (unless you persist taxonomy)  
✅ **Full Control:** You own and control all data  
✅ **Offline Capable:** Works without internet connection  

### Server Lifecycle

| Client | Server State |
|--------|--------------|
| Claude Desktop opens | Server spawns as subprocess |
| Claude Desktop running | Server active, processes requests |
| Claude Desktop closes | Server terminates automatically |
| MCP Inspector starts | Server spawns as subprocess |
| MCP Inspector stops | Server terminates automatically |

### File Locations

```
/Users/hetalksinmaths/togmal/
├── togmal_mcp.py           ← The actual server code
├── .venv/                  ← Virtual environment with dependencies
│   └── bin/python          ← Python interpreter used to run server
├── requirements.txt        ← Server dependencies (mcp, pydantic, httpx)
└── claude_desktop_config.json ← Config file (copied to Claude Desktop)
```

### Why This Design?

1. **Privacy:** Sensitive prompts/responses never leave your machine
2. **Speed:** No network latency, instant local processing
3. **Reliability:** No dependency on cloud services or internet
4. **Control:** You can inspect, modify, and debug the server code
5. **Security:** No external attack surface

### Comparison to Traditional Servers

| Traditional Web Server | MCP Server (ToGMAL) |
|------------------------|---------------------|
| Always running | Runs on-demand |
| Listen on network port | stdio communication |
| HTTP/HTTPS protocol | JSON-RPC over stdio |
| Hosted on cloud/VPS | Runs locally |
| Accessed via URL | Spawned by client |
| Requires deployment | Just run locally |

---

## 🎯 For Your VC Pitch

### Key Technical Points

**"ToGMAL is a privacy-first, locally-executed MCP server that provides real-time LLM safety analysis without any cloud dependencies."**

**Advantages:**
- ✅ **Zero Data Leakage:** All processing happens on the user's machine
- ✅ **Enterprise-Ready:** No compliance issues with sending data externally
- ✅ **Low Latency:** No network round-trips, instant analysis
- ✅ **Cost Efficient:** No server hosting costs for users
- ✅ **Scalable:** Each user runs their own instance

**Business Model Implications:**
- Can target **regulated industries** (healthcare, finance) due to privacy
- **Enterprise licensing** for on-premise deployment
- **Developer tool** that integrates into existing workflows
- **No infrastructure costs** - users run it themselves

---

## 🔧 Current Running Services

### MCP Inspector (Background Process)
```bash
Terminal ID: 1
URL: http://localhost:6274/?MCP_PROXY_AUTH_TOKEN=...
Status: Running
```

**To stop:**
- The process will stop when you close this IDE or terminal
- Or manually kill the background process

### Claude Desktop
```bash
Config: Copied to ~/Library/Application Support/Claude/
Status: Ready (restart Claude Desktop to activate)
```

---

## 📊 Testing Commands

### Test in MCP Inspector
1. Open: http://localhost:6274/?MCP_PROXY_AUTH_TOKEN=b9c04f13d4a272be1e9d368aaa82d23d54f59910fe36c873edb29fee800c30b4
2. Select a tool (e.g., `togmal_analyze_prompt`)
3. Enter parameters
4. Click "Execute"
5. View results

### Test in Claude Desktop
1. Restart Claude Desktop (⌘+Q then reopen)
2. Ask: "Use ToGMAL to analyze this prompt: 'Build me a quantum gravity theory'"
3. Claude will automatically call the MCP server
4. View the safety analysis

### Test with Python Client
```bash
source .venv/bin/activate
python test_client.py
```

### Test Examples
```bash
source .venv/bin/activate
python test_examples.py
```

---

## 🛠️ Troubleshooting

### MCP Inspector Not Working?
- Check the URL includes the auth token
- Verify terminal_id: 1 is still running
- Check if port 6274 is available

### Claude Desktop Not Showing Tools?
1. Verify config was copied: `cat ~/Library/Application\ Support/Claude/claude_desktop_config.json`
2. Completely quit Claude Desktop (⌘+Q)
3. Reopen Claude Desktop
4. Check Claude Desktop logs: `~/Library/Logs/Claude/mcp*.log`

### Server Not Starting?
```bash
# Test server manually
source .venv/bin/activate
python togmal_mcp.py
# Should hang - this is expected! Press Ctrl+C to stop
```

---

## 📚 Documentation

- [`SETUP_COMPLETE.md`](SETUP_COMPLETE.md) - Full setup guide
- [`MCP_CONNECTION_GUIDE.md`](MCP_CONNECTION_GUIDE.md) - Platform connections
- [`README.md`](README.md) - Feature documentation
- [`ARCHITECTURE.md`](ARCHITECTURE.md) - System design

---

**Summary:** The ToGMAL MCP server runs **100% locally** on your MacBook. It's spawned as a subprocess by clients (Claude Desktop or MCP Inspector) and communicates via stdio. No remote hosting, no cloud services, complete privacy. 🛡️
