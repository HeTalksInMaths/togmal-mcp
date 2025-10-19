# ToGMAL Deployment Guide

## Quick Start

### 1. Install Dependencies

```bash
# Install Python dependencies
pip install mcp pydantic httpx --break-system-packages

# Or use the requirements file
pip install -r requirements.txt --break-system-packages
```

### 2. Verify Installation

```bash
# Check Python syntax
python -m py_compile togmal_mcp.py

# View available commands
python togmal_mcp.py --help
```

### 3. Test the Server

```bash
# Option A: Use the MCP Inspector (recommended)
npx @modelcontextprotocol/inspector python togmal_mcp.py

# Option B: Run test examples
python test_examples.py
```

## Claude Desktop Integration

### macOS Configuration

1. Open Claude Desktop configuration:
```bash
code ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

2. Add ToGMAL server:
```json
{
  "mcpServers": {
    "togmal": {
      "command": "python",
      "args": ["/absolute/path/to/togmal_mcp.py"]
    }
  }
}
```

3. Restart Claude Desktop

### Windows Configuration

1. Open configuration file:
```powershell
notepad %APPDATA%\Claude\claude_desktop_config.json
```

2. Add ToGMAL server (use forward slashes or escaped backslashes):
```json
{
  "mcpServers": {
    "togmal": {
      "command": "python",
      "args": ["C:/path/to/togmal_mcp.py"]
    }
  }
}
```

3. Restart Claude Desktop

### Linux Configuration

1. Open configuration:
```bash
nano ~/.config/Claude/claude_desktop_config.json
```

2. Add ToGMAL server:
```json
{
  "mcpServers": {
    "togmal": {
      "command": "python",
      "args": ["/home/username/togmal_mcp.py"]
    }
  }
}
```

3. Restart Claude Desktop

## Verification

After setup, verify the server is working:

1. Open Claude Desktop
2. Start a new conversation
3. Check that ToGMAL tools appear in the available tools list:
   - `togmal_analyze_prompt`
   - `togmal_analyze_response`
   - `togmal_submit_evidence`
   - `togmal_get_taxonomy`
   - `togmal_get_statistics`

## Basic Usage Examples

### Example 1: Analyze a Prompt

**User:** "Can you analyze this prompt for issues?"

Then provide the prompt:
```
Build me a quantum computer simulation that proves my theory of everything
```

The assistant will use `togmal_analyze_prompt` and provide a risk assessment.

### Example 2: Check a Response

**User:** "Check if this medical advice is safe:"

```
You definitely have the flu. Take 1000mg of vitamin C and 
you'll be fine in 2 days. No need to see a doctor.
```

The assistant will use `togmal_analyze_response` and flag the ungrounded medical advice.

### Example 3: Submit Evidence

**User:** "I want to report a concerning LLM response"

The assistant will guide you through using `togmal_submit_evidence` with human-in-the-loop confirmation.

### Example 4: View Statistics

**User:** "Show me the taxonomy statistics"

The assistant will use `togmal_get_statistics` to display the current state of the database.

## Troubleshooting

### Server Won't Start

**Issue:** Server hangs when running directly
```bash
python togmal_mcp.py
# Hangs indefinitely...
```

**Solution:** This is expected! MCP servers are long-running processes that wait for stdio input. Use the MCP Inspector or integrate with Claude Desktop instead.

### Import Errors

**Issue:** `ModuleNotFoundError: No module named 'mcp'`

**Solution:** Install dependencies:
```bash
pip install mcp pydantic --break-system-packages
```

### Tools Not Appearing in Claude

**Issue:** ToGMAL tools don't show up in Claude Desktop

**Checklist:**
1. Verify configuration file path is correct
2. Ensure Python path in config is absolute
3. Check that togmal_mcp.py is executable
4. Restart Claude Desktop completely
5. Check Claude Desktop logs for errors

### Permission Errors

**Issue:** Permission denied when running server

**Solution:**
```bash
# Make script executable (Unix-like systems)
chmod +x togmal_mcp.py

