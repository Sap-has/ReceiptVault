# ReceiptVault for Linux

ReceiptVault is a local, privacy-first receipt tracking app. On Linux, Docker is the recommended setup, and native installation is also supported for desktop and server environments.

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
- Install Docker Engine or Docker Desktop for Linux from https://docs.docker.com/engine/install/
- No Python or Git installation is needed on the host

### Native installation

For Ubuntu/Debian:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
```

For GUI mode, also install the Tk backend:

```bash
sudo apt install -y python3-tk
```

---

## 2. Installation

### Option A: Docker (recommended)

```bash
git clone https://github.com/Sap-has/ReceiptVault.git
cd ReceiptVault
./installation/docker-up.sh
```

This starts the app in web mode and prints the local URL.

### Option B: Native Linux installation

```bash
git clone https://github.com/Sap-has/ReceiptVault.git
cd ReceiptVault
chmod +x installation/update_and_run.sh
./installation/update_and_run.sh
```

The launcher handles dependency setup and virtual environment creation automatically.

---

## 3. Running ReceiptVault

### Docker (recommended)

```bash
./installation/docker-up.sh
```

Or with Compose:

```bash
cd installation
docker compose up
```

### Native Linux

If a graphical desktop is present, you can choose Web Mode or GUI Mode. If no display is detected, web mode starts automatically.

```bash
./installation/update_and_run.sh
```

---

## 4. Using the App

### Web Mode
- Best for headless servers and remote access
- Opens in the browser when available
- The terminal will report the selected local port

### GUI Mode
- Requires a desktop environment
- Opens a native app window

### Stopping the app
- Web mode: press Ctrl+C in the terminal
- GUI mode: close the window
- Docker: press Ctrl+C or run `docker compose down`

---

## 5. Updating

### Docker

```bash
./installation/docker-up.sh
```

### Native installation

```bash
git pull origin main
```

Then restart the app.

---

## 6. Troubleshooting

### Permission denied when running scripts

```bash
chmod +x installation/update_and_run.sh installation/update_and_run.command installation/docker-up.sh
```

### GUI mode does not open
Verify that a graphical session is running and that `DISPLAY` is set:

```bash
echo $DISPLAY
```

### Port 7000 is already in use
The app will usually choose the next free port automatically.

---

## 7. Command-Line Reference

```bash
python main.py --web
python main.py --web --port 8080
python main.py --web --host 0.0.0.0
python main.py --gui
```

| Command | Description |
|---|---|
| `python main.py --web` | Start the web interface |
| `python main.py --web --port 8080` | Pin a specific port |
| `python main.py --web --host 0.0.0.0` | Listen on all interfaces |
| `python main.py --gui` | Start the desktop GUI |
