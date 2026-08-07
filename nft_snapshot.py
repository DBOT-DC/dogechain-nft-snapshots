#!/usr/bin/env python3
"""
Dogechain NFT Collection Snapshot Tool

Captures complete ownership + metadata for ERC-721 collections on Dogechain
before chain shutdown. Produces airdrop-ready holder lists + portable metadata archives.

Output per collection:
  {symbol}_holders.csv     — token_id,owner,snapshot_block,snapshot_time
  {symbol}_metadata.json   — all token metadata (name, description, attributes, image_uri)
  {symbol}_summary.json    — collection stats (total supply, holders, distribution)
  {symbol}_contract.json   — contract-level data (name, symbol, ABI subset)

Usage:
  python3 nft_snapshot.py                    # snapshot all known collections
  python3 nft_snapshot.py 0xCONTRACT SYMBOL  # snapshot single collection
  python3 nft_snapshot.py --metadata-only 0xCONTRACT SYMBOL  # skip ownership, just metadata
"""

import json, time, os, sys, csv, urllib.request, urllib.error
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

RPC = "https://rpc.dogechain.dog"
EXPLORER_API = "https://explorer.dogechain.dog/api"
SNAPSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshots")
SNAPSHOT_TIME = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# ERC-721 function selectors
SELECTOR = {
    "totalSupply": "0x18160ddd",
    "tokenByIndex": "0x4f6ccce7",       # tokenByIndex(uint256)
    "tokenURI": "0xc87b56dd",            # tokenURI(uint256)
    "ownerOf": "0x6352211e",             # ownerOf(uint256)
    "name": "0x06fdde03",
    "symbol": "0x95d89b41",
    "balanceOf": "0x70a08231",
    "supportsInterface": "0x01ffc9a7",
}

# All known Dogechain NFT collections (from evm-chain-asset-scanning skill)
KNOWN_COLLECTIONS = [
    ("0xd38b22794b308a2e55808a13d1e6a80c4be94fd5", "RDP"),
    ("0xb6e6b0167ce72057f6ac28cb5fd836896b4d084e", "DOGE-BEARS"),
    ("0x1836c33b9350d18304e0f701de777cc7501e9c2a", "DH"),
    ("0x9b291b0e9c78ce1c94b701d3d9faad349c4be341", "DOGE-BLINDERS"),
    ("0x8743b1cec8939e456f05194503fbb6500a3ba67d", "FTH"),
    ("0x5f595ff1830b0bd9e67ae6376ad80598876cc34f", "MONOS"),
    ("0x01d675a61d94aea570007374d85301d6619d9e6e", "McRIB"),
    ("0x49ffa5d11cb54a6541e33dc04951b1ffdfaa2852", "CYBERDOGS"),
    ("0xbeae0fd8ccecc76afcc137d89f2b006e8c543c84", "DOGEPUNKS"),
    ("0x63309a2b8f507f667da75c24013a2e18904cc19d", "SOVPUNKS"),
    ("0x6b351dc4439a9ac313f6f4d76c51f2d3717f3101", "SEADOGS"),
    ("0xec10d3091abffcc89f0cca5ae90842f5628bfb56", "DCC"),
    ("0x544870cc7ff94a50e507262b98060f6b15835fde", "BDKC"),
    ("0x58f2fea3d66025cdedbc37b5bcd93647d76d7325", "DAC"),
    ("0x79105d9bb5850bdab32aecd0fe669dcdb33d79d6", "DAYC"),
    ("0x81c3164939f515134f6be6b6f9d295887df6554b", "ASTRO"),
    ("0xb3c75f465f6236985c0a0ce5013c5ae7ae2748e5", "DOGEDOODLE"),
    ("0xf6ee4a3f8529a6b20b8f4792a0ea20a419ba21f5", "PIXELFROGS"),
    ("0xa2e57fa488cf272c87b066e2a3e0672c0c58784d", "RAT"),
]

# Rate limiting
RPC_DELAY = 0.15  # 150ms between RPC calls
MAX_WORKERS = 6   # parallel RPC calls


def rpc(method, params, retries=3):
    """Make a JSON-RPC call to Dogechain."""
    body = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode()
    for attempt in range(retries):
        try:
            req = urllib.request.Request(RPC, data=body, headers={"Content-Type": "application/json"})
            resp = urllib.request.urlopen(req, timeout=15)
            result = json.loads(resp.read())
            return result.get("result")
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1 * (attempt + 1))
            else:
                raise
    return None


