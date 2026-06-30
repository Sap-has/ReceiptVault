# ReceiptVault for Windows

ReceiptVault is a local, privacy-first receipt tracking app. On Windows, Docker is the recommended setup, but you can also run the app natively with the provided batch script.

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Installation](#2-installation)
3. [Running ReceiptVault](#3-running-receiptvault)
4. [Using the App](#4-using-the-app)
5. [Updating](#5-updating)
6. [Troubleshooting](#6-troubleshooting)
7. [Command-Line Reference](#7-command-line-reference)

---

## 1. Prerequisites

### Recommended: Docker
- Install Docker Desktop for Windows from https://www.docker.com/products/docker-desktop/
- No Python or Git installation is required on the host

### Native installation
- Python 3.11+ from https://www.python.org/downloads/
- Git from https://git-scm.com/downloads/
- During Python setup, make sure to check "Add Python to PATH"

---

## 2. Installation

### Option A: Docker (recommended)

```powershell
git clone https://github.com/Sap-has/ReceiptVault.git
cd ReceiptVault
./installation/docker-up.sh
```

This builds the container, starts the app, and prints the local URL to open in your browser.

### Option B: Native Windows installation

```powershell
git clone https://github.com/Sap-has/ReceiptVault.git
cd ReceiptVault
installation\run_app.bat
```

The launch script will create a virtual environment and install the required dependencies automatically on first run.

---

## 3. Running ReceiptVault

### Docker (recommended)

From the project root:

```powershell
./installation/docker-up.sh
```

You can also use Compose directly:

```powershell
cd installation
docker compose up
```

### Native Windows

Double-click the batch file or run:

```powershell
installation\run_app.bat
```

You will be asked whether to start Web Mode or GUI Mode.

---

## 4. Using the App

### Web Mode
- Opens in your default browser
- Best for most users
- The app will show the assigned local address and port

### GUI Mode
- Opens a desktop window
- Works with a graphical Windows desktop session

### Stopping the app
- Web mode: press Ctrl+C in the terminal
- GUI mode: close the window
- Docker: press Ctrl+C or run `docker compose down` from the installation folder

---

## 5. Updating

ReceiptVault checks for updates each time you launch it.

### Docker
Run the same command again:

```powershell
./installation/docker-up.sh
```

### Native installation
Run:

```powershell
git pull origin main
```

Then start the app again.

---

## 6. Troubleshooting

### Python not found
Reinstall Python and confirm that the PATH option was enabled.

### Script blocked by Windows security
If the batch file is blocked, run it from PowerShell instead of double-clicking it.

### Port 7000 is already in use
The app will usually select the next available port automatically.

### Docker refuses to start
Check that Docker Desktop is running and that virtualization is enabled in your system settings.

---

## 7. Command-Line Reference

```powershell
python main.py --web
python main.py --web --port 8080
python main.py --gui
```

| Command | Description |
|---|---|
| `python main.py --web` | Start the web interface |
| `python main.py --web --port 8080` | Pin a specific port |
| `python main.py --gui` | Start the desktop GUI |
