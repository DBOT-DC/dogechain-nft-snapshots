#!/usr/bin/env python3
"""
Parallel Transfer event scanner — uses ThreadPoolExecutor to scan
multiple 5K-block windows concurrently per collection.
~10x faster than sequential scanning.
"""
import json, urllib.request, time, os, csv, sys
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

RPC = "https://rpc.dogechain.dog"
SNAPSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshots")
SNAPSHOT_TIME = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

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


def rpc_single(method, params):
    body = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode()
    for attempt in range(3):
        try:
            req = urllib.request.Request(RPC, data=body, headers={"Content-Type": "application/json"})
            return json.loads(urllib.request.urlopen(req, timeout=30).read()).get("result")
        except:
            time.sleep(1 * (attempt + 1))
    return None


def fetch_chunk(args):
    contract, start, end = args
    payload = json.dumps({
        "jsonrpc": "2.0",
        "method": "eth_getLogs",
        "params": [{
            "fromBlock": hex(start),
            "toBlock": hex(end),
            "address": contract,
            "topics": [TRANSFER_TOPIC]
        }],
        "id": 1
    }).encode()
    for attempt in range(3):
        try:
            req = urllib.request.Request(RPC, data=payload, headers={"Content-Type": "application/json"})
            data = json.loads(urllib.request.urlopen(req, timeout=30).read())
            return data.get("result", [])
        except:
            time.sleep(1 * (attempt + 1))
    return []


def decode_string(hex_result):
    if not hex_result or hex_result == "0x":
        return ""
    try:
        hb = bytes.fromhex(hex_result[2:])
        if len(hb) < 64:
            return ""
        length = int.from_bytes(hb[32:64], "big")
        return hb[64:64+length].decode("utf-8", errors="replace").strip("\x00")
    except:
        return ""


def get_transfers_parallel(contract, max_workers=8):
    latest_hex = rpc_single("eth_blockNumber", [])
    if not latest_hex:
        return [], 0
    latest = int(latest_hex, 16)

    chunk = 5000
    chunks = []
    for start in range(0, latest, chunk):
        end = min(start + chunk - 1, latest)
        chunks.append((contract, start, end))

    print(f"    {len(chunks):,} chunks, {max_workers} workers", flush=True)

    all_logs = []
    done = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_chunk, c): c for c in chunks}
        for future in as_completed(futures):
            logs = future.result()
            all_logs.extend(logs)
            done += 1
            if done % 2000 == 0:
                print(f"    {done:,}/{len(chunks):,} chunks done, {len(all_logs):,} transfers", flush=True)

    return all_logs, latest


def build_ownership(logs):
    token_owner = {}
    for log in logs:
        topics = log.get("topics", [])
        if len(topics) < 4:
            continue
        to_addr = "0x" + topics[2][-40:]
        token_id = int(topics[3], 16)
        if to_addr.lower() == "0x0000000000000000000000000000000000000000":
            token_owner.pop(token_id, None)
        else:
            token_owner[token_id] = to_addr.lower()
    return token_owner


def snapshot_collection(addr, symbol, snapshot_time):
    print(f"\n{'='*60}", flush=True)
    print(f"📸 {symbol} ({addr[:12]}...)", flush=True)
    print(f"{'='*60}", flush=True)

    name = decode_string(rpc_single("eth_call", [{"to": addr, "data": "0x06fdde03"}, "latest"]) or "")
    sym = decode_string(rpc_single("eth_call", [{"to": addr, "data": "0x95d89b41"}, "latest"]) or "")
    supply_hex = rpc_single("eth_call", [{"to": addr, "data": "0x18160ddd"}, "latest"]) or "0x0"
    supply = int(supply_hex, 16) if supply_hex and supply_hex != "0x" else 0

    print(f"  {name} ({sym}) | Supply: {supply:,}", flush=True)
    print(f"  Scanning Transfer events (parallel)...", flush=True)

    logs, block = get_transfers_parallel(addr)
    print(f"  {len(logs):,} Transfer events found", flush=True)

    token_owner = build_ownership(logs)
    print(f"  {len(token_owner):,} tokens with current owners", flush=True)

    wallet_tokens = {}
    for tid, owner in token_owner.items():
        wallet_tokens.setdefault(owner, []).append(tid)
    for w in wallet_tokens:
        wallet_tokens[w].sort()

    print(f"  {len(wallet_tokens):,} unique holders", flush=True)

    col_dir = os.path.join(SNAPSHOT_DIR, symbol)
    os.makedirs(col_dir, exist_ok=True)

    with open(os.path.join(col_dir, f"{symbol}_token_owners.json"), "w") as f:
        json.dump({
            "contract": addr, "name": name, "symbol": sym,
            "snapshot_block": block, "snapshot_time": snapshot_time,
            "total_supply": supply, "unique_tokens": len(token_owner),
            "total_holders": len(wallet_tokens),
            "token_owners": {str(tid): owner for tid, owner in sorted(token_owner.items())}
        }, f, indent=2)

    with open(os.path.join(col_dir, f"{symbol}_wallet_tokens.json"), "w") as f:
        json.dump({
            "contract": addr, "name": name, "symbol": sym,
            "snapshot_block": block, "snapshot_time": snapshot_time,
            "wallets": {w: tids for w, tids in wallet_tokens.items()}
        }, f, indent=2)

    with open(os.path.join(col_dir, f"{symbol}_wallets.csv"), "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["wallet", "nft_count", "token_ids", "contract", "snapshot_block", "snapshot_time"])
        for wallet, tids in sorted(wallet_tokens.items(), key=lambda x: len(x[1]), reverse=True):
            writer.writerow([wallet, len(tids), ",".join(str(t) for t in tids), addr, block, snapshot_time])

    with open(os.path.join(col_dir, f"{symbol}_summary.json"), "w") as f:
        json.dump({
            "contract": addr, "symbol": symbol, "name": name,
            "total_supply": supply, "holder_count": len(wallet_tokens),
            "tokens_with_ids": len(token_owner),
            "snapshot_block": block, "snapshot_time": snapshot_time,
            "status": "complete"
        }, f, indent=2)

    print(f"  ✅ token_owners.json + wallet_tokens.json + wallets.csv", flush=True)
    return {"symbol": symbol, "holders": len(wallet_tokens), "tokens": len(token_owner)}


def main():
    print(f"🚀 Parallel Transfer-Event Token Enumeration — {SNAPSHOT_TIME}", flush=True)
    print(f"   {len(REMAINING)} collections to process\n", flush=True)

    results = []
    for i, (addr, symbol) in enumerate(REMAINING, 1):
        print(f"[{i}/{len(REMAINING)}]", flush=True)
        try:
            r = snapshot_collection(addr, symbol, SNAPSHOT_TIME)
            results.append(r)
        except Exception as e:
            print(f"  ❌ ERROR: {e}", flush=True)
            results.append({"symbol": symbol, "error": str(e)})
        time.sleep(1)

    print(f"\n{'='*60}", flush=True)
    ok = sum(1 for r in results if "error" not in r)
    print(f"DONE: {ok}/{len(REMAINING)}", flush=True)
    print(f"\n{'Symbol':<16} {'Holders':>8} {'Tokens':>8}", flush=True)
    print("-" * 36, flush=True)
    for r in sorted(results, key=lambda x: x.get("holders", 0), reverse=True):
        if "error" in r:
            print(f"{r['symbol']:<16} ERROR", flush=True)
        else:
            print(f"{r['symbol']:<16} {r['holders']:>8} {r['tokens']:>8}", flush=True)


if __name__ == "__main__":
    main()
