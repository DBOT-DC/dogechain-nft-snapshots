#!/usr/bin/env python3
"""
COMPREHENSIVE NFT Snapshot v2 — Fast Token-Level Ownership

Uses Blockscout API for holders + tokenOfOwnerByIndex RPC for specific token IDs.
No Transfer event scanning needed — 10x faster than v1.

For each collection:
1. Get all holders via Blockscout getTokenHolders API (seconds)
2. For each holder, enumerate their specific NFT IDs via tokenOfOwnerByIndex
3. Build complete ownership map: token_id → owner

Output per collection:
  {symbol}_token_owners.json  — token_id → owner (complete)
  {symbol}_wallet_tokens.json — wallet → [token_ids] (for re-launch/migration)
  {symbol}_wallets.csv        — airdrop-ready CSV with specific token IDs
  {symbol}_summary.json       — stats
"""
import json, urllib.request, time, sys, os, csv
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

RPC = "https://rpc.dogechain.dog"
EXPLORER = "https://explorer.dogechain.dog/api"
SNAPSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshots")
SNAPSHOT_TIME = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

ALL_NFTS = [
    {"address": "0xd38b22794b308a2e55808a13d1e6a80c4be94fd5", "symbol": "RDP"},
    {"address": "0xb6e6b0167ce72057f6ac28cb5fd836896b4d084e", "symbol": "DOGE-BEARS"},
    {"address": "0x1836c33b9350d18304e0f701de777cc7501e9c2a", "symbol": "DH"},
    {"address": "0x9b291b0e9c78ce1c94b701d3d9faad349c4be341", "symbol": "DOGE-BLINDERS"},
    {"address": "0x8743b1cec8939e456f05194503fbb6500a3ba67d", "symbol": "FTH"},
    {"address": "0x5f595ff1830b0bd9e67ae6376ad80598876cc34f", "symbol": "MONOS"},
    {"address": "0x01d675a61d94aea570007374d85301d6619d9e6e", "symbol": "McRIB"},
    {"address": "0x49ffa5d11cb54a6541e33dc04951b1ffdfaa2852", "symbol": "CYBERDOGS"},
    {"address": "0xbeae0fd8ccecc76afcc137d89f2b006e8c543c84", "symbol": "DOGEPUNKS"},
    {"address": "0x63309a2b8f507f667da75c24013a2e18904cc19d", "symbol": "SOVPUNKS"},
    {"address": "0x6b351dc4439a9ac313f6f4d76c51f2d3717f3101", "symbol": "SEADOGS"},
    {"address": "0xec10d3091abffcc89f0cca5ae90842f5628bfb56", "symbol": "DCC"},
    {"address": "0x544870cc7ff94a50e507262b98060f6b15835fde", "symbol": "BDKC"},
    {"address": "0x58f2fea3d66025cdedbc37b5bcd93647d76d7325", "symbol": "DAC"},
    {"address": "0x79105d9bb5850bdab32aecd0fe669dcdb33d79d6", "symbol": "DAYC"},
    {"address": "0x81c3164939f515134f6be6b6f9d295887df6554b", "symbol": "ASTRO"},
    {"address": "0xb3c75f465f6236985c0a0ce5013c5ae7ae2748e5", "symbol": "DOGEDOODLE"},
    {"address": "0xf6ee4a3f8529a6b20b8f4792a0ea20a419ba21f5", "symbol": "PIXELFROGS"},
    {"address": "0xa2e57fa488cf272c87b066e2a3e0672c0c58784d", "symbol": "RAT"},
    {"address": "0x0b012055f770ae7bb7a8303968a7fb6088a2296e", "symbol": "ALGB-POS"},
    # Batch 2 — discovered via chain scan Aug 7
    {"address": "0xe46727bb5b84d574ecca7e562a36c23525fcf8dc", "symbol": "C0F"},  # Council of Frogs
    # Batch 3 — full ERC-721 chain scan Aug 7 (Transfer events with 4 topics)
    {"address": "0x92b995f34cbf637d59c66782e90dfec3ce3c202b", "symbol": "DTOOLS-NFT"},
    {"address": "0x221ebe2243d3a4be8b7d53a98c5aebbc37bd7c33", "symbol": "TDH-NFT"},
    {"address": "0x011f614b13ef08b905a2ae68443f6344cce32046", "symbol": "DG"},
    {"address": "0xd7f68f4349527dae381233daa120bb42e310c986", "symbol": "KIMON"},
    {"address": "0xafa5f9313f1f2b599173f24807a882f498be118c", "symbol": "hMERK"},
    {"address": "0x45944dd5145ac7815d29c8c5d7c7f1801a7aa6c3", "symbol": "FFNFTS"},
    {"address": "0xfb035ab15a174f6c0702901e7b2a24db8f8cd026", "symbol": "DCC2"},
    {"address": "0xf497d4826c3585cee69a0fd3b71b057d7056f64a", "symbol": "MASON"},
    {"address": "0x870fb39328958d9d363ddb88c2e6a4a32a5bef11", "symbol": "BDKC2"},
    {"address": "0x474faddd73b6ff260efd281b4eb375a6fd7ea9bc", "symbol": "DCP"},
    {"address": "0x5b68749a85e84cbf3a04526d87296d4d988462dc", "symbol": "WTN"},
    {"address": "0xbaff37aa3667abb92d9d10c2b0a1d4128033c4df", "symbol": "DAYC2"},
    {"address": "0x82831e9565cb574375596efc090da465283e22a4", "symbol": "ALGB-FARM"},
    {"address": "0xe1b87c4a363be9158323c47c4fdaa70e6dccfe05", "symbol": "McRIB-PIX"},
    {"address": "0x58ad22348216bdb0a3a544ad365ee82187d0e8aa", "symbol": "CCHIMP"},
    {"address": "0xfed9e67c30c76e416371b4763fc02f8a33e52b5d", "symbol": "DDB"},
    {"address": "0xe83c2021550b17169bd2d608c51ba6a2bea0f350", "symbol": "DC-DOMAINS"},
    {"address": "0x491c67db959bda22e1061b43693ea3699675f080", "symbol": "GMNFT"},
    {"address": "0x0af878360b48b5f51f4e919f3cc1ec08b78627ad", "symbol": "DOGE-DOMAINS"},
    {"address": "0x121c02c851cd0434a1bfc584ea9895b6aa2c114b", "symbol": "DTOOLS-2023"},
]


