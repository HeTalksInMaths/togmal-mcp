#!/bin/bash
# Quick launch script for ToGMAL Chat Demo with MCP Tools

echo "🚀 ToGMAL Chat Demo Launcher"
echo "============================"
echo ""

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}📁 Project root: $PROJECT_ROOT${NC}"
echo ""

# Check if in Togmal-demo directory
if [[ "$SCRIPT_DIR" == *"Togmal-demo"* ]]; then
    DEMO_DIR="$SCRIPT_DIR"
else
    DEMO_DIR="$SCRIPT_DIR/Togmal-demo"
fi

echo -e "${BLUE}📁 Demo directory: $DEMO_DIR${NC}"
echo ""

# Check if virtual environment exists
VENV_PATH="$PROJECT_ROOT/.venv/bin/python3"

if [ ! -f "$VENV_PATH" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found at: $PROJECT_ROOT/.venv${NC}"
    echo ""
    echo "Please create a virtual environment first:"
    echo "  cd $PROJECT_ROOT"
    echo "  python3 -m venv .venv"
    echo "  source .venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

echo -e "${GREEN}✅ Virtual environment found${NC}"
echo ""

# Check if chat_app.py exists
CHAT_APP="$DEMO_DIR/chat_app.py"

if [ ! -f "$CHAT_APP" ]; then
    echo -e "${YELLOW}⚠️  Chat app not found at: $CHAT_APP${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Chat app found${NC}"
echo ""

# Run tests first (optional)
read -p "Run integration tests first? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${BLUE}🧪 Running integration tests...${NC}"
    echo ""
    cd "$DEMO_DIR"
    "$VENV_PATH" test_chat_integration.py
    TEST_RESULT=$?
    
    if [ $TEST_RESULT -ne 0 ]; then
        echo ""
        echo -e "${YELLOW}⚠️  Some tests failed. Continue anyway? (y/N)${NC}"
        read -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        echo ""
        echo -e "${GREEN}✅ All tests passed!${NC}"
    fi
    echo ""
fi

# Launch the chat app
echo -e "${GREEN}🚀 Launching ToGMAL Chat Demo...${NC}"
echo ""
echo "The demo will be available at: http://localhost:7860"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

cd "$DEMO_DIR"
"$VENV_PATH" chat_app.py
