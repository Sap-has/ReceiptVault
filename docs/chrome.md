# ReceiptVault for ChromeOS

ReceiptVault is a local, privacy-first receipt tracking app. On ChromeOS, Docker is the recommended setup, and the app can also run from the Linux container provided by Crostini.

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
- Enable Linux development environment in ChromeOS settings
- Install Docker Desktop or Docker Engine inside the Linux container if available
- No Python or Git installation is required on the host

### Native installation
In the Linux terminal, install:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
```

---

## 2. Installation

### Option A: Docker (recommended)

```bash
git clone https://github.com/Sap-has/ReceiptVault.git
cd ReceiptVault
./installation/docker-up.sh
```

This runs the app in web mode and opens the local URL in the browser when available.

### Option B: Native ChromeOS installation

```bash
git clone https://github.com/Sap-has/ReceiptVault.git
cd ReceiptVault
chmod +x installation/update_and_run.sh
./installation/update_and_run.sh
```

ChromeOS will usually start in web mode automatically.

---

## 3. Running ReceiptVault

### Docker (recommended)

```bash
./installation/docker-up.sh
```

### Native ChromeOS

```bash
./installation/update_and_run.sh
```

The app runs best in the Linux container and should open a local browser window when possible.

---

## 4. Using the App

### Web Mode
- Recommended for ChromeOS users
- Opens in the browser from the Linux environment
- Great for headless or lightweight setups

### Stopping the app
- Web mode: press Ctrl+C in the terminal
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

### Linux container is not available
Go to ChromeOS settings and enable the Linux development environment.

### Permission denied when running scripts

```bash
chmod +x installation/update_and_run.sh installation/update_and_run.command installation/docker-up.sh
```

### Browser does not open
Wait a few seconds and refresh the page, or check the terminal output for the assigned port.

---

## 7. Command-Line Reference

```bash
python main.py --web
python main.py --web --port 8080
python main.py --web --host 0.0.0.0
```

| Command | Description |
|---|---|
| `python main.py --web` | Start the web interface |
| `python main.py --web --port 8080` | Pin a specific port |
| `python main.py --web --host 0.0.0.0` | Listen on all interfaces |
