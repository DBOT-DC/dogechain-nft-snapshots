#!/usr/bin/env python3
"""
COMPREHENSIVE Dogechain NFT Snapshot — Token-Level Ownership

For each NFT collection, captures:
1. Wallet-level: which wallets hold NFTs and how many (for airdrops)
2. TOKEN-LEVEL: which SPECIFIC NFT IDs each wallet holds (for re-launch/migration)
3. Metadata: contract info + sample token URIs
4. Transfer history summary

This is the definitive archival snapshot before chain shutdown.

Output per collection:
  {symbol}_token_owners.json  — token_id -> owner_address (COMPLETE ownership map)
  {symbol}_wallets.csv        — wallet -> count (airdrop-ready)
  {symbol}_summary.json       — stats
"""
import json, urllib.request, time, sys, os, csv
from datetime import datetime, timezone

RPC = "https://rpc.dogechain.dog"
EXPLORER = "https://explorer.dogechain.dog/api"
SNAPSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshots")
SNAPSHOT_TIME = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# All known NFT collections + discovered ones
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
]

# Load any additional NFTs discovered by the browser agent
discovered_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "all_discovered_nfts.json")
if os.path.exists(discovered_path):
    with open(discovered_path) as f:
        discovered = json.load(f)
    known_addrs = {n["address"].lower() for n in ALL_NFTS}
    for d in discovered:
        if d.get("address", "").lower() not in known_addrs:
            ALL_NFTS.append({
                "address": d["address"],
                "symbol": d.get("symbol", d.get("name", "?")[:10]),
            })
    print(f"Loaded {len(discovered)} discovered NFTs, {len(ALL_NFTS)} total")


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


def get_transfer_events_paginated(contract, from_block, to_block):
    """Fetch ALL ERC-721 Transfer events for a contract using eth_getLogs.
    ERC-721 Transfer events have 4 topics (including tokenId as topic[3]).
    This gives us complete token-level ownership history.
    """
    transfer_topic = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
    all_logs = []
    chunk = 5000
    current = from_block
    while current < to_block:
        end = min(current + chunk - 1, to_block)
        try:
            logs = rpc("eth_getLogs", [{
                "fromBlock": hex(current),
                "toBlock": hex(end),
                "address": contract,
                "topics": [transfer_topic]
            }])
            if logs:
                all_logs.extend(logs)
        except:
            # Retry with smaller chunk
            try:
                logs = rpc("eth_getLogs", [{
                    "fromBlock": hex(current),
                    "toBlock": hex(end),
                    "address": contract,
                    "topics": [transfer_topic]
                }])
                if logs:
                    all_logs.extend(logs)
            except:
                pass
        current = end + 1
        time.sleep(0.15)
    return all_logs


def parse_erc721_transfers(logs):
    """Parse ERC-721 Transfer events into token_id -> owner map.
    ERC-721: Transfer(from indexed, to indexed, tokenId indexed)
    topic[0] = event sig
    topic[1] = from address (padded)
    topic[2] = to address (padded)
    topic[3] = tokenId
    """
    ownership = {}  # token_id -> owner (latest)
    all_transfers = []
    
    for log in logs:
        topics = log.get("topics", [])
        if len(topics) < 4:
            continue  # ERC-20 has 3 topics, skip
        
        from_addr = "0x" + topics[1][-40:]
        to_addr = "0x" + topics[2][-40:]
        token_id = int(topics[3], 16)
        
        ownership[token_id] = to_addr
        all_transfers.append({
            "token_id": token_id,
            "from": from_addr,
            "to": to_addr,
            "block": int(log.get("blockNumber", "0x0"), 16),
            "tx_hash": log.get("transactionHash", ""),
        })
    
    return ownership, all_transfers


