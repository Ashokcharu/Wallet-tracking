# Proposal: walleTracker MVP

## Overview
walleTracker is a lean, free-to-operate Solana wallet monitoring system designed to detect meme token trading activity. It targets traders who want to follow "smart money" without paying for expensive private APIs or RPCs.

## Problem Statement
Meme token trading on Solana is fast-paced. Tracking successful wallets manually is tedious, and existing automated tools often require paid subscriptions or complex setups.

## Proposed Solution
A Python-based backend that polls public Solana RPCs to monitor a curated list of wallets. It detects buy events on major DEXs (Raydium, Jupiter, Pump.fun) and alerts the user via Telegram.

## Scope
- Manual wallet entry and management.
- Real-time (best-effort) monitoring of wallet transactions.
- Detection of meme token buys.
- Aggregate signals: "X wallets bought $TOKEN".
- Simple profit/loss tracking and wallet accuracy scoring.

## Out of Scope
- Multi-chain support (Solana only).
- Automated trading (copy-trading).
- Complex charting or UI (Terminal/Telegram focus).
- Paid API integrations.
