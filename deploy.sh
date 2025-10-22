#!/bin/bash

echo "╔════════════════════════════════════════════════╗"
echo "║  ToGMAL Deployment - Final Steps              ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

cd /Users/hetalksinmaths/togmal/Togmal-demo

echo "📦 Staging files..."
git add app_combined.py
git add README.md
git add PUSH_READY.md
git add DEPLOY_NOW.md
git add deploy.sh

echo ""
echo "📋 Files staged:"
git status --short

echo ""
echo "💾 Committing..."
git commit -m "Add combined tabbed interface: Difficulty Analyzer + Chat Assistant with MCP tools"

echo ""
echo "╔════════════════════════════════════════════════╗"
echo "║  Ready to Push!                                ║"
echo "╚════════════════════════════════════════════════╝"
echo ""
echo "Repository: $(git remote get-url origin 2>/dev/null || echo 'Not configured')"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "You will be prompted for:"
echo "  1. Username: JustTheStatsHuman"
echo "  2. Password: [Your HuggingFace token starting with hf_]"
echo ""
echo "⚠️  IMPORTANT: The token won't be visible when you type it"
echo ""
echo "Get your token at: https://huggingface.co/settings/tokens"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
read -p "Press Enter to push to HuggingFace... " -r
echo ""

git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ SUCCESS! Your space is deploying!"
    echo ""
    echo "🌐 View it at: https://huggingface.co/spaces/JustTheStatsHuman/Togmal-demo"
    echo "📊 Build logs: https://huggingface.co/spaces/JustTheStatsHuman/Togmal-demo/logs"
    echo ""
    echo "⏱️  First build takes ~3-5 minutes"
    echo ""
else
    echo ""
    echo "❌ Push failed."
    echo ""
    echo "Common issues:"
    echo "  • Wrong token - Get it from https://huggingface.co/settings/tokens"
    echo "  • Token needs 'write' permission"
    echo "  • Check git remote: git remote -v"
    echo ""
fi
