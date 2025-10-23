#!/bin/bash

echo "════════════════════════════════════════════════════"
echo "  Push to HuggingFace Spaces + GitHub"
echo "════════════════════════════════════════════════════"
echo ""

cd /Users/hetalksinmaths/togmal/Togmal-demo

# Stage files
echo "📦 Staging files..."
git add app_combined.py QUICK_PUSH.txt

# Commit
echo "💾 Committing..."
git commit -m "Fix chat: Format tool results directly for reliability" || echo "Nothing new to commit"

# Check remotes
echo ""
echo "🔍 Checking configured remotes..."
git remote -v

echo ""
echo "════════════════════════════════════════════════════"
echo "  Push 1/2: HuggingFace Spaces"
echo "════════════════════════════════════════════════════"
echo ""

# Push to HuggingFace (origin)
git push origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ HuggingFace push successful!"
    echo "🌐 Demo: https://huggingface.co/spaces/JustTheStatsHuman/Togmal-demo"
    echo "📊 Logs: https://huggingface.co/spaces/JustTheStatsHuman/Togmal-demo/logs"
else
    echo ""
    echo "❌ HuggingFace push failed!"
fi

echo ""
echo "════════════════════════════════════════════════════"
echo "  Push 2/2: GitHub"
echo "════════════════════════════════════════════════════"
echo ""

# Check if github remote exists
if git remote | grep -q "github"; then
    echo "📤 Pushing to GitHub remote..."
    git push github main
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ GitHub push successful!"
        echo "🐙 GitHub: https://github.com/HeTalksInMaths/togmal-mcp"
    else
        echo ""
        echo "❌ GitHub push failed!"
        echo "💡 You may need to set up authentication"
    fi
else
    echo "ℹ️  Setting up GitHub remote..."
    git remote add github https://github.com/HeTalksInMaths/togmal-mcp.git
    
    echo "📤 Pushing to GitHub..."
    git push -u github main
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ GitHub remote added and pushed successfully!"
        echo "🐙 GitHub: https://github.com/HeTalksInMaths/togmal-mcp"
    else
        echo ""
        echo "❌ GitHub push failed!"
        echo "💡 You may need to authenticate (use PAT as password)"
        echo "   Get PAT at: https://github.com/settings/tokens"
    fi
fi

echo ""
echo "════════════════════════════════════════════════════"
echo "  ✅ Done!"
echo "════════════════════════════════════════════════════"
