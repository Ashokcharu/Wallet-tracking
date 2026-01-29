#!/usr/bin/env python3
"""
walleTracker - Solana Wallet Monitoring System
Run this file directly: python run.py
"""
import sys
import os

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Now import and run
from main import App
import asyncio

if __name__ == "__main__":
    print("🚀 Starting walleTracker v2...")
    app = App()
    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        print("\n👋 Stopped.")
