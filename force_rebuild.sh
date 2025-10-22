#!/bin/bash

echo "════════════════════════════════════════════════════"
echo "  Force HuggingFace Spaces Rebuild"
echo "════════════════════════════════════════════════════"
echo ""

cd /Users/hetalksinmaths/togmal/Togmal-demo

echo "📋 Current files that will be pushed:"
echo ""
git status --short

echo ""
echo "📝 Checking if app_combined.py exists..."
if [ -f "app_combined.py" ]; then
    echo "✅ app_combined.py exists ($(wc -l < app_combined.py) lines)"
else
    echo "❌ app_combined.py NOT FOUND!"
    exit 1
fi

echo ""
echo "📝 Checking README.md configuration..."
grep "app_file:" README.md

echo ""
echo "🔄 Adding all files and creating trigger commit..."
git add .
git commit -m "Force rebuild: Update to combined tabbed interface" --allow-empty

echo ""
echo "🚀 Pushing to HuggingFace Spaces..."
echo "   This will FORCE a rebuild"
echo ""

git push origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "════════════════════════════════════════════════════"
    echo "  ✅ SUCCESS! Space will rebuild now"
    echo "════════════════════════════════════════════════════"
    echo ""
    echo "🌐 View Space: https://huggingface.co/spaces/JustTheStatsHuman/Togmal-demo"
    echo "📊 Build Logs: https://huggingface.co/spaces/JustTheStatsHuman/Togmal-demo/logs"
    echo ""
    echo "⏱️  Wait 3-5 minutes for build to complete"
    echo ""
    echo "💡 TIP: If it still shows old version:"
    echo "   1. Go to Settings on HuggingFace Space"
    echo "   2. Click 'Factory Reboot' to force complete rebuild"
    echo ""
else
    echo ""
    echo "❌ Push failed"
    echo ""
fi