# Or specify Python interpreter explicitly
python togmal_mcp.py
```

## Advanced Configuration

### Custom Detection Patterns

Edit `togmal_mcp.py` to add custom patterns:

```python
def detect_custom_category(text: str) -> Dict[str, Any]:
    patterns = {
        'my_pattern': [
            r'custom pattern 1',
            r'custom pattern 2'
        ]
    }
    # Add detection logic
    return {
        'detected': False,
        'categories': [],
        'confidence': 0.0
    }
```

### Adjust Sensitivity

Modify confidence thresholds:

```python
def calculate_risk_level(analysis_results: Dict[str, Any]) -> RiskLevel:
    risk_score = 0.0
    
    # Adjust these weights to change sensitivity
    if analysis_results['math_physics']['detected']:
        risk_score += analysis_results['math_physics']['confidence'] * 0.5
    
    # Lower threshold for more sensitive detection
    if risk_score >= 0.3:  # Was 0.5
        return RiskLevel.MODERATE
```

### Database Persistence

By default, taxonomy data is stored in memory. For persistence, modify:

```python
import json
import os

TAXONOMY_FILE = "/path/to/taxonomy.json"

# Load on startup
if os.path.exists(TAXONOMY_FILE):
    with open(TAXONOMY_FILE, 'r') as f:
        TAXONOMY_DB = json.load(f)

# Save after each submission
def save_taxonomy():
    with open(TAXONOMY_FILE, 'w') as f:
        json.dump(TAXONOMY_DB, f, indent=2, default=str)
```

## Performance Optimization

### For High-Volume Usage

1. **Index Taxonomy Data:**
```python
from collections import defaultdict

# Add indices for faster queries
TAXONOMY_INDEX = defaultdict(list)
```

2. **Implement Caching:**
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def detect_cached(text: str, detector_name: str):
    # Cache detection results
    pass
```

3. **Async Improvements:**
```python
import asyncio

# Run detectors in parallel
async def analyze_parallel(text: str):
    results = await asyncio.gather(
        detect_math_physics_speculation(text),
        detect_ungrounded_medical_advice(text),
        # ... other detectors
    )
```

## Production Deployment

### Using a Process Manager

**systemd (Linux):**

Create `/etc/systemd/system/togmal.service`:
```ini
[Unit]
Description=ToGMAL MCP Server
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/togmal
ExecStart=/usr/bin/python /path/to/togmal_mcp.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable togmal
sudo systemctl start togmal
```

**Docker:**

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY togmal_mcp.py .

CMD ["python", "togmal_mcp.py"]
```

Build and run:
```bash
docker build -t togmal-mcp .
docker run togmal-mcp
```

## Monitoring

### Logging

Add logging to the server:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/togmal.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('togmal')
```

### Metrics

Track usage metrics:

```python
from collections import Counter

USAGE_STATS = {
    'tool_calls': Counter(),
    'detections': Counter(),
    'interventions': Counter()
}

# In each tool function:
USAGE_STATS['tool_calls'][tool_name] += 1
```

## Security Considerations

1. **Input Validation:** Already handled by Pydantic models
2. **Rate Limiting:** Consider adding for public deployments
3. **Data Privacy:** Taxonomy stores prompts/responses - be mindful of sensitive data
4. **Access Control:** Implement authentication for multi-user scenarios

## Updates and Maintenance

### Updating Detection Patterns

1. Edit detection functions in `togmal_mcp.py`
2. Test with `test_examples.py`
3. Restart the MCP server
4. Verify changes in Claude Desktop

### Updating Dependencies

```bash
pip install --upgrade mcp pydantic httpx --break-system-packages
```

### Backup Taxonomy Data

If using persistent storage:
```bash
# Create backup
cp /path/to/taxonomy.json /path/to/taxonomy.backup.json

# Restore if needed
cp /path/to/taxonomy.backup.json /path/to/taxonomy.json
```

## Getting Help

- **GitHub Issues:** Report bugs and request features
- **Documentation:** See README.md for detailed information
- **MCP Documentation:** https://modelcontextprotocol.io
- **Community:** Join MCP community discussions

## Next Steps

1. ✅ Install and configure ToGMAL
2. ✅ Test with example prompts
3. ✅ Submit evidence to improve detection
4. 📝 Customize patterns for your use case
5. 🚀 Deploy to production
6. 📊 Monitor usage and effectiveness
7. 🔄 Iterate and improve

Happy safe LLM usage! 🛡️
