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
| Windows 10 / 11 | ✅ | ✅ | `run_app.bat` |
| macOS 12+ | ✅ | ✅ | `update_and_run.command` |
| Linux (with desktop) | ✅ | ✅ | `update_and_run.sh` |
| Linux (headless / server) | ✅ | ❌ | `update_and_run.sh` (auto web) |
| ChromeOS (Crostini) | ✅ | ❌ | `update_and_run.sh` (auto web) |
| Docker | ✅ (default) | ✅ (Linux X11) | `docker compose up` |

> **Web Mode** opens ReceiptVault in your default browser at `http://127.0.0.1:7000`. It works on every OS and is the recommended choice for most users.  
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
git clone https://github.com/YOUR_GITHUB_USERNAME/ReceiptVault.git
cd ReceiptVault
```

> If you don't have Git, you can also click **Code → Download ZIP** on the GitHub page and extract the folder.

### Step 2 – Make scripts executable (macOS / Linux only)

```bash
chmod +x update_and_run.sh update_and_run.command
```

That's it. The launch scripts handle everything else (virtual environment, dependency installation) automatically on first run.

---

## 4. Running the App

### Windows

Double-click `run_app.bat` **or** run it from a terminal:

```cmd
run_app.bat
```

You will be asked to choose **Web Mode** or **GUI Mode** each time you launch.

### macOS

Double-click `update_and_run.command` in Finder.

> The first time you open it, macOS may show a security warning ("can't be opened because it's from an unidentified developer"). Right-click → **Open** → **Open** to bypass this. You won't need to do it again.

You will be asked to choose **Web Mode** or **GUI Mode** each time you launch.

### Linux

```bash
./update_and_run.sh
```

- **If a graphical desktop is detected**, you will be asked to choose Web Mode or GUI Mode.
- **If no display is detected** (headless server, SSH without X forwarding), Web Mode starts automatically. Browse to `http://YOUR_SERVER_IP:7000` from another machine (only if you change `--host` to `0.0.0.0`; by default it only listens on localhost for security).

### ChromeOS

Open the Linux terminal and run:

```bash
cd ~/ReceiptVault      # or wherever you cloned it
./update_and_run.sh
```

Web Mode starts automatically. The script detects ChromeOS and skips the mode prompt. Your default browser will open `http://127.0.0.1:7000`.

### Docker (any OS)

**Web mode** (recommended):
```bash
docker compose up
```
Then open `http://127.0.0.1:7000` in your browser.

**GUI mode** (Linux with X11 only):
```bash
xhost +local:docker          # allow Docker to use your display
docker compose --profile gui up
```

**One-off run without Compose:**
```bash
docker build -t receipt-vault .
docker run -p 7000:7000 -v "$(pwd)/data:/app/data" receipt-vault
```

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

After the app starts your browser opens to `http://127.0.0.1:7000` automatically. The available API endpoints are shown on the home page; a full UI is served from the same address.

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

- **Web Mode**: Press `Ctrl+C` in the terminal window where you launched the app.
- **GUI Mode**: Close the desktop window.

---

## 7. Updating

ReceiptVault can update itself automatically. **Each time you use a launch script it pulls the latest code from GitHub before starting.**

You can also trigger an update manually:

- **From the web interface**: `POST /api/update` (or click the Update button when the UI is complete).
- **From the GUI**: Click the **⬆ Update App** button in the sidebar.
- **From the terminal**: `git pull origin main` inside the project folder.

After an update the app restarts automatically to apply the changes.

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
chmod +x update_and_run.sh update_and_run.command
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

Launch the app on a different port:
```bash
python main.py --web --port 8080
```
Or find and stop the process using port 7000:
```bash
lsof -i :7000          # macOS / Linux
netstat -ano | findstr 7000   # Windows
```

### After an update the app shows an error

Run `pip install -r requirements.txt` inside the virtual environment (the launch script does this automatically). If the problem continues, delete the `venv/` folder and re-run the launch script.

---

## 11. Command-Line Reference

```
python main.py --web            # Start web server (default port 7000)
python main.py --web --port 8080            # Use a different port
python main.py --web --host 0.0.0.0         # Listen on all interfaces (LAN access)
python main.py --web --no-browser           # Don't auto-open a browser tab
python main.py --gui                        # Start desktop GUI window
```

| Flag | Description |
|---|---|
| `--web` | Launch the web interface via Flask |
| `--gui` | Launch the native desktop GUI via CustomTkinter |
| `--host HOST` | (Web only) Bind address, default `127.0.0.1` |
| `--port PORT` | (Web only) Port number, default `7000` |
| `--no-browser` | (Web only) Skip auto-opening a browser tab |

---

*ReceiptVault stores all data locally. Your receipts are yours.*