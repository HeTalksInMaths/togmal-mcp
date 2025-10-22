#!/bin/bash

# Quick Push to HuggingFace + GitHub
# Usage: ./quick_push.sh "Your commit message"

cd /Users/hetalksinmaths/togmal/Togmal-demo

MESSAGE="${1:-Update demo}"

echo "════════════════════════════════════════════════════"
echo "  Quick Push: HuggingFace + GitHub"
echo "════════════════════════════════════════════════════"
echo ""
echo "📝 Commit message: $MESSAGE"
echo ""

# Add all changes
git add .

# Commit
git commit -m "$MESSAGE" || echo "ℹ️  Nothing new to commit"

echo ""
echo "🚀 Pushing to both platforms..."
echo ""

# Push to HuggingFace (origin)
echo "1️⃣  Pushing to HuggingFace Spaces..."
git push origin main

if [ $? -eq 0 ]; then
    echo "   ✅ HuggingFace updated!"
    echo "   🌐 https://huggingface.co/spaces/JustTheStatsHuman/Togmal-demo"
else
    echo "   ❌ HuggingFace push failed"
fi

echo ""

# Push to GitHub
echo "2️⃣  Pushing to GitHub..."

# Check if github remote exists, if not add it
if ! git remote | grep -q "github"; then
    echo "   ℹ️  Adding GitHub remote..."
    git remote add github https://github.com/HeTalksInMaths/togmal-mcp.git
fi

git push github main

if [ $? -eq 0 ]; then
    echo "   ✅ GitHub updated!"
    echo "   🐙 https://github.com/HeTalksInMaths/togmal-mcp"
else
    echo "   ❌ GitHub push failed"
    echo "   💡 You may need to authenticate with PAT"
    echo "   Get token at: https://github.com/settings/tokens"
fi

echo ""
echo "════════════════════════════════════════════════════"
echo "  ✨ Done!"
echo "════════════════════════════════════════════════════"