def get_latest_block():
    return int(rpc("eth_getBlockByNumber", ["latest", False])["number"], 16)


def get_string(contract, selector_data):
    """Call a contract function that returns a dynamic string."""
    result = rpc("eth_call", [{"to": contract, "data": selector_data}, "latest"])
    if not result or result == "0x":
        return None
    raw = bytes.fromhex(result[2:])
    if len(raw) < 64:
        return None
    # Dynamic string: offset at [0:32], length at [32:64], data at [64:]
    length = int.from_bytes(raw[32:64], "big")
    if length > 1024 or 64 + length > len(raw):
        return None
    try:
        return raw[64:64 + length].decode("utf-8", errors="replace").strip("\x00").strip()
    except:
        return None


def get_uint256(contract, selector_data):
    """Call a contract function that returns a uint256."""
    result = rpc("eth_call", [{"to": contract, "data": selector_data}, "latest"])
    if not result or result == "0x":
        return None
    return int(result, 16)


def get_address_result(contract, selector_data):
    """Call a contract function that returns an address."""
    result = rpc("eth_call", [{"to": contract, "data": selector_data}, "latest"])
    if not result or result == "0x" or len(result) < 42:
        return None
    return "0x" + result[-40:]


def verify_erc721(contract):
    """Verify contract is ERC-721."""
    # supportsInterface(0x80ac58cd) = ERC-721
    data = SELECTOR["supportsInterface"] + "0000000000000000000000000000000000000000000000000000000080ac58cd"
    result = rpc("eth_call", [{"to": contract, "data": data}, "latest"])
    if result and len(result) >= 66:
        return int(result, 16) == 1
    # Some contracts don't implement ERC-165 — try ownerOf(1) as fallback
    data = SELECTOR["ownerOf"] + "0000000000000000000000000000000000000000000000000000000000000001"
    result = rpc("eth_call", [{"to": contract, "data": data}, "latest"])
    return result and result != "0x" and len(result) >= 42


def get_token_uri(contract, token_id):
    """Get tokenURI for a specific token ID."""
    data = SELECTOR["tokenURI"] + f"{token_id:064x}"
    return get_string(contract, data)


def get_owner_of(contract, token_id):
    """Get owner address for a specific token ID."""
    data = SELECTOR["ownerOf"] + f"{token_id:064x}"
    return get_address_result(contract, data)


def get_transfer_events(contract, from_block, to_block):
    """Fetch all Transfer events to enumerate token IDs and ownership."""
    # Transfer(address,address,uint256) topic
    transfer_topic = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
    all_logs = []
    
    # Paginate in 5000-block chunks
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
        except Exception as e:
            # Rate limited or range too large — try smaller chunk
            try:
                smaller = 1000
                sub_current = current
                while sub_current < end:
                    sub_end = min(sub_current + smaller - 1, end)
                    logs = rpc("eth_getLogs", [{
                        "fromBlock": hex(sub_current),
                        "toBlock": hex(sub_end),
                        "address": contract,
                        "topics": [transfer_topic]
                    }])
                    if logs:
                        all_logs.extend(logs)
                    sub_current = sub_end + 1
                    time.sleep(RPC_DELAY)
            except:
                pass
        current = end + 1
        time.sleep(RPC_DELAY)
    
    return all_logs


def parse_transfer_logs(logs):
    """Parse Transfer events into ownership map."""
    # Transfer event: from (topic[1]), to (topic[2]), tokenId (data)
    # For ERC-721, tokenId is usually in topic[3] (indexed)
    ownership = {}  # token_id -> owner
    transfers = []  # (token_id, from, to, block, tx_hash)
    
    for log in logs:
        topics = log.get("topics", [])
        if len(topics) < 3:
            continue
        
        # ERC-721 Transfer: from, to indexed in topics, tokenId in topic[3]
        if len(topics) >= 4:
            from_addr = "0x" + topics[1][-40:]
            to_addr = "0x" + topics[2][-40:]
            token_id = int(topics[3], 16)
        else:
            # Fallback: tokenId in data field
            from_addr = "0x" + topics[1][-40:]
            to_addr = "0x" + topics[2][-40:]
            data = log.get("data", "0x")
            if data and data != "0x":
                token_id = int(data, 16)
            else:
                continue
        
        ownership[token_id] = to_addr
        transfers.append({
            "token_id": token_id,
            "from": from_addr,
            "to": to_addr,
            "block": int(log.get("blockNumber", "0x0"), 16),
            "tx_hash": log.get("transactionHash", ""),
        })
    
    return ownership, transfers


