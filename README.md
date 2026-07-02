# 📄 ReceiptVault

ReceiptVault is a local, privacy-first receipt-tracking app. Docker is the recommended way to run it on any operating system.

## Table of Contents

1. [Windows](docs/windows.md)
2. [macOS](docs/mac.md)
3. [Linux](docs/linux.md)
4. [ChromeOS](docs/chrome.md)

---

## Docker (Recommended)

```bash
git clone https://github.com/Sap-has/ReceiptVault.git
cd ReceiptVault
./installation/docker-up.sh
```

This builds the image, starts the app, and prints the local URL to open in your browser.

## Using the App

Once the container is running, open the URL shown in the terminal. The web interface is the default and recommended experience.

## Updating

Run the same Docker command again to pull the latest changes and rebuild the container:

```bash
./installation/docker-up.sh
```

## Troubleshooting

If you run into issues, use the operating-system-specific guide for more detailed steps:

- [Windows](docs/windows.md)
- [macOS](docs/mac.md)
- [Linux](docs/linux.md)
- [ChromeOS](docs/chrome.md)

---

*ReceiptVault stores all data locally. Your receipts are yours.*