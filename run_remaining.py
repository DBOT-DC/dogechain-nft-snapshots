#!/usr/bin/env python3
"""
Run token-level enumeration for the 19 remaining collections.
Processes them sequentially with progress logging to /tmp/token_enum_progress.log
"""
import subprocess, sys, time, os

# The 19 collections that need token-level data
REMAINING = [
    ("0x92b995f34cbf637d59c66782e90dfec3ce3c202b", "DTOOLS-NFT"),
    ("0x221ebe2243d3a4be8b7d53a98c5aebbc37bd7c33", "TDH-NFT"),
    ("0x011f614b13ef08b905a2ae68443f6344cce32046", "DG"),
    ("0xd7f68f4349527dae381233daa120bb42e310c986", "KIMON"),
    ("0xafa5f9313f1f2b599173f24807a882f498be118c", "hMERK"),
    ("0x45944dd5145ac7815d29c8c5d7c7f1801a7aa6c3", "FFNFTS"),
    ("0xfb035ab15a174f6c0702901e7b2a24db8f8cd026", "DCC2"),
    ("0xf497d4826c3585cee69a0fd3b71b057d7056f64a", "MASON"),
    ("0x870fb39328958d9d363ddb88c2e6a4a32a5bef11", "BDKC2"),
    ("0x474faddd73b6ff260efd281b4eb375a6fd7ea9bc", "DCP"),
    ("0x5b68749a85e84cbf3a04526d87296d4d988462dc", "WTN"),
    ("0xbaff37aa3667abb92d9d10c2b0a1d4128033c4df", "DAYC2"),
    ("0x82831e9565cb574375596efc090da465283e22a4", "ALGB-FARM"),
    ("0xe1b87c4a363be9158323c47c4fdaa70e6dccfe05", "McRIB-PIX"),
    ("0x58ad22348216bdb0a3a544ad365ee82187d0e8aa", "CCHIMP"),
    ("0xfed9e67c30c76e416371b4763fc02f8a33e52b5d", "DDB"),
    ("0xe83c2021550b17169bd2d608c51ba6a2bea0f350", "DC-DOMAINS"),
    ("0x491c67db959bda22e1061b43693ea3699675f080", "GMNFT"),
    ("0x0af878360b48b5f51f4e919f3cc1ec08b78627ad", "DOGE-DOMAINS"),
    ("0x121c02c851cd0434a1bfc584ea9895b6aa2c114b", "DTOOLS-2023"),
]

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nft_snapshot_v2.py")
PROGRESS_FILE = "/tmp/token_enum_progress.log"

def log(msg):
    with open(PROGRESS_FILE, "a") as f:
        f.write(f"{time.strftime('%H:%M:%S')} | {msg}\n")
    print(msg, flush=True)

log(f"Starting token-level enumeration for {len(REMAINING)} collections")

done = []
failed = []

for i, (addr, symbol) in enumerate(REMAINING, 1):
    log(f"[{i}/{len(REMAINING)}] Processing {symbol} ({addr[:10]}...)")
    
    try:
        result = subprocess.run(
            [sys.executable, SCRIPT, addr, symbol],
            capture_output=True, text=True, timeout=600  # 10 min per collection
        )
        
        output = result.stdout.strip()
        if "✅" in output:
            log(f"  ✅ {symbol} done")
            done.append(symbol)
        else:
            log(f"  ⚠️ {symbol} — no success marker. Exit: {result.returncode}")
            if result.stderr:
                log(f"  STDERR: {result.stderr[-200:]}")
            failed.append(symbol)
        
        # Show last 3 lines of output
        lines = [l for l in output.split("\n") if l.strip()]
        for line in lines[-3:]:
            log(f"  > {line}")
            
    except subprocess.TimeoutExpired:
        log(f"  ❌ {symbol} TIMED OUT (600s)")
        failed.append(symbol)
    except Exception as e:
        log(f"  ❌ {symbol} ERROR: {e}")
        failed.append(symbol)
    
    # Brief pause between collections
    time.sleep(2)

log(f"\n{'='*60}")
log(f"DONE: {len(done)}/{len(REMAINING)} completed")
log(f"Success: {done}")
if failed:
    log(f"Failed: {failed}")
