# 📄 ReceiptVault

ReceiptVault is a **local, privacy-first** receipt-tracking application. It runs entirely on your own computer – no cloud accounts, no subscriptions, no data ever leaves your machine. You access it either through your web browser (recommended for most people) or through a native desktop window, depending on your OS and preference.

---

## Table of Contents

1. [Supported Platforms & Modes](#1-supported-platforms--modes)
2. [Prerequisites](#2-prerequisites)
3. [Installation](#3-installation)
4. [Running the App](#4-running-the-app)
   - [Windows](#windows)
   - [macOS](#macos)
   - [Linux](#linux)
   - [ChromeOS](#chromeos)
   - [Docker (any OS)](#docker-any-os)
5. [Choosing Between Web Mode and GUI Mode](#5-choosing-between-web-mode-and-gui-mode)
6. [Using ReceiptVault](#6-using-receiptvault)
7. [Updating](#7-updating)
8. [Your Data](#8-your-data)
9. [Uninstalling](#9-uninstalling)
10. [Troubleshooting](#10-troubleshooting)
11. [Command-Line Reference](#11-command-line-reference)

---

## 1. Supported Platforms & Modes

| Operating System | Web Mode | GUI Mode | Launch Script |
|---|---|---|---|
| Windows 10 / 11 | ✅ | ✅ | `installation/run_app.bat` |
| macOS 12+ | ✅ | ✅ | `installation/update_and_run.command` |
| Linux (with desktop) | ✅ | ✅ | `installation/update_and_run.sh` |
| Linux (headless / server) | ✅ | ❌ | `installation/update_and_run.sh` (auto web) |
| ChromeOS (Crostini) | ✅ | ❌ | `installation/update_and_run.sh` (auto web) |
| Docker | ✅ (default) | ✅ (Linux X11) | `./installation/docker-up.sh` (or `docker compose up` from inside `installation/`) |

> **Web Mode** opens ReceiptVault in your default browser. It picks the first free port starting at 7000 automatically and tells you which one it used, so it works even if something else on your machine is already using 7000. It works on every OS and is the recommended choice for most users. 
> **GUI Mode** opens a native desktop window using CustomTkinter. It requires a graphical desktop environment (not available on ChromeOS or headless Linux).

---

## 2. Prerequisites

### All platforms
| Requirement | Minimum Version | Notes |
|---|---|---|
| **Python** | 3.11 | See per-OS instructions below |
| **Git** | Any recent | Required for auto-updates |

### Windows
- Download Python from [python.org](https://www.python.org/downloads/) – **check "Add Python to PATH"** during setup.
- Download Git from [git-scm.com](https://git-scm.com/downloads).

### macOS
Option A (Homebrew – recommended):
```bash
brew install python git
```
Option B: Download Python from [python.org](https://www.python.org/downloads/); Git is included with Xcode Command Line Tools (`xcode-select --install`).

### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
```
For GUI mode, also install the Tk backend:
```bash
sudo apt install -y python3-tk
```

### ChromeOS
Enable Linux (Crostini) via **Settings → Advanced → Developers → Linux development environment**, then open the Linux terminal and run:
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
```

### Docker (optional alternative)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows / macOS) or Docker Engine (Linux).
- No Python or Git installation needed on the host.

---

## 3. Installation

### Step 1 – Download ReceiptVault

Open a terminal (or Git Bash on Windows) and clone the repository:

```bash
git clone https://github.com/Sap-has/ReceiptVault.git
cd ReceiptVault
```

> If you don't have Git, you can also click **Code → Download ZIP** on the GitHub page and extract the folder.

All of the installation/launch tooling (Dockerfile, docker-compose.yml, docker-up.sh, requirements.txt, run_app.bat, update_and_run.command, update_and_run.sh) lives inside the `installation/` subfolder to keep the project root focused on the application code itself (`main.py`, `core/`, `gui/`, `web/`, `utils.py`). The launch scripts below all account for this automatically — they locate the repo root themselves, so you can run them either from inside `installation/` or by pointing at them from the repo root (e.g. `./installation/update_and_run.sh`).

### Step 2 – Make scripts executable (macOS / Linux only)

```bash
chmod +x installation/update_and_run.sh installation/update_and_run.command installation/docker-up.sh
```

That's it. The launch scripts handle everything else (virtual environment, dependency installation) automatically on first run.

---

## 4. Running the App

### Windows

Double-click `installation\run_app.bat` **or** run it from a terminal:

```cmd
installation\run_app.bat
```

You will be asked to choose **Web Mode** or **GUI Mode** each time you launch.

### macOS

Double-click `update_and_run.command` inside the `installation/` folder in Finder.

> The first time you open it, macOS may show a security warning ("can't be opened because it's from an unidentified developer"). Right-click → **Open** → **Open** to bypass this. You won't need to do it again.

You will be asked to choose **Web Mode** or **GUI Mode** each time you launch.

### Linux

```bash
./installation/update_and_run.sh
```

- **If a graphical desktop is detected**, you will be asked to choose Web Mode or GUI Mode.
- **If no display is detected** (headless server, SSH without X forwarding), Web Mode starts automatically. The terminal will print the port it picked (starting at 7000, or the next free one if that's taken) — browse to http://YOUR_SERVER_IP:<that port> from another machine (only if you change --host to 0.0.0.0; by default it only listens on localhost for security).

### ChromeOS

Open the Linux terminal and run:

```bash
cd ~/ReceiptVault      # or wherever you cloned it
./installation/update_and_run.sh
```

Web Mode starts automatically. The script detects ChromeOS and skips the mode prompt. Your default browser will open to the URL printed in the terminal (http://127.0.0.1:7000 unless that port is already in use, in which case the next free one is used instead).

### Docker (any OS)

**Web mode** (recommended, and the default — see below):
```bash
./installation/docker-up.sh
```
This builds the image, starts the container, and prints the URL to open — including the actual port, which is chosen automatically so it won't clash with anything else already using 7000 on your machine. (`docker-up.sh` automatically moves into `installation/` itself before running, so this works whether you run it from the repo root as shown above or from inside `installation/` directly.)

You can also use plain Compose — since `docker-compose.yml` lives in `installation/`, `cd` there first:
```bash
cd installation
docker compose up
```

`docker compose up` always starts web mode by default — the GUI service is only included when you explicitly ask for it (see below), so a bare `docker compose up` never starts the GUI by accident. With plain Compose you'll need to look up the assigned port yourself once it's running (still from inside `installation/`):
```bash
docker compose ps              # look in the PORTS column, e.g. 0.0.0.0:54827->7000/tcp
docker compose port app 7000   # prints just the host port
```
Then open http://localhost:<that port> in your browser.

**GUI mode** (Linux with X11 only):
```bash
xhost +local:docker          # allow Docker to use your display
cd installation
docker compose --profile gui up
```
Or, from the repo root: `./installation/docker-up.sh --gui`

**One-off run without Compose:**

Run this from the **repo root** (not from inside `installation/`) — the Dockerfile's `COPY . .` needs to see the whole project (`core/`, `gui/`, `web/`, `main.py`, etc.), so the build context has to be the root even though the Dockerfile itself now lives in `installation/`:
```bash
docker build -f installation/Dockerfile -t receipt-vault .
docker run --name receipt-vault -p 7000 -v "$(pwd)/data:/app/data" receipt-vault
docker port receipt-vault 7000   # find out which host port got assigned
```
(-p 7000 with no host-side number tells Docker to pick any free host port. Pin a specific one instead with -p 7000:7000, if you'd rather choose it yourself and are confident it's free.)

---

## 5. Choosing Between Web Mode and GUI Mode

| | Web Mode | GUI Mode |
|---|---|---|
| **Interface** | Browser tab | Desktop window |
| **Works on ChromeOS** | ✅ | ❌ |
| **Works headless** | ✅ | ❌ |
| **Multiple browser tabs** | ✅ | N/A |
| **Keyboard shortcuts** | Browser shortcuts | App shortcuts |
| **Feels like** | A website | A desktop app |
| **Recommended for** | Most users | Users who prefer native apps |

Both modes share the **same database** (`data/bills_data.db`). You can switch between them freely.

---

## 6. Using ReceiptVault

### Web Mode

After the app starts, your browser opens automatically to the URL printed in the terminal — http://127.0.0.1:7000 by default, or the next free port if 7000 is already in use on your machine. The available API endpoints are shown on the home page; a full UI is served from the same address.

### GUI Mode

A native window opens with a sidebar for navigation:

| Section | Purpose |
|---|---|
| Dashboard | Summary of spending |
| All Receipts | Browse, filter, search bills |
| Add Receipt | Manually log a new receipt or import via OCR |
| Categories | Manage spending categories |
| Vendors | Manage vendor names |

### OCR Receipt Scanning

ReceiptVault uses **PaddleOCR** to extract data from receipt photos. To scan a receipt:

1. Go to **Add Receipt**.
2. Click **Scan Receipt** and select a photo (JPEG or PNG).
3. Review the extracted date, vendor, and amount before saving.

### Stopping the App

**Native Mode (Windows, macOS, Linux):**
- **Web Mode**: Press `Ctrl+C` in the terminal window where you launched the app. The server will shut down gracefully.
- **GUI Mode**: Close the desktop window. The app will close immediately.

**Docker:**
- Press `Ctrl+C` in the terminal where you ran `./installation/docker-up.sh`. The container will shut down gracefully and all resources will be cleaned up.
- If you ran `docker-up.sh -d` (detached mode), or if you ran `docker compose up` manually, stop the container with:
  ```bash
  docker compose down       # from inside installation/ folder
  ```

---

## 7. Updating

ReceiptVault automatically checks for updates from GitHub **each time you launch the app**. The latest code is pulled before the app starts.

### Automatic updates when launching:
- **Windows**: Each time you run `installation\run_app.bat`
- **macOS**: Each time you double-click `installation/update_and_run.command`
- **Linux**: Each time you run `./installation/update_and_run.sh`
- **Docker**: Each time you run `./installation/docker-up.sh` or `docker compose up` (the `--build` flag ensures the image is rebuilt with latest code)

### Manual update triggers:
- **Web Mode UI**: Click the "🔄 Update" button (or `POST /api/update` API endpoint). The browser will show an update notification, and the app will restart shortly with the latest code.
- **GUI Mode**: Click the **⬆ Update App** button in the sidebar. A popup will appear and the app will restart.
- **Terminal** (any platform): Run `git pull origin main` inside the project folder, then restart the app.

### What happens during an update:
1. The latest code is pulled from GitHub
2. Dependencies are checked and updated if needed (happens automatically in launch scripts)
3. The app restarts automatically
4. Your database and data in `data/bills_data.db` is never touched – only the application code changes

If an update fails, the app will continue running with the current version. Check the terminal output for error details.

---

## 8. Your Data

| Item | Location |
|---|---|
| **Database** | `data/bills_data.db` (inside the project folder) |
| **Backups** | Copy this file anywhere to back up all your receipts |
| **Migration** | Move the whole project folder (or just `data/`) to a new machine |

The database is never sent to any server. Updates from GitHub only change the application code; your `data/` folder is never overwritten or touched by `git pull`.

### Backing up

```bash
cp data/bills_data.db ~/Desktop/bills_backup_$(date +%F).db
```

### Restoring

Replace the `data/bills_data.db` file with your backup copy and restart the app.

---

## 9. Uninstalling

1. Close the app if it is running.
2. Delete the project folder:
   ```bash
   rm -rf ~/ReceiptVault      # macOS / Linux
   # On Windows: delete the folder in File Explorer
   ```
3. (Optional) Remove Python and Git if you installed them only for this app.

---

## 10. Troubleshooting

### "Python was not found" / "python3: command not found"

Make sure Python 3.11+ is installed and on your PATH. On Windows, reinstall Python and check **"Add Python to PATH"**.

### "Permission denied" when running the script (macOS / Linux)

```bash
chmod +x installation/update_and_run.sh installation/update_and_run.command installation/docker-up.sh
```

### The browser opens but shows "This site can't be reached"

The web server may still be starting. Wait 2–3 seconds and refresh. If the problem persists, check the terminal for error messages.

### GUI mode window doesn't appear (Linux)

Make sure you have a graphical session running and that `DISPLAY` is set:
```bash
echo $DISPLAY      # should print something like :0 or :1
```
Also install the Tk backend: `sudo apt install python3-tk`

### OCR results are inaccurate

- Use a well-lit, flat photo of the receipt.
- Crop the image to just the receipt before scanning.
- PaddleOCR downloads model files on first use; make sure you are connected to the internet for that initial download.

### Port 7000 is already in use
As of the current version, web mode automatically picks the next free port starting at 7000 and tells you which one it's using — so you generally don't need to do anything. This section only applies if you've pinned a specific port yourself.

If you passed --port explicitly (e.g. python main.py --web --port 8080) and that exact port is taken, the app will exit with a clear error instead of guessing for you — just drop --port to go back to auto-selection, or pick a different number. To find out what's using a given port:
```bash
lsof -i :8080          # macOS / Linux
netstat -ano | findstr 8080   # Windows
```

If you see an error that no free port could be found at all (unlikely — it scans 100 ports starting at 7000), something unusual is tying up a large range of ports on your machine; free some up or specify a known-free --port manually.

### After an update the app shows an error

Run `pip install -r installation/requirements.txt` inside the virtual environment (the launch script does this automatically). If the problem continues, delete the `venv/` folder and re-run the launch script.

---

## 11. Command-Line Reference

```
python main.py --web            # Start web server (auto-picks a free port starting at 7000)
python main.py --web --port 8080            # Pin a specific port (errors if it's already taken)
python main.py --web --host 0.0.0.0         # Listen on all interfaces (LAN access)
python main.py --web --no-browser           # Don't auto-open a browser tab
python main.py --gui                        # Start desktop GUI window
```

| Flag | Description |
|---|---|
| `--web` | Launch the web interface via Flask |
| `--gui` | Launch the native desktop GUI via CustomTkinter |
| `--host HOST` | (Web only) Bind address, default `127.0.0.1` |
| `--port PORT` | (Web only) Pin a specific port number. If omitted, the next free port starting at 7000 is selected automatically and printed to the terminal. |
| `--no-browser` | (Web only) Skip auto-opening a browser tab |

---

*ReceiptVault stores all data locally. Your receipts are yours.*