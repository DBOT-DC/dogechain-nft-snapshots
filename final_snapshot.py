#!/usr/bin/env python3
"""
FINAL NFT Snapshot — runs Aug 8 2026 10:00 UTC (2h before Dogechain shutdown).
Runs the same nft_snapshot.py but with a --final flag for the output naming.
This is the last-chance snapshot before RPC goes down.
"""
import subprocess, sys, os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT_SCRIPT = os.path.join(SCRIPT_DIR, "nft_snapshot.py")

print("=" * 60)
print("🚨 FINAL Dogechain NFT Snapshot — Pre-Shutdown")
print("=" * 60)

result = subprocess.run(
    [sys.executable, SNAPSHOT_SCRIPT],
    cwd=SCRIPT_DIR,
    capture_output=False,
    timeout=7200  # 2 hours max
)

sys.exit(result.returncode)