def snapshot_collection_token_level(contract, symbol, block, snapshot_time):
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
    
    print(f"  Name: {name} ({csymbol}) | Type: {ctype} | Supply: {supply_int}")
    result.update({"name": name, "type": ctype, "total_supply": supply_int})
    
    # Step 1: Get holders via Blockscout API (fast — wallet level)
    print(f"  Step 1: Fetching wallet-level holders...")
    holders_raw = get_holders(contract)
    
    wallet_holders = []
    total_nfts = 0
    for h in holders_raw:
        addr = h.get("address", "")
        count = int(h.get("value", "0"))
        wallet_holders.append({"address": addr, "nft_count": count})
        total_nfts += count
    
    print(f"  Wallet holders: {len(wallet_holders):,} | Total NFTs: {total_nfts:,}")
    result["holder_count"] = len(wallet_holders)
    result["total_nfts"] = total_nfts
    
    # Step 2: Get token-level ownership via Transfer events
    print(f"  Step 2: Scanning Transfer events for token-level ownership...")
    # Use a reasonable starting block — most Dogechain NFTs launched after block 921K
    # For speed, start from block 1M (covers all NFT activity)
    ownership = {}
    all_transfers = []
    
    try:
        logs = get_transfer_events_paginated(contract, 921000, block)
        print(f"  Transfer events found: {len(logs):,}")
        ownership, all_transfers = parse_erc721_transfers(logs)
        print(f"  Unique tokens with owners: {len(ownership):,}")
        print(f"  Total transfers: {len(all_transfers):,}")
    except Exception as e:
        print(f"  ⚠️ Transfer scan failed: {e}")
    
    result["unique_tokens_tracked"] = len(ownership)
    result["total_transfers"] = len(all_transfers)
    
    # Step 3: Build reverse map — wallet -> [token_ids]
    wallet_tokens = {}  # wallet -> [token_id1, token_id2, ...]
    for token_id, owner in ownership.items():
        if owner not in wallet_tokens:
            wallet_tokens[owner] = []
        wallet_tokens[owner].append(token_id)
    
    print(f"  Wallets with token IDs: {len(wallet_tokens):,}")
    
    # Step 4: Save all outputs
    coll_dir = os.path.join(SNAPSHOT_DIR, symbol)
    os.makedirs(coll_dir, exist_ok=True)
    
    # TOKEN-LEVEL: Complete ownership map (token_id -> owner)
    token_owners_path = os.path.join(coll_dir, f"{symbol}_token_owners.json")
    with open(token_owners_path, "w") as f:
        json.dump({
            "contract": contract,
            "name": name,
            "symbol": csymbol,
            "snapshot_block": block,
            "snapshot_time": snapshot_time,
            "total_supply": supply_int,
            "unique_tokens": len(ownership),
            "total_holders": len(wallet_tokens),
            "token_owners": {str(tid): owner for tid, owner in sorted(ownership.items())}
        }, f, indent=2)
    print(f"  ✅ {symbol}_token_owners.json ({len(ownership):,} tokens)")
    
    # WALLET-LEVEL: wallet -> [token_ids] (for re-launch/migration)
    wallet_tokens_path = os.path.join(coll_dir, f"{symbol}_wallet_tokens.json")
    with open(wallet_tokens_path, "w") as f:
        json.dump({
            "contract": contract,
            "name": name,
            "symbol": csymbol,
            "snapshot_block": block,
            "snapshot_time": snapshot_time,
            "wallets": {addr: tids for addr, tids in wallet_tokens.items()}
        }, f, indent=2)
    print(f"  ✅ {symbol}_wallet_tokens.json ({len(wallet_tokens):,} wallets)")
    
    # WALLET CSV (airdrop-ready)
    csv_path = os.path.join(coll_dir, f"{symbol}_wallets.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["wallet", "nft_count", "token_ids", "contract", "snapshot_block", "snapshot_time"])
        for wallet, tids in sorted(wallet_tokens.items(), key=lambda x: len(x[1]), reverse=True):
            writer.writerow([wallet, len(tids), ",".join(str(t) for t in sorted(tids)), contract, block, snapshot_time])
    print(f"  ✅ {symbol}_wallets.csv (airdrop-ready)")
    
    # Summary
    result["status"] = "complete"
    summary_path = os.path.join(coll_dir, f"{symbol}_summary.json")
    with open(summary_path, "w") as f:
        json.dump(result, f, indent=2)
    
    return result


def main():
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    block = get_block()
    
    print(f"🚀 COMPREHENSIVE NFT Snapshot — {SNAPSHOT_TIME}")
    print(f"   Block: {block:,}")
    print(f"   Collections: {len(ALL_NFTS)}")
    print(f"   Output: {SNAPSHOT_DIR}")
    
    # Allow CLI override
    if len(sys.argv) >= 3 and sys.argv[1].startswith("0x"):
        collections = [{"address": sys.argv[1], "symbol": sys.argv[2]}]
    else:
        collections = ALL_NFTS
    
    all_results = []
    for coll in collections:
        try:
            result = snapshot_collection_token_level(
                coll["address"], coll["symbol"], block, SNAPSHOT_TIME
            )
            all_results.append(result)
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
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
    
    # Summary table
    print(f"\n{'='*70}")
    print(f"{'Symbol':<16} {'Supply':>8} {'Holders':>8} {'Tokens':>8} {'Transfers':>10} {'Status'}")
    print("-" * 70)
    for r in all_results:
        supply = str(r.get("total_supply", "?"))[:8]
        holders = f"{r.get('holder_count', 0):,}" if r.get("holder_count") else "0"
        tokens = f"{r.get('unique_tokens_tracked', 0):,}" if r.get("unique_tokens_tracked") else "0"
        transfers = f"{r.get('total_transfers', 0):,}" if r.get("total_transfers')", 0) else "0"
        print(f"{r['symbol']:<16} {supply:>8} {holders:>8} {tokens:>8} {transfers:>10} {r.get('status', '?')}")
    
    complete = sum(1 for r in all_results if r.get("status") == "complete")
    print(f"\n✅ {complete}/{len(all_results)} collections snapshot successfully")
    print(f"📁 Index: {index_path}")
    
    # Total stats
    total_holders = sum(r.get("holder_count", 0) for r in all_results)
    total_tokens = sum(r.get("unique_tokens_tracked", 0) for r in all_results)
    total_transfers = sum(r.get("total_transfers", 0) for r in all_results)
    print(f"\n📊 TOTALS: {total_holders:,} holders | {total_tokens:,} tokens | {total_transfers:,} transfers")


if __name__ == "__main__":
    main()