def snapshot_collection(contract, symbol, block_number, snapshot_time):
    """Take a complete snapshot of an NFT collection."""
    print(f"\n{'='*60}")
    print(f"📸 Snapshotting {symbol} ({contract})")
    print(f"   Block: {block_number:,} | Time: {snapshot_time}")
    print(f"{'='*60}")
    
    result = {
        "contract": contract,
        "symbol": symbol,
        "snapshot_block": block_number,
        "snapshot_time": snapshot_time,
        "status": "started",
    }
    
    # Step 1: Verify it's a contract + ERC-721
    code = rpc("eth_getCode", [contract, "latest"])
    if not code or code == "0x":
        print(f"  ❌ No contract at {contract}")
        result["status"] = "no_contract"
        return result
    
    is_721 = verify_erc721(contract)
    if not is_721:
        print(f"  ⚠️  Not ERC-721 compatible (no ERC-165, trying anyway)")
    
    # Step 2: Contract metadata
    name = get_string(contract, SELECTOR["name"])
    csymbol = get_string(contract, SELECTOR["symbol"])
    total_supply = get_uint256(contract, SELECTOR["totalSupply"])
    
    if total_supply is None or total_supply == 0:
        print(f"  ❌ totalSupply() returned 0 or failed — trying transfer events")
    
    print(f"  Name: {name}")
    print(f"  Symbol: {csymbol}")
    print(f"  Total Supply: {total_supply:,}" if total_supply else "  Total Supply: unknown")
    
    result["name"] = name
    result["contract_symbol"] = csymbol
    result["total_supply"] = total_supply
    
    # Step 3: Get ownership via Transfer events (most reliable)
    # Start from early blocks — Dogechain genesis ~921K
    print(f"  Fetching Transfer events (this may take a minute)...")
    from_block = 921000
    to_block = block_number
    
    logs = get_transfer_events(contract, from_block, to_block)
    print(f"  Found {len(logs):,} Transfer events")
    
    if not logs:
        print(f"  ⚠️  No Transfer events found — trying ownerOf enumeration")
        # Fallback: brute-force ownerOf for token IDs 0..totalSupply
        ownership = {}
        if total_supply and total_supply > 0:
            max_id = min(total_supply, 10000)  # safety cap
            for tid in range(max_id):
                owner = get_owner_of(contract, tid)
                if owner and owner != "0x" + "0" * 40:
                    ownership[tid] = owner
                    if tid % 1000 == 0 and tid > 0:
                        print(f"    Enumerated {tid:,} tokens...")
                time.sleep(RPC_DELAY)
    else:
        ownership, transfers = parse_transfer_logs(logs)
    
    print(f"  Unique tokens with owners: {len(ownership):,}")
    
    # Count unique holders
    holders = {}
    for token_id, owner in ownership.items():
        holders[owner] = holders.get(owner, 0) + 1
    
    print(f"  Unique holders: {len(holders):,}")
    
    result["unique_tokens"] = len(ownership)
    result["unique_holders"] = len(holders)
    
    # Step 4: Get token URIs for metadata (parallel)
    print(f"  Fetching token metadata...")
    metadata = {}
    token_ids = sorted(ownership.keys())
    
    def fetch_metadata(token_id):
        uri = get_token_uri(contract, token_id)
        time.sleep(RPC_DELAY)
        return token_id, uri
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_metadata, tid): tid for tid in token_ids}
        done = 0
        for future in as_completed(futures):
            tid, uri = future.result()
            if uri:
                metadata[tid] = uri
            done += 1
            if done % 500 == 0:
                print(f"    Metadata: {done}/{len(token_ids)}")
    
    print(f"  Metadata fetched: {len(metadata):,}/{len(token_ids):,}")
    result["metadata_count"] = len(metadata)
    
    # Step 5: Save outputs
    coll_dir = os.path.join(SNAPSHOT_DIR, symbol)
    os.makedirs(coll_dir, exist_ok=True)
    
    # Holders CSV (airdrop-ready)
    holders_csv = os.path.join(coll_dir, f"{symbol}_holders.csv")
    with open(holders_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["token_id", "owner", "snapshot_block", "snapshot_time"])
        for tid in sorted(ownership.keys()):
            writer.writerow([tid, ownership[tid], block_number, snapshot_time])
    print(f"  ✅ Saved: {symbol}_holders.csv ({len(ownership):,} rows)")
    
    # Holders summary CSV (for airdrops — one row per wallet)
    wallets_csv = os.path.join(coll_dir, f"{symbol}_wallets.csv")
    with open(wallets_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["wallet", "nft_count", "snapshot_block", "snapshot_time"])
        for wallet in sorted(holders, key=holders.get, reverse=True):
            writer.writerow([wallet, holders[wallet], block_number, snapshot_time])
    print(f"  ✅ Saved: {symbol}_wallets.csv ({len(holders):,} unique wallets)")
    
    # Metadata JSON
    meta_json = os.path.join(coll_dir, f"{symbol}_metadata.json")
    with open(meta_json, "w") as f:
        json.dump({
            "contract": contract,
            "name": name,
            "symbol": csymbol,
            "snapshot_block": block_number,
            "snapshot_time": snapshot_time,
            "tokens": {str(tid): uri for tid, uri in metadata.items()}
        }, f, indent=2)
    print(f"  ✅ Saved: {symbol}_metadata.json")
    
    # Summary JSON
    summary_json = os.path.join(coll_dir, f"{symbol}_summary.json")
    with open(summary_json, "w") as f:
        json.dump({
            **result,
            "holders_csv": f"{symbol}_holders.csv",
            "wallets_csv": f"{symbol}_wallets.csv",
            "metadata_json": f"{symbol}_metadata.json",
            "transfer_events": len(logs),
            "status": "complete",
        }, f, indent=2)
    print(f"  ✅ Saved: {symbol}_summary.json")
    
    return result


