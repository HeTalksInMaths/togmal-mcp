# 🐙 Push to GitHub - Quick Setup

## Option 1: Quick Push (If GitHub Remote Already Configured)

```bash
cd /Users/hetalksinmaths/togmal/Togmal-demo
chmod +x push_to_both.sh
./push_to_both.sh
```

This will:
1. ✅ Push to HuggingFace Spaces (live demo)
2. ✅ Push to GitHub (code backup)

---

## Option 2: First-Time GitHub Setup

### Step 1: Create GitHub Repository

1. Go to: https://github.com/new
2. Repository name: `togmal-demo` (or any name)
3. Description: "ToGMAL - AI Difficulty & Safety Analysis Platform"
4. **Public** or **Private** (your choice)
5. **Do NOT initialize** with README (we already have files)
6. Click "Create repository"

### Step 2: Add GitHub Remote

```bash
cd /Users/hetalksinmaths/togmal/Togmal-demo

# Add GitHub as a remote (replace YOUR_USERNAME)
git remote add github https://github.com/YOUR_USERNAME/togmal-demo.git

# Verify remotes
git remote -v
```

You should see:
```
github  https://github.com/YOUR_USERNAME/togmal-demo.git (fetch)
github  https://github.com/YOUR_USERNAME/togmal-demo.git (push)
origin  https://huggingface.co/spaces/JustTheStatsHuman/Togmal-demo (fetch)
origin  https://huggingface.co/spaces/JustTheStatsHuman/Togmal-demo (push)
```

### Step 3: Push to GitHub

```bash
# First push
git push -u github main
```

You'll be prompted for:
- **Username:** Your GitHub username
- **Password:** Your GitHub Personal Access Token (PAT)

**Get your PAT:**
1. Go to: https://github.com/settings/tokens
2. Click "Generate new token" → "Classic"
3. Name: "ToGMAL Demo"
4. Scopes: Check `repo` (all repo permissions)
5. Click "Generate token"
6. Copy the token (starts with `ghp_`)
7. Use it as your password

### Step 4: Future Pushes

```bash
./push_to_both.sh
```

This pushes to both HuggingFace and GitHub automatically!

---

## Option 3: Manual Commands

### Push to HuggingFace Only
```bash
git add .
git commit -m "Your message"
git push origin main
```

### Push to GitHub Only
```bash
git add .
git commit -m "Your message"
git push github main
```

### Push to Both
```bash
git add .
git commit -m "Your message"
git push origin main
git push github main
```

---

## 🔐 Authentication Tips

### HuggingFace
- Username: `JustTheStatsHuman`
- Password: Your HF token (starts with `hf_`)
- Get token: https://huggingface.co/settings/tokens

### GitHub
- Username: Your GitHub username
- Password: Personal Access Token (starts with `ghp_`)
- Get PAT: https://github.com/settings/tokens

### Cache Credentials (Optional)
```bash
# Cache for 1 hour
git config --global credential.helper 'cache --timeout=3600'

# Or use macOS Keychain
git config --global credential.helper osxkeychain
```

---

## 📊 Repository Structure

```
HuggingFace Spaces (origin)
├── Purpose: Live demo hosting
├── URL: https://huggingface.co/spaces/JustTheStatsHuman/Togmal-demo
└── Auto-deploys on push

GitHub (github)  
├── Purpose: Code backup & collaboration
├── URL: https://github.com/YOUR_USERNAME/togmal-demo
└── Version control
```

---

## ✅ Verification

After pushing to both:

**HuggingFace:**
- View demo: https://huggingface.co/spaces/JustTheStatsHuman/Togmal-demo
- Check logs: https://huggingface.co/spaces/JustTheStatsHuman/Togmal-demo/logs

**GitHub:**
- View code: https://github.com/YOUR_USERNAME/togmal-demo
- Check commits: See your commit history

---

## 🎯 Best Practice

1. **Make changes locally**
2. **Test locally** (optional)
3. **Commit once:**
   ```bash
   git add .
   git commit -m "Description of changes"
   ```
4. **Push to both:**
   ```bash
   ./push_to_both.sh
   ```

---

## 🐛 Troubleshooting

**"fatal: remote github already exists"**
```bash
git remote remove github
git remote add github https://github.com/YOUR_USERNAME/togmal-demo.git
```

**"Authentication failed"**
- Make sure you're using PAT, not your GitHub password
- PAT needs `repo` scope
- Check token hasn't expired

**"Push rejected"**
```bash
# Pull first, then push
git pull github main --rebase
git push github main
```

---

Ready to push to both platforms! 🚀
