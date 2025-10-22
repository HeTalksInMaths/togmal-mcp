#!/bin/bash

echo "════════════════════════════════════════════════════"
echo "  GitHub Remote Setup for Togmal-demo"
echo "════════════════════════════════════════════════════"
echo ""

cd /Users/hetalksinmaths/togmal/Togmal-demo

echo "Current directory: $(pwd)"
echo ""

# Check current remotes
echo "📋 Current remotes:"
git remote -v
echo ""

# Remove old github remote if exists
git remote remove github 2>/dev/null

echo "🔧 Adding GitHub remote for togmal-mcp..."
git remote add github https://github.com/HeTalksInMaths/togmal-mcp.git

echo ""
echo "✅ Updated remotes:"
git remote -v

echo ""
echo "════════════════════════════════════════════════════"
echo "  Ready to Push!"
echo "════════════════════════════════════════════════════"
echo ""
echo "Now you can push with:"
echo "  git push github main"
echo ""
echo "Or push to both:"
echo "  git push origin main && git push github main"
echo ""
