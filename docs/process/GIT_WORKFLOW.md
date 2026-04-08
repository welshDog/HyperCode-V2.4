# Git Workflow & Contribution Guide

## 🚀 Getting Started

Clone the repository:
```bash
git clone https://github.com/welshDog/HyperCode-V2.0.git
cd HyperCode-V2.0
```

> Note: This repo does not require git submodules for standard development.

## 🤝 Contribution Workflow

1. **Pull Latest Changes**:
   ```bash
   git pull origin main
   ```

2. **Create Feature Branch**:
   ```bash
   git checkout -b feat/my-feature
   ```

3. **Commit & Push**:
   ```bash
   git add .
   git commit -m "feat: description"
   git push origin feat/my-feature
   ```

4. **Merge Conflicts**:
   If you encounter conflicts:
   - Resolve file conflicts as usual.
   - Use `git status` to see what is happening.

## 🛡️ Security

- **NEVER** commit `.env` files.
- **NEVER** commit secrets or API keys.
- Use `.env.example` for templates.
- The `.gitignore` is configured to exclude sensitive files.

## 🆘 Troubleshooting

If you hit auth issues pushing, confirm your GitHub credentials and remote URL are correct.