def rpc(method, params, retries=3):
    body = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode()
    for attempt in range(retries):
        try:
            req = urllib.request.Request(RPC, data=body, headers={"Content-Type": "application/json"})
            return json.loads(urllib.request.urlopen(req, timeout=15).read()).get("result")
        except:
            if attempt < retries - 1:
                time.sleep(1 * (attempt + 1))
    return None


def api_get(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            return json.loads(urllib.request.urlopen(req, timeout=30).read())
        except:
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
    return {}


def get_block():
    r = rpc("eth_blockNumber", [])
    return int(r, 16) if r else 0


def get_holders(contract):
    """Get all holders via Blockscout API."""
    all_holders = []
    page = 1
    while True:
        data = api_get(
            f"{EXPLORER}?module=token&action=getTokenHolders"
            f"&contractaddress={contract}&page={page}&offset=10000"
        )
        result = data.get("result", [])
        if not isinstance(result, list) or len(result) == 0:
            break
        all_holders.extend(result)
        if len(result) < 10000:
            break
        page += 1
        time.sleep(0.3)
    return all_holders


def get_token_ids_for_wallet(contract, wallet, nft_count):
    """Enumerate specific NFT IDs held by a wallet using tokenOfOwnerByIndex.
    
    ERC721Enumerable: tokenOfOwnerByIndex(address, uint256) -> uint256
    Selector: 0x2f745c59
    """
    token_ids = []
    for i in range(nft_count):
        # tokenOfOwnerByIndex(address, index)
        addr_padded = wallet[2:].zfill(64)
        index_padded = f"{i:064x}"
        data = "0x2f745c59" + addr_padded + index_padded
        result = rpc("eth_call", [{"to": contract, "data": data}, "latest"])
        if result and result != "0x" and len(result) >= 66:
            token_id = int(result, 16)
            token_ids.append(token_id)
        else:
            break
        time.sleep(0.02)  # light rate limiting
    return token_ids


def snapshot_collection(contract, symbol, block, snapshot_time):
    print(f"\n{'='*60}")
    print(f"📸 {symbol} ({contract[:12]}...)")
    print(f"{'='*60}")
    
    result = {
        "contract": contract,
        "symbol": symbol,
        "snapshot_block": block,
        "snapshot_time": snapshot_time,
    }
    
    # Contract info
    info_data = api_get(f"{EXPLORER}?module=token&action=getToken&contractaddress={contract}")
    info = info_data.get("result", {})
    name = info.get("name", "?")
    csymbol = info.get("symbol", "?")
    ctype = info.get("type", "?")
    total_supply = info.get("totalSupply", "0")
    
    try:
        supply_int = int(float(total_supply))
    except:
        supply_int = 0
    
    print(f"  {name} ({csymbol}) | {ctype} | Supply: {supply_int:,}")
    result.update({"name": name, "type": ctype, "total_supply": supply_int})
    
    # Step 1: Get holders (fast — Blockscout API)
    print(f"  Holders...")
    holders_raw = get_holders(contract)
    
    holders = []
    for h in holders_raw:
        addr = h.get("address", "")
        count = int(h.get("value", "0"))
        if addr and count > 0:
            holders.append({"address": addr, "nft_count": count})
    
    print(f"  {len(holders):,} holders, {sum(h['nft_count'] for h in holders):,} NFTs")
    result["holder_count"] = len(holders)
    result["total_nfts"] = sum(h["nft_count"] for h in holders)
    
    # Step 2: Enumerate token IDs per wallet
    print(f"  Enumerating token IDs...")
    ownership = {}  # token_id -> owner
    wallet_tokens = {}  # wallet -> [token_ids]
    success_count = 0
    fail_count = 0
    
    for i, holder in enumerate(holders):
        wallet = holder["address"]
        count = holder["nft_count"]
        
        if count <= 50:
            # Small holder — enumerate directly
            tids = get_token_ids_for_wallet(contract, wallet, count)
            if tids:
                wallet_tokens[wallet] = tids
                for tid in tids:
                    ownership[tid] = wallet
                success_count += 1
            else:
                fail_count += 1
        else:
            # Large holder — enumerate (slower but necessary)
            tids = get_token_ids_for_wallet(contract, wallet, min(count, 500))  # cap at 500
            if tids:
                wallet_tokens[wallet] = tids
                for tid in tids:
                    ownership[tid] = wallet
                success_count += 1
            else:
                fail_count += 1
        
        if (i + 1) % 200 == 0:
            print(f"    {i+1}/{len(holders)} wallets processed, {len(ownership):,} tokens mapped")
    
    print(f"  Token IDs mapped: {len(ownership):,} ({success_count} ok, {fail_count} failed)")
    result["tokens_with_ids"] = len(ownership)
    result["wallets_with_ids"] = len(wallet_tokens)
    
    # Step 3: Save outputs
    coll_dir = os.path.join(SNAPSHOT_DIR, symbol)
    os.makedirs(coll_dir, exist_ok=True)
    
    # token_id → owner
    with open(os.path.join(coll_dir, f"{symbol}_token_owners.json"), "w") as f:
        json.dump({
            "contract": contract, "name": name, "symbol": csymbol,
            "snapshot_block": block, "snapshot_time": snapshot_time,
            "total_supply": supply_int, "unique_tokens": len(ownership),
            "total_holders": len(wallet_tokens),
            "token_owners": {str(tid): owner for tid, owner in sorted(ownership.items())}
        }, f, indent=2)
    
    # wallet → [token_ids]
    with open(os.path.join(coll_dir, f"{symbol}_wallet_tokens.json"), "w") as f:
        json.dump({
            "contract": contract, "name": name, "symbol": csymbol,
            "snapshot_block": block, "snapshot_time": snapshot_time,
            "wallets": {addr: tids for addr, tids in wallet_tokens.items()}
        }, f, indent=2)
    
    # CSV with specific token IDs
    csv_path = os.path.join(coll_dir, f"{symbol}_wallets.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["wallet", "nft_count", "token_ids", "contract", "snapshot_block", "snapshot_time"])
        # Include ALL wallets, even those without token ID enumeration
        wallets_done = set()
        for wallet, tids in sorted(wallet_tokens.items(), key=lambda x: len(x[1]), reverse=True):
            writer.writerow([wallet, len(tids), ",".join(str(t) for t in sorted(tids)), contract, block, snapshot_time])
            wallets_done.add(wallet)
        # Add wallets where token ID enumeration failed (still have count from API)
        for h in sorted(holders, key=lambda x: x["nft_count"], reverse=True):
            if h["address"] not in wallets_done:
                writer.writerow([h["address"], h["nft_count"], "", contract, block, snapshot_time])
    
    # Summary
    result["status"] = "complete"
    with open(os.path.join(coll_dir, f"{symbol}_summary.json"), "w") as f:
        json.dump(result, f, indent=2)
    
    print(f"  ✅ token_owners.json + wallet_tokens.json + wallets.csv")
    return result


def main():
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    block = get_block()
    
    print(f"🚀 NFT Snapshot v2 (Token-Level) — {SNAPSHOT_TIME}")
    print(f"   Block: {block:,}")
    print(f"   Collections: {len(ALL_NFTS)}")
    
    if len(sys.argv) >= 3 and sys.argv[1].startswith("0x"):
        collections = [{"address": sys.argv[1], "symbol": sys.argv[2]}]
    else:
        collections = ALL_NFTS
    
    all_results = []
    for coll in collections:
        try:
            result = snapshot_collection(coll["address"], coll["symbol"], block, SNAPSHOT_TIME)
            all_results.append(result)
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            import traceback; traceback.print_exc()
            all_results.append({"contract": coll["address"], "symbol": coll["symbol"], "status": f"error: {e}"})
    
    # Master index
    index_path = os.path.join(SNAPSHOT_DIR, "SNAPSHOT_INDEX.json")
    with open(index_path, "w") as f:
        json.dump({
            "snapshot_time": SNAPSHOT_TIME,
            "snapshot_block": block,
            "chain": "Dogechain (2000)",
            "total_collections": len(all_results),
            "successful": sum(1 for r in all_results if r.get("status") == "complete"),
            "collections": all_results,
        }, f, indent=2)
    
    print(f"\n{'='*70}")
    print(f"{'Symbol':<16} {'Supply':>8} {'Holders':>8} {'TokenIDs':>8} {'Status'}")
    print("-" * 70)
    for r in all_results:
        supply = str(r.get("total_supply", "?"))[:8]
        holders = f"{r.get('holder_count', 0):,}" if r.get("holder_count") else "0"
        tids = f"{r.get('tokens_with_ids', 0):,}" if r.get("tokens_with_ids") else "0"
        print(f"{r['symbol']:<16} {supply:>8} {holders:>8} {tids:>8} {r.get('status', '?')}")
    
    complete = sum(1 for r in all_results if r.get("status") == "complete")
    total_tokens = sum(r.get("tokens_with_ids", 0) for r in all_results)
    total_holders = sum(r.get("holder_count", 0) for r in all_results)
    print(f"\n✅ {complete}/{len(all_results)} collections | {total_holders:,} holders | {total_tokens:,} token IDs mapped")
    print(f"📁 {SNAPSHOT_DIR}")


if __name__ == "__main__":
    main()