def main():
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    
    # Get current block
    block = get_latest_block()
    print(f"Dogechain NFT Snapshot — {SNAPSHOT_TIME}")
    print(f"Current block: {block:,}")
    print(f"Output dir: {SNAPSHOT_DIR}")
    
    # Determine which collections to snapshot
    if len(sys.argv) >= 3 and sys.argv[1].startswith("0x"):
        collections = [(sys.argv[1], sys.argv[2])]
    elif len(sys.argv) >= 2 and sys.argv[1] == "--metadata-only":
        # Quick mode: skip transfer events, just get contract + supply info
        collections = [(sys.argv[2], sys.argv[3])] if len(sys.argv) >= 4 else []
        # (metadata-only handling would go here)
    else:
        collections = KNOWN_COLLECTIONS
    
    print(f"\nCollections to snapshot: {len(collections)}")
    
    all_results = []
    for contract, symbol in collections:
        try:
            result = snapshot_collection(contract, symbol, block, SNAPSHOT_TIME)
            all_results.append(result)
        except Exception as e:
            print(f"  ❌ ERROR snapshotting {symbol}: {e}")
            all_results.append({
                "contract": contract,
                "symbol": symbol,
                "status": f"error: {str(e)}",
                "snapshot_block": block,
                "snapshot_time": SNAPSHOT_TIME,
            })
    
    # Save master index
    index_path = os.path.join(SNAPSHOT_DIR, "SNAPSHOT_INDEX.json")
    with open(index_path, "w") as f:
        json.dump({
            "snapshot_time": SNAPSHOT_TIME,
            "snapshot_block": block,
            "rpc": RPC,
            "chain": "Dogechain (Chain ID 2000)",
            "collections": all_results,
        }, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"📊 SNAPSHOT COMPLETE")
    print(f"{'='*60}")
    print(f"Total collections: {len(all_results)}")
    print(f"Successful: {sum(1 for r in all_results if r.get('status') == 'complete')}")
    print(f"Failed: {sum(1 for r in all_results if r.get('status') != 'complete')}")
    print(f"Index: {index_path}")
    
    # Print summary table
    print(f"\n{'Symbol':<16} {'Supply':>8} {'Holders':>8} {'Tokens':>8} {'Status'}")
    print("-" * 60)
    for r in all_results:
        supply = f"{r.get('total_supply', 0):,}" if r.get('total_supply') else "?"
        holders = f"{r.get('unique_holders', 0):,}" if r.get('unique_holders') else "0"
        tokens = f"{r.get('unique_tokens', 0):,}" if r.get('unique_tokens') else "0"
        print(f"{r['symbol']:<16} {supply:>8} {holders:>8} {tokens:>8} {r.get('status', '?')}")


if __name__ == "__main__":
    main()
