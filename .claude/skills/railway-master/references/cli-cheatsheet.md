# 🛠️ Railway CLI — Full Command Reference

## 🔐 Auth
```bash
railway login                   # Login with browser
railway login --browserless     # Login without browser (SSH, CI)
railway logout                  # Log out
railway whoami                  # Show current logged-in user
```

## 📁 Project Management
```bash
railway init                    # Create new Railway project
railway link                    # Link current dir to existing Railway project
railway link --project <id>     # Link to specific project by ID
railway unlink                  # Unlink from project
railway list                    # List all your Railway projects
railway status                  # Show current project/service/environment status
railway open                    # Open project in Railway dashboard (browser)
```

## 🚢 Deployment
```bash
railway up                      # Deploy current directory
railway up --detach             # Deploy without watching logs (great for CI)
railway up --service <name>     # Deploy to a specific service
railway deploy                  # Deploy from source
railway redeploy                # Redeploy current service (same image/code)
railway restart                 # Restart a service (without rebuild)
railway down                    # Take down a deployment
```

## ⚙️ Services
```bash
railway add                     # Add a new service or plugin
railway add --plugin postgresql # Add PostgreSQL database
railway add --plugin mysql      # Add MySQL database
railway add --plugin redis      # Add Redis
railway add --plugin mongodb    # Add MongoDB
railway service                 # Manage / switch between services
railway scale                   # Scale a service (replicas, resources)
railway delete                  # Delete a service
```

## 🔒 Variables (Env Vars)
```bash
railway variable                          # List ALL env vars for current service
railway variable --set KEY=VALUE          # Set a single variable
railway variable --set KEY1=V1 KEY2=V2    # Set multiple variables
railway variable --unset KEY              # Remove a variable
railway variable --service <name>         # Target a specific service
railway variable --environment <env>      # Target a specific environment
```

## 🌍 Environments
```bash
railway environment                       # Interactive environment switcher
railway environment <name>                # Switch to named environment (staging, production)
```

## 💻 Local Dev
```bash
railway run <command>                     # Run command with Railway env vars injected
railway shell                             # Open shell with Railway env vars loaded
railway dev                               # Start local dev with Railway tunnel
```

## 🐛 Logs & Debug
```bash
railway logs                              # Stream live logs
railway logs --tail 100                   # Last 100 log lines
railway logs --service <name>             # Logs for specific service
railway ssh                               # SSH into deployed container
railway connect                           # Connect to a database/service (creates tunnel)
railway connect postgresql                # Open psql shell to Railway PostgreSQL
railway connect redis                     # Open redis-cli to Railway Redis
```

## 🌐 Networking & Storage
```bash
railway domain                            # Manage custom domains
railway domain add <domain>               # Add custom domain
railway volume                            # Manage persistent volumes
railway volume add                        # Add a new volume
```

## 🔑 Token / API Auth (for CI/CD)
```bash
# Set as environment secret in GitHub/CI:
RAILWAY_TOKEN=<project-token>             # Project-scoped token
RAILWAY_API_TOKEN=<account-token>         # Account-scoped token

# Then run:
railway up --detach                       # Deploys without interactive auth
```

## 🧩 Useful Flag Combos
```bash
railway up --service api --environment production --detach
railway logs --service api --tail 200
railway variable --set KEY=VALUE --service worker --environment staging
```

## 🚫 .railwayignore (Speed Up Deploys)
Create `.railwayignore` in your project root to exclude unnecessary files:
```
node_modules/
.git/
__pycache__/
.env
*.pyc
dist/
.pytest_cache/
```
This massively speeds up `railway up` upload time. Always add it!
