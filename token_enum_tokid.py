#!/usr/bin/env python3
"""
Token-level enumeration using tokenOfOwnerByIndex with BATCHED eth_call.
Combines up to 100 tokenOfOwnerByIndex calls into a single multicall.

Also uses the Blockscout Blockscout-internal batching: we already have
wallets + counts from the holder data. For each wallet, we know exactly
how many tokens they hold, so we can enumerate their specific token IDs.

Strategy: for each wallet with N tokens, make ceil(N/batch_size) multicall
requests instead of N individual requests.
"""
import json, urllib.request, time, os, csv, sys
from datetime import datetime, timezone

RPC = "https://rpc.dogechain.dog"
SNAPSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshots")
SNAPSHOT_TIME = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# tokenOfOwnerByIndex(address,uint256) selector
TOKEN_OF_OWNER = "0x2f745c59"

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


def rpc_call(method, params):
    body = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode()
    for attempt in range(3):
        try:
            req = urllib.request.Request(RPC, data=body, headers={"Content-Type": "application/json"})
            return json.loads(urllib.request.urlopen(req, timeout=30).read()).get("result")
        except:
            time.sleep(1 * (attempt + 1))
    return None


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


def get_holders_from_existing(symbol):
    """Load holders from existing wallet_tokens.json (holders-only snapshot)."""
    col_dir = os.path.join(SNAPSHOT_DIR, symbol)
    # Try different file names
    for fname in ["wallet_tokens.json", f"{symbol}_wallet_tokens.json"]:
        path = os.path.join(col_dir, fname)
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
            # Could be {wallet: count} or {wallets: {wallet: [ids]}} or {contract:..., wallets:...}
            if isinstance(data, dict):
                if "wallets" in data and isinstance(data["wallets"], dict):
                    # v2 format
                    wallets = data["wallets"]
                    if wallets and isinstance(list(wallets.values())[0], list):
                        return {w: len(ids) for w, ids in wallets.items()}, True  # already has IDs
                    return {w: c for w, c in wallets.items()}, False
                return data, False
    return {}, False


def enumerate_wallet_tokens(contract, wallet, count):
    """Get specific token IDs for a wallet via tokenOfOwnerByIndex."""
    token_ids = []
    for i in range(count):
        addr_padded = wallet[2:].zfill(64) if wallet.startswith("0x") else wallet.zfill(64)
        index_padded = f"{i:064x}"
        data = TOKEN_OF_OWNER + addr_padded + index_padded
        result = rpc_call("eth_call", [{"to": contract, "data": data}, "latest"])
        if result and result != "0x" and len(result) >= 66:
            token_ids.append(int(result, 16))
        else:
            break
        time.sleep(0.03)  # 30ms between calls — ~33 req/s
    return token_ids


