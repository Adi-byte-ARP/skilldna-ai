#!/usr/bin/env bash
# Installs Tesseract OCR, the one dependency in this project that isn't a
# Python package (pytesseract just wraps the system binary). Run this once
# before starting the backend if `tesseract --version` doesn't already work.
#
# Usage: bash backend/scripts/setup_ocr.sh

set -e

if command -v tesseract >/dev/null 2>&1; then
  echo "Tesseract is already installed: $(tesseract --version | head -1)"
  exit 0
fi

OS="$(uname -s 2>/dev/null || echo unknown)"

case "$OS" in
  Linux)
    echo "Detected Linux. Installing via apt-get (needs sudo)..."
    if command -v apt-get >/dev/null 2>&1; then
      sudo apt-get update && sudo apt-get install -y tesseract-ocr
    else
      echo "apt-get not found. If you're on a non-Debian distro, install the"
      echo "'tesseract-ocr' (or 'tesseract') package with your distro's package manager."
      exit 1
    fi
    ;;
  Darwin)
    echo "Detected Mac. Installing via Homebrew..."
    if command -v brew >/dev/null 2>&1; then
      brew install tesseract
    else
      echo "Homebrew not found. Install it from https://brew.sh, then run:"
      echo "  brew install tesseract"
      exit 1
    fi
    ;;
  *)
    echo "This script only automates Linux and Mac installs."
    echo ""
    echo "On Windows:"
    echo "  1. Download and run the installer from"
    echo "     https://github.com/UB-Mannheim/tesseract/wiki"
    echo "  2. Note the install path (usually C:\\Program Files\\Tesseract-OCR\\tesseract.exe)"
    echo "  3. Add it to backend/.env as:"
    echo "     TESSERACT_CMD=C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
    exit 1
    ;;
esac

echo ""
echo "Done. Verifying:"
tesseract --version | head -1
