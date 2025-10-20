#!/bin/bash
# Clean large files from git history for Hugging Face deployment

set -e

echo "==================================================================="
echo "Cleaning Git History - Removing Large Files"
echo "==================================================================="
echo ""
echo "This will remove large files from ALL git history."
echo "The files will still exist locally but won't be tracked by git."
echo ""

# Check if git-filter-repo is available
if ! command -v git-filter-repo &> /dev/null; then
    echo "❌ git-filter-repo not found"
    echo ""
    echo "Install it with one of:"
    echo "  brew install git-filter-repo          # macOS"
    echo "  pip install git-filter-repo           # Python"
    echo "  sudo apt install git-filter-repo      # Ubuntu/Debian"
    echo ""
    exit 1
fi

echo "✓ git-filter-repo is installed"
echo ""

# Backup current branch
echo "📦 Creating backup branch..."
git branch backup-before-filter 2>/dev/null || echo "  (backup branch already exists)"

# Files to remove from history
FILES_TO_REMOVE=(
    "data/benchmark_vector_db"
    "data/benchmark_results/mmlu_real_results.json"
)

echo ""
echo "🗑️  Removing from history:"
for file in "${FILES_TO_REMOVE[@]}"; do
    echo "   - $file"
done
echo ""

# Confirm
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 1
fi

# Remove files from history
echo ""
echo "🔄 Filtering git history (this may take a minute)..."

for file in "${FILES_TO_REMOVE[@]}"; do
    echo "   Removing: $file"
    git filter-repo --path "$file" --invert-paths --force
done

echo ""
echo "✅ Git history cleaned!"
echo ""

# Show size reduction
echo "📊 Repository size:"
du -sh .git
echo ""

echo "==================================================================="
echo "Next Steps:"
echo "==================================================================="
echo ""
echo "1. Verify the changes:"
echo "   git log --oneline"
echo "   git status"
echo ""
echo "2. Re-add the remote (filter-repo removes it for safety):"
echo "   git remote add origin https://huggingface.co/spaces/JustTheStatsHuman/Togmal-demo"
echo ""
echo "3. Force push (⚠️  use with caution):"
echo "   git push origin main --force"
echo ""
echo "4. If something went wrong, restore from backup:"
echo "   git reset --hard backup-before-filter"
echo ""