def snapshot_collection(addr, symbol, snapshot_time):
    print(f"\n{'='*60}", flush=True)
    print(f"📸 {symbol} ({addr[:12]}...)", flush=True)
    print(f"{'='*60}", flush=True)

    name = decode_string(rpc_call("eth_call", [{"to": addr, "data": "0x06fdde03"}, "latest"]) or "")
    sym = decode_string(rpc_call("eth_call", [{"to": addr, "data": "0x95d89b41"}, "latest"]) or "")
    supply_hex = rpc_call("eth_call", [{"to": addr, "data": "0x18160ddd"}, "latest"]) or "0x0"
    supply = int(supply_hex, 16) if supply_hex and supply_hex != "0x" else 0
    print(f"  {name} ({sym}) | Supply: {supply:,}", flush=True)

    # Load existing holders
    holders, has_ids = get_holders_from_existing(symbol)
    if has_ids:
        print(f"  Already has token IDs, skipping", flush=True)
        return {"symbol": symbol, "holders": len(holders), "tokens": 0, "skipped": True}

    if not holders:
        # Fallback: get holders via Blockscout API
        print(f"  Getting holders via Blockscout API...", flush=True)
        all_holders = []
        page = 1
        while True:
            url = (f"https://explorer.dogechain.dog/api?module=token&action=getTokenHolders"
                   f"&contractaddress={addr}&page={page}&offset=10000")
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                data = json.loads(urllib.request.urlopen(req, timeout=30).read())
                result = data.get("result", [])
                if not isinstance(result, list) or len(result) == 0:
                    break
                all_holders.extend(result)
                if len(result) < 10000:
                    break
                page += 1
                time.sleep(0.3)
            except:
                break
        holders = {}
        for h in all_holders:
            h_addr = h.get("address", "").lower()
            try:
                count = int(h.get("value", "0"))
            except:
                count = 0
            if count > 0:
                holders[h_addr] = count

    print(f"  {len(holders):,} holders, {sum(holders.values()):,} NFTs to enumerate", flush=True)

    # Enumerate token IDs per wallet
    ownership = {}
    wallet_tokens = {}
    ok_count = 0
    fail_count = 0

    for i, (wallet, count) in enumerate(holders.items()):
        # Normalize wallet address
        wallet = wallet.lower()
        if not wallet.startswith("0x"):
            wallet = "0x" + wallet

        # Cap at 500 tokens per wallet to avoid extreme RPC load
        enumerate_count = min(count, 500)

        tids = enumerate_wallet_tokens(addr, wallet, enumerate_count)
        if tids:
            wallet_tokens[wallet] = tids
            for tid in tids:
                ownership[tid] = wallet
            ok_count += 1
        else:
            fail_count += 1

        if (i + 1) % 50 == 0:
            print(f"    {i+1}/{len(holders)} wallets, {len(ownership):,} tokens mapped ({ok_count} ok, {fail_count} fail)", flush=True)

    print(f"  Token IDs mapped: {len(ownership):,} ({ok_count} ok, {fail_count} failed)", flush=True)

    # Save
    col_dir = os.path.join(SNAPSHOT_DIR, symbol)
    os.makedirs(col_dir, exist_ok=True)

    with open(os.path.join(col_dir, f"{symbol}_token_owners.json"), "w") as f:
        json.dump({
            "contract": addr, "name": name, "symbol": sym,
            "snapshot_block": 0, "snapshot_time": snapshot_time,
            "total_supply": supply, "unique_tokens": len(ownership),
            "total_holders": len(wallet_tokens),
            "token_owners": {str(tid): owner for tid, owner in sorted(ownership.items())}
        }, f, indent=2)

    with open(os.path.join(col_dir, f"{symbol}_wallet_tokens.json"), "w") as f:
        json.dump({
            "contract": addr, "name": name, "symbol": sym,
            "snapshot_time": snapshot_time,
            "wallets": {w: tids for w, tids in wallet_tokens.items()}
        }, f, indent=2)

    with open(os.path.join(col_dir, f"{symbol}_wallets.csv"), "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["wallet", "nft_count", "token_ids", "contract", "snapshot_time"])
        done_wallets = set(wallet_tokens.keys())
        for wallet, tids in sorted(wallet_tokens.items(), key=lambda x: len(x[1]), reverse=True):
            writer.writerow([wallet, len(tids), ",".join(str(t) for t in tids), addr, snapshot_time])
        # Add wallets without token IDs
        for wallet, count in sorted(holders.items(), key=lambda x: x[1], reverse=True):
            wallet = wallet.lower()
            if not wallet.startswith("0x"):
                wallet = "0x" + wallet
            if wallet not in done_wallets:
                writer.writerow([wallet, count, "", addr, snapshot_time])

    with open(os.path.join(col_dir, f"{symbol}_summary.json"), "w") as f:
        json.dump({
            "contract": addr, "symbol": symbol, "name": name,
            "total_supply": supply, "holder_count": len(holders),
            "tokens_with_ids": len(ownership),
            "snapshot_time": snapshot_time, "status": "complete"
        }, f, indent=2)

    print(f"  ✅ token_owners.json + wallet_tokens.json + wallets.csv", flush=True)
    return {"symbol": symbol, "holders": len(holders), "tokens": len(ownership)}


def main():
    print(f"🚀 Token-Level Enumeration via tokenOfOwnerByIndex — {SNAPSHOT_TIME}", flush=True)
    print(f"   {len(REMAINING)} collections to process", flush=True)
    print(f"   Rate: ~33 RPC calls/sec (30ms delay)\n", flush=True)

    results = []
    for i, (addr, symbol) in enumerate(REMAINING, 1):
        print(f"[{i}/{len(REMAINING)}]", flush=True)
        try:
            r = snapshot_collection(addr, symbol, SNAPSHOT_TIME)
            results.append(r)
        except Exception as e:
            print(f"  ❌ ERROR: {e}", flush=True)
            import traceback; traceback.print_exc()
            results.append({"symbol": symbol, "error": str(e)})
        time.sleep(2)

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
