# ReceiptVault for macOS

ReceiptVault is a local, privacy-first receipt tracking app. On macOS, Docker is the recommended path, but a native installation is also supported.

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
- Install Docker Desktop for Mac from https://www.docker.com/products/docker-desktop/
- No Python or Git installation is needed on the host

### Native installation
- Homebrew is recommended:

```bash
brew install python git
```

- Alternatively, install Python from https://www.python.org/downloads/ and Git via Xcode Command Line Tools:

```bash
xcode-select --install
```

---

## 2. Installation

### Option A: Docker (recommended)

```bash
git clone https://github.com/Sap-has/ReceiptVault.git
cd ReceiptVault
./installation/docker-up.sh
```

This builds the app image and starts the web interface automatically.

### Option B: Native macOS installation

```bash
git clone https://github.com/Sap-has/ReceiptVault.git
cd ReceiptVault
chmod +x installation/update_and_run.command
open installation/update_and_run.command
```

The first time you open the script, macOS may ask you to confirm it is safe to run.

---

## 3. Running ReceiptVault

### Docker (recommended)

```bash
./installation/docker-up.sh
```

You may also use:

```bash
cd installation
docker compose up
```

### Native macOS

Double-click the launcher in the installation folder or run:

```bash
./installation/update_and_run.command
```

---

## 4. Using the App

### Web Mode
- Best for most users
- Opens in your browser automatically
- The app prints the chosen local address and port

### GUI Mode
- Opens a native desktop window
- Useful if you prefer a desktop-style app experience

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

### The app cannot be opened because it is from an unidentified developer
Right-click the launcher, choose Open, and confirm the prompt.

### Permission denied when running scripts

```bash
chmod +x installation/update_and_run.sh installation/update_and_run.command installation/docker-up.sh
```

### Port 7000 is busy
ReceiptVault will usually select the next free port automatically.

---

## 7. Command-Line Reference

```bash
python main.py --web
python main.py --web --port 8080
python main.py --gui
```

| Command | Description |
|---|---|
| `python main.py --web` | Start the web interface |
| `python main.py --web --port 8080` | Pin a specific port |
| `python main.py --gui` | Start the desktop GUI |
