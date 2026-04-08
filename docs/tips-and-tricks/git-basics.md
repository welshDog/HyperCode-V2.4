# 📚 Git Basics — Essential Commands Guide

**What You'll Learn:**
- Clone a repository from GitHub
- Check status of your changes
- Commit your work safely
- Push changes to GitHub
- Pull updates from others

**Reading Time:** 8 minutes  
**Skill Level:** Beginner  
**Last Updated:** 2026-03-03

---

## 🎯 What is Git?

Git is a **version control system** — think of it as a **save point system for your code**.

**Like a video game:**
- You make changes (play the level)
- You commit (save your progress)
- You push (sync to cloud)
- You can go back to any save point!

**GitHub** = Cloud storage for your Git saves

---

## 🚨 The Golden Rules

**Before we start:**

1. ✅ **Always check your branch** before committing
2. ✅ **Commit often** (small saves are better than big ones)
3. ✅ **Pull before you push** (get others' changes first)
4. ⚠️ **Never commit secrets** (.env files, API keys)
5. ⚠️ **Write clear commit messages** (future you will thank you)

---

## 🔧 Essential Commands

### 1. Clone a Repository
**What it does:** Download a project from GitHub to your computer  
**Risk Level:** 🟢 **ZERO RISK**

```bash
# Clone HyperCode V2.0
git clone https://github.com/welshDog/HyperCode-V2.0.git

# Go into the folder
cd HyperCode-V2.0
```

**What happens:**
- Creates a new folder with the repo name
- Downloads all files + entire history
- Sets up connection to GitHub (called "origin")

**When to use:** First time setting up a project

---

### 2. Check Status
**What it does:** See what files you've changed  
**Risk Level:** 🟢 **ZERO RISK** (read-only)

```bash
# See what's changed
git status
```

**Output example:**
```
On branch main
Your branch is up to date with 'origin/main'.

Changes not staged for commit:
  modified:   README.md
  modified:   docs/tips-and-tricks/git-basics.md

Untracked files:
  docs/new-guide.md
```

**Color coding:**
- **Red** = Changed but not staged
- **Green** = Staged (ready to commit)
- **Gray** = New files not tracked yet

**When to use:** Before committing, to see what you're about to save

---

### 3. Add Files (Stage Changes)
**What it does:** Mark files to include in your next commit  
**Risk Level:** 🟢 **ZERO RISK** (just preparing)

```bash
# Add a specific file
git add README.md

# Add all changed files in a folder
git add docs/

# Add ALL changed files (use carefully!)
git add .
```

**Think of it like:** Putting items in your shopping cart before checkout

**When to use:** After making changes, before committing

---

### 4. Commit Your Changes
**What it does:** Save your changes with a message  
**Risk Level:** 🟡 **LOCAL ONLY** (doesn't affect GitHub yet)

```bash
# Commit with a message
git commit -m "📚 Add Git Basics guide"

# Commit all changed files (skips 'git add')
git commit -am "Update README and docs"
```

**Good commit messages:**
```bash
✅ git commit -m "📸 Add screenshot gallery documentation"
✅ git commit -m "Fix: Agent crash on startup"
✅ git commit -m "Update dependencies to latest versions"
```

**Bad commit messages:**
```bash
❌ git commit -m "stuff"
❌ git commit -m "fix"
❌ git commit -m "asdfasdf"
```

**When to use:** After staging files with `git add`

---

### 5. Push to GitHub
**What it does:** Upload your commits to GitHub  
**Risk Level:** 🟡 **AFFECTS REMOTE** (others will see this)

```bash
# Push to main branch
git push origin main

# Push your current branch (whatever it is)
git push
```

**What happens:**
- Your commits upload to GitHub
- Others can now see your changes
- Your local and remote are now synced

**⚠️ BEFORE YOU PUSH:**
```bash
# Always pull first!
git pull origin main
```

**When to use:** After committing, when you want to share your work

---

### 6. Pull from GitHub
**What it does:** Download others' changes from GitHub  
**Risk Level:** 🟡 **MERGES CODE** (can cause conflicts)

```bash
# Pull latest changes from main
git pull origin main

# Pull from your current branch
git pull
```

**What happens:**
- Downloads new commits from GitHub
- Merges them into your local code
- Updates your files

**⚠️ IMPORTANT:**
- Always commit or stash your changes BEFORE pulling
- If you have uncommitted work, Git will warn you

**When to use:** 
- Before starting work each day
- Before pushing your changes
- When someone says "I just pushed an update"

---

## 📝 Complete Workflow Example

**Scenario:** You want to add a new tip to the knowledge base.

### Step 1: Start Fresh
```bash
# Make sure you're on main
git checkout main

# Get latest changes
git pull origin main
```
**Risk:** 🟢 Safe

---

### Step 2: Create Your Changes
```bash
# Create a new file
echo "# My Tip" > docs/tips-and-tricks/my-tip.md

# Edit it (use your favorite editor)
code docs/tips-and-tricks/my-tip.md
```
**Risk:** 🟢 Local only

---

### Step 3: Check What Changed
```bash
# See your changes
git status

# See the actual differences
git diff
```
**Risk:** 🟢 Read-only

---

### Step 4: Stage Your Changes
```bash
# Add your new file
git add docs/tips-and-tricks/my-tip.md

# Verify it's staged
git status
```
**Risk:** 🟢 Just preparing

---

### Step 5: Commit
```bash
# Save with a clear message
git commit -m "📚 Add my-tip guide to knowledge base"
```
**Risk:** 🟡 Local only (not on GitHub yet)

---

### Step 6: Push to GitHub
```bash
# Pull first (good habit!)
git pull origin main

# Now push
git push origin main
```
**Risk:** 🟡 Now public on GitHub!

---

### Step 7: Verify on GitHub
```
1. Go to https://github.com/welshDog/HyperCode-V2.0
2. Navigate to docs/tips-and-tricks/
3. See your new file!
```
**Risk:** 🟢 Just looking

---

## ⚡ Quick Reference Cheat Sheet

```bash
# === STATUS & INFO ===
git status              # What's changed?
git log --oneline       # Recent commits
git branch              # Which branch am I on?

# === GETTING CODE ===
git clone <url>         # Download repo
git pull                # Get latest changes

# === SAVING WORK ===
git add <file>          # Stage specific file
git add .               # Stage all changes
git commit -m "msg"     # Save with message
git commit -am "msg"    # Stage + commit (tracked files only)

# === SHARING WORK ===
git push                # Upload to GitHub
git push origin main    # Upload to main branch

# === UNDO (SAFE) ===
git checkout -- <file>  # Discard changes to file
git reset HEAD <file>   # Unstage file
git stash               # Temporarily save changes
git stash pop           # Restore stashed changes
```

---

## 🚨 Common Mistakes & Fixes

### Mistake 1: "I committed to the wrong branch!"
**Fix:**
```bash
# See your last commit SHA
git log --oneline -1

# Switch to correct branch
git checkout correct-branch

# Bring that commit here (cherry-pick)
git cherry-pick <SHA>

# Go back to wrong branch
git checkout wrong-branch

# Remove the commit (keep changes)
git reset --soft HEAD~1
```
**Risk:** 🟡 Medium (but fixable)

---

### Mistake 2: "I want to undo my last commit!"
**Fix (keep the changes):**
```bash
# Undo commit, keep files changed
git reset --soft HEAD~1

# Your changes are still there!
git status
```
**Risk:** 🟡 Safe (changes preserved)

**Fix (discard everything):**
```bash
# DANGER: Deletes the commit AND changes
git reset --hard HEAD~1
```
**Risk:** 🔴 DANGEROUS (can't undo!)

---

### Mistake 3: "I accidentally committed my .env file!"
**Fix:**
```bash
# Remove from Git but keep the file
git rm --cached .env

# Add to .gitignore
echo ".env" >> .gitignore

# Commit the fix
git add .gitignore
git commit -m "Remove .env from tracking"
git push
```
**Risk:** 🟡 Safe fix, but damage may be done  
**⚠️ IMPORTANT:** If you pushed it, rotate your API keys immediately!

---

### Mistake 4: "My push was rejected!"
**Error message:**
```
! [rejected]        main -> main (fetch first)
```

**Fix:**
```bash
# Someone else pushed first - pull their changes
git pull origin main

# Resolve any conflicts (if needed)
# Then push again
git push origin main
```
**Risk:** 🟡 Safe process

---

## 📊 Visual Workflow

```
💻 YOUR COMPUTER              🌐 GITHUB
┌──────────────────────────────┐
│ Working Directory         │
│ (your files)              │
└─────────┬────────────────────┘
         │ git add
         ↓
┌─────────┴────────────────────┐
│ Staging Area              │
│ (ready to commit)         │
└─────────┬────────────────────┘
         │ git commit
         ↓
┌─────────┴────────────────────┐
│ Local Repository          │
│ (saved commits)           │
└─────────┬────────────────────┘
         │ git push
         ↓
┌─────────┴────────────────────┐
│ Remote Repository         │  ← GITHUB
│ (GitHub)                  │
└──────────────────────────────┘
         ↑ git pull
         │
    (gets others' changes)
```

---

## 🔗 Related Guides

- [Git Commit SHA Guide](git-commit-sha-guide.md) — Understand commit SHAs
- [Branch Management](branch-management.md) 📋 — Work with branches
- [Undo Changes](undo-changes.md) 📋 — Fix mistakes safely
- [GitHub Web Interface](github-web-guide.md) 📋 — Use GitHub without terminal

---

## 📚 Glossary

| Term | What It Means |
|:-----|:--------------|
| **Repository (Repo)** | A project folder tracked by Git |
| **Commit** | A saved snapshot of your code |
| **Push** | Upload commits to GitHub |
| **Pull** | Download commits from GitHub |
| **Clone** | Download a repo for the first time |
| **Branch** | A parallel version of your code |
| **Merge** | Combine two branches |
| **Origin** | The GitHub remote (default name) |
| **HEAD** | Your current position in Git history |
| **SHA** | Unique ID for a commit (40 chars) |

---

## 🎯 Summary

**The Basic Git Cycle:**
1. 🔄 **Pull** — Get latest changes (`git pull`)
2. ✏️ **Edit** — Make your changes
3. 👀 **Status** — Check what changed (`git status`)
4. ➕ **Add** — Stage files (`git add`)
5. 💾 **Commit** — Save locally (`git commit -m "message"`)
6. 🚀 **Push** — Upload to GitHub (`git push`)

**Remember:**
- ✅ Commit often (small saves)
- ✅ Pull before push (avoid conflicts)
- ✅ Write clear messages (help future you)
- ⚠️ Never commit secrets (.env, API keys)

---

**Created By:** HyperCode Documentation Team  
**Maintained By:** BROski (Hyper Orchestrator)  
**Last Updated:** 2026-03-03  
**Feedback:** Open an issue or discussion on GitHub!
