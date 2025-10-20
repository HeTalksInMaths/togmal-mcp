#!/bin/bash
# Simple solution: Create fresh repo without large files

set -e

echo "==================================================================="
echo "Fresh Repository Setup (Simpler Alternative)"
echo "==================================================================="
echo ""
echo "This creates a fresh git repo with only the current state (no history)"
echo ""

# Confirm
read -p "Continue? This will reset git history. (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 1
fi

echo ""
echo "📦 Backing up current .git folder..."
mv .git .git.backup

echo "🔄 Creating fresh repository..."
git init
git add .
git commit -m "Initial commit - Togmal Demo for HuggingFace Spaces

Features:
- Vector database-based prompt difficulty assessment
- Real-time analysis using benchmark questions
- Auto-builds database on first launch
- Small repo size (no large binary files)"

echo ""
echo "✅ Fresh repository created!"
echo ""

# Show what will be committed
echo "📊 Files that will be pushed:"
git ls-files | head -20
echo "..."
echo ""

echo "Repository size:"
du -sh .git
echo ""

echo "==================================================================="
echo "Next Steps:"
echo "==================================================================="
echo ""
echo "1. Add Hugging Face remote:"
echo "   git remote add origin https://huggingface.co/spaces/JustTheStatsHuman/Togmal-demo"
echo ""
echo "2. Force push (this is safe since we're starting fresh):"
echo "   git push origin main --force"
echo ""
echo "3. If something went wrong, restore old git:"
echo "   rm -rf .git && mv .git.backup .git"
echo ""
