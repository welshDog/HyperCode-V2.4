# Quick Zip Guide for BROski Agents

## Option 1: Terminal (Fastest - 10 seconds)

```bash
# Navigate to your project directory
cd /path/to/broski-agents

# Create zip file
zip -r broski-agents.zip . -x "node_modules/*" ".git/*" "dist/*" ".env.local"

# Done! File is ready to share
# Size: ~500KB (without node_modules)
```

## Option 2: Mac Finder (15 seconds)

1. Right-click folder
2. Select "Compress"
3. Renames to `broski-agents.zip`
4. Done!

## Option 3: Windows Explorer (15 seconds)

1. Right-click folder
2. Select "Send to" → "Compressed (zipped) folder"
3. Renames to `broski-agents.zip`
4. Done!

## What NOT to Include

The zip command above excludes:
- ✅ `node_modules/` (too large, 200MB+)
- ✅ `.git/` (version control, not needed)
- ✅ `dist/` (build output, regenerates)
- ✅ `.env.local` (contains API keys, never share!)

## What WILL Be Included

- ✅ All source files (.ts, .tsx, .js, .json, .md)
- ✅ Configuration files (vite, eslint, prettier, etc)
- ✅ Documentation (README, QUICKSTART, etc)
- ✅ GitHub workflows (.github/)
- ✅ .env.example (safe to share)
- ✅ .gitignore
- ✅ package.json (so others can `npm install`)

## After Someone Unzips

They'll run:
```bash
unzip broski-agents.zip
cd broski-agents
npm install        # Installs node_modules from package.json
npm run dev        # Starts dev server
```

## Share Via

- **GitHub** - Just push (recommended)
- **Email** - Zip file (~500KB)
- **Google Drive** - Upload zip
- **Dropbox** - Upload zip
- **WeTransfer** - Large files

---

**Preferred Method?** Just push to GitHub. Then people can:
```bash
git clone https://github.com/YOUR_USERNAME/broski-agents.git
cd broski-agents
npm install
npm run dev
```

No zip needed, always latest version. 🚀
