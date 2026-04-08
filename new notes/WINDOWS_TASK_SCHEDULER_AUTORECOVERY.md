# Windows Task Scheduler — Auto-recovery every 5 minutes (WSL)

Goal: run `healthfix/scripts/restart-failed-agents.sh` on a schedule so exited/restarting agents are restarted automatically.

## Prereqs

1. This HealthFix pack is copied into your repo at:
   `HyperCode-V2.0\\healthfix\\...`
2. WSL is installed and your distro can run Docker Desktop integration.
3. The script is executable inside WSL:
   ```bash
   cd ~/HyperCode-V2.0
   chmod +x healthfix/scripts/restart-failed-agents.sh
   ```

## Create the scheduled task

1. Open **Task Scheduler**
2. Click **Create Task…**
3. **General**
   - Name: `HyperCode - Restart Failed Agents`
   - “Run whether user is logged on or not” (optional)
   - “Run with highest privileges” (recommended)
4. **Triggers**
   - New Trigger → “Daily”
   - Advanced settings → “Repeat task every: 5 minutes” for “Indefinitely”
5. **Actions**
   - New Action → “Start a program”
   - Program/script:
     ```
     wsl.exe
     ```
   - Add arguments (edit the distro name if you want, otherwise default distro is fine):
     ```
     -e bash -lc "cd ~/HyperCode-V2.0 && bash healthfix/scripts/restart-failed-agents.sh >> healthfix/recovery.log 2>&1"
     ```
6. **Conditions**
   - Uncheck “Start the task only if the computer is on AC power” (if on laptop and you want it always)
7. **Settings**
   - Allow task to be run on demand ✅
   - If the task fails, restart every 1 minute (optional)

## Test

- Right click the task → **Run**
- In WSL:
  ```bash
  tail -n 200 ~/HyperCode-V2.0/healthfix/recovery.log
  ```

## Optional hardening

- Add Docker restart policies (`restart: unless-stopped` or `on-failure`) to agents so Docker does some of this automatically.
- If `wsl.exe` can’t find your repo at `~/HyperCode-V2.0`, replace with the correct Linux path.

