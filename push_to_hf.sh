#!/bin/bash

echo "╔════════════════════════════════════════════════╗"
echo "║  HuggingFace Spaces Deployment                ║"
echo "╚════════════════════════════════════════════════╝"
echo ""
echo "Repository: $(git remote get-url origin)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "You will be prompted for:"
echo "  1. Username: JustTheStatsHuman"
echo "  2. Password: [Your HuggingFace token starting with hf_]"
echo ""
echo "Note: The password won't be visible when you type it"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
read -p "Press Enter to start the push... "
echo ""

git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ SUCCESS! Your space is deploying!"
    echo ""
    echo "View it at: https://huggingface.co/spaces/JustTheStatsHuman/Togmal-demo"
    echo ""
else
    echo ""
    echo "❌ Push failed. Check your token and try again."
    echo ""
fi
